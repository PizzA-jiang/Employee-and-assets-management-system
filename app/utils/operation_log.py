from sqlalchemy.orm import Session
from app.models import OperationLog


def log_operation(
    db: Session,
    user_id: int,
    action: str,
    target_type: str,
    target_id: int,
    target_name: str = None,
    detail: str = None,
    ip_address: str = None,
):
    """记录操作日志"""
    log = OperationLog(
        user_id=user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        target_name=target_name,
        detail=detail,
        ip_address=ip_address,
    )
    db.add(log)
    db.commit()
