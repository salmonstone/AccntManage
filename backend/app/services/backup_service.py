from __future__ import annotations

import logging
import os
import shutil
from datetime import datetime, timezone
from pathlib import Path

from backend.app.core.config import settings

logger = logging.getLogger(__name__)

BACKUP_DIR = Path("data/backups")


class BackupService:
    def __init__(self) -> None:
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    async def create_backup(self) -> str:
        db_path = settings.DATABASE_URL.split("///")[-1]
        if not Path(db_path).exists():
            raise ValueError("Database file not found")

        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{ts}.db"
        backup_path = BACKUP_DIR / backup_name
        shutil.copy2(db_path, str(backup_path))
        logger.info("Backup created: %s", backup_name)
        return backup_name

    def list_backups(self) -> list[dict]:
        backups = []
        for f in sorted(BACKUP_DIR.glob("backup_*.db"), reverse=True):
            stat = f.stat()
            backups.append({
                "name": f.name,
                "size_bytes": stat.st_size,
                "created_at": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat(),
            })
        return backups

    def delete_backup(self, name: str) -> None:
        safe_name = Path(name).name
        if safe_name != name or ".." in name:
            raise ValueError("Invalid backup name")
        path = BACKUP_DIR / safe_name
        if not path.exists():
            raise ValueError("Backup not found")
        path.unlink()

    def cleanup_old_backups(self) -> int:
        cutoff = datetime.now(timezone.utc).timestamp() - (settings.BACKUP_RETENTION_DAYS * 86400)
        removed = 0
        for f in BACKUP_DIR.glob("backup_*.db"):
            if f.stat().st_mtime < cutoff:
                f.unlink()
                removed += 1
        return removed
