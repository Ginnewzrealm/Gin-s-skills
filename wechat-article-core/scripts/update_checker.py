import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def check_for_updates(skill_dir: Path) -> dict:
    """检查本地 skill 是否落后于远程仓库。"""
    last_check_file = skill_dir / ".last-update-check"
    now = datetime.now()

    if last_check_file.exists():
        last_check = datetime.fromtimestamp(last_check_file.stat().st_mtime)
        if now - last_check < timedelta(days=30):
            return {"status": "skipped", "reason": "最近 30 天内已检查"}

    last_check_file.touch()

    try:
        subprocess.run(["git", "fetch", "origin"], cwd=skill_dir, check=True, capture_output=True)
        local = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=skill_dir, check=True, capture_output=True, text=True
        ).stdout.strip()
        remote = subprocess.run(
            ["git", "rev-parse", "origin/HEAD"], cwd=skill_dir, check=True, capture_output=True, text=True
        ).stdout.strip()

        if local != remote:
            return {"status": "behind", "local": local, "remote": remote}
        return {"status": "up_to_date"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
