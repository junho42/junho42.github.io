"""포트폴리오 빌드 진입점.

  python portfolio/tools/build.py            # 전체 빌드
  python portfolio/tools/build.py --check    # 생성물의 참조만 검증

경고는 출력하되 빌드를 멈추지 않는다. 종료 코드가 0이 아닌 경우는
설정 파일을 읽을 수 없을 때와 참조가 깨졌을 때뿐이다.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# 이 스크립트는 한글 메시지를 출력한다. Windows 콘솔은 로캘에 따라
# 기본 스트림 인코딩이 CP949 등으로 잡히므로, 그대로 두면 이 스크립트를
# UTF-8로 디코딩하는 호출자(예: subprocess 로 결과를 읽는 CI/테스트)에서
# 깨진 바이트로 크래시한다. 표준 스트림이 없는 실행 방식(pythonw 등)에서도
# 안전하도록 존재 여부와 실패를 모두 허용한다.
for _stream in (sys.stdout, sys.stderr):
    if _stream is not None and hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError, OSError):
            pass

from dates import git_added_at  # noqa: E402
from linkcheck import check_links  # noqa: E402
from images import SYMBOL_WIDTH, image_size, make_symbol, needs_rebuild  # noqa: E402
from manifest import build_manifest, write_manifest  # noqa: E402
from render import render_site  # noqa: E402
from scanner import scan  # noqa: E402
from textfile import join_paragraphs  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _load_config(site_root: Path) -> dict:
    return json.loads((site_root / "site.config.json").read_text(encoding="utf-8"))


# define.json — 페이지 제목과 연락처. 작가가 가장 자주 고칠 값만 따로 모았다.
DEFINE_FIELDS = (
    "title", "email", "instagram", "name", "phone", "address",
    "contact-title", "contact-content",
)
# 단락 목록(["첫 단락", "둘째 단락"])으로도 적을 수 있는 항목
DEFINE_PARAGRAPH_FIELDS = ("contact-content",)
# define.json의 이름 → 렌더러가 읽는 설정 이름. 나머지는 이름이 같다.
DEFINE_RENAMES = {"contact-title": "contactTitle", "contact-content": "contactNote"}


def _load_define(site_root: Path) -> tuple[dict, list[str]]:
    """define.json을 읽어 (값, 경고)를 돌려준다. 파일이 없으면 빈 값이다.

    문법 오류는 json.JSONDecodeError로 그대로 올려 build()가 줄 번호와
    함께 알리게 한다 — 연락처가 조용히 사라지는 것보다 빌드가 멈추는 편이 낫다.
    """
    path = site_root / "define.json"
    if not path.exists():
        return {}, []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        return {}, ["define.json: { }로 감싼 형식이 아니어서 무시합니다"]
    values: dict[str, str] = {}
    warnings: list[str] = []
    for key in DEFINE_FIELDS:
        value = data.get(key)
        if value is None:
            continue
        if key in DEFINE_PARAGRAPH_FIELDS:
            value = join_paragraphs(value)
            if value is None:
                warnings.append(
                    f"define.json: {key} 값은 글자 또는 [\"단락\", \"단락\"] 목록이어야 해서 무시합니다"
                )
                continue
        elif not isinstance(value, str):
            warnings.append(f"define.json: {key} 값은 따옴표로 감싼 글자여야 해서 무시합니다")
            continue
        values[key] = value.strip()
    return values, warnings


# Contact 왼쪽 심볼의 원본. 이 파일만 바꿔 넣으면 다음 빌드에서 웹용
# 사본이 다시 만들어진다. 사본은 media/_site/ 에 둔다 — media/ 는 워크플로가
# 커밋하는 산출물 폴더이고, "_"로 시작하는 이름은 작업물 폴더가 쓸 수 없어
# (scanner._visible) 게시물 주소와 겹치지 않는다.
SYMBOL_SOURCE = Path("assets") / "img" / "faran_symbol.png"
SYMBOL_DEST = Path("media") / "_site" / f"faran_symbol-{SYMBOL_WIDTH}.webp"


def _build_symbol(site_root: Path) -> tuple[dict | None, list[str]]:
    """심볼 웹용 사본을 만들고 ({src, w, h}, 경고)를 돌려준다. 원본이 없으면 None."""
    source = site_root / SYMBOL_SOURCE
    if not source.exists():
        return None, []
    dest = site_root / SYMBOL_DEST
    try:
        size = make_symbol(source, dest) if needs_rebuild(source, dest) else image_size(dest)
    except OSError as exc:
        return None, [f"{SYMBOL_SOURCE.as_posix()}: 심볼 이미지를 열 수 없어 Contact에서 뺐습니다 ({exc})"]
    return {"src": SYMBOL_DEST.as_posix(), "w": size[0], "h": size[1]}, []


def _repo_root(site_root: Path) -> Path:
    """게시물 날짜 조회(dates.git_added_at)에 넘길 git 저장소 루트를 찾는다.

    스펙 12장의 이전 절차 1단계("portfolio/를 새 저장소 루트로 복사")를
    거치면 site_root 자체가 저장소 루트가 되어, site_root.parent는
    저장소 밖의 상위 디렉터리가 된다. git이 실제 루트를 답할 수 있으면
    그 값을 쓰고, 저장소가 아니거나 git이 없으면 기존 동작(부모 디렉터리)
    으로 대체한다 — 저장소가 아닌 임시 디렉터리를 쓰는 기존 테스트들도
    이 대체 경로를 그대로 탄다.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(site_root),
            capture_output=True,
            # git은 경로를 UTF-8로 찍는다. text=True만 쓰면 Windows
            # 로캘(예: cp949)로 잘못 디코딩돼 한글이 섞인 경로가 깨진다.
            encoding="utf-8",
            errors="replace",
            timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return site_root.parent

    if completed.returncode != 0:
        return site_root.parent

    output = completed.stdout.strip()
    if not output:
        return site_root.parent
    # git이 내놓는 경로는 (Windows에서도) 슬래시 형태다. Path.resolve()로
    # 정규화해 site_root.resolve()와 드라이브 문자·구분자가 어긋나지 않게 한다.
    return Path(output).resolve()


def _collect_pages(site_root: Path) -> list[Path]:
    pages = [site_root / name for name in ("index.html", "contact.html")]
    pages += sorted((site_root / "works").rglob("index.html"))
    return [page for page in pages if page.exists()]


def build(site_root: Path, repo_root: Path) -> tuple[int, list[str]]:
    # README는 작가에게 GitHub 웹 UI에서 이 파일을 직접 고치라고 안내한다.
    # 쉼표 하나, 스마트 쿼트 하나로도 깨질 수 있는 자리이므로, 원시
    # 파이썬 트레이스백 대신 어디를 봐야 하는지 알려준다.
    try:
        config = _load_config(site_root)
    except OSError as exc:
        return 1, [f"site.config.json을 읽을 수 없습니다: {exc}"]
    except json.JSONDecodeError as exc:
        return 1, [f"site.config.json의 {exc.lineno}번째 줄에 문법 오류가 있습니다: {exc.msg}"]

    try:
        define, define_warnings = _load_define(site_root)
    except OSError as exc:
        return 1, [f"define.json을 읽을 수 없습니다: {exc}"]
    except json.JSONDecodeError as exc:
        return 1, [f"define.json의 {exc.lineno}번째 줄에 문법 오류가 있습니다: {exc.msg}"]
    # define.json이 site.config.json보다 우선한다.
    config = {**config, **{DEFINE_RENAMES.get(key, key): value for key, value in define.items()}}

    works, warnings = scan(site_root / "upload")
    warnings = define_warnings + warnings

    for work in works:
        work.date = git_added_at(repo_root, work.directory)

    manifest, media_warnings = build_manifest(
        works,
        site_root / "media",
        datetime.now(timezone.utc).astimezone(),
    )
    warnings.extend(media_warnings)
    write_manifest(manifest, site_root / "works.json")

    symbol, symbol_warnings = _build_symbol(site_root)
    warnings.extend(symbol_warnings)
    config["symbol"] = symbol

    pages, render_warnings = render_site(
        manifest, config, site_root, site_root / "templates"
    )
    warnings.extend(render_warnings)

    errors = check_links(site_root, pages)
    messages = [f"게시물 {len(manifest['works'])}개, 페이지 {len(pages)}개 생성"]
    return (1 if errors else 0), messages + warnings + errors


def check_only(site_root: Path) -> tuple[int, list[str]]:
    pages = _collect_pages(site_root)
    if not pages:
        return 1, ["생성된 페이지가 없습니다. 먼저 빌드하세요."]
    errors = check_links(site_root, pages)
    if errors:
        return 1, errors
    return 0, [f"페이지 {len(pages)}개의 참조를 모두 확인했습니다"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="포트폴리오 정적 사이트 빌드")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="portfolio 디렉터리")
    parser.add_argument("--check", action="store_true", help="빌드 없이 참조만 검증")
    arguments = parser.parse_args(argv)

    site_root = arguments.root.resolve()
    repo_root = _repo_root(site_root)

    if arguments.check:
        code, messages = check_only(site_root)
    else:
        code, messages = build(site_root, repo_root)

    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
