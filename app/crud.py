from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, text
from app.models import User, Employee, Asset, AssetLog, UserRole, AssetStatus, LogAction
from app.schemas import (
    UserCreate, UserUpdate,
    EmployeeCreate, EmployeeUpdate,
    AssetCreate, AssetUpdate,
    AssetLogCreate,
    PageParams,
)
from app.security import get_password_hash, verify_password
#

# User CRUD
def get_user(db: Session, user_id: int) -> Optional[User]:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    return db.query(User).filter(User.username == username).first()


def get_user_by_email(db: Session, email: str) -> Optional[User]:
    return db.query(User).filter(User.email == email).first()


def get_users(db: Session, skip: int = 0, limit: int = 100) -> List[User]:
    return db.query(User).offset(skip).limit(limit).all()


def create_user(db: Session, user_in: UserCreate) -> User:
    hashed_password = get_password_hash(user_in.password)
    user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=hashed_password,
        role=user_in.role,
    )
    db.add(user)
    db.flush()
    db.refresh(user)
    return user


def update_user(db: Session, user_id: int, user_in: UserUpdate) -> Optional[User]:
    user = get_user(db, user_id)
    if not user:
        return None
    update_data = user_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(user, field, value)
    db.flush()
    db.refresh(user)
    return user


def delete_user(db: Session, user_id: int) -> bool:
    user = get_user(db, user_id)
    if not user:
        return False
    db.delete(user)
    db.flush()
    return True


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    user = get_user_by_username(db, username)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


# Employee CRUD
def get_employee(db: Session, employee_id: int) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.id == employee_id).first()


def get_employee_by_user_id(db: Session, user_id: int) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.user_id == user_id).first()


def get_employee_by_no(db: Session, employee_no: str) -> Optional[Employee]:
    return db.query(Employee).filter(Employee.employee_no == employee_no).first()


def get_employees(
    db: Session,
    params: PageParams,
    name: Optional[str] = None,
    department: Optional[str] = None,
    status: Optional[int] = None,
    keyword: Optional[str] = None,
) -> Tuple[List[Employee], int]:
    query = db.query(Employee).options(joinedload(Employee.user))
    
    if keyword:
        query = query.filter(
            or_(
                Employee.name.contains(keyword),
                Employee.employee_no.contains(keyword),
                Employee.department.contains(keyword),
                Employee.position.contains(keyword),
                Employee.phone.contains(keyword),
            )
        )
    else:
        if name:
            query = query.filter(Employee.name.contains(name))
        if department:
            query = query.filter(Employee.department.contains(department))
        if status is not None:
            query = query.filter(Employee.status == status)
    
    total = query.count()
    items = query.order_by(desc(Employee.created_at)).offset((params.page - 1) * params.size).limit(params.size).all()
    return items, total


def create_employee(db: Session, employee_in: EmployeeCreate) -> Employee:
    employee = Employee(**employee_in.model_dump())
    db.add(employee)
    db.flush()
    db.refresh(employee)
    return employee


def update_employee(db: Session, employee_id: int, employee_in: EmployeeUpdate) -> Optional[Employee]:
    employee = get_employee(db, employee_id)
    if not employee:
        return None
    update_data = employee_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(employee, field, value)
    db.flush()
    db.refresh(employee)
    return employee


def delete_employee(db: Session, employee_id: int) -> bool:
    employee = get_employee(db, employee_id)
    if not employee:
        return False
    db.query(AssetLog).filter(AssetLog.employee_id == employee_id).delete()
    db.delete(employee)
    db.flush()
    return True


# Asset CRUD
def get_asset(db: Session, asset_id: int) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.id == asset_id).first()


def get_asset_by_no(db: Session, asset_no: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.asset_no == asset_no).first()


def get_asset_by_serial(db: Session, serial_number: str) -> Optional[Asset]:
    return db.query(Asset).filter(Asset.serial_number == serial_number).first()


def get_assets(
    db: Session,
    params: PageParams,
    name: Optional[str] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    keyword: Optional[str] = None,
) -> Tuple[List[Asset], int]:
    query = db.query(Asset)
    
    if keyword:
        query = query.filter(
            or_(
                Asset.asset_no.contains(keyword),
                Asset.name.contains(keyword),
                Asset.brand.contains(keyword),
                Asset.model.contains(keyword),
                Asset.serial_number.contains(keyword),
                Asset.location.contains(keyword),
            )
        )
    else:
        if name:
            query = query.filter(Asset.name.contains(name))
        if asset_type:
            query = query.filter(Asset.asset_type == asset_type)
        if status:
            query = query.filter(Asset.status == status)
    
    total = query.count()
    items = query.order_by(desc(Asset.created_at)).offset((params.page - 1) * params.size).limit(params.size).all()
    return items, total


def create_asset(db: Session, asset_in: AssetCreate) -> Asset:
    asset = Asset(**asset_in.model_dump())
    db.add(asset)
    db.flush()
    db.refresh(asset)
    return asset


def update_asset(db: Session, asset_id: int, asset_in: AssetUpdate) -> Optional[Asset]:
    asset = get_asset(db, asset_id)
    if not asset:
        return None
    update_data = asset_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(asset, field, value)
    db.flush()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int) -> bool:
    asset = get_asset(db, asset_id)
    if not asset:
        return False
    if asset.status == AssetStatus.IN_USE:
        return False
    db.query(AssetLog).filter(AssetLog.asset_id == asset_id).delete()
    db.delete(asset)
    db.flush()
    return True


# AssetLog CRUD
def get_asset_log(db: Session, log_id: int) -> Optional[AssetLog]:
    return db.query(AssetLog).options(
        joinedload(AssetLog.asset),
        joinedload(AssetLog.employee)
    ).filter(AssetLog.id == log_id).first()


def get_asset_logs(
    db: Session,
    params: PageParams,
    asset_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    action: Optional[str] = None,
) -> Tuple[List[AssetLog], int]:
    query = db.query(AssetLog).options(
        joinedload(AssetLog.asset),
        joinedload(AssetLog.employee)
    )
    
    if asset_id:
        query = query.filter(AssetLog.asset_id == asset_id)
    if employee_id:
        query = query.filter(AssetLog.employee_id == employee_id)
    if action:
        query = query.filter(AssetLog.action == action)
    
    total = query.count()
    items = query.order_by(desc(AssetLog.created_at)).offset((params.page - 1) * params.size).limit(params.size).all()
    return items, total


def create_asset_log(db: Session, log_in: AssetLogCreate, operator_id: int) -> AssetLog:
    log = AssetLog(**log_in.model_dump(), operator_id=operator_id)
    db.add(log)
    
    # Use select_for_update to lock the asset row and prevent concurrent modification
    asset = db.query(Asset).filter(Asset.id == log_in.asset_id).with_for_update().first()
    if asset:
        # Check optimistic lock version to detect concurrent changes
        current_version = asset.version
        if log_in.action == LogAction.CHECKOUT:
            asset.status = AssetStatus.IN_USE
        elif log_in.action == LogAction.RETURN:
            asset.status = AssetStatus.AVAILABLE
        elif log_in.action == LogAction.MAINTENANCE_IN:
            asset.status = AssetStatus.MAINTENANCE
        elif log_in.action == LogAction.MAINTENANCE_OUT:
            asset.status = AssetStatus.AVAILABLE
        elif log_in.action == LogAction.SCRAP:
            asset.status = AssetStatus.SCRAPPED
        # Increment version for optimistic locking
        asset.version = current_version + 1
    
    db.flush()
    db.refresh(log)
    return log


# Dashboard stats
def get_dashboard_stats(db: Session) -> dict:
    total_employees = db.query(Employee).filter(Employee.status == 1).count()
    total_assets = db.query(Asset).count()
    assets_in_use = db.query(Asset).filter(Asset.status == AssetStatus.IN_USE).count()
    assets_available = db.query(Asset).filter(Asset.status == AssetStatus.AVAILABLE).count()
    assets_maintenance = db.query(Asset).filter(Asset.status == AssetStatus.MAINTENANCE).count()
    assets_scrapped = db.query(Asset).filter(Asset.status == AssetStatus.SCRAPPED).count()
    
    recent_logs = db.query(AssetLog).options(
        joinedload(AssetLog.asset),
        joinedload(AssetLog.employee)
    ).order_by(desc(AssetLog.created_at)).limit(10).all()
    
    return {
        "total_employees": total_employees,
        "total_assets": total_assets,
        "assets_in_use": assets_in_use,
        "assets_available": assets_available,
        "assets_maintenance": assets_maintenance,
        "assets_scrapped": assets_scrapped,
        "recent_logs": recent_logs,
    }