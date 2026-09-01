from datetime import datetime
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, desc, text
from app.models import User, Employee, Asset, AssetLog, UserRole, AssetStatus, LogAction
from app.models import KnowledgeDocument, KnowledgeChunk, DocStatus, EmbeddingStatus
from app.models import AIConfig, MCPServer, ChatConversation, ChatMessage
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


# Knowledge Document CRUD
def get_knowledge_document(db: Session, doc_id: int) -> Optional[KnowledgeDocument]:
    return db.query(KnowledgeDocument).filter(KnowledgeDocument.id == doc_id).first()


def get_knowledge_documents(
    db: Session,
    page: int = 1,
    size: int = 20,
    keyword: Optional[str] = None,
) -> Tuple[List[KnowledgeDocument], int]:
    query = db.query(KnowledgeDocument)

    if keyword:
        query = query.filter(
            or_(
                KnowledgeDocument.title.contains(keyword),
                KnowledgeDocument.filename.contains(keyword),
            )
        )

    total = query.count()
    items = query.order_by(desc(KnowledgeDocument.created_at)).offset((page - 1) * size).limit(size).all()
    return items, total


def create_knowledge_document(
    db: Session,
    title: str,
    filename: str,
    stored_name: str,
    file_path: str,
    file_size: int,
    mime_type: Optional[str],
    file_type: "FileType",
    created_by: int,
) -> KnowledgeDocument:
    doc = KnowledgeDocument(
        title=title,
        filename=filename,
        stored_name=stored_name,
        file_path=file_path,
        file_size=file_size,
        mime_type=mime_type,
        file_type=file_type,
        status=DocStatus.PROCESSING,
        created_by=created_by,
    )
    db.add(doc)
    db.flush()
    db.refresh(doc)
    return doc


def update_knowledge_document_status(
    db: Session,
    doc_id: int,
    status: DocStatus,
    chunk_count: int = 0,
    error_message: Optional[str] = None,
) -> Optional[KnowledgeDocument]:
    doc = get_knowledge_document(db, doc_id)
    if not doc:
        return None
    doc.status = status
    doc.chunk_count = chunk_count
    doc.error_message = error_message
    db.flush()
    db.refresh(doc)
    return doc


def update_knowledge_document_title(
    db: Session,
    doc_id: int,
    title: str,
) -> Optional[KnowledgeDocument]:
    doc = get_knowledge_document(db, doc_id)
    if not doc:
        return None
    doc.title = title
    db.flush()
    db.refresh(doc)
    return doc


def delete_knowledge_document(db: Session, doc_id: int) -> bool:
    doc = get_knowledge_document(db, doc_id)
    if not doc:
        return False
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == doc_id).delete()
    db.delete(doc)
    db.flush()
    return True


def create_knowledge_chunks(
    db: Session,
    document_id: int,
    chunks: list,
) -> List[KnowledgeChunk]:
    db_chunks = []
    for i, chunk in enumerate(chunks):
        db_chunk = KnowledgeChunk(
            document_id=document_id,
            chunk_index=i,
            content=chunk.content,
            token_count=chunk.token_count,
            metadata_json=str(chunk.metadata) if chunk.metadata else None,
            embedding_status=EmbeddingStatus.PENDING,
        )
        db.add(db_chunk)
        db_chunks.append(db_chunk)
    db.flush()
    return db_chunks


def get_knowledge_chunks(
    db: Session,
    document_id: int,
    page: int = 1,
    size: int = 20,
) -> Tuple[List[KnowledgeChunk], int]:
    query = db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document_id)
    total = query.count()
    items = query.order_by(KnowledgeChunk.chunk_index).offset((page - 1) * size).limit(size).all()
    return items, total


def delete_knowledge_chunks_by_document(db: Session, document_id: int) -> bool:
    db.query(KnowledgeChunk).filter(KnowledgeChunk.document_id == document_id).delete()
    db.flush()
    return True


# AI Config CRUD
def get_ai_config(db: Session, config_key: str) -> Optional[AIConfig]:
    return db.query(AIConfig).filter(AIConfig.config_key == config_key).first()


def get_all_ai_configs(db: Session) -> List[AIConfig]:
    return db.query(AIConfig).order_by(AIConfig.config_key).all()


def upsert_ai_config(
    db: Session,
    config_key: str,
    config_value: str,
    config_type: str = "string",
    description: Optional[str] = None,
    updated_by: Optional[int] = None,
) -> AIConfig:
    config = get_ai_config(db, config_key)
    if config:
        config.config_value = config_value
        config.config_type = config_type
        if description is not None:
            config.description = description
        if updated_by is not None:
            config.updated_by = updated_by
    else:
        config = AIConfig(
            config_key=config_key,
            config_value=config_value,
            config_type=config_type,
            description=description,
            updated_by=updated_by,
        )
        db.add(config)
    db.flush()
    db.refresh(config)
    return config


def get_ai_config_value(db: Session, config_key: str, default: str = "") -> str:
    config = get_ai_config(db, config_key)
    return config.config_value if config else default


# Filtered query helpers for AI tool calling
def query_employees_filtered(
    db: Session,
    name: Optional[str] = None,
    department: Optional[str] = None,
    position: Optional[str] = None,
    status: Optional[int] = None,
    limit: int = 20,
) -> List[dict]:
    query = db.query(Employee)
    if name:
        query = query.filter(Employee.name.contains(name))
    if department:
        query = query.filter(Employee.department.contains(department))
    if position:
        query = query.filter(Employee.position.contains(position))
    if status is not None:
        query = query.filter(Employee.status == status)
    items = query.order_by(desc(Employee.created_at)).limit(limit).all()
    return [
        {
            "id": e.id,
            "employee_no": e.employee_no,
            "name": e.name,
            "department": e.department,
            "position": e.position,
            "phone": e.phone,
            "hire_date": e.hire_date.isoformat() if e.hire_date else None,
            "status": e.status,
        }
        for e in items
    ]


def query_assets_filtered(
    db: Session,
    name: Optional[str] = None,
    asset_type: Optional[str] = None,
    status: Optional[str] = None,
    location: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    query = db.query(Asset)
    if name:
        query = query.filter(Asset.name.contains(name))
    if asset_type:
        query = query.filter(Asset.asset_type == asset_type)
    if status:
        query = query.filter(Asset.status == status)
    if location:
        query = query.filter(Asset.location.contains(location))
    items = query.order_by(desc(Asset.created_at)).limit(limit).all()
    return [
        {
            "id": a.id,
            "asset_no": a.asset_no,
            "name": a.name,
            "asset_type": a.asset_type.value if a.asset_type else None,
            "brand": a.brand,
            "model": a.model,
            "status": a.status.value if a.status else None,
            "location": a.location,
        }
        for a in items
    ]


def query_asset_logs_filtered(
    db: Session,
    employee_name: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 20,
) -> List[dict]:
    query = db.query(AssetLog).options(
        joinedload(AssetLog.asset),
        joinedload(AssetLog.employee),
    )
    if employee_name:
        query = query.join(Employee).filter(Employee.name.contains(employee_name))
    if action:
        query = query.filter(AssetLog.action == action)
    items = query.order_by(desc(AssetLog.created_at)).limit(limit).all()
    return [
        {
            "id": l.id,
            "asset_name": l.asset.name if l.asset else None,
            "employee_name": l.employee.name if l.employee else None,
            "action": l.action.value if l.action else None,
            "remark": l.remark,
            "created_at": l.created_at.isoformat() if l.created_at else None,
        }
        for l in items
    ]


# MCP Server CRUD
def get_mcp_server(db: Session, server_id: int) -> Optional[MCPServer]:
    return db.query(MCPServer).filter(MCPServer.id == server_id).first()


def get_all_mcp_servers(db: Session) -> List[MCPServer]:
    return db.query(MCPServer).order_by(MCPServer.sort_order, MCPServer.id).all()


def get_enabled_mcp_servers(db: Session) -> List[MCPServer]:
    return db.query(MCPServer).filter(MCPServer.is_enabled == 1).order_by(MCPServer.sort_order, MCPServer.id).all()


def create_mcp_server(db: Session, **kwargs) -> MCPServer:
    server = MCPServer(**kwargs)
    db.add(server)
    db.flush()
    db.refresh(server)
    return server


def update_mcp_server(db: Session, server_id: int, **kwargs) -> Optional[MCPServer]:
    server = get_mcp_server(db, server_id)
    if not server:
        return None
    for key, value in kwargs.items():
        if value is not None and hasattr(server, key):
            setattr(server, key, value)
    db.flush()
    db.refresh(server)
    return server


def delete_mcp_server(db: Session, server_id: int) -> bool:
    server = get_mcp_server(db, server_id)
    if not server:
        return False
    db.delete(server)
    db.flush()
    return True


# Chat History CRUD
def get_user_conversations(db: Session, user_id: int, limit: int = 20) -> List[ChatConversation]:
    return db.query(ChatConversation).filter(
        ChatConversation.user_id == user_id
    ).order_by(desc(ChatConversation.updated_at)).limit(limit).all()


def get_conversation(db: Session, conv_id: int, user_id: int) -> Optional[ChatConversation]:
    return db.query(ChatConversation).filter(
        ChatConversation.id == conv_id,
        ChatConversation.user_id == user_id,
    ).first()


def create_conversation(db: Session, user_id: int, title: str = "新对话") -> ChatConversation:
    conv = ChatConversation(user_id=user_id, title=title)
    db.add(conv)
    db.flush()
    db.refresh(conv)
    return conv


def update_conversation_title(db: Session, conv_id: int, title: str) -> Optional[ChatConversation]:
    conv = db.query(ChatConversation).filter(ChatConversation.id == conv_id).first()
    if conv:
        conv.title = title
        db.flush()
        db.refresh(conv)
    return conv


def delete_conversation(db: Session, conv_id: int, user_id: int) -> bool:
    conv = db.query(ChatConversation).filter(
        ChatConversation.id == conv_id,
        ChatConversation.user_id == user_id,
    ).first()
    if not conv:
        return False
    db.delete(conv)
    db.flush()
    return True


def get_conversation_messages(db: Session, conv_id: int) -> List[ChatMessage]:
    return db.query(ChatMessage).filter(
        ChatMessage.conversation_id == conv_id
    ).order_by(ChatMessage.created_at).all()


def add_chat_message(
    db: Session,
    conv_id: int,
    role: str,
    content: str,
    sources_json: Optional[str] = None,
    model_used: Optional[str] = None,
) -> ChatMessage:
    msg = ChatMessage(
        conversation_id=conv_id,
        role=role,
        content=content,
        sources_json=sources_json,
        model_used=model_used,
    )
    db.add(msg)
    db.flush()
    db.refresh(msg)
    return msg


def trim_user_conversations(db: Session, user_id: int, keep: int = 3):
    """保留用户最近 keep 轮对话，删除多余的旧对话"""
    convs = db.query(ChatConversation).filter(
        ChatConversation.user_id == user_id
    ).order_by(desc(ChatConversation.updated_at)).all()
    if len(convs) > keep:
        for conv in convs[keep:]:
            db.delete(conv)
        db.flush()