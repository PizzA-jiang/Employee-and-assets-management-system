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
    knowledge_documents = relationship("KnowledgeDocument", back_populates="owner")


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
    version = Column(Integer, default=0, nullable=False, comment="乐观锁版本号")
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


class DocStatus(str, enum.Enum):
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class FileType(str, enum.Enum):
    PDF = "pdf"
    DOCX = "docx"
    XLSX = "xlsx"
    TXT = "txt"
    MD = "md"


class EmbeddingStatus(str, enum.Enum):
    PENDING = "pending"
    DONE = "done"
    FAILED = "failed"


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, comment="文档标题")
    filename = Column(String(255), nullable=False, comment="原始文件名")
    stored_name = Column(String(255), nullable=False, comment="存储文件名")
    file_path = Column(String(500), nullable=False, comment="文件路径")
    file_size = Column(Integer, nullable=False, comment="文件大小(字节)")
    mime_type = Column(String(100), nullable=True, comment="MIME类型")
    file_type = Column(Enum(FileType), nullable=False, comment="文件类型")
    status = Column(Enum(DocStatus), default=DocStatus.PROCESSING, nullable=False, comment="处理状态")
    chunk_count = Column(Integer, default=0, comment="分块数量")
    error_message = Column(Text, nullable=True, comment="错误信息")
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False, comment="上传者ID")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    owner = relationship("User")
    chunks = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, comment="文档ID")
    chunk_index = Column(Integer, nullable=False, comment="分块序号")
    content = Column(Text, nullable=False, comment="分块内容")
    token_count = Column(Integer, default=0, comment="token数量")
    metadata_json = Column(Text, nullable=True, comment="元数据JSON")
    embedding_status = Column(Enum(EmbeddingStatus), default=EmbeddingStatus.PENDING, comment="向量化状态")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    document = relationship("KnowledgeDocument", back_populates="chunks")

    __table_args__ = (
        Index("idx_chunk_document", "document_id", "chunk_index"),
    )


class AIConfig(Base):
    __tablename__ = "ai_configs"

    id = Column(Integer, primary_key=True, index=True)
    config_key = Column(String(50), unique=True, index=True, nullable=False, comment="配置键名")
    config_value = Column(Text, nullable=False, comment="加密后的配置值")
    config_type = Column(String(20), default="string", comment="值类型: string/boolean/integer")
    description = Column(String(255), nullable=True, comment="配置描述")
    updated_by = Column(Integer, ForeignKey("users.id"), nullable=True, comment="更新者ID")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    updater = relationship("User")


class MCPServer(Base):
    __tablename__ = "mcp_servers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, comment="MCP服务名称")
    host = Column(String(255), nullable=False, default="localhost", comment="服务器地址")
    port = Column(Integer, nullable=False, default=3306, comment="端口")
    username = Column(String(100), nullable=True, comment="数据库用户名")
    password = Column(String(500), nullable=True, comment="数据库密码")
    database = Column(String(100), nullable=True, comment="数据库名")
    charset = Column(String(20), default="utf8mb4", comment="字符集")
    is_enabled = Column(Integer, default=1, nullable=False, comment="是否启用 1=启用 0=禁用")
    sort_order = Column(Integer, default=0, comment="排序")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")


class ChatConversation(Base):
    __tablename__ = "chat_conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, comment="用户ID")
    title = Column(String(255), default="新对话", comment="对话标题")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, comment="更新时间")

    user = relationship("User")
    messages = relationship("ChatMessage", back_populates="conversation", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("chat_conversations.id", ondelete="CASCADE"), nullable=False, comment="对话ID")
    role = Column(String(20), nullable=False, comment="角色: user/assistant")
    content = Column(Text, nullable=False, comment="消息内容")
    sources_json = Column(Text, nullable=True, comment="引用来源JSON")
    model_used = Column(String(100), nullable=True, comment="使用的模型")
    created_at = Column(DateTime, default=datetime.utcnow, comment="创建时间")

    conversation = relationship("ChatConversation", back_populates="messages")

    __table_args__ = (
        Index("idx_chat_msg_conv", "conversation_id", "created_at"),
    )


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