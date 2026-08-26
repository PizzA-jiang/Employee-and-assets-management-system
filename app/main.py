from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import get_settings
from app.database import engine, Base
from app.routers import auth, employees, assets, asset_logs, dashboard
from app.utils.response import register_exception_handlers

settings = get_settings()
#主页面启动
# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    debug=settings.debug,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, prefix="/api")
app.include_router(employees.router, prefix="/api")
app.include_router(assets.router, prefix="/api")
app.include_router(asset_logs.router, prefix="/api")
app.include_router(dashboard.router, prefix="/api")

# Register exception handlers
register_exception_handlers(app)


@app.get("/")
def root():
    return {
        "message": "企业资产管理后台系统 API",
        "version": settings.app_version,
        "docs": "/docs",
        "redoc": "/redoc",
    }


@app.get("/health")
def health_check():
    return {"status": "ok"}