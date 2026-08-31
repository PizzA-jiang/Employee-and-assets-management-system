import os
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
from app.utils.file_storage import (
    save_private_file,
    copy_file_to_share,
    delete_file,
    delete_share_dir,
)

router = APIRouter(prefix="/cloud-files", tags=["云盘"])

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".pdf",
                      ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".zip", ".rar"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


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
    shared_to_names: Optional[List[str]] = None
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
    file_path_str = save_private_file(current_user.id, stored_name, content)

    cloud_file = CloudFile(
        user_id=current_user.id,
        filename=file.filename,
        stored_name=stored_name,
        file_path=file_path_str,
        file_size=len(content),
        mime_type=file.content_type,
    )
    db.add(cloud_file)
    db.flush()
    db.refresh(cloud_file)

    log_operation(
        db=db,
        user_id=current_user.id,
        action="upload",
        target_type="file",
        target_id=cloud_file.id,
        target_name=cloud_file.filename,
    )

    db.commit()

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
        query = db.query(CloudFile).options(
            joinedload(CloudFile.owner),
            joinedload(CloudFile.shares).joinedload(FileShare.shared_to),
        ).filter(
            CloudFile.user_id == current_user.id
        )
    else:
        shared_file_ids = db.query(FileShare.file_id).filter(
            FileShare.shared_to_id == current_user.id
        ).subquery()

        query = db.query(CloudFile).options(
            joinedload(CloudFile.owner),
            joinedload(CloudFile.shares).joinedload(FileShare.shared_to),
        ).filter(
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
        shared_to_names = None

        if not is_shared:
            shared_to_names = [
                s.shared_to.username for s in f.shares if s.shared_to
            ]
        else:
            share_record = next(
                (s for s in f.shares if s.shared_to_id == current_user.id), None
            )
            if share_record:
                shared_by_name = share_record.shared_by.username if share_record.shared_by else None

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
            shared_to_names=shared_to_names,
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

    is_owner = (cloud_file.user_id == current_user.id)

    share_record = None
    if not is_owner:
        share_record = db.query(FileShare).filter(
            FileShare.file_id == file_id,
            FileShare.shared_to_id == current_user.id,
        ).first()
        if not share_record:
            raise HTTPException(status_code=403, detail="无权访问此文件")

    if is_owner:
        download_path = cloud_file.file_path
    else:
        download_path = f"file/share/{share_record.id}/{cloud_file.stored_name}"

    if not os.path.exists(download_path):
        raise HTTPException(status_code=404, detail="文件不存在(可能已被删除)")

    log_operation(
        db=db,
        user_id=current_user.id,
        action="download",
        target_type="file",
        target_id=cloud_file.id,
        target_name=cloud_file.filename,
    )

    db.commit()

    return FileResponse(
        path=download_path,
        filename=cloud_file.filename,
        media_type=cloud_file.mime_type or "application/octet-stream",
    )


@router.delete("/{file_id}")
def delete_file_endpoint(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    if cloud_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="无权删除此文件")

    shares = db.query(FileShare).filter(FileShare.file_id == file_id).all()
    for share in shares:
        delete_share_dir(share.id)

    delete_file(cloud_file.file_path)

    db.query(FileShare).filter(FileShare.file_id == file_id).delete()
    db.delete(cloud_file)
    db.flush()

    log_operation(
        db=db,
        user_id=current_user.id,
        action="delete",
        target_type="file",
        target_id=file_id,
        target_name=cloud_file.filename,
    )

    db.commit()

    return {"message": "删除成功"}


@router.post("/{file_id}/share")
def share_file(
    file_id: int,
    share_in: FileShareCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    if cloud_file.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="只能共享自己的文件")

    for user_id in share_in.user_ids:
        if user_id == current_user.id:
            continue

        target_user = db.query(User).filter(User.id == user_id).first()
        if not target_user:
            continue

        existing = db.query(FileShare).filter(
            FileShare.file_id == file_id,
            FileShare.shared_to_id == user_id,
        ).first()
        if existing:
            continue

        share = FileShare(
            file_id=file_id,
            shared_to_id=user_id,
            shared_by_id=current_user.id,
        )
        db.add(share)
        db.flush()

        copy_file_to_share(
            source_path=cloud_file.file_path,
            share_id=share.id,
            stored_name=cloud_file.stored_name,
        )

    db.flush()

    log_operation(
        db=db,
        user_id=current_user.id,
        action="share",
        target_type="file",
        target_id=file_id,
        target_name=cloud_file.filename,
        detail=f"共享给用户: {share_in.user_ids}",
    )

    db.commit()

    return {"message": "共享成功"}


@router.delete("/{file_id}/share/{share_id}")
def cancel_share(
    file_id: int,
    share_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    share = db.query(FileShare).filter(
        FileShare.id == share_id,
        FileShare.file_id == file_id,
    ).first()
    if not share:
        raise HTTPException(status_code=404, detail="共享记录不存在")

    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()

    if cloud_file.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权取消共享")

    delete_share_dir(share_id)

    db.delete(share)
    db.flush()

    log_operation(
        db=db,
        user_id=current_user.id,
        action="cancel_share",
        target_type="file",
        target_id=file_id,
        target_name=cloud_file.filename,
        detail=f"取消共享给用户: {share.shared_to_id}",
    )

    db.commit()

    return {"message": "取消共享成功"}


@router.get("/shared")
def list_shared_files(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(FileShare).options(
        joinedload(FileShare.file).joinedload(CloudFile.owner),
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


@router.get("/{file_id}/shares")
def list_file_shares(
    file_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    cloud_file = db.query(CloudFile).filter(CloudFile.id == file_id).first()
    if not cloud_file:
        raise HTTPException(status_code=404, detail="文件不存在")

    if cloud_file.user_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="无权查看此文件的共享情况")

    shares = db.query(FileShare).options(
        joinedload(FileShare.shared_to),
        joinedload(FileShare.shared_by),
    ).filter(FileShare.file_id == file_id).all()

    result = []
    for s in shares:
        result.append({
            "share_id": s.id,
            "shared_to_id": s.shared_to_id,
            "shared_to_name": s.shared_to.username if s.shared_to else None,
            "shared_by_name": s.shared_by.username if s.shared_by else None,
            "created_at": s.created_at.isoformat() if s.created_at else None,
        })

    return {"file_id": file_id, "shares": result}
