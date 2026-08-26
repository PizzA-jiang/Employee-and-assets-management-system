#建表

import enum
from datetime import datetime
from sqlalchemy import (
    Column,
    Integer,
    String,
    DateTime,
    Enum,
    ForeignKey,
    Text,
    Index,
)
from sqlalchemy.orm import relationship
from app.database import Base


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    EMPLOYEE = "employee"


class AssetStatus(str, enum.Enum):
    AVAILABLE = "available"      # 闲置
    IN_USE = "in_use"            # 使用中
    MAINTENANCE = "maintenance"  # 维修中
    SCRAPPED = "scrapped"        # 报废


class AssetType(str, enum.Enum):
    COMPUTER = "computer"        # 电脑
    PHONE = "phone"              # 手机
    MONITOR = "monitor"          # 显示器
    PERIPHERAL = "peripheral"    # 外设
    FURNITURE = "furniture"      # 办公家具
    OTHER = "other"              # 其他


class LogAction(str, enum.Enum):
    CHECKOUT = "checkout"        # 领用
    RETURN = "return"            # 归还
    TRANSFER = "transfer"        # 调拨
    MAINTENANCE_IN = "maintenance_in"   # 送修
    MAINTENANCE_OUT = "maintenance_out" # 修好
    SCRAP = "scrap"              # 报废


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False, comment="用户名")
    email = Column(String(100), unique=True, index=True, nullable=True, comment="邮箱")
    hashed_password = Column(String(255), nullable=False, comment="加密密码")
    role = Column(Enum(UserRole), default=UserRole.EMPLOYEE, nullable=False, comment="角色")
    is_active = Column(Integer, default=1, nullable=False, comment="是否启用 1=启用 0=禁用")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    employee = relationship("Employee", back_populates="user", uselist=False)


class Employee(Base):
    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, comment="关联用户ID")
    employee_no = Column(String(30), unique=True, index=True, nullable=False, comment="工号")
    name = Column(String(50), nullable=False, comment="姓名")
    department = Column(String(50), nullable=True, comment="部门")
    position = Column(String(50), nullable=True, comment="职位")
    phone = Column(String(20), nullable=True, comment="电话")
    hire_date = Column(DateTime, nullable=True, comment="入职日期")
    status = Column(Integer, default=1, nullable=False, comment="状态 1=在职 0=离职")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    user = relationship("User", back_populates="employee")
    asset_logs = relationship("AssetLog", back_populates="employee")


class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    asset_no = Column(String(50), unique=True, index=True, nullable=False, comment="资产编号")
    name = Column(String(100), nullable=False, comment="资产名称")
    asset_type = Column(Enum(AssetType), nullable=False, comment="资产类型")
    brand = Column(String(50), nullable=True, comment="品牌")
    model = Column(String(100), nullable=True, comment="型号")
    serial_number = Column(String(100), unique=True, index=True, nullable=True, comment="序列号")
    status = Column(Enum(AssetStatus), default=AssetStatus.AVAILABLE, nullable=False, comment="状态")
    purchase_date = Column(DateTime, nullable=True, comment="采购日期")
    purchase_price = Column(Integer, nullable=True, comment="采购价格(分)")
    location = Column(String(100), nullable=True, comment="存放位置")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    logs = relationship("AssetLog", back_populates="asset")


class AssetLog(Base):
    __tablename__ = "asset_logs"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id", ondelete="CASCADE"), nullable=False, comment="资产ID")
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, comment="员工ID")
    action = Column(Enum(LogAction), nullable=False, comment="操作类型")
    operator_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="操作人ID")
    remark = Column(Text, nullable=True, comment="备注")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    asset = relationship("Asset", back_populates="logs")
    employee = relationship("Employee", back_populates="asset_logs")

    __table_args__ = (
        Index("idx_asset_log_asset_created", "asset_id", "created_at"),
        Index("idx_asset_log_employee_created", "employee_id", "created_at"),
    )