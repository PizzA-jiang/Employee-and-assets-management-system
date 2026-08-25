from typing import Any, Generic, Optional, TypeVar, Type
from datetime import datetime, date
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from enum import Enum


class CodeEnum(int, Enum):
    SUCCESS = 200
    CREATED = 201
    BAD_REQUEST = 400
    UNAUTHORIZED = 401
    FORBIDDEN = 403
    NOT_FOUND = 404
    CONFLICT = 409
    VALIDATION_ERROR = 422
    SERVER_ERROR = 500


T = TypeVar("T")


class BaseResponse(BaseModel, Generic[T]):
    code: int = Field(description="业务状态码")
    message: str = Field(description="提示信息")
    data: Optional[T] = Field(default=None, description="响应数据")

    class Config:
        from_attributes = True


class PageInfo(BaseModel):
    page: int = Field(default=1, description="当前页码")
    size: int = Field(default=20, description="每页大小")
    total: int = Field(default=0, description="总记录数")
    pages: int = Field(default=0, description="总页数")


class PageResponse(BaseModel, Generic[T]):
    code: int = Field(default=CodeEnum.SUCCESS, description="业务状态码")
    message: str = Field(default="成功", description="提示信息")
    data: list[T] = Field(default_factory=list, description="列表数据")
    page_info: PageInfo = Field(default_factory=PageInfo, description="分页信息")


class R:
    """统一响应工具类"""

    @staticmethod
    def _to_serializable(data: Any, schema: Type[BaseModel] = None) -> Any:
        """将 ORM 对象转换为可序列化的字典"""
        if data is None:
            return None
        if isinstance(data, list):
            return [R._to_serializable(item, schema) for item in data]
        if isinstance(data, (datetime, date)):
            return data.isoformat()
        if schema and hasattr(data, '__dict__'):
            # ORM object -> Pydantic model -> dict (use mode='json' to serialize datetime)
            return schema.model_validate(data).model_dump(mode='json')
        if hasattr(data, 'model_dump'):
            return data.model_dump(mode='json')
        if hasattr(data, 'dict'):
            return data.dict()
        if hasattr(data, '__dict__'):
            return data.__dict__
        return data

    @staticmethod
    def ok(data: Any = None, message: str = "成功", schema: Type[BaseModel] = None) -> JSONResponse:
        """成功响应"""
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=BaseResponse(code=CodeEnum.SUCCESS, message=message, data=R._to_serializable(data, schema)).model_dump()
        )

    @staticmethod
    def created(data: Any = None, message: str = "创建成功", schema: Type[BaseModel] = None) -> JSONResponse:
        """创建成功"""
        return JSONResponse(
            status_code=status.HTTP_201_CREATED,
            content=BaseResponse(code=CodeEnum.CREATED, message=message, data=R._to_serializable(data, schema)).model_dump()
        )

    @staticmethod
    def fail(
        message: str = "失败",
        code: int = CodeEnum.BAD_REQUEST,
        data: Any = None,
        http_status: int = status.HTTP_200_OK
    ) -> JSONResponse:
        """失败响应"""
        return JSONResponse(
            status_code=http_status,
            content=BaseResponse(code=code, message=message, data=R._to_serializable(data)).model_dump()
        )

    @staticmethod
    def bad_request(message: str = "参数错误", data: Any = None) -> JSONResponse:
        return R.fail(message, CodeEnum.BAD_REQUEST, data)

    @staticmethod
    def unauthorized(message: str = "未授权，请先登录") -> JSONResponse:
        return R.fail(message, CodeEnum.UNAUTHORIZED, http_status=status.HTTP_401_UNAUTHORIZED)

    @staticmethod
    def forbidden(message: str = "权限不足") -> JSONResponse:
        return R.fail(message, CodeEnum.FORBIDDEN, http_status=status.HTTP_403_FORBIDDEN)

    @staticmethod
    def not_found(message: str = "资源不存在") -> JSONResponse:
        return R.fail(message, CodeEnum.NOT_FOUND, http_status=status.HTTP_404_NOT_FOUND)

    @staticmethod
    def conflict(message: str = "资源冲突") -> JSONResponse:
        return R.fail(message, CodeEnum.CONFLICT, http_status=status.HTTP_409_CONFLICT)

    @staticmethod
    def validation_error(message: str = "数据校验失败", data: Any = None) -> JSONResponse:
        return R.fail(message, CodeEnum.VALIDATION_ERROR, data, http_status=status.HTTP_422_UNPROCESSABLE_ENTITY)

    @staticmethod
    def server_error(message: str = "服务器内部错误") -> JSONResponse:
        return R.fail(message, CodeEnum.SERVER_ERROR, http_status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @staticmethod
    def page(
        items: list[Any],
        total: int,
        page: int = 1,
        size: int = 20,
        message: str = "成功",
        schema: Type[BaseModel] = None
    ) -> JSONResponse:
        """分页响应"""
        pages = (total + size - 1) // size if size > 0 else 0
        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content=PageResponse(
                code=CodeEnum.SUCCESS,
                message=message,
                data=[R._to_serializable(item, schema) for item in items],
                page_info=PageInfo(page=page, size=size, total=total, pages=pages)
            ).model_dump()
        )

    @staticmethod
    def custom(code: int, message: str, data: Any = None, http_status: int = 200, schema: Type[BaseModel] = None) -> JSONResponse:
        """自定义响应"""
        return JSONResponse(
            status_code=http_status,
            content=BaseResponse(code=code, message=message, data=R._to_serializable(data, schema)).model_dump()
        )


class BizException(HTTPException):
    """业务异常 - 用于在依赖注入/服务层抛出，由全局异常处理器捕获"""

    def __init__(
        self,
        message: str = "业务异常",
        code: int = CodeEnum.BAD_REQUEST,
        data: Any = None,
        http_status: int = status.HTTP_200_OK
    ):
        self.code = code
        self.message = message
        self.data = data
        super().__init__(status_code=http_status, detail=message)


def register_exception_handlers(app):
    """注册全局异常处理器"""
    from fastapi import Request
    from fastapi.exceptions import RequestValidationError
    from starlette.exceptions import HTTPException as StarletteHTTPException

    @app.exception_handler(BizException)
    async def biz_exception_handler(request: Request, exc: BizException):
        return R.fail(exc.message, exc.code, exc.data, exc.status_code)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        errors = []
        for e in exc.errors():
            loc = " -> ".join(str(x) for x in e["loc"])
            errors.append(f"{loc}: {e['msg']}")
        return R.validation_error("参数校验失败", "; ".join(errors))

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):
        if exc.status_code == 401:
            return R.unauthorized(exc.detail)
        elif exc.status_code == 403:
            return R.forbidden(exc.detail)
        elif exc.status_code == 404:
            return R.not_found(exc.detail)
        return R.fail(str(exc.detail), exc.status_code, http_status=exc.status_code)

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        import traceback
        traceback.print_exc()
        return R.server_error(f"服务器内部错误: {str(exc)}")