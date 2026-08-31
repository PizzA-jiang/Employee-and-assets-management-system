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
    cloud_files = relationship("CloudFile", back_populates="owner")


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


class OperationLog(Base):
    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="操作人ID")
    action = Column(String(50), nullable=False, comment="操作类型")
    target_type = Column(String(50), nullable=False, comment="目标类型")
    target_id = Column(Integer, nullable=False, comment="目标ID")
    target_name = Column(String(100), nullable=True, comment="目标名称")
    detail = Column(Text, nullable=True, comment="操作详情")
    ip_address = Column(String(50), nullable=True, comment="IP地址")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    user = relationship("User")


class CloudFile(Base):
    __tablename__ = "cloud_files"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="所有者ID")
    filename = Column(String(255), nullable=False, comment="原始文件名")
    stored_name = Column(String(255), nullable=False, comment="存储文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_size = Column(Integer, nullable=False, comment="文件大小(字节)")
    mime_type = Column(String(100), nullable=True, comment="MIME类型")
    is_public = Column(Integer, default=0, comment="是否公共文件(1=是, 0=否)")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    owner = relationship("User", back_populates="cloud_files")
    shares = relationship("FileShare", back_populates="file", cascade="all, delete-orphan")


class FileShare(Base):
    __tablename__ = "file_shares"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("cloud_files.id"), nullable=False, comment="文件ID")
    shared_to_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="共享给用户ID")
    shared_by_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="分享者ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="共享时间")

    file = relationship("CloudFile", back_populates="shares")
    shared_to = relationship("User", foreign_keys=[shared_to_id])
    shared_by = relationship("User", foreign_keys=[shared_by_id])