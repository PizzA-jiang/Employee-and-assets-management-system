from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from pydantic import BaseModel, ConfigDict

from app.database import get_db
from app.models import User, OperationLog
from app.dependencies import get_current_user, get_current_admin

router = APIRouter(prefix="/operation-logs", tags=["操作日志"])


class OperationLogResponse(BaseModel):
    id: int
    user_id: int
    action: str
    target_type: str
    target_id: int
    target_name: Optional[str] = None
    detail: Optional[str] = None
    ip_address: Optional[str] = None
    created_at: Optional[datetime] = None
    username: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class OperationLogPageResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int
    items: List[OperationLogResponse]


@router.get("", response_model=OperationLogPageResponse)
def list_operation_logs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    action: str = None,
    target_type: str = None,
    user_id: int = None,
    start_date: datetime = None,
    end_date: datetime = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    query = db.query(OperationLog).options(joinedload(OperationLog.user))
    
    if action:
        query = query.filter(OperationLog.action == action)
    if target_type:
        query = query.filter(OperationLog.target_type == target_type)
    if user_id:
        query = query.filter(OperationLog.user_id == user_id)
    if start_date:
        query = query.filter(OperationLog.created_at >= start_date)
    if end_date:
        query = query.filter(OperationLog.created_at <= end_date)
    
    total = query.count()
    items = query.order_by(desc(OperationLog.created_at)).offset((page - 1) * size).limit(size).all()
    pages = (total + size - 1) // size
    
    result = []
    for log in items:
        result.append(OperationLogResponse(
            id=log.id,
            user_id=log.user_id,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            target_name=log.target_name,
            detail=log.detail,
            ip_address=log.ip_address,
            created_at=log.created_at,
            username=log.user.username if log.user else None,
        ))
    
    return {
        "total": total,
        "page": page,
        "size": size,
        "pages": pages,
        "items": result,
    }
