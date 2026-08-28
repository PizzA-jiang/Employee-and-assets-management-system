import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, Body
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc, or_
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.models import User, UserRole, CloudFile, FileShare
from app.schemas import FileShareCreate
from app.dependencies import get_current_user, get_current_admin
from app.utils.operation_log import log_operation

router = APIRouter(prefix="/cloud-files", tags=["云盘"])

FILE_DIR = Path("file")
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".pdf", 
                      ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".zip", ".rar"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


def get_user_folder_name(user: User) -> str:
    """获取用户的文件夹名"""
    if user.role == UserRole.ADMIN:
        return "admin"
    
    folder_name = user.username
    if any('\u4e00' <= c <= '\u9fff' for c in folder_name):
        try:
            from pypinyin import lazy_pinyin
            folder_name = ''.join(lazy_pinyin(folder_name))
        except ImportError:
            pass
    
    folder_name = re.sub(r'[^\w\-]', '', folder_name)
    return folder_name if folder_name else str(user.id)


def get_user_upload_dir(user: User) -> Path:
    """获取用户的上传目录"""
    folder_name = get_user_folder_name(user)
    upload_dir = FILE_DIR / folder_name
    upload_dir.mkdir(parents=True, exist_ok=True)
    return upload_dir


class CloudFileResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    mime_type: Optional[str] = None
    is_public: int = 0
    user_id: int
    owner_name: Optional[str] = None
    is_shared: bool = False
    shared_by: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CloudFilePageResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[CloudFileResponse]


@router.post("/upload", response_model=CloudFileResponse)
async def upload_file(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    
    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制(50MB)")
    
    stored_name = f"{uuid.uuid4().hex}{ext}"
    upload_dir = get_user_upload_dir(current_user)
    file_path = upload_dir / stored_name
    
    with open(file_path, "wb") as f:
        f.write(content)
    
    cloud_file = CloudFile(
        user_id=current_user.id,
        filename=file.filename,
        stored_name=stored_name,
        file_path=str(file_path),
        file_size=len(content),
        mime_type=file.content_type,
    )
    db.add(cloud_file)
    db.commit()
    db.refresh(cloud_file)
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="upload",
        target_type="file",
        target_id=cloud_file.id,
        target_name=cloud_file.filename,
    )
    
    return CloudFileResponse(
        id=cloud_file.id,
        filename=cloud_file.filename,
        file_size=cloud_file.file_size,
        mime_type=cloud_file.mime_type,
        is_public=cloud_file.is_public,
        user_id=cloud_file.user_id,
        owner_name=current_user.username,
        created_at=cloud_file.created_at,
    )


@router.get("", response_model=CloudFilePageResponse)
def list_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role == UserRole.ADMIN:
        query = db.query(CloudFile).options(joinedload(CloudFile.owner)).filter(
            CloudFile.user_id == current_user.id
        )
    else:
        shared_file_ids = db.query(FileShare.file_id).filter(
            FileShare.shared_to_id == current_user.id
        ).subquery()
        
        query = db.query(CloudFile).options(joinedload(CloudFile.owner)).filter(
            or_(
                CloudFile.user_id == current_user.id,
                CloudFile.id.in_(shared_file_ids),
            )
        )
    
    if keyword:
        query = query.filter(CloudFile.filename.contains(keyword))
    
    total = query.count()
    items = query.order_by(desc(CloudFile.created_at)).offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size
    
    result = []
    for f in items:
        is_shared = f.user_id != current_user.id
        shared_by_name = None
        if is_shared:
            share_record = db.query(FileShare).filter(
                FileShare.file_id == f.id,
                FileShare.shared_to_id == current_user.id,
            ).first()
            if share_record:
                shared_by_user = db.query(User).filter(User.id == share_record.shared_by_id).first()
                shared_by_name = shared_by_user.username if shared_by_user else None
        
        result.append(CloudFileResponse(
            id=f.id,
            filename=f.filename,
            file_size=f.file_size,
            mime_type=f.mime_type,
            is_public=f.is_public,
            user_id=f.user_id,
            owner_name=f.owner.username if f.owner else None,
            is_shared=is_shared,
            shared_by=shared_by_name,
            created_at=f.created_at,
        ))
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": result,
    }


@router.get("/{file_id}/download")
def download_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if cloud_file.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        share = db.query(FileShare).filter(
            FileShare.file_id == file_id,
            FileShare.shared_to_id == current_user.id,
        ).first()
        if not share:
            raise HTTPException(status_code=403, detail="无权访问此文件")
    
    if not os.path.exists(cloud_file.file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="download",
        target_type="file",
        target_id=cloud_file.id,
        target_name=cloud_file.filename,
    )
    
    return FileResponse(
        path=cloud_file.file_path,
        filename=cloud_file.filename,
        media_type=cloud_file.mime_type or "application/octet-stream",
    )


@router.delete("/{file_id}")
def delete_file(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if cloud_file.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权删除此文件")
    
    if os.path.exists(cloud_file.file_path):
        os.remove(cloud_file.file_path)
    
    db.query(FileShare).filter(FileShare.file_id == file_id).delete()
    db.delete(cloud_file)
    db.commit()
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="delete",
        target_type="file",
        target_id=file_id,
        target_name=cloud_file.filename,
    )
    
    return {"message": "删除成功"}


@router.post("/{file_id}/share")
def share_file(
    file_id: int,
    share_in: FileShareCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")
    
    if cloud_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能共享自己的文件")
    
    for user_id in share_in.user_ids:
        existing = db.query(FileShare).filter(
            FileShare.file_id == file_id,
            FileShare.shared_to_id == user_id,
        ).first()
        if not existing:
            share = FileShare(
                file_id=file_id,
                shared_to_id=user_id,
                shared_by_id=current_user.id,
            )
            db.add(share)
    
    db.commit()
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="share",
        target_type="file",
        target_id=file_id,
        target_name=cloud_file.filename,
        detail=f"共享给用户: {share_in.user_ids}",
    )
    
    return {"message": "共享成功"}


@router.get("/shared")
def list_shared_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(FileShare).options(
        joinedload(FileShare.file),
        joinedload(FileShare.shared_by),
    ).filter(FileShare.shared_to_id == current_user.id)
    
    total = query.count()
    shares = query.order_by(desc(FileShare.created_at)).offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size
    
    result = []
    for share in shares:
        if share.file:
            result.append(CloudFileResponse(
                id=share.file.id,
                filename=share.file.filename,
                file_size=share.file.file_size,
                mime_type=share.file.mime_type,
                is_public=share.file.is_public,
                user_id=share.file.user_id,
                owner_name=share.file.owner.username if share.file.owner else None,
                is_shared=True,
                shared_by=share.shared_by.username if share.shared_by else None,
                created_at=share.file.created_at,
            ))
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": result,
    }
