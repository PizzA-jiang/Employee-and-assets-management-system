import uuid
import logging
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Query, BackgroundTasks
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc

from app.database import get_db
from app.models import User, UserRole, KnowledgeDocument, KnowledgeChunk, DocStatus, EmbeddingStatus
from app.schemas import (
    KnowledgeDocumentResponse, KnowledgeDocumentPageResponse,
    KnowledgeDocumentUpdate, KnowledgeChunkResponse, KnowledgeChunkPageResponse,
    KnowledgeSearchRequest, KnowledgeSearchResponse, KnowledgeSearchResult,
)
from app.dependencies import get_current_user, get_current_admin
from app.utils.operation_log import log_operation
from app.utils.file_storage import save_knowledge_file, delete_knowledge_file
from app.utils.response import R
from app.services.file_parser import parse_file, detect_file_type
from app.services.text_chunker import chunk_text
from app.services.vector_store import vector_store
from app import crud

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/knowledge", tags=["知识库"])

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024


def _process_document(doc_id: int, file_path: str, file_type: str):
    from app.database import SessionLocal
    db = SessionLocal()
    try:
        doc = crud.get_knowledge_document(db, doc_id)
        if not doc:
            return

        try:
            from app.models import FileType
            ft = FileType(file_type)
            text = parse_file(file_path, ft)
            chunks = chunk_text(text)

            db_chunks = []
            if chunks:
                db_chunks = crud.create_knowledge_chunks(db, doc_id, chunks)

            # 向量化: 生成嵌入并存入 ChromaDB
            embedding_success = 0
            if db_chunks:
                ok = vector_store.add_chunks(
                    chunk_ids=[c.id for c in db_chunks],
                    documents=[c.content for c in db_chunks],
                    metadatas=[
                        {"document_id": doc_id, "document_title": doc.title}
                        for c in db_chunks
                    ],
                )
                if ok:
                    embedding_success = len(db_chunks)
                    for c in db_chunks:
                        c.embedding_status = EmbeddingStatus.DONE
                    logger.info(f"Document {doc_id}: {embedding_success} chunks vectorized")
                else:
                    logger.warning(f"Document {doc_id}: vectorization failed, chunks remain PENDING")

            crud.update_knowledge_document_status(
                db, doc_id, DocStatus.SUCCESS, chunk_count=len(chunks)
            )

            log_operation(
                db=db,
                user_id=doc.created_by,
                action="process",
                target_type="knowledge_document",
                target_id=doc_id,
                target_name=doc.title,
                detail=f"文档处理完成，共{len(chunks)}个分块，向量化成功{embedding_success}个",
            )

            db.commit()
        except Exception as e:
            logger.exception(f"Failed to process document {doc_id}")
            crud.update_knowledge_document_status(
                db, doc_id, DocStatus.FAILED, error_message=str(e)
            )
            db.commit()
    finally:
        db.close()


@router.post("/upload", response_model=KnowledgeDocumentResponse)
async def upload_document(
    file: UploadFile = File(...),
    title: Optional[str] = Query(None, max_length=255),
    background_tasks: BackgroundTasks = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    ext = Path(file.filename).suffix.lower()
    file_type = detect_file_type(file.filename)
    if ext not in ALLOWED_EXTENSIONS or not file_type:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="文件大小超过限制(50MB)")

    stored_name = f"{uuid.uuid4().hex}{ext}"
    file_path_str = save_knowledge_file(stored_name, content)

    doc_title = title or Path(file.filename).stem

    doc = crud.create_knowledge_document(
        db=db,
        title=doc_title,
        filename=file.filename,
        stored_name=stored_name,
        file_path=file_path_str,
        file_size=len(content),
        mime_type=file.content_type,
        file_type=file_type,
        created_by=current_user.id,
    )

    log_operation(
        db=db,
        user_id=current_user.id,
        action="upload",
        target_type="knowledge_document",
        target_id=doc.id,
        target_name=doc.title,
    )

    db.commit()
    db.refresh(doc)

    if background_tasks:
        background_tasks.add_task(
            _process_document, doc.id, file_path_str, file_type.value
        )

    return R.ok(
        data=KnowledgeDocumentResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            file_type=doc.file_type,
            status=doc.status,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_by=doc.created_by,
            creator_name=current_user.username,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        ),
        message="上传成功",
    )


@router.get("/documents", response_model=KnowledgeDocumentPageResponse)
def list_documents(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    keyword: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    items, total = crud.get_knowledge_documents(db, page, size, keyword)
    pages = (total + size - 1) // size

    result = []
    for doc in items:
        result.append(KnowledgeDocumentResponse(
            id=doc.id,
            title=doc.title,
            filename=doc.filename,
            file_size=doc.file_size,
            mime_type=doc.mime_type,
            file_type=doc.file_type,
            status=doc.status,
            chunk_count=doc.chunk_count,
            error_message=doc.error_message,
            created_by=doc.created_by,
            creator_name=doc.owner.username if doc.owner else None,
            created_at=doc.created_at,
            updated_at=doc.updated_at,
        ))

    return {"total": total, "page": page, "size": size, "pages": pages, "items": result}


@router.get("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
def get_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doc = crud.get_knowledge_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    return KnowledgeDocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_by=doc.created_by,
        creator_name=doc.owner.username if doc.owner else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.put("/documents/{doc_id}", response_model=KnowledgeDocumentResponse)
def update_document(
    doc_id: int,
    data: KnowledgeDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doc = crud.get_knowledge_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    if data.title is not None:
        doc = crud.update_knowledge_document_title(db, doc_id, data.title)

    log_operation(
        db=db,
        user_id=current_user.id,
        action="update",
        target_type="knowledge_document",
        target_id=doc_id,
        target_name=doc.title,
    )

    db.commit()
    db.refresh(doc)

    return KnowledgeDocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_by=doc.created_by,
        creator_name=doc.owner.username if doc.owner else None,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.delete("/documents/{doc_id}")
def delete_document(
    doc_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doc = crud.get_knowledge_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    delete_knowledge_file(doc.file_path)
    vector_store.delete_document(doc_id)
    crud.delete_knowledge_document(db, doc_id)

    log_operation(
        db=db,
        user_id=current_user.id,
        action="delete",
        target_type="knowledge_document",
        target_id=doc_id,
        target_name=doc.filename,
    )

    db.commit()

    return {"message": "删除成功"}


@router.get("/documents/{doc_id}/chunks", response_model=KnowledgeChunkPageResponse)
def list_chunks(
    doc_id: int,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doc = crud.get_knowledge_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    items, total = crud.get_knowledge_chunks(db, doc_id, page, size)
    pages = (total + size - 1) // size

    result = []
    for chunk in items:
        result.append(KnowledgeChunkResponse(
            id=chunk.id,
            document_id=chunk.document_id,
            chunk_index=chunk.chunk_index,
            content=chunk.content,
            token_count=chunk.token_count,
            metadata_json=chunk.metadata_json,
            embedding_status=chunk.embedding_status,
            created_at=chunk.created_at,
        ))

    return {"total": total, "page": page, "size": size, "pages": pages, "items": result}


@router.post("/documents/{doc_id}/reprocess", response_model=KnowledgeDocumentResponse)
def reprocess_document(
    doc_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    doc = crud.get_knowledge_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    vector_store.delete_document(doc_id)
    crud.delete_knowledge_chunks_by_document(db, doc_id)
    crud.update_knowledge_document_status(db, doc_id, DocStatus.PROCESSING, chunk_count=0)

    log_operation(
        db=db,
        user_id=current_user.id,
        action="reprocess",
        target_type="knowledge_document",
        target_id=doc_id,
        target_name=doc.title,
    )

    db.commit()
    db.refresh(doc)

    background_tasks.add_task(
        _process_document, doc.id, doc.file_path, doc.file_type.value
    )

    return KnowledgeDocumentResponse(
        id=doc.id,
        title=doc.title,
        filename=doc.filename,
        file_size=doc.file_size,
        mime_type=doc.mime_type,
        file_type=doc.file_type,
        status=doc.status,
        chunk_count=doc.chunk_count,
        error_message=doc.error_message,
        created_by=doc.created_by,
        creator_name=current_user.username,
        created_at=doc.created_at,
        updated_at=doc.updated_at,
    )


@router.post("/search", response_model=KnowledgeSearchResponse)
def search_knowledge(
    data: KnowledgeSearchRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = vector_store.search_by_text(
        query_text=data.query,
        top_k=data.top_k,
    )

    search_results = []
    for r in results:
        search_results.append(KnowledgeSearchResult(
            chunk_id=r.chunk_id,
            document_id=r.document_id,
            document_title=r.document_title,
            content=r.content,
            score=r.score,
        ))

    return KnowledgeSearchResponse(query=data.query, results=search_results)
