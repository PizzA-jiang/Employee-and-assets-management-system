from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
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
from app.models import User, UserRole, Employee
from app.utils.operation_log import log_operation
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
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="create",
        target_type="employee",
        target_id=employee.id,
        target_name=employee.name,
    )
    
    return employee


@router.get("", response_model=EmployeePageResponse)
def list_employees(
    params: PageParams = Depends(),
    name: str = None,
    department: str = None,
    status: int = None,
    keyword: str = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    items, total = get_employees(db, params, name, department, status, keyword)
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
    employee = db.query(Employee).filter(
        Employee.user_id == current_user.id
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
        existing = db.query(Employee).filter(
            Employee.employee_no == employee_in.employee_no,
            Employee.id != employee_id
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail="工号已存在")
    
    employee = update_employee(db, employee_id, employee_in)
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="update",
        target_type="employee",
        target_id=employee.id,
        target_name=employee.name,
    )
    
    return employee


@router.delete("/{employee_id}")
def delete_employee_by_id(
    employee_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail="员工不存在")
    
    employee_name = employee.name
    if not delete_employee(db, employee_id):
        raise HTTPException(status_code=404, detail="员工不存在")
    
    log_operation(
        db=db,
        user_id=current_user.id,
        action="delete",
        target_type="employee",
        target_id=employee_id,
        target_name=employee_name,
    )
    
    return {"message": "删除成功"}


@router.get("/export/excel")
def export_employees(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    from fastapi.responses import StreamingResponse
    import io
    import openpyxl
    
    employees = db.query(Employee).options(joinedload(Employee.user)).all()
    
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "员工花名册"
    
    headers = ["工号", "姓名", "部门", "职位", "电话", "入职日期", 
               "状态", "关联账号", "邮箱", "创建时间"]
    ws.append(headers)
    
    for emp in employees:
        ws.append([
            emp.employee_no,
            emp.name,
            emp.department or "",
            emp.position or "",
            emp.phone or "",
            emp.hire_date.strftime("%Y-%m-%d") if emp.hire_date else "",
            "在职" if emp.status == 1 else "离职",
            emp.user.username if emp.user else "",
            emp.user.email if emp.user else "",
            emp.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ])
    
    output = io.BytesIO()
    wb.save(output)
    output.seek(0)
    
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=employees_export.xlsx"},
    )