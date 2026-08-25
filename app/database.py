from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy.exc import OperationalError
from app.config import get_settings
import urllib.parse

settings = get_settings()

def create_database_if_not_exists():
    """Create database if it doesn't exist"""
    # Parse the database URL to extract connection info without database name
    parsed = urllib.parse.urlparse(settings.database_url)
    db_name = parsed.path.lstrip('/')
    # Create URL without database name
    base_url = f"{parsed.scheme}://{parsed.netloc}/?charset=utf8mb4"
    
    temp_engine = create_engine(base_url, pool_pre_ping=True)
    try:
        with temp_engine.connect() as conn:
            conn.execute(text(f"CREATE DATABASE IF NOT EXISTS `{db_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"))
            conn.commit()
    except Exception:
        pass  # Ignore errors, maybe database already exists or no permission
    finally:
        temp_engine.dispose()

# Create database if not exists
create_database_if_not_exists()

engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()