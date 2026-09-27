import os
import subprocess
from datetime import datetime, timezone

from dates import git_added_at


def _git(repo, *args, env=None):
    """Run git command with optional environment variables merged over os.environ."""
    git_env = os.environ.copy()
    if env:
        git_env.update(env)
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True, env=git_env)


def test_폴더가_추가된_커밋_시각을_읽는다(tmp_path):
    repo = tmp_path / "repo"
    (repo / "work").mkdir(parents=True)
    (repo / "work" / "a.txt").write_text("a", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")

    # Seed a specific commit timestamp 30 days in the past
    specific_time = datetime(2026, 8, 28, 14, 30, 0, tzinfo=timezone.utc)
    iso_time = specific_time.isoformat()
    _git(repo, "commit", "-q", "-m", "add work",
         env={"GIT_AUTHOR_DATE": iso_time, "GIT_COMMITTER_DATE": iso_time})

    result = git_added_at(repo, repo / "work")

    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    # 결과는 설정한 커밋 시각과 같아야 한다 (git의 timestamp 정확도 범위 내에서)
    assert abs((specific_time - result).total_seconds()) < 5


def test_이력이_없으면_현재_시각으로_대체한다(tmp_path):
    repo = tmp_path / "repo"
    (repo / "work").mkdir(parents=True)
    _git(repo, "init", "-q")

    result = git_added_at(repo, repo / "work")

    assert result.tzinfo is not None
    assert abs((datetime.now(timezone.utc) - result).total_seconds()) < 60


def test_git_저장소가_아니어도_예외를_내지_않는다(tmp_path):
    result = git_added_at(tmp_path, tmp_path / "없는폴더")
    assert result.tzinfo is not None
