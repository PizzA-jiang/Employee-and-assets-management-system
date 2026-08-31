import os
import shutil
from pathlib import Path

FILE_BASE_DIR = Path("file")


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_private_dir(user_id: int) -> Path:
    d = FILE_BASE_DIR / str(user_id)
    ensure_dir(d)
    return d


def get_share_dir(share_id: int) -> Path:
    d = FILE_BASE_DIR / "share" / str(share_id)
    ensure_dir(d)
    return d


def save_private_file(user_id: int, stored_name: str, content: bytes) -> str:
    upload_dir = get_private_dir(user_id)
    file_path = upload_dir / stored_name
    with open(file_path, "wb") as f:
        f.write(content)
    return str(file_path)


def copy_file_to_share(source_path: str, share_id: int, stored_name: str) -> str:
    share_dir = get_share_dir(share_id)
    dest_path = share_dir / stored_name
    shutil.copy2(source_path, dest_path)
    return str(dest_path)


def delete_file(file_path: str) -> bool:
    if os.path.exists(file_path):
        os.remove(file_path)
        return True
    return False


def delete_share_dir(share_id: int) -> bool:
    share_dir = FILE_BASE_DIR / "share" / str(share_id)
    if share_dir.exists() and share_dir.is_dir():
        shutil.rmtree(share_dir)
        return True
    return False
