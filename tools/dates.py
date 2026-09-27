"""게시물 폴더가 저장소에 추가된 시점을 읽는다.

접두사가 없는 게시물은 이 시각의 내림차순으로 정렬된다.
얕은 클론에서는 이력이 잘려 값이 부정확해지므로,
워크플로의 checkout은 fetch-depth: 0 이어야 한다.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path


def _now() -> datetime:
    return datetime.now(timezone.utc).astimezone()


def git_added_at(repo_root: Path, path: Path) -> datetime:
    """폴더가 추가된 커밋 시각. 알 수 없으면 현재 시각."""
    try:
        completed = subprocess.run(
            ["git", "log", "--diff-filter=A", "--format=%cI", "-1", "--", str(path)],
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return _now()

    if completed.returncode != 0:
        return _now()

    lines = [line for line in completed.stdout.strip().splitlines() if line.strip()]
    if not lines:
        return _now()

    try:
        return datetime.fromisoformat(lines[0].strip())
    except ValueError:
        return _now()
