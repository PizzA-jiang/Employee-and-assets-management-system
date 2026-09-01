from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from app.models import UserRole, AssetType, AssetStatus, LogAction

#分角色模块，用户/资产/log/员工
class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[UserRole] = None


# User schemas
class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[EmailStr] = None
    role: UserRole = UserRole.EMPLOYEE


class UserCreate(UserBase):
    password: str = Field(..., min_length=6, max_length=50)


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    role: Optional[UserRole] = None
    is_active: Optional[int] = None


class UserResponse(UserBase):
    id: int
    is_active: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class UserWithEmployee(UserResponse):
    employee: Optional["EmployeeResponse"] = None


# Employee schemas
class EmployeeBase(BaseModel):
    employee_no: str = Field(..., min_length=1, max_length=30)
    name: str = Field(..., min_length=1, max_length=50)
    department: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    hire_date: Optional[datetime] = None


class EmployeeCreate(EmployeeBase):
    user_id: Optional[int] = None


class EmployeeUpdate(BaseModel):
    employee_no: Optional[str] = Field(None, min_length=1, max_length=30)
    name: Optional[str] = Field(None, min_length=1, max_length=50)
    department: Optional[str] = Field(None, max_length=50)
    position: Optional[str] = Field(None, max_length=50)
    phone: Optional[str] = Field(None, max_length=20)
    hire_date: Optional[datetime] = None
    status: Optional[int] = None


class EmployeeResponse(EmployeeBase):
    id: int
    user_id: int
    status: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class EmployeeWithUser(EmployeeResponse):
    user: Optional[UserResponse] = None


# Asset schemas
class AssetBase(BaseModel):
    asset_no: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    asset_type: AssetType
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[int] = None
    location: Optional[str] = Field(None, max_length=100)
    remark: Optional[str] = None


class AssetCreate(AssetBase):
    pass


class AssetUpdate(BaseModel):
    asset_no: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    asset_type: Optional[AssetType] = None
    brand: Optional[str] = Field(None, max_length=50)
    model: Optional[str] = Field(None, max_length=100)
    serial_number: Optional[str] = Field(None, max_length=100)
    status: Optional[AssetStatus] = None
    purchase_date: Optional[datetime] = None
    purchase_price: Optional[int] = None
    location: Optional[str] = Field(None, max_length=100)
    remark: Optional[str] = None


class AssetResponse(AssetBase):
    id: int
    status: AssetStatus
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# AssetLog schemas
class AssetLogBase(BaseModel):
    asset_id: int
    employee_id: int
    action: LogAction
    remark: Optional[str] = None


class AssetLogCreate(AssetLogBase):
    pass


class AssetLogResponse(AssetLogBase):
    id: int
    operator_id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AssetLogWithDetails(AssetLogResponse):
    asset: Optional[AssetResponse] = None
    employee: Optional[EmployeeResponse] = None


# Pagination
class PageParams(BaseModel):
    page: int = Field(1, ge=1)
    size: int = Field(20, ge=1, le=100)


class PageResponse(BaseModel):
    total: int
    page: int
    size: int
    pages: int


class EmployeePageResponse(PageResponse):
    items: List[EmployeeResponse]


class AssetPageResponse(PageResponse):
    items: List[AssetResponse]


class AssetLogPageResponse(PageResponse):
    items: List[AssetLogWithDetails]


# Dashboard stats
class DashboardStats(BaseModel):
    total_employees: int
    total_assets: int
    assets_in_use: int
    assets_available: int
    assets_maintenance: int
    assets_scrapped: int
    recent_logs: List[AssetLogWithDetails]


# Login
class LoginRequest(BaseModel):
    username: str
    password: str


# CloudFile schemas
class CloudFileResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    mime_type: Optional[str] = None
    is_public: int = 0
    user_id: int
    owner_name: Optional[str] = None
    is_shared: bool = False
    shared_by: Optional[str] = None
    shared_to_names: Optional[List[str]] = None
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class CloudFilePageResponse(PageResponse):
    items: List[CloudFileResponse]


class FileShareCreate(BaseModel):
    user_ids: List[int]


# Knowledge Document schemas
from app.models import DocStatus, FileType, EmbeddingStatus


class KnowledgeDocumentResponse(BaseModel):
    id: int
    title: str
    filename: str
    file_size: int
    mime_type: Optional[str] = None
    file_type: FileType
    status: DocStatus
    chunk_count: int
    error_message: Optional[str] = None
    created_by: int
    creator_name: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeDocumentPageResponse(PageResponse):
    items: List[KnowledgeDocumentResponse]


class KnowledgeDocumentUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)


class KnowledgeChunkResponse(BaseModel):
    id: int
    document_id: int
    chunk_index: int
    content: str
    token_count: int
    metadata_json: Optional[str] = None
    embedding_status: EmbeddingStatus
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class KnowledgeChunkPageResponse(PageResponse):
    items: List[KnowledgeChunkResponse]


class KnowledgeSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=500)
    top_k: int = Field(5, ge=1, le=20)


class KnowledgeSearchResult(BaseModel):
    chunk_id: int
    document_id: int
    document_title: str
    content: str
    score: float


class KnowledgeSearchResponse(BaseModel):
    query: str
    results: List[KnowledgeSearchResult]


# Forward references
UserWithEmployee.model_rebuild()
EmployeeWithUser.model_rebuild()