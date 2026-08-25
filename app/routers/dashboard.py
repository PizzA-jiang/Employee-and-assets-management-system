from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database import get_db
from app.schemas import DashboardStats
from app.crud import get_dashboard_stats
from app.dependencies import get_current_user
from app.models import User, UserRole, Asset, AssetStatus, Employee, AssetLog, LogAction

router = APIRouter(prefix="/dashboard", tags=["数据看板"])


@router.get("/stats", response_model=DashboardStats)
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_dashboard_stats(db)


@router.get("/charts/assets-by-type")
def get_assets_by_type(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = db.query(Asset.asset_type, func.count(Asset.id)).group_by(Asset.asset_type).all()
    return [{"type": r[0].value, "count": r[1]} for r in results]


@router.get("/charts/assets-by-status")
def get_assets_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = db.query(Asset.status, func.count(Asset.id)).group_by(Asset.status).all()
    return [{"status": r[0].value, "count": r[1]} for r in results]


@router.get("/charts/logs-by-action")
def get_logs_by_action(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = db.query(AssetLog.action, func.count(AssetLog.id)).group_by(AssetLog.action).all()
    return [{"action": r[0].value, "count": r[1]} for r in results]


@router.get("/charts/employees-by-department")
def get_employees_by_department(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = db.query(Employee.department, func.count(Employee.id)).filter(
        Employee.status == 1
    ).group_by(Employee.department).all()
    return [{"department": r[0] or "未分类", "count": r[1]} for r in results]


@router.get("/charts/monthly-checkouts")
def get_monthly_checkouts(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from sqlalchemy import extract
    results = db.query(
        extract('month', AssetLog.created_at).label('month'),
        func.count(AssetLog.id)
    ).filter(AssetLog.action == LogAction.CHECKOUT).group_by('month').all()
    return [{"month": int(r[0]), "count": r[1]} for r in results]