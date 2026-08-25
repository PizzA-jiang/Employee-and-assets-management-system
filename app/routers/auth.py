from datetime import timedelta
from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.schemas import (
    LoginRequest, Token, UserCreate, UserResponse,
    UserUpdate, UserWithEmployee, PageParams,
)
from app.crud import (
    get_user_by_username, create_user, get_users,
    update_user, delete_user, authenticate_user,
)
from app.security import create_access_token, get_settings
from app.dependencies import get_current_user, get_current_admin
from app.models import User, UserRole
from app.utils.response import R, BizException

settings = get_settings()

router = APIRouter(prefix="/auth", tags=["认证"])


@router.post("/login", response_model=Token)
def login(login_data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, login_data.username, login_data.password)
    if not user:
        raise BizException("用户名或密码错误", code=401, http_status=401)
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role.value},
        expires_delta=access_token_expires,
    )
    return R.ok(data={"access_token": access_token, "token_type": "bearer"}, message="登录成功")


@router.get("/me")
def get_current_user_info(current_user: User = Depends(get_current_user)):
    return R.ok(data=current_user, schema=UserWithEmployee)


@router.post("/register", response_model=UserResponse)
def register(user_in: UserCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_admin)):
    if get_user_by_username(db, user_in.username):
        raise BizException("用户名已存在", code=400)
    if user_in.email and db.query(User).filter(User.email == user_in.email).first():
        raise BizException("邮箱已被注册", code=400)
    user = create_user(db, user_in)
    return user


@router.get("/users")
def list_users(
    params: PageParams = Depends(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    users = get_users(db, skip=(params.page - 1) * params.size, limit=params.size)
    total = db.query(User).count()
    return R.page(users, total=total, page=params.page, size=params.size, schema=UserResponse)


@router.get("/users/{user_id}")
def get_user_detail(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise BizException("用户不存在", code=404)
    return R.ok(data=user, schema=UserWithEmployee)


@router.put("/users/{user_id}")
def update_user_info(
    user_id: int,
    user_in: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    user = update_user(db, user_id, user_in)
    if not user:
        raise BizException("用户不存在", code=404)
    return R.ok(data=user, message="更新成功", schema=UserResponse)


@router.delete("/users/{user_id}")
def delete_user_by_id(
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin),
):
    if user_id == current_user.id:
        raise BizException("不能删除自己", code=400)
    if not delete_user(db, user_id):
        raise BizException("用户不存在", code=404)
    return R.ok(message="删除成功")