from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    AssetCreate, AssetUpdate, AssetResponse,
    AssetPageResponse, PageParams,
)
from app.crud import (
    get_asset, get_asset_by_no, get_asset_by_serial, get_assets,
    create_asset, update_asset, delete_asset,
)
from app.dependencies import get_current_user, get_current_admin
from app.models import User, UserRole, AssetStatus

router = APIRouter(prefix="/assets", tags=["资产管理"])


@router.post("", response_model=AssetResponse, status_code=status.HTTP_201_CREATED)
def create_asset_api(
    asset_in: AssetCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if get_asset_by_no(db, asset_in.asset_no):
        raise HTTPException(status_code=400, detail="资产编号已存在")
    if asset_in.serial_number and get_asset_by_serial(db, asset_in.serial_number):
        raise HTTPException(status_code=400, detail="序列号已存在")
    asset = create_asset(db, asset_in)
    return asset


@router.get("", response_model=AssetPageResponse)
def list_assets(
    params: PageParams = Depends(),
    name: str = None,
    asset_type: str = None,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_assets(db, params, name, asset_type, status)
    pages = (total + params.size - 1) // params.size
    return {
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
        "items": items,
    }


@router.get("/stats/summary")
def get_asset_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from app.crud import get_dashboard_stats
    return get_dashboard_stats(db)


@router.get("/{asset_id}", response_model=AssetResponse)
def get_asset_detail(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    asset = get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@router.put("/{asset_id}", response_model=AssetResponse)
def update_asset_info(
    asset_id: int,
    asset_in: AssetUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if asset_in.asset_no and get_asset_by_no(db, asset_in.asset_no):
        existing = db.query(get_asset.__globals__['Asset']).filter(
            get_asset.__globals__['Asset'].asset_no == asset_in.asset_no,
            get_asset.__globals__['Asset'].id != asset_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="资产编号已存在")
    if asset_in.serial_number and get_asset_by_serial(db, asset_in.serial_number):
        existing = db.query(get_asset.__globals__['Asset']).filter(
            get_asset.__globals__['Asset'].serial_number == asset_in.serial_number,
            get_asset.__globals__['Asset'].id != asset_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="序列号已存在")
    
    asset = update_asset(db, asset_id, asset_in)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    return asset


@router.delete("/{asset_id}")
def delete_asset_by_id(
    asset_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    asset = get_asset(db, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="资产不存在")
    if asset.status == AssetStatus.IN_USE:
        raise HTTPException(status_code=400, detail="资产正在使用中，无法删除")
    if not delete_asset(db, asset_id):
        raise HTTPException(status_code=404, detail="资产不存在")
    return {"message": "删除成功"}


# 导出资产数据
@router.get("/export/excel")
def export_assets(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from fastapi.responses import StreamingResponse
    import io
    import openpyxl
    
    assets = db.query(get_asset.__globals__['Asset']).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "资产台账"
    
    headers = ["资产编号", "资产名称", "类型", "品牌", "型号", "序列号", "状态", 
               "采购日期", "采购价格(元)", "存放位置", "备注", "创建时间"]
    ws.append(headers)
    
    for asset in assets:
        ws.append([
            asset.asset_no,
            asset.name,
            asset.asset_type.value,
            asset.brand or "",
            asset.model or "",
            asset.serial_number or "",
            asset.status.value,
            asset.purchase_date.strftime("%Y-%m-%d") if asset.purchase_date else "",
            asset.purchase_price / 100 if asset.purchase_price else "",
            asset.location or "",
            asset.remark or "",
            asset.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=assets_export.xlsx"},
    )