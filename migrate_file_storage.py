"""
一次性迁移脚本: 将 file/admin/ 迁移到 file/{user_id}/
运行前请备份 file/ 目录和数据库
"""
import os
import shutil
from pathlib import Path
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import CloudFile, User, UserRole
from app.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url)
Session = sessionmaker(bind=engine)

FILE_DIR = Path("file")


def migrate():
    db = Session()

    admin_dir = FILE_DIR / "admin"
    if admin_dir.exists():
        admin_user = db.query(User).filter(User.role == UserRole.ADMIN).first()
        if not admin_user:
            print("未找到管理员用户，跳过")
        else:
            target_dir = FILE_DIR / str(admin_user.id)
            target_dir.mkdir(parents=True, exist_ok=True)

            files = db.query(CloudFile).all()
            for cf in files:
                old_path = Path(cf.file_path)
                if old_path.exists():
                    new_path = target_dir / cf.stored_name
                    shutil.copy2(old_path, new_path)
                    cf.file_path = str(new_path)
                    print(f"迁移: {old_path} -> {new_path}")
                else:
                    print(f"警告: 文件不存在 {old_path}")

            db.commit()

    db.commit()
    db.close()
    print("迁移完成!")


if __name__ == "__main__":
    migrate()
