from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    EmployeeCreate, EmployeeUpdate, EmployeeResponse,
    EmployeeWithUser, EmployeePageResponse, PageParams,
)
from app.crud import (
    get_employee, get_employee_by_no, get_employees,
    create_employee, update_employee, delete_employee,
)
from app.dependencies import get_current_user, get_current_admin
from app.models import User, UserRole

router = APIRouter(prefix="/employees", tags=["员工管理"])


@router.post("", response_model=EmployeeResponse, status_code=status.HTTP_201_CREATED)
def create_employee_api(
    employee_in: EmployeeCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if get_employee_by_no(db, employee_in.employee_no):
        raise HTTPException(status_code=400, detail="工号已存在")
    if employee_in.user_id and get_employee(db, employee_in.user_id):
        raise HTTPException(status_code=400, detail="该用户已关联员工信息")
    employee = create_employee(db, employee_in)
    return employee


@router.get("", response_model=EmployeePageResponse)
def list_employees(
    params: PageParams = Depends(),
    name: str = None,
    department: str = None,
    status: int = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_employees(db, params, name, department, status)
    pages = (total + params.size - 1) // params.size
    return {
        "total": total,
        "page": params.page,
        "size": params.size,
        "pages": pages,
        "items": items,
    }


@router.get("/me", response_model=EmployeeWithUser)
def get_my_employee_info(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = db.query(current_user.employee.__class__).filter(
        current_user.employee.__class__.user_id == current_user.id
    ).first() if current_user.employee else None
    
    if not employee:
        raise HTTPException(status_code=404, detail="未找到关联的员工信息")
    return employee


@router.get("/{employee_id}", response_model=EmployeeWithUser)
def get_employee_detail(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    employee = get_employee(db, employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    # 普通员工只能看自己
    if current_user.role != UserRole.ADMIN and employee.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="权限不足")
    return employee


@router.put("/{employee_id}", response_model=EmployeeResponse)
def update_employee_info(
    employee_id: int,
    employee_in: EmployeeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if employee_in.employee_no and get_employee_by_no(db, employee_in.employee_no):
        existing = db.query(current_user.employee.__class__).filter(
            current_user.employee.__class__.employee_no == employee_in.employee_no,
            current_user.employee.__class__.id != employee_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="工号已存在")
    
    employee = update_employee(db, employee_id, employee_in)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    return employee


@router.delete("/{employee_id}")
def delete_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if not delete_employee(db, employee_id):
        raise HTTPException(status_code=404, detail="员工不存在")
    return {"message": "删除成功"}