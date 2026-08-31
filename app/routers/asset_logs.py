from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session,joinedload
from app.database import get_db
from app.schemas import (
    AssetLogCreate, AssetLogResponse, AssetLogWithDetails,
    AssetLogPageResponse, PageParams,
)
from app.crud import (
    get_asset_log, get_asset_logs, create_asset_log,
    get_asset, get_employee,
)
from app.dependencies import get_current_user, get_current_admin
from app.models import User, UserRole, AssetStatus, LogAction,AssetLog,Employee

router = APIRouter(prefix="/asset-logs", tags=["资产流转记录"])


@router.post("", response_model=AssetLogResponse, status_code=status.HTTP_201_CREATED)
def create_asset_log_api(
    log_in: AssetLogCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify asset exists
    asset = get_asset(db, log_in.asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    # Verify employee exists
    employee = get_employee(db, log_in.employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    # Business logic validation
    if log_in.action == LogAction.CHECKOUT:
        if asset.status != AssetStatus.AVAILABLE:
            raise HTTPException(status_code=400, detail="资产当前不可领用")
        # Check if employee already has this type of asset
        pass
    elif log_in.action == LogAction.RETURN:
        if asset.status != AssetStatus.IN_USE:
            raise HTTPException(status_code=400, detail="资产当前不在使用中")
        # Verify the employee is the one who checked out
        last_log = db.query(AssetLog).filter(
            AssetLog.asset_id == log_in.asset_id,
            AssetLog.action == LogAction.CHECKOUT
        ).order_by(AssetLog.created_at.desc()).first()
        if last_log and last_log.employee_id != log_in.employee_id:
            raise HTTPException(status_code=400, detail="归还人与领用人不一致")
    elif log_in.action == LogAction.MAINTENANCE_IN:
        if asset.status not in [AssetStatus.AVAILABLE, AssetStatus.IN_USE]:
            raise HTTPException(status_code=400, detail="资产状态不允许送修")
    elif log_in.action == LogAction.MAINTENANCE_OUT:
        if asset.status != AssetStatus.MAINTENANCE:
            raise HTTPException(status_code=400, detail="资产不在维修中")
    elif log_in.action == LogAction.SCRAP:
        if asset.status == AssetStatus.SCRAPPED:
            raise HTTPException(status_code=400, detail="资产已报废")
    
    log = create_asset_log(db, log_in, current_user.id)
    db.commit()
    db.refresh(log)
    return log


@router.get("", response_model=AssetLogPageResponse)
def list_asset_logs(
    params: PageParams = Depends(),
    asset_id: int = None,
    employee_id: int = None,
    action: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 普通员工只能看自己的记录
    if current_user.role != UserRole.ADMIN:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if employee:
            employee_id = employee.id
        else:
            employee_id = -1  # No records
    
    items, total = get_asset_logs(db, params, asset_id, employee_id, action)
    pages = (total + params.size - 1) // params.size
    return {
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
        "items": items,
    }


@router.get("/asset/{asset_id}", response_model=AssetLogPageResponse)
def get_asset_history(
    asset_id: int,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    
    items, total = get_asset_logs(db, params, asset_id=asset_id)
    pages = (total + params.size - 1) // params.size
    return {
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
        "items": items,
    }


@router.get("/employee/{employee_id}", response_model=AssetLogPageResponse)
def get_employee_assets(
    employee_id: int,
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # 普通员工只能看自己的
    if current_user.role != UserRole.ADMIN:
        employee = db.query(Employee).filter(
            Employee.user_id == current_user.id
        ).first()
        if not employee or employee.id != employee_id:
            raise HTTPException(status_code=403, detail="权限不足")
    
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    items, total = get_asset_logs(db, params, employee_id=employee_id)
    pages = (total + params.size - 1) // params.size
    return {
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
        "items": items,
    }


@router.get("/{log_id}", response_model=AssetLogWithDetails)
def get_asset_log_detail(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    log = get_asset_log(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="记录不存在")
    return log


# 导出流转记录
@router.get("/export/excel")
def export_asset_logs(
    asset_id: int = None,
    employee_id: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from fastapi.responses import StreamingResponse
    import io
    import openpyxl
    
    query = db.query(AssetLog).options(
        joinedload(AssetLog.asset),
        joinedload(AssetLog.employee)
    )
    
    if asset_id:
        query = query.filter(AssetLog.asset_id == asset_id)
    if employee_id:
        query = query.filter(AssetLog.employee_id == employee_id)
    
    logs = query.order_by(AssetLog.created_at.desc()).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产流转记录"
    
    headers = ["记录ID", "资产编号", "资产名称", "员工工号", "员工姓名", "操作类型", 
               "操作人", "备注", "操作时间"]
    ws.append(headers)
    
    for log in logs:
        ws.append([
            log.id,
            log.asset.asset_no if log.asset else "",
            log.asset.name if log.asset else "",
            log.employee.employee_no if log.employee else "",
            log.employee.name if log.employee else "",
            log.action.value,
            log.operator_id,
            log.remark or "",
            log.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=asset_logs_export.xlsx"},
    )