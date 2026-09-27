# 컬러리스트 포트폴리오 사이트 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 색보정 작가가 `portfolio/upload/`에 폴더만 올리면 카테고리별 그리드 목록과 게시물 페이지가 자동 생성되는, Jekyll과 절연된 정적 포트폴리오 사이트를 만든다.

**Architecture:** `portfolio/upload/<카테고리>/<게시물>/` 2단 폴더를 Python 스크립트가 스캔해 `works.json`(manifest)과 모든 HTML을 생성한다. 생성물은 작가의 업로드 영역과 분리된 `portfolio/works/`·`portfolio/media/`에 쌓이고, GitHub Actions가 푸시마다 그 스크립트를 돌려 결과를 커밋한다. 산출물은 front matter도 Liquid도 없는 순수 정적 파일이라 Jekyll이 바이트 그대로 통과시키며, 폴더째 다른 호스팅으로 옮길 수 있다.

**Tech Stack:** Python 3.12 + Pillow(이미지 리사이즈)만 사용. 템플릿 엔진 없이 `{{TOKEN}}` 치환. 프런트엔드는 의존성 없는 순수 HTML/CSS/JS. 테스트는 pytest. CI는 GitHub Actions(ubuntu-latest).

**Spec:** [docs/superpowers/specs/2026-09-27-colorist-portfolio-design.md](../specs/2026-09-27-colorist-portfolio-design.md)

## Global Constraints

모든 태스크의 요구사항에 아래가 암묵적으로 포함된다.

- **front matter(`---`)와 Liquid 문법(`{{ site.x }}`, `{% ... %}`)을 `portfolio/` 안의 어떤 파일에도 쓰지 않는다.** 단, 생성기 자체의 토큰 치환 문법인 `{{TOKEN}}`은 템플릿 파일(`portfolio/templates/`) 안에서만 쓰며, 그 파일들은 Jekyll 배포에서 제외되고 생성된 HTML에는 `{{`가 하나도 남지 않아야 한다.
- **참조는 전부 상대경로.** 페이지 깊이에 맞는 접두사(`../../`)를 생성기가 계산해 넣는다. 루트 절대경로(`/assets/...`)와 Jekyll 변수는 금지. `file://`로 열어도 동작해야 한다.
- **생성 경로에 `_` 또는 `.` 접두사를 쓰지 않는다.** Jekyll이 산출물에서 제외해버린다.
- 외부 런타임 의존을 만들지 않는다. 웹폰트를 제외한 모든 자산은 저장소 안에 있어야 한다.
- Python 의존성은 **Pillow 하나**. 표준 라이브러리 외 다른 패키지를 추가하지 않는다.
- 다크 테마 고정. `prefers-color-scheme` 라이트 분기를 만들지 않는다.
- UI에 색을 쓰지 않는다. 배경은 거의 검정, 텍스트는 무채색 회색 계단. 화면에서 색을 가진 것은 작업물 이미지뿐이어야 한다.
- 모바일 우선. 좌우 여백 16px, 가로 스크롤이 생기지 않아야 한다.
- 이미지 크기 숫자는 모두 **가로 기준**: 커버 600px(16:9 크롭), 갤러리 1600px(비율 유지), webp 품질 82.
- 파일은 UTF-8(BOM 없음)로 쓴다. 커밋은 태스크마다 한 번.
- 테스트 실행은 저장소 루트에서 `python -m pytest portfolio/tools/tests -v`.

---

### Task 1: 공간 준비와 Jekyll 절연

`lab/`을 `portfolio/`로 바꾸고, Jekyll이 업로드 원본과 소스 파일을 배포에서 빼도록 설정한다.

**Files:**
- Rename: `lab/` → `portfolio/`
- Delete: `portfolio/index.html`, `portfolio/css/style.css`, `portfolio/js/main.js` (플레이스홀더. 새 구조는 `assets/` 아래를 쓰고 `index.html`은 생성물이다)
- Modify: `_config.yml:47-61` (`exclude`와 `defaults`)
- Create: `portfolio/site.config.json`
- Create: `portfolio/upload/.gitkeep`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `portfolio/` 디렉터리 루트, `portfolio/site.config.json` (이후 모든 태스크가 이 경로를 기준으로 한다)

- [ ] **Step 1: 폴더 이름 변경과 플레이스홀더 제거**

```bash
cd /c/Users/oort_/Desktop/cloud/Develop/cloud1202.github.io
git mv lab portfolio
git rm -q portfolio/index.html portfolio/css/style.css portfolio/js/main.js
rmdir portfolio/css portfolio/js 2>/dev/null
mkdir -p portfolio/upload
touch portfolio/upload/.gitkeep
```

- [ ] **Step 2: `_config.yml`의 `exclude`를 수정**

`exclude:` 블록을 아래로 바꾼다. `upload/`는 원본 이미지를 웹에 노출하지 않기 위해, `templates/`와 `tools/`는 소스 파일이 배포될 이유가 없어서 제외한다.

```yaml
exclude:
  - docs/
  - portfolio/upload/
  - portfolio/templates/
  - portfolio/tools/
```

- [ ] **Step 3: `_config.yml`의 sitemap 제외 경로를 `lab` → `portfolio`로 수정**

```yaml
  # portfolio/ is a standalone space outside the Jekyll site - keep it out of sitemap.xml
  -
    scope:
      path: "portfolio"
    values:
      sitemap: false
```

- [ ] **Step 4: `portfolio/site.config.json` 작성**

지인에게 받기 전까지는 플레이스홀더다. `siteUrl`은 OG 태그의 절대 URL 생성에만 쓰고, 이전할 때 이 값과 `noindex`만 바꾼다.

```json
{
  "siteName": "NAME",
  "tagline": "Color Grading — Video & Photo",
  "siteUrl": "https://cloud1202.github.io/portfolio",
  "email": "hello@example.com",
  "instagram": "",
  "about": "소개 문단이 들어갑니다.\n\n빈 줄로 단락을 나눕니다.",
  "contactNote": "작업 문의는 이메일로 받습니다.",
  "gridPageSize": 8,
  "noindex": true,
  "ogImage": ""
}
```

- [ ] **Step 5: Jekyll 빌드로 절연을 검증**

Run:

```bash
bundle exec jekyll build --quiet
test ! -e _site/portfolio/upload && echo "OK: upload 미배포"
test ! -e _site/portfolio/tools && echo "OK: tools 미배포"
grep -c 'portfolio' _site/sitemap.xml || echo "OK: sitemap에 portfolio 없음"
```

Expected: `OK: upload 미배포`, `OK: tools 미배포`, `OK: sitemap에 portfolio 없음` 세 줄이 모두 나온다. `grep -c`가 0이 아닌 수를 출력하면 Step 3이 잘못된 것이다.

- [ ] **Step 6: 커밋**

```bash
git add -A portfolio _config.yml
git commit -m "chore: lab을 portfolio로 전환하고 Jekyll 배포에서 소스·원본 제외"
```

---

### Task 2: 이름 규칙 모듈 (`naming.py`)

폴더 이름에서 순서 접두사를 떼고, 자연 정렬 키를 만들고, 슬러그 충돌을 해소한다.

**Files:**
- Create: `portfolio/tools/naming.py`
- Create: `portfolio/tools/tests/conftest.py`
- Test: `portfolio/tools/tests/test_naming.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `strip_order_prefix(name: str) -> tuple[int | None, str]` — `("01_화보")` → `(1, "화보")`, 접두사가 없으면 `(None, name)`
  - `natural_key(name: str) -> list` — `sorted(key=natural_key)`에 쓰는 자연 정렬 키
  - `dedupe_slug(slug: str, taken: set[str]) -> str` — 충돌 시 `-2`, `-3` 접미사

- [ ] **Step 1: `conftest.py`로 import 경로를 열어준다**

`portfolio/tools/tests/conftest.py`:

```python
"""테스트가 tools/ 모듈을 import할 수 있게 경로를 넣는다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
```

- [ ] **Step 2: 실패하는 테스트 작성**

`portfolio/tools/tests/test_naming.py`:

```python
from naming import strip_order_prefix, natural_key, dedupe_slug


def test_밑줄_접두사를_떼고_숫자를_돌려준다():
    assert strip_order_prefix("01_화보") == (1, "화보")


def test_점과_하이픈_접두사도_인식한다():
    assert strip_order_prefix("10.뮤직비디오") == (10, "뮤직비디오")
    assert strip_order_prefix("2-단편영화") == (2, "단편영화")


def test_접두사가_없으면_이름을_그대로_돌려준다():
    assert strip_order_prefix("TAEMIN-Guilty") == (None, "TAEMIN-Guilty")


def test_구분자_없는_숫자로_시작하는_이름은_접두사가_아니다():
    # "2026웨딩스냅"의 2026은 제목의 일부다
    assert strip_order_prefix("2026웨딩스냅") == (None, "2026웨딩스냅")


def test_접두사_뒤_공백을_제거한다():
    assert strip_order_prefix("03_ 화보 ") == (3, "화보")


def test_자연_정렬은_숫자를_수로_비교한다():
    names = ["10.jpg", "2.jpg", "1.jpg"]
    assert sorted(names, key=natural_key) == ["1.jpg", "2.jpg", "10.jpg"]


def test_자연_정렬은_영문_대소문자를_구분하지_않는다():
    assert sorted(["b.jpg", "A.jpg"], key=natural_key) == ["A.jpg", "b.jpg"]


def test_자연_정렬은_숫자와_문자가_섞여도_예외를_내지_않는다():
    names = ["cover.jpg", "2.jpg", "img10.jpg", "img2.jpg"]
    assert sorted(names, key=natural_key) == ["2.jpg", "cover.jpg", "img2.jpg", "img10.jpg"]


def test_슬러그가_비어있으면_그대로_통과한다():
    assert dedupe_slug("화보", set()) == "화보"


def test_슬러그가_충돌하면_번호를_붙인다():
    assert dedupe_slug("화보", {"화보"}) == "화보-2"
    assert dedupe_slug("화보", {"화보", "화보-2"}) == "화보-3"
```

- [ ] **Step 3: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_naming.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'naming'`

- [ ] **Step 4: `naming.py` 구현**

```python
"""폴더 이름에서 순서 접두사와 제목을 분리하고, 목록 정렬 키를 만든다."""

from __future__ import annotations

import re

# "01_화보", "10.뮤직비디오", "2-단편영화" 형태만 접두사로 본다.
# 구분자가 없는 "2026웨딩스냅"은 제목의 일부이므로 건드리지 않는다.
_PREFIX = re.compile(r"^(\d+)\s*[_.\-]\s*(.+)$")
_DIGITS = re.compile(r"(\d+)")


def strip_order_prefix(name: str) -> tuple[int | None, str]:
    """(순서, 제목)을 돌려준다. 접두사가 없으면 순서는 None."""
    match = _PREFIX.match(name)
    if not match:
        return None, name
    return int(match.group(1)), match.group(2).strip()


def natural_key(name: str) -> list:
    """숫자를 수로 비교하는 정렬 키.

    re.split이 캡처 그룹으로 나누면 짝수 인덱스는 항상 문자열,
    홀수 인덱스는 항상 숫자가 되므로 타입이 어긋나 비교 오류가 나지 않는다.
    """
    return [
        int(part) if index % 2 else part.lower()
        for index, part in enumerate(_DIGITS.split(name))
    ]


def dedupe_slug(slug: str, taken: set[str]) -> str:
    """이미 쓰인 슬러그면 -2, -3을 붙여 비켜준다."""
    if slug not in taken:
        return slug
    suffix = 2
    while f"{slug}-{suffix}" in taken:
        suffix += 1
    return f"{slug}-{suffix}"
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_naming.py -v`
Expected: PASS — 10 passed

- [ ] **Step 6: 커밋**

```bash
git add portfolio/tools/naming.py portfolio/tools/tests/conftest.py portfolio/tools/tests/test_naming.py
git commit -m "feat(portfolio): 폴더 이름 접두사·자연정렬·슬러그 충돌 처리"
```

---

### Task 3: 텍스트 파일 읽기 (`textfile.py`)

작가가 메모장으로 저장한 txt를 인코딩과 무관하게 읽고, 본문 HTML로 바꾼다.

**Files:**
- Create: `portfolio/tools/textfile.py`
- Test: `portfolio/tools/tests/test_textfile.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `read_text(path: Path) -> tuple[str, str | None]` — `(본문, 경고 또는 None)`
  - `body_to_html(text: str) -> str` — 이스케이프된 `<p>` 단락 문자열

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_textfile.py`:

```python
from textfile import read_text, body_to_html


def test_UTF8_한글을_읽는다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("utf-8"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_BOM이_붙은_UTF8도_읽는다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("utf-8-sig"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_CP949_한글을_읽는다(tmp_path):
    # 윈도우 메모장이 'ANSI'로 저장하면 이 인코딩이 된다
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("cp949"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_판별_불가_바이트는_경고와_함께_복구한다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes(b"\xff\xfe\x00broken")
    text, warning = read_text(path)
    assert warning is not None
    assert "memo.txt" in warning
    assert text  # 빈 문자열이 아니어야 한다


def test_빈_줄이_단락을_나눈다():
    html = body_to_html("첫 단락\n\n두 번째 단락")
    assert html == "<p>첫 단락</p>\n<p>두 번째 단락</p>"


def test_단일_줄바꿈은_br이_된다():
    assert body_to_html("한 줄\n다음 줄") == "<p>한 줄<br>\n다음 줄</p>"


def test_HTML을_이스케이프한다():
    html = body_to_html('<script>alert("x")</script>')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_CRLF를_정규화한다():
    assert body_to_html("첫 단락\r\n\r\n두 번째") == "<p>첫 단락</p>\n<p>두 번째</p>"


def test_빈_본문은_빈_문자열():
    assert body_to_html("   \n\n  ") == ""
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_textfile.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'textfile'`

- [ ] **Step 3: `textfile.py` 구현**

```python
"""작가가 넣은 txt를 인코딩과 무관하게 읽고 본문 HTML로 바꾼다."""

from __future__ import annotations

import re
from html import escape
from pathlib import Path

# UTF-8을 먼저 시도한다. 순서를 바꾸면 UTF-8 한글이 CP949로도
# 디코딩되면서 깨진 글자가 조용히 통과한다.
_ENCODINGS = ("utf-8-sig", "cp949")

_PARAGRAPH_BREAK = re.compile(r"\n\s*\n")


def read_text(path: Path) -> tuple[str, str | None]:
    """(본문, 경고)를 돌려준다. 경고가 None이면 정상 판별이다."""
    raw = path.read_bytes()
    for encoding in _ENCODINGS:
        try:
            return raw.decode(encoding), None
        except UnicodeDecodeError:
            continue
    recovered = raw.decode("utf-8", errors="replace")
    return recovered, f"{path.name}: 인코딩을 판별하지 못해 일부 문자를 대체했습니다"


def body_to_html(text: str) -> str:
    """빈 줄을 단락으로, 단일 줄바꿈을 <br>로 바꾼다. 전부 이스케이프한다."""
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return ""

    paragraphs = []
    for block in _PARAGRAPH_BREAK.split(normalized):
        lines = [escape(line.strip()) for line in block.split("\n") if line.strip()]
        if lines:
            paragraphs.append("<p>" + "<br>\n".join(lines) + "</p>")
    return "\n".join(paragraphs)
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_textfile.py -v`
Expected: PASS — 9 passed

- [ ] **Step 5: 커밋**

```bash
git add portfolio/tools/textfile.py portfolio/tools/tests/test_textfile.py
git commit -m "feat(portfolio): txt 인코딩 폴백과 본문 HTML 변환"
```

---

### Task 4: 영상 링크 파싱 (`video.py`)

`link.txt`의 주소를 임베드 가능한 형태로 바꾼다.

**Files:**
- Create: `portfolio/tools/video.py`
- Test: `portfolio/tools/tests/test_video.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `parse_video_url(url: str) -> dict | None` — `{"kind": "youtube"|"vimeo"|"link", "id": str|None, "embed": str|None, "url": str}`. URL이 아니면 `None`.

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_video.py`:

```python
from video import parse_video_url


def test_youtu_be_단축주소():
    result = parse_video_url("https://youtu.be/dQw4w9WgXcQ")
    assert result["kind"] == "youtube"
    assert result["id"] == "dQw4w9WgXcQ"
    assert result["embed"] == "https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ"


def test_watch_주소():
    result = parse_video_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=10s")
    assert result["kind"] == "youtube"
    assert result["id"] == "dQw4w9WgXcQ"


def test_shorts_주소():
    result = parse_video_url("https://www.youtube.com/shorts/dQw4w9WgXcQ")
    assert result["kind"] == "youtube"
    assert result["id"] == "dQw4w9WgXcQ"


def test_vimeo_주소():
    result = parse_video_url("https://vimeo.com/123456789")
    assert result["kind"] == "vimeo"
    assert result["id"] == "123456789"
    assert result["embed"] == "https://player.vimeo.com/video/123456789"


def test_모르는_주소는_링크로_남긴다():
    result = parse_video_url("https://example.com/my-reel")
    assert result["kind"] == "link"
    assert result["embed"] is None
    assert result["url"] == "https://example.com/my-reel"


def test_주소가_아니면_None():
    assert parse_video_url("영상 없음") is None
    assert parse_video_url("") is None


def test_앞뒤_공백을_무시한다():
    result = parse_video_url("  https://youtu.be/dQw4w9WgXcQ  \n")
    assert result["kind"] == "youtube"
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_video.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'video'`

- [ ] **Step 3: `video.py` 구현**

```python
"""link.txt의 주소를 임베드 가능한 형태로 바꾼다."""

from __future__ import annotations

import re
from urllib.parse import parse_qs, urlparse

_YOUTUBE_HOSTS = {
    "youtube.com",
    "www.youtube.com",
    "m.youtube.com",
    "youtu.be",
    "www.youtu.be",
    "youtube-nocookie.com",
    "www.youtube-nocookie.com",
}
_VIMEO_HOSTS = {"vimeo.com", "www.vimeo.com", "player.vimeo.com"}

_YOUTUBE_ID = re.compile(r"^[A-Za-z0-9_-]{6,}$")


def _youtube_id(parsed) -> str | None:
    host = parsed.netloc.lower()
    if host.endswith("youtu.be"):
        candidate = parsed.path.strip("/").split("/")[0]
    elif parsed.path.startswith("/watch"):
        candidate = (parse_qs(parsed.query).get("v") or [""])[0]
    elif parsed.path.startswith(("/shorts/", "/embed/", "/live/")):
        parts = parsed.path.strip("/").split("/")
        candidate = parts[1] if len(parts) > 1 else ""
    else:
        candidate = ""
    return candidate if _YOUTUBE_ID.match(candidate) else None


def parse_video_url(url: str) -> dict | None:
    """영상 정보를 돌려준다. 주소 형태가 아니면 None."""
    url = (url or "").strip()
    if not url.startswith(("http://", "https://")):
        return None

    parsed = urlparse(url)
    host = parsed.netloc.lower()

    if host in _YOUTUBE_HOSTS:
        video_id = _youtube_id(parsed)
        if video_id:
            return {
                "kind": "youtube",
                "id": video_id,
                "embed": f"https://www.youtube-nocookie.com/embed/{video_id}",
                "url": url,
            }

    if host in _VIMEO_HOSTS:
        match = re.search(r"/(\d+)", parsed.path)
        if match:
            return {
                "kind": "vimeo",
                "id": match.group(1),
                "embed": f"https://player.vimeo.com/video/{match.group(1)}",
                "url": url,
            }

    return {"kind": "link", "id": None, "embed": None, "url": url}
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_video.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: 커밋**

```bash
git add portfolio/tools/video.py portfolio/tools/tests/test_video.py
git commit -m "feat(portfolio): YouTube·Vimeo 링크 임베드 변환"
```

---

### Task 5: 업로드 시점 조회 (`dates.py`)

접두사 없는 게시물의 정렬 기준인 "폴더가 추가된 시점"을 git 이력에서 읽는다.

**Files:**
- Create: `portfolio/tools/dates.py`
- Test: `portfolio/tools/tests/test_dates.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `git_added_at(repo_root: Path, path: Path) -> datetime` — 타임존이 붙은 datetime. git 이력이 없거나 git 실행이 실패하면 현재 시각.

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_dates.py`:

```python
import subprocess
from datetime import datetime, timezone

from dates import git_added_at


def _git(repo, *args):
    subprocess.run(["git", *args], cwd=str(repo), check=True, capture_output=True)


def test_폴더가_추가된_커밋_시각을_읽는다(tmp_path):
    repo = tmp_path / "repo"
    (repo / "work").mkdir(parents=True)
    (repo / "work" / "a.txt").write_text("a", encoding="utf-8")
    _git(repo, "init", "-q")
    _git(repo, "config", "user.email", "t@example.com")
    _git(repo, "config", "user.name", "t")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "add work")

    result = git_added_at(repo, repo / "work")

    assert isinstance(result, datetime)
    assert result.tzinfo is not None
    # 방금 만든 커밋이므로 현재와 하루 이상 벌어질 수 없다
    assert abs((datetime.now(timezone.utc) - result).total_seconds()) < 86400


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
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_dates.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'dates'`

- [ ] **Step 3: `dates.py` 구현**

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_dates.py -v`
Expected: PASS — 3 passed

- [ ] **Step 5: 커밋**

```bash
git add portfolio/tools/dates.py portfolio/tools/tests/test_dates.py
git commit -m "feat(portfolio): git 이력에서 게시물 추가 시점 조회"
```

---

### Task 6: 업로드 폴더 스캔 (`scanner.py`)

`upload/` 트리를 훑어 카테고리와 게시물 자료구조를 만든다. 파일시스템만 읽고 아무것도 쓰지 않는다.

**Files:**
- Create: `portfolio/tools/scanner.py`
- Test: `portfolio/tools/tests/test_scanner.py`

**Interfaces:**
- Consumes: `naming.strip_order_prefix`, `naming.natural_key`, `naming.dedupe_slug`, `textfile.read_text`, `textfile.body_to_html`, `video.parse_video_url`
- Produces:
  - `@dataclass Work`: `title: str`, `slug: str`, `order: int | None`, `directory: Path`, `images: list[Path]`, `cover: Path | None`, `video: dict | None`, `body: str`, `date: datetime | None = None`
  - `@dataclass Category`: `title: str`, `slug: str`, `order: int | None`, `directory: Path`, `works: list[Work]`
  - `scan(upload_dir: Path) -> tuple[list[Category], list[str]]` — `(카테고리 목록, 경고 목록)`
  - 상수 `IMAGE_EXTENSIONS: set[str]`, `VIDEO_EXTENSIONS: set[str]`

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_scanner.py`:

```python
from scanner import scan


def _make(root, relative, content=b"x"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def test_카테고리와_게시물을_2단으로_읽는다(tmp_path):
    _make(tmp_path, "01_화보/2026웨딩스냅/01.jpg")
    _make(tmp_path, "01_화보/2026웨딩스냅/02.jpg")

    categories, warnings = scan(tmp_path)

    assert [c.title for c in categories] == ["화보"]
    assert categories[0].order == 1
    assert [w.title for w in categories[0].works] == ["2026웨딩스냅"]
    assert len(categories[0].works[0].images) == 2
    assert warnings == []


def test_이미지는_자연_정렬된다(tmp_path):
    _make(tmp_path, "화보/작업/10.jpg")
    _make(tmp_path, "화보/작업/2.jpg")

    categories, _ = scan(tmp_path)

    names = [p.name for p in categories[0].works[0].images]
    assert names == ["2.jpg", "10.jpg"]


def test_cover_파일이_있으면_커버로_쓴다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _make(tmp_path, "화보/작업/cover.jpg")

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.cover.name == "cover.jpg"
    # 커버는 갤러리에서 빠진다
    assert [p.name for p in work.images] == ["01.jpg"]


def test_cover가_없으면_첫_이미지가_커버다(tmp_path):
    _make(tmp_path, "화보/작업/02.jpg")
    _make(tmp_path, "화보/작업/01.jpg")

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.cover.name == "01.jpg"
    # 커버로 쓰였어도 갤러리에는 남는다
    assert [p.name for p in work.images] == ["01.jpg", "02.jpg"]


def test_link_txt는_영상이_되고_본문에서_빠진다(tmp_path):
    _make(tmp_path, "뮤비/작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")
    _make(tmp_path, "뮤비/작업/memo.txt", "본문입니다".encode("utf-8"))

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.video["kind"] == "youtube"
    assert "본문입니다" in work.body
    assert "youtu.be" not in work.body


def test_mp4가_있으면_파일_영상으로_인식한다(tmp_path):
    _make(tmp_path, "뮤비/작업/reel.mp4")

    categories, _ = scan(tmp_path)

    assert categories[0].works[0].video["kind"] == "file"


def test_link_txt가_mp4보다_우선한다(tmp_path):
    _make(tmp_path, "뮤비/작업/reel.mp4")
    _make(tmp_path, "뮤비/작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")

    categories, _ = scan(tmp_path)

    assert categories[0].works[0].video["kind"] == "youtube"


def test_비어있는_게시물_폴더는_건너뛰고_경고한다(tmp_path):
    (tmp_path / "화보" / "빈작업").mkdir(parents=True)
    _make(tmp_path, "화보/정상작업/01.jpg")

    categories, warnings = scan(tmp_path)

    assert [w.title for w in categories[0].works] == ["정상작업"]
    assert any("빈작업" in w for w in warnings)


def test_카테고리_없이_업로드_루트에_놓인_파일은_경고한다(tmp_path):
    _make(tmp_path, "떠도는사진.jpg")

    categories, warnings = scan(tmp_path)

    assert categories == []
    assert any("떠도는사진.jpg" in w for w in warnings)


def test_점과_밑줄로_시작하는_항목은_무시한다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _make(tmp_path, "화보/작업/.DS_Store")
    _make(tmp_path, "화보/작업/_임시메모.txt", "무시".encode("utf-8"))
    _make(tmp_path, "_숨긴카테고리/작업/01.jpg")

    categories, _ = scan(tmp_path)

    assert [c.title for c in categories] == ["화보"]
    assert [p.name for p in categories[0].works[0].images] == ["01.jpg"]
    assert categories[0].works[0].body == ""


def test_같은_카테고리_안에서_슬러그가_충돌하면_번호를_붙인다(tmp_path):
    _make(tmp_path, "화보/01_작업/01.jpg")
    _make(tmp_path, "화보/02_작업/01.jpg")

    categories, warnings = scan(tmp_path)

    slugs = [w.slug for w in categories[0].works]
    assert slugs == ["작업", "작업-2"]
    assert any("작업" in w for w in warnings)


def test_업로드_폴더가_없으면_빈_결과와_경고(tmp_path):
    categories, warnings = scan(tmp_path / "없음")

    assert categories == []
    assert len(warnings) == 1


def test_카테고리는_접두사_순서로_정렬된다(tmp_path):
    _make(tmp_path, "02_뮤비/작업/01.jpg")
    _make(tmp_path, "01_화보/작업/01.jpg")
    _make(tmp_path, "잡다한것/작업/01.jpg")

    categories, _ = scan(tmp_path)

    # 접두사가 있는 것이 먼저, 그 뒤는 이름 순
    assert [c.title for c in categories] == ["화보", "뮤비", "잡다한것"]
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_scanner.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'scanner'`

- [ ] **Step 3: `scanner.py` 구현**

```python
"""upload/ 트리를 훑어 카테고리와 게시물 자료구조를 만든다.

파일시스템을 읽기만 한다. 이미지 변환·날짜 조회·렌더링은 하지 않는다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from naming import dedupe_slug, natural_key, strip_order_prefix
from textfile import body_to_html, read_text
from video import parse_video_url

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}

LINK_FILENAME = "link.txt"
COVER_STEM = "cover"


@dataclass
class Work:
    title: str
    slug: str
    order: int | None
    directory: Path
    images: list[Path] = field(default_factory=list)
    cover: Path | None = None
    video: dict | None = None
    body: str = ""
    date: datetime | None = None


@dataclass
class Category:
    title: str
    slug: str
    order: int | None
    directory: Path
    works: list[Work] = field(default_factory=list)


def _visible(path: Path) -> bool:
    """`.` 또는 `_`로 시작하는 항목은 없는 것으로 본다."""
    return not path.name.startswith((".", "_"))


def _sorted_children(directory: Path) -> list[Path]:
    return sorted(
        (child for child in directory.iterdir() if _visible(child)),
        key=lambda child: natural_key(child.name),
    )


def _read_work(directory: Path) -> tuple[Work | None, list[str]]:
    warnings: list[str] = []
    images: list[Path] = []
    videos: list[Path] = []
    body_files: list[Path] = []
    link_file: Path | None = None

    for child in _sorted_children(directory):
        if child.is_dir():
            warnings.append(f"{directory.name}/{child.name}: 게시물 안의 하위 폴더는 무시합니다")
            continue
        suffix = child.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images.append(child)
        elif suffix in VIDEO_EXTENSIONS:
            videos.append(child)
        elif suffix == ".txt":
            if child.name.lower() == LINK_FILENAME:
                link_file = child
            else:
                body_files.append(child)

    video: dict | None = None
    if link_file is not None:
        text, warning = read_text(link_file)
        if warning:
            warnings.append(warning)
        for line in text.splitlines():
            video = parse_video_url(line)
            if video:
                break
        if video is None:
            warnings.append(f"{directory.name}/{link_file.name}: 주소를 찾지 못했습니다")
    if video is None and videos:
        video = {"kind": "file", "id": None, "embed": None, "url": videos[0].name}

    if not images and video is None:
        return None, warnings + [f"{directory.name}: 이미지도 영상도 없어 건너뜁니다"]

    cover: Path | None = None
    for image in images:
        if image.stem.lower() == COVER_STEM:
            cover = image
            break
    if cover is not None:
        # 커버 전용 파일은 갤러리에서 뺀다
        images = [image for image in images if image != cover]
    elif images:
        cover = images[0]

    body_parts = []
    for body_file in body_files:
        text, warning = read_text(body_file)
        if warning:
            warnings.append(warning)
        html = body_to_html(text)
        if html:
            body_parts.append(html)

    order, title = strip_order_prefix(directory.name)
    return (
        Work(
            title=title,
            slug=title,
            order=order,
            directory=directory,
            images=images,
            cover=cover,
            video=video,
            body="\n".join(body_parts),
        ),
        warnings,
    )


def _category_sort_key(category: Category) -> tuple:
    # 접두사가 있는 카테고리가 먼저, 그 뒤는 이름 순
    return (0, category.order, []) if category.order is not None else (1, 0, natural_key(category.title))


def scan(upload_dir: Path) -> tuple[list[Category], list[str]]:
    """(카테고리 목록, 경고 목록)을 돌려준다. 예외를 던지지 않는다."""
    warnings: list[str] = []
    if not upload_dir.is_dir():
        return [], [f"업로드 폴더가 없습니다: {upload_dir}"]

    categories: list[Category] = []
    for entry in _sorted_children(upload_dir):
        if entry.is_file():
            warnings.append(f"{entry.name}: 카테고리 폴더 밖의 파일은 무시합니다")
            continue

        order, title = strip_order_prefix(entry.name)
        category = Category(title=title, slug=title, order=order, directory=entry)

        taken_slugs: set[str] = set()
        for child in _sorted_children(entry):
            if child.is_file():
                warnings.append(f"{entry.name}/{child.name}: 게시물 폴더 밖의 파일은 무시합니다")
                continue
            work, work_warnings = _read_work(child)
            warnings.extend(work_warnings)
            if work is None:
                continue
            unique = dedupe_slug(work.slug, taken_slugs)
            if unique != work.slug:
                warnings.append(f"{entry.name}/{work.title}: 주소가 겹쳐 {unique}로 바꿨습니다")
            work.slug = unique
            taken_slugs.add(unique)
            category.works.append(work)

        if category.works:
            categories.append(category)
        else:
            warnings.append(f"{entry.name}: 게시물이 없어 건너뜁니다")

    categories.sort(key=_category_sort_key)
    return categories, warnings
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_scanner.py -v`
Expected: PASS — 13 passed

- [ ] **Step 5: 전체 테스트를 돌려 회귀가 없는지 확인**

Run: `python -m pytest portfolio/tools/tests -v`
Expected: PASS — 42 passed

- [ ] **Step 6: 커밋**

```bash
git add portfolio/tools/scanner.py portfolio/tools/tests/test_scanner.py
git commit -m "feat(portfolio): 업로드 폴더 2단 스캔과 경고 수집"
```

---

### Task 7: 이미지 변환 (`images.py`)

커버를 16:9로 잘라 600px, 갤러리를 비율 유지 1600px webp로 만든다.

**Files:**
- Create: `portfolio/tools/images.py`
- Test: `portfolio/tools/tests/test_images.py`

**Interfaces:**
- Consumes: 없음 (Pillow만)
- Produces:
  - `needs_rebuild(source: Path, dest: Path) -> bool`
  - `image_size(path: Path) -> tuple[int, int]` — 이미 만들어둔 산출물의 크기를 읽는다(증분 처리용)
  - `make_cover(source: Path, dest: Path, width: int = 600) -> tuple[int, int]` — 16:9 가운데 크롭. 반환값은 `(가로, 세로)`
  - `make_gallery(source: Path, dest: Path, width: int = 1600) -> tuple[int, int]` — 비율 유지
  - `fetch_youtube_cover(video_id: str, dest: Path, opener=None) -> bool` — 성공 여부
  - 상수 `COVER_WIDTH = 600`, `GALLERY_WIDTH = 1600`, `WEBP_QUALITY = 82`

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_images.py`:

```python
import io

import pytest
from PIL import Image

from images import (
    COVER_WIDTH,
    fetch_youtube_cover,
    image_size,
    make_cover,
    make_gallery,
    needs_rebuild,
)


def _write_image(path, size, color=(120, 90, 60)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def test_커버는_16대9로_잘린다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (2000, 2000))
    dest = tmp_path / "out" / "cover-600.webp"

    size = make_cover(source, dest)

    assert size == (600, 338)
    with Image.open(dest) as image:
        assert image.size == (600, 338)
        assert image.format == "WEBP"


def test_커버는_원본보다_크게_늘리지_않는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (320, 320))
    dest = tmp_path / "out" / "cover-600.webp"

    size = make_cover(source, dest)

    assert size[0] == 320


def test_갤러리는_비율을_유지한다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (3000, 2000))
    dest = tmp_path / "out" / "01-1600.webp"

    size = make_gallery(source, dest)

    assert size == (1600, 1067)


def test_갤러리도_원본보다_크게_늘리지_않는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (800, 600))
    dest = tmp_path / "out" / "01-1600.webp"

    assert make_gallery(source, dest) == (800, 600)


def test_깨진_이미지는_예외를_던진다(tmp_path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")

    with pytest.raises(OSError):
        make_gallery(broken, tmp_path / "out.webp")


def test_산출물이_없으면_다시_만들어야_한다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (100, 100))
    assert needs_rebuild(source, tmp_path / "없음.webp") is True


def test_이미_만든_산출물의_크기를_읽는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (2400, 1600))
    dest = tmp_path / "out" / "cover-600.webp"
    make_cover(source, dest)

    assert image_size(dest) == (600, 338)


def test_산출물이_원본보다_새것이면_건너뛴다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (100, 100))
    dest = tmp_path / "out.webp"
    make_gallery(source, dest)
    import os

    os.utime(dest, (source.stat().st_mtime + 10, source.stat().st_mtime + 10))

    assert needs_rebuild(source, dest) is False


def test_유튜브_썸네일을_받아_저장한다(tmp_path):
    buffer = io.BytesIO()
    Image.new("RGB", (1280, 720), (10, 10, 10)).save(buffer, format="JPEG")
    payload = buffer.getvalue()

    def fake_opener(url, timeout=0):
        assert "dQw4w9WgXcQ" in url

        class Response:
            def read(self):
                return payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Response()

    dest = tmp_path / "out" / "cover-600.webp"
    assert fetch_youtube_cover("dQw4w9WgXcQ", dest, opener=fake_opener) is True
    with Image.open(dest) as image:
        assert image.size == (COVER_WIDTH, 338)


def test_유튜브_썸네일을_못_받으면_False(tmp_path):
    def failing_opener(url, timeout=0):
        raise OSError("404")

    dest = tmp_path / "out" / "cover-600.webp"
    assert fetch_youtube_cover("dQw4w9WgXcQ", dest, opener=failing_opener) is False
    assert not dest.exists()
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_images.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'images'`

- [ ] **Step 3: `images.py` 구현**

```python
"""업로드된 원본을 웹용 webp로 바꾼다.

원본은 절대 수정하지 않는다. 산출물은 media/ 아래에만 쓴다.
"""

from __future__ import annotations

import io
from pathlib import Path
from urllib.request import urlopen

from PIL import Image, ImageOps

COVER_WIDTH = 600
GALLERY_WIDTH = 1600
WEBP_QUALITY = 82
COVER_RATIO = (16, 9)

_YOUTUBE_THUMBNAILS = (
    "https://i.ytimg.com/vi/{id}/maxresdefault.jpg",
    "https://i.ytimg.com/vi/{id}/hqdefault.jpg",
)


def needs_rebuild(source: Path, dest: Path) -> bool:
    """산출물이 없거나 원본보다 오래됐으면 다시 만든다."""
    if not dest.exists():
        return True
    return dest.stat().st_mtime < source.stat().st_mtime


def image_size(path: Path) -> tuple[int, int]:
    """이미 만들어둔 산출물의 크기만 읽는다. 다시 만들지 않을 때 쓴다."""
    with Image.open(path) as image:
        return image.size


def _load(source: Path) -> Image.Image:
    with Image.open(source) as image:
        image.load()
        return ImageOps.exif_transpose(image).convert("RGB")


def _save(image: Image.Image, dest: Path) -> tuple[int, int]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    image.save(dest, "WEBP", quality=WEBP_QUALITY, method=6)
    return image.size


def make_cover(source: Path, dest: Path, width: int = COVER_WIDTH) -> tuple[int, int]:
    """16:9로 가운데를 잘라 저장한다. 원본보다 크게 늘리지 않는다."""
    image = _load(source)
    target_width = min(width, image.width)
    target_height = max(1, round(target_width * COVER_RATIO[1] / COVER_RATIO[0]))
    fitted = ImageOps.fit(
        image,
        (target_width, target_height),
        method=Image.LANCZOS,
        centering=(0.5, 0.5),
    )
    return _save(fitted, dest)


def make_gallery(source: Path, dest: Path, width: int = GALLERY_WIDTH) -> tuple[int, int]:
    """비율을 유지한 채 가로를 맞춘다. 원본보다 크게 늘리지 않는다."""
    image = _load(source)
    if image.width > width:
        height = max(1, round(image.height * width / image.width))
        image = image.resize((width, height), Image.LANCZOS)
    return _save(image, dest)


def fetch_youtube_cover(video_id: str, dest: Path, opener=None) -> bool:
    """이미지가 없는 영상 게시물의 커버를 유튜브 썸네일로 채운다.

    빌드 시점에 내려받아 로컬 파일로 저장하므로 런타임 외부 의존이 없다.
    """
    open_url = opener or urlopen
    for template in _YOUTUBE_THUMBNAILS:
        try:
            with open_url(template.format(id=video_id), timeout=20) as response:
                payload = response.read()
            with Image.open(io.BytesIO(payload)) as downloaded:
                downloaded.load()
                image = ImageOps.exif_transpose(downloaded).convert("RGB")
        except (OSError, ValueError):
            continue
        target_height = max(1, round(COVER_WIDTH * COVER_RATIO[1] / COVER_RATIO[0]))
        fitted = ImageOps.fit(
            image,
            (COVER_WIDTH, target_height),
            method=Image.LANCZOS,
            centering=(0.5, 0.5),
        )
        _save(fitted, dest)
        return True
    return False
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_images.py -v`
Expected: PASS — 10 passed

- [ ] **Step 5: 커밋**

```bash
git add portfolio/tools/images.py portfolio/tools/tests/test_images.py
git commit -m "feat(portfolio): 커버 16:9 크롭·갤러리 리사이즈·유튜브 썸네일"
```

---

### Task 8: manifest 조립 (`manifest.py`)

스캔 결과와 이미지 변환을 엮어 `works.json`을 만든다. 정렬 규칙이 여기서 확정된다.

**Files:**
- Create: `portfolio/tools/manifest.py`
- Test: `portfolio/tools/tests/test_manifest.py`

**Interfaces:**
- Consumes: `scanner.Category`, `scanner.Work`, `naming.natural_key`, `images.make_cover`, `images.make_gallery`, `images.needs_rebuild`, `images.fetch_youtube_cover`
- Produces:
  - `sort_works(works: list[Work]) -> list[Work]` — 접두사 있는 것 먼저(숫자 오름차순), 그다음 날짜 내림차순
  - `build_manifest(categories: list[Category], media_root: Path, generated_at: datetime) -> tuple[dict, list[str]]` — 이미지 변환까지 수행하고 `(manifest, 경고)`를 돌려준다
  - `write_manifest(manifest: dict, path: Path) -> None`

- [ ] **Step 1: 실패하는 테스트 작성**

`portfolio/tools/tests/test_manifest.py`:

```python
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from manifest import build_manifest, sort_works, write_manifest
from scanner import Category, Work

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _work(title, order=None, days_ago=0):
    return Work(
        title=title,
        slug=title,
        order=order,
        directory=Path("/tmp") / title,
        date=NOW - timedelta(days=days_ago),
    )


def test_접두사가_있는_게시물이_먼저_온다():
    works = [_work("최신", days_ago=0), _work("고정", order=1, days_ago=100)]
    assert [w.title for w in sort_works(works)] == ["고정", "최신"]


def test_접두사끼리는_숫자_오름차순():
    works = [_work("둘째", order=2), _work("첫째", order=1)]
    assert [w.title for w in sort_works(works)] == ["첫째", "둘째"]


def test_접두사가_없으면_최신순():
    works = [_work("옛것", days_ago=30), _work("새것", days_ago=1)]
    assert [w.title for w in sort_works(works)] == ["새것", "옛것"]


def _fixture_category(tmp_path):
    work_dir = tmp_path / "upload" / "화보" / "작업"
    work_dir.mkdir(parents=True)
    Image.new("RGB", (2400, 1600), (90, 90, 90)).save(work_dir / "cover.jpg")
    Image.new("RGB", (2400, 1600), (40, 40, 40)).save(work_dir / "01.jpg")
    work = Work(
        title="작업",
        slug="작업",
        order=None,
        directory=work_dir,
        images=[work_dir / "01.jpg"],
        cover=work_dir / "cover.jpg",
        video={"kind": "youtube", "id": "abcdef", "embed": "https://e/abcdef", "url": "https://youtu.be/abcdef"},
        body="<p>본문</p>",
        date=NOW,
    )
    return Category(title="화보", slug="화보", order=1, directory=work_dir.parent, works=[work])


def test_manifest에_카테고리와_게시물이_담긴다(tmp_path):
    category = _fixture_category(tmp_path)

    manifest, warnings = build_manifest([category], tmp_path / "media", NOW)

    assert manifest["generatedAt"] == NOW.isoformat()
    assert len(manifest["categories"]) == 1
    entry = manifest["categories"][0]["works"][0]
    assert entry["title"] == "작업"
    assert entry["url"] == "works/화보/작업/"
    assert entry["video"]["kind"] == "youtube"
    assert entry["body"] == "<p>본문</p>"
    assert warnings == []


def test_커버와_갤러리_이미지가_실제로_생성된다(tmp_path):
    category = _fixture_category(tmp_path)
    media_root = tmp_path / "media"

    manifest, _ = build_manifest([category], media_root, NOW)
    entry = manifest["categories"][0]["works"][0]

    cover_path = tmp_path / entry["cover"]["src"]
    assert cover_path.exists()
    assert (entry["cover"]["w"], entry["cover"]["h"]) == (600, 338)

    gallery_path = tmp_path / entry["images"][0]["src"]
    assert gallery_path.exists()
    assert entry["images"][0]["w"] == 1600


def test_이미지가_깨져도_빌드가_계속된다(tmp_path):
    category = _fixture_category(tmp_path)
    broken = category.works[0].directory / "broken.jpg"
    broken.write_bytes(b"not an image")
    category.works[0].images.append(broken)

    manifest, warnings = build_manifest([category], tmp_path / "media", NOW)

    assert len(manifest["categories"][0]["works"][0]["images"]) == 1
    assert any("broken.jpg" in w for w in warnings)


def test_manifest를_UTF8_JSON으로_쓴다(tmp_path):
    category = _fixture_category(tmp_path)
    manifest, _ = build_manifest([category], tmp_path / "media", NOW)
    out = tmp_path / "works.json"

    write_manifest(manifest, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["categories"][0]["title"] == "화보"
    # 한글이 \uXXXX로 이스케이프되지 않아야 한다
    assert "화보" in out.read_text(encoding="utf-8")
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_manifest.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'manifest'`

- [ ] **Step 3: `manifest.py` 구현**

```python
"""스캔 결과와 이미지 변환을 엮어 works.json을 만든다."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from images import (
    COVER_WIDTH,
    GALLERY_WIDTH,
    fetch_youtube_cover,
    image_size,
    make_cover,
    make_gallery,
    needs_rebuild,
)
from naming import natural_key
from scanner import Category, Work

# media_root 의 부모를 기준으로 상대경로를 만든다. 이 값이 사이트 루트다.
COVER_FILENAME = f"cover-{COVER_WIDTH}.webp"


def sort_works(works: list[Work]) -> list[Work]:
    """접두사가 있는 게시물이 먼저(숫자 오름차순), 그다음 날짜 내림차순."""
    pinned = sorted(
        (work for work in works if work.order is not None),
        key=lambda work: (work.order, natural_key(work.title)),
    )
    recent = sorted(
        (work for work in works if work.order is None),
        key=lambda work: (work.date is not None, work.date),
        reverse=True,
    )
    return pinned + recent


def _gallery_filename(source: Path, index: int) -> str:
    return f"{index:02d}-{source.stem}-{GALLERY_WIDTH}.webp"


def _relative(site_root: Path, path: Path) -> str:
    return path.relative_to(site_root).as_posix()


def _build_work(
    work: Work,
    category: Category,
    media_root: Path,
    site_root: Path,
) -> tuple[dict, list[str]]:
    warnings: list[str] = []
    out_dir = media_root / category.slug / work.slug

    cover_entry = None
    if work.cover is not None:
        cover_dest = out_dir / COVER_FILENAME
        try:
            if needs_rebuild(work.cover, cover_dest):
                size = make_cover(work.cover, cover_dest)
            else:
                size = image_size(cover_dest)
            cover_entry = {"src": _relative(site_root, cover_dest), "w": size[0], "h": size[1]}
        except OSError:
            warnings.append(f"{category.title}/{work.title}/{work.cover.name}: 이미지를 열 수 없어 커버에서 제외했습니다")
    elif work.video and work.video.get("kind") == "youtube":
        cover_dest = out_dir / COVER_FILENAME
        if fetch_youtube_cover(work.video["id"], cover_dest):
            cover_entry = {"src": _relative(site_root, cover_dest), "w": COVER_WIDTH, "h": round(COVER_WIDTH * 9 / 16)}
        else:
            warnings.append(f"{category.title}/{work.title}: 유튜브 썸네일을 받지 못했습니다")

    image_entries = []
    for index, source in enumerate(work.images, start=1):
        dest = out_dir / _gallery_filename(source, index)
        try:
            if needs_rebuild(source, dest):
                size = make_gallery(source, dest)
            else:
                size = image_size(dest)
        except OSError:
            warnings.append(f"{category.title}/{work.title}/{source.name}: 이미지를 열 수 없어 건너뜁니다")
            continue
        image_entries.append({"src": _relative(site_root, dest), "w": size[0], "h": size[1]})

    entry = {
        "title": work.title,
        "slug": work.slug,
        "url": f"works/{category.slug}/{work.slug}/",
        "date": work.date.isoformat() if work.date else None,
        "order": work.order,
        "cover": cover_entry,
        "video": work.video,
        "images": image_entries,
        "body": work.body,
    }
    return entry, warnings


def build_manifest(
    categories: list[Category],
    media_root: Path,
    generated_at: datetime,
) -> tuple[dict, list[str]]:
    """이미지 변환까지 수행하고 (manifest, 경고)를 돌려준다."""
    site_root = media_root.parent
    warnings: list[str] = []
    category_entries = []

    for category in categories:
        work_entries = []
        for work in sort_works(category.works):
            entry, work_warnings = _build_work(work, category, media_root, site_root)
            warnings.extend(work_warnings)
            work_entries.append(entry)
        category_entries.append(
            {
                "title": category.title,
                "slug": category.slug,
                "order": category.order,
                "works": work_entries,
            }
        )

    return {
        "generatedAt": generated_at.isoformat(),
        "categories": category_entries,
    }, warnings


def write_manifest(manifest: dict, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_manifest.py -v`
Expected: PASS — 7 passed

- [ ] **Step 5: 커밋**

```bash
git add portfolio/tools/manifest.py portfolio/tools/tests/test_manifest.py
git commit -m "feat(portfolio): manifest 조립과 정렬 규칙"
```

---

### Task 9: 템플릿과 렌더러 (`render.py` + `templates/`)

manifest와 설정을 HTML로 찍는다. 페이지 깊이에 맞는 상대경로를 계산하는 것이 이 태스크의 핵심이다.

**Files:**
- Create: `portfolio/templates/page.html`
- Create: `portfolio/templates/partials/card.html`
- Create: `portfolio/templates/partials/section.html`
- Create: `portfolio/templates/partials/post.html`
- Create: `portfolio/templates/partials/figure.html`
- Create: `portfolio/tools/render.py`
- Test: `portfolio/tools/tests/test_render.py`

**Interfaces:**
- Consumes: `manifest` dict (Task 8), `site.config.json` dict
- Produces:
  - `render_template(text: str, values: dict[str, str]) -> str` — `{{TOKEN}}` 치환
  - `relative_prefix(depth: int) -> str` — `0` → `""`, `3` → `"../../../"`
  - `render_site(manifest: dict, config: dict, site_root: Path, templates_dir: Path) -> tuple[list[Path], list[str]]` — `(생성한 파일 목록, 경고)`

- [ ] **Step 1: 템플릿 파일들을 작성**

`portfolio/templates/page.html` — 모든 페이지의 껍데기.

```html
<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{TITLE}}</title>
{{META}}
<link rel="stylesheet" href="{{REL}}assets/css/style.css">
</head>
<body>
<a class="skip" href="#main">본문으로 건너뛰기</a>
<header class="masthead">
  <a class="brand" href="{{REL}}index.html">{{SITE_NAME}}</a>
  <nav class="nav">
    <a href="{{REL}}index.html">Works</a>
    <a href="{{REL}}about.html">About</a>
    <a href="{{REL}}contact.html">Contact</a>
  </nav>
</header>
<main id="main">
{{CONTENT}}
</main>
<footer class="footer">
  <p class="footer-name">{{SITE_NAME}}</p>
  <p class="footer-links">{{FOOTER_LINKS}}</p>
</footer>
<script src="{{REL}}assets/js/app.js" defer></script>
</body>
</html>
```

`portfolio/templates/partials/card.html` — 그리드 카드 하나.

```html
<a class="card" href="{{REL}}{{URL}}">
  <span class="card-frame">
    <img src="{{REL}}{{COVER}}" width="{{COVER_W}}" height="{{COVER_H}}" alt="{{TITLE}}" loading="lazy" decoding="async">
    {{BADGE}}
  </span>
  <span class="card-title">{{TITLE}}</span>
</a>
```

`portfolio/templates/partials/section.html` — 카테고리 한 덩이.

```html
<section class="category" data-more="{{HAS_MORE}}">
  <h2 class="category-title">{{TITLE}}</h2>
  <div class="grid">
{{CARDS}}
  </div>
  {{MORE_BUTTON}}
</section>
```

`portfolio/templates/partials/post.html` — 게시물 본문.

```html
<article class="post">
  {{VIDEO}}
  <header class="post-head">
    <p class="post-category">{{CATEGORY}}</p>
    <h1 class="post-title">{{TITLE}}</h1>
    <p class="post-date">{{DATE}}</p>
  </header>
  <div class="gallery">
{{GALLERY}}
  </div>
  <div class="post-body">
{{BODY}}
  </div>
  <nav class="post-nav">{{POST_NAV}}</nav>
</article>
```

`portfolio/templates/partials/figure.html` — 갤러리 이미지 하나.

```html
<figure class="shot">
  <img src="{{REL}}{{SRC}}" width="{{W}}" height="{{H}}" alt="{{ALT}}" loading="lazy" decoding="async" data-zoom="{{REL}}{{SRC}}">
</figure>
```

- [ ] **Step 2: 실패하는 테스트 작성**

`portfolio/tools/tests/test_render.py`:

```python
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from render import relative_prefix, render_site, render_template

TEMPLATES = Path(__file__).resolve().parents[2] / "templates"
NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)

CONFIG = {
    "siteName": "NAME",
    "tagline": "Color Grading",
    "siteUrl": "https://example.com/portfolio",
    "email": "hello@example.com",
    "instagram": "https://instagram.com/x",
    "about": "소개 문단\n\n둘째 단락",
    "contactNote": "메일로 연락 주세요",
    "gridPageSize": 2,
    "noindex": True,
    "ogImage": "",
}


def _manifest(work_count=1):
    works = []
    for index in range(1, work_count + 1):
        works.append(
            {
                "title": f"작업{index}",
                "slug": f"작업{index}",
                "url": f"works/화보/작업{index}/",
                "date": NOW.isoformat(),
                "order": None,
                "cover": {"src": f"media/화보/작업{index}/cover-600.webp", "w": 600, "h": 338},
                "video": None,
                "images": [{"src": f"media/화보/작업{index}/01-a-1600.webp", "w": 1600, "h": 1067}],
                "body": "<p>본문</p>",
            }
        )
    return {
        "generatedAt": NOW.isoformat(),
        "categories": [{"title": "화보", "slug": "화보", "order": 1, "works": works}],
    }


def test_토큰을_치환한다():
    assert render_template("<p>{{A}}-{{B}}</p>", {"A": "1", "B": "2"}) == "<p>1-2</p>"


def test_없는_토큰은_빈_문자열로_지운다():
    assert render_template("<p>{{A}}{{MISSING}}</p>", {"A": "1"}) == "<p>1</p>"


def test_상대경로_접두사():
    assert relative_prefix(0) == ""
    assert relative_prefix(1) == "../"
    assert relative_prefix(3) == "../../../"


def test_목록과_게시물과_고정페이지를_만든다(tmp_path):
    pages, warnings = render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)

    names = {page.relative_to(tmp_path).as_posix() for page in pages}
    assert "index.html" in names
    assert "about.html" in names
    assert "contact.html" in names
    assert "works/화보/작업1/index.html" in names
    assert warnings == []


def test_생성물에_치환되지_않은_토큰이_남지_않는다(tmp_path):
    pages, _ = render_site(_manifest(3), CONFIG, tmp_path, TEMPLATES)
    for page in pages:
        assert "{{" not in page.read_text(encoding="utf-8"), page


def test_게시물_페이지는_상대경로로_자산을_참조한다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "화보" / "작업1" / "index.html").read_text(encoding="utf-8")

    # works/화보/작업1/ 은 3단 깊이다
    assert "../../../assets/css/style.css" in html
    assert "../../../media/화보/작업1/01-a-1600.webp" in html
    assert "/assets/css" not in html.replace("../../../assets/css", "")


def test_목록_페이지는_접두사_없이_참조한다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert 'href="assets/css/style.css"' in html
    assert "../" not in html


def test_noindex가_켜져_있으면_robots_메타가_들어간다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert '<meta name="robots" content="noindex, nofollow">' in html


def test_noindex를_끄면_robots_메타가_사라진다(tmp_path):
    config = dict(CONFIG, noindex=False)
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "noindex" not in html


def test_게시물_OG_태그는_절대주소를_쓴다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "화보" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert 'property="og:title"' in html
    # 사이트 내부 링크와 같은 규칙으로 퍼센트 인코딩된다
    assert (
        "https://example.com/portfolio/media/%ED%99%94%EB%B3%B4/%EC%9E%91%EC%97%851/cover-600.webp"
        in html
    )


def test_gridPageSize를_넘으면_더보기_버튼이_생긴다(tmp_path):
    render_site(_manifest(3), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert 'data-more="true"' in html
    assert "Show more" in html


def test_개수가_적으면_더보기_버튼이_없다(tmp_path):
    render_site(_manifest(1), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert 'data-more="false"' in html
    assert "Show more" not in html


def test_영상_게시물은_영상이_본문보다_먼저_온다(tmp_path):
    manifest = _manifest()
    manifest["categories"][0]["works"][0]["video"] = {
        "kind": "youtube",
        "id": "abcdef",
        "embed": "https://www.youtube-nocookie.com/embed/abcdef",
        "url": "https://youtu.be/abcdef",
    }
    render_site(manifest, CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "화보" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert html.index("youtube-nocookie") < html.index("post-title")


def test_작업물이_없으면_빈_상태를_보여준다(tmp_path):
    empty = {"generatedAt": NOW.isoformat(), "categories": []}
    render_site(empty, CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "준비 중" in html


def test_이전_다음_링크가_연결된다(tmp_path):
    render_site(_manifest(2), CONFIG, tmp_path, TEMPLATES)
    first = (tmp_path / "works" / "화보" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert "작업2" in first
```

- [ ] **Step 3: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_render.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'render'`

- [ ] **Step 4: `render.py` 구현**

```python
"""manifest와 설정을 HTML로 찍는다.

템플릿 엔진을 쓰지 않는다. templates/ 의 {{TOKEN}}을 문자열로 치환하고,
페이지 깊이에 맞는 상대경로 접두사를 계산해 넣는다. 산출물에는
{{ 가 하나도 남지 않아야 한다(test_render가 이를 검사한다).
"""

from __future__ import annotations

import re
from datetime import datetime
from html import escape
from pathlib import Path
from urllib.parse import quote

from textfile import body_to_html

_TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")


def render_template(text: str, values: dict[str, str]) -> str:
    """{{TOKEN}}을 치환한다. 값이 없는 토큰은 지운다."""
    return _TOKEN.sub(lambda match: values.get(match.group(1), ""), text)


def relative_prefix(depth: int) -> str:
    """페이지가 사이트 루트에서 depth만큼 깊을 때의 접두사."""
    return "../" * depth


def _url_path(path: str) -> str:
    """한글 경로를 퍼센트 인코딩한다. 슬래시는 남긴다."""
    return quote(path, safe="/-_.~")


def _load(templates_dir: Path, name: str) -> str:
    return (templates_dir / name).read_text(encoding="utf-8")


def _meta_block(config: dict, title: str, description: str, absolute_cover: str | None) -> str:
    lines = []
    if config.get("noindex"):
        lines.append('<meta name="robots" content="noindex, nofollow">')
    if description:
        lines.append(f'<meta name="description" content="{escape(description)}">')
    lines.append(f'<meta property="og:title" content="{escape(title)}">')
    lines.append('<meta property="og:type" content="website">')
    if description:
        lines.append(f'<meta property="og:description" content="{escape(description)}">')
    if absolute_cover:
        lines.append(f'<meta property="og:image" content="{escape(absolute_cover)}">')
        lines.append('<meta name="twitter:card" content="summary_large_image">')
    return "\n".join(lines)


def _footer_links(config: dict) -> str:
    parts = []
    email = config.get("email")
    if email:
        parts.append(f'<a href="mailto:{escape(email)}">{escape(email)}</a>')
    instagram = config.get("instagram")
    if instagram:
        parts.append(f'<a href="{escape(instagram)}" rel="noopener">Instagram</a>')
    return " · ".join(parts)


def _absolute(config: dict, relative: str) -> str | None:
    base = (config.get("siteUrl") or "").rstrip("/")
    if not base or not relative:
        return None
    return f"{base}/{relative}"


def _video_html(video: dict | None, rel: str, title: str) -> str:
    if not video:
        return ""
    kind = video.get("kind")
    if kind in {"youtube", "vimeo"} and video.get("embed"):
        return (
            '<div class="player">'
            f'<iframe src="{escape(video["embed"])}" title="{escape(title)}" '
            'loading="lazy" allowfullscreen '
            'allow="accelerometer; clipboard-write; encrypted-media; picture-in-picture">'
            "</iframe></div>"
        )
    if kind == "file":
        source = _url_path(video.get("url") or "")
        return (
            '<div class="player">'
            f'<video controls preload="metadata" src="{rel}{source}"></video>'
            "</div>"
        )
    if kind == "link" and video.get("url"):
        return (
            '<p class="player-link">'
            f'<a href="{escape(video["url"])}" rel="noopener">영상 보기 ↗</a></p>'
        )
    return ""


def _format_date(iso: str | None) -> str:
    if not iso:
        return ""
    try:
        return datetime.fromisoformat(iso).strftime("%Y.%m")
    except ValueError:
        return ""


def _write(path: Path, html: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def _page(templates_dir: Path, config: dict, *, depth: int, title: str, meta: str, content: str) -> str:
    rel = relative_prefix(depth)
    return render_template(
        _load(templates_dir, "page.html"),
        {
            "REL": rel,
            "TITLE": escape(title),
            "META": meta,
            "SITE_NAME": escape(config.get("siteName", "")),
            "CONTENT": content,
            "FOOTER_LINKS": _footer_links(config),
        },
    )


def _render_index(manifest: dict, config: dict, site_root: Path, templates_dir: Path) -> Path:
    card_template = _load(templates_dir, "partials/card.html")
    section_template = _load(templates_dir, "partials/section.html")
    page_size = int(config.get("gridPageSize") or 8)

    sections = []
    for category in manifest["categories"]:
        cards = []
        for index, work in enumerate(category["works"]):
            cover = work.get("cover") or {}
            badge = '<span class="badge">VIDEO</span>' if work.get("video") else ""
            classes = "" if index < page_size else " extra"
            card = render_template(
                card_template,
                {
                    "REL": "",
                    "URL": _url_path(work["url"]),
                    "COVER": _url_path(cover.get("src", "")),
                    "COVER_W": str(cover.get("w", 600)),
                    "COVER_H": str(cover.get("h", 338)),
                    "TITLE": escape(work["title"]),
                    "BADGE": badge,
                },
            )
            if classes:
                card = card.replace('class="card"', 'class="card extra"', 1)
            cards.append("    " + card.strip())

        has_more = len(category["works"]) > page_size
        more_button = (
            '<button class="more" type="button">Show more</button>' if has_more else ""
        )
        sections.append(
            render_template(
                section_template,
                {
                    "TITLE": escape(category["title"]),
                    "CARDS": "\n".join(cards),
                    "HAS_MORE": "true" if has_more else "false",
                    "MORE_BUTTON": more_button,
                },
            )
        )

    if not sections:
        sections.append('<p class="empty">작업물 준비 중입니다.</p>')

    tagline = config.get("tagline", "")
    hero = f'<p class="tagline">{escape(tagline)}</p>' if tagline else ""
    content = hero + "\n" + "\n".join(sections)
    meta = _meta_block(
        config,
        config.get("siteName", ""),
        tagline,
        _absolute(config, _url_path(config.get("ogImage") or "")),
    )
    html = _page(
        templates_dir,
        config,
        depth=0,
        title=config.get("siteName", ""),
        meta=meta,
        content=content,
    )
    return _write(site_root / "index.html", html)


def _render_simple_page(
    filename: str,
    heading: str,
    body_text: str,
    config: dict,
    site_root: Path,
    templates_dir: Path,
) -> Path:
    body = body_to_html(body_text or "")
    content = f'<article class="page"><h1 class="page-title">{escape(heading)}</h1>\n{body}</article>'
    meta = _meta_block(config, f"{heading} — {config.get('siteName','')}", "", None)
    html = _page(
        templates_dir,
        config,
        depth=0,
        title=f"{heading} — {config.get('siteName','')}",
        meta=meta,
        content=content,
    )
    return _write(site_root / filename, html)


def _render_post(
    work: dict,
    category: dict,
    neighbours: tuple[dict | None, dict | None],
    config: dict,
    site_root: Path,
    templates_dir: Path,
) -> Path:
    depth = 3  # works/<카테고리>/<게시물>/
    rel = relative_prefix(depth)
    figure_template = _load(templates_dir, "partials/figure.html")

    figures = []
    for index, image in enumerate(work["images"], start=1):
        figures.append(
            "    "
            + render_template(
                figure_template,
                {
                    "REL": rel,
                    "SRC": _url_path(image["src"]),
                    "W": str(image["w"]),
                    "H": str(image["h"]),
                    "ALT": escape(f"{work['title']} — {index}번째 이미지"),
                },
            ).strip()
        )

    previous_work, next_work = neighbours
    nav_parts = []
    if previous_work:
        nav_parts.append(
            f'<a class="prev" href="{rel}{_url_path(previous_work["url"])}">← {escape(previous_work["title"])}</a>'
        )
    nav_parts.append(f'<a class="up" href="{rel}index.html">전체 보기</a>')
    if next_work:
        nav_parts.append(
            f'<a class="next" href="{rel}{_url_path(next_work["url"])}">{escape(next_work["title"])} →</a>'
        )

    content = render_template(
        _load(templates_dir, "partials/post.html"),
        {
            "VIDEO": _video_html(work.get("video"), rel, work["title"]),
            "TITLE": escape(work["title"]),
            "CATEGORY": escape(category["title"]),
            "DATE": _format_date(work.get("date")),
            "GALLERY": "\n".join(figures),
            "BODY": work.get("body", ""),
            "POST_NAV": "\n".join(nav_parts),
        },
    )

    cover = work.get("cover") or {}
    meta = _meta_block(
        config,
        f"{work['title']} — {config.get('siteName','')}",
        f"{category['title']} · {config.get('siteName','')}",
        _absolute(config, _url_path(cover.get("src", ""))),
    )
    html = _page(
        templates_dir,
        config,
        depth=depth,
        title=f"{work['title']} — {config.get('siteName','')}",
        meta=meta,
        content=content,
    )
    return _write(site_root / "works" / category["slug"] / work["slug"] / "index.html", html)


def render_site(
    manifest: dict,
    config: dict,
    site_root: Path,
    templates_dir: Path,
) -> tuple[list[Path], list[str]]:
    """목록·고정 페이지·게시물 페이지를 모두 쓰고 (생성 파일, 경고)를 돌려준다."""
    warnings: list[str] = []
    pages = [
        _render_index(manifest, config, site_root, templates_dir),
        _render_simple_page("about.html", "About", config.get("about", ""), config, site_root, templates_dir),
        _render_simple_page("contact.html", "Contact", config.get("contactNote", ""), config, site_root, templates_dir),
    ]

    for category in manifest["categories"]:
        works = category["works"]
        for index, work in enumerate(works):
            previous_work = works[index - 1] if index > 0 else None
            next_work = works[index + 1] if index + 1 < len(works) else None
            if work.get("cover") is None:
                warnings.append(f"{category['title']}/{work['title']}: 커버 이미지가 없습니다")
            pages.append(
                _render_post(
                    work,
                    category,
                    (previous_work, next_work),
                    config,
                    site_root,
                    templates_dir,
                )
            )
    return pages, warnings
```

- [ ] **Step 5: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_render.py -v`
Expected: PASS — 15 passed

- [ ] **Step 6: 커밋**

```bash
git add portfolio/templates portfolio/tools/render.py portfolio/tools/tests/test_render.py
git commit -m "feat(portfolio): 템플릿과 렌더러, 게시물별 OG 태그"
```

---

### Task 10: 스타일과 동작 (`assets/`)

다크 고정·무채색 UI를 구현하고, `Show more`와 이미지 확대를 붙인다.

**Files:**
- Create: `portfolio/assets/css/style.css`
- Create: `portfolio/assets/js/app.js`

**Interfaces:**
- Consumes: Task 9가 찍는 클래스 이름 — `.masthead .brand .nav .tagline .category .category-title .grid .card .card.extra .card-frame .card-title .badge .more .post .player .player-link .post-head .post-category .post-title .post-date .gallery .shot .post-body .post-nav .page .page-title .empty .footer .footer-name .footer-links .skip`, 그리고 `<section class="category" data-more="true|false">`, `<img data-zoom="...">`
- Produces: 라이트박스 마크업(`.lightbox`)은 JS가 런타임에 만든다

- [ ] **Step 1: `portfolio/assets/css/style.css` 작성**

```css
/* 색보정 포트폴리오 — 다크 고정.
   밝은 배경은 옆에 놓인 이미지의 체감 채도와 콘트라스트를 왜곡한다.
   그래서 라이트 모드 분기를 의도적으로 만들지 않는다.
   UI에는 색을 쓰지 않는다. 화면에서 색을 가진 것은 작업물뿐이어야 한다. */

:root {
  --bg: #0b0b0c;
  --surface: #141416;
  --line: #26262a;
  --text: #ededed;
  --muted: #8a8a8f;
  --faint: #5c5c61;
  --gutter: 16px;
  --max: 1360px;
}

* { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font-family: "Pretendard", -apple-system, BlinkMacSystemFont, "Segoe UI",
               "Apple SD Gothic Neo", "Malgun Gothic", sans-serif;
  line-height: 1.7;
  -webkit-font-smoothing: antialiased;
}

img, video, iframe { display: block; max-width: 100%; }

a { color: inherit; text-decoration: none; }

.skip {
  position: absolute;
  left: -9999px;
}
.skip:focus {
  left: var(--gutter);
  top: 8px;
  z-index: 10;
  padding: 8px 12px;
  background: var(--surface);
  border: 1px solid var(--line);
}

/* 헤더 */
.masthead {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  max-width: var(--max);
  margin: 0 auto;
  padding: 28px var(--gutter) 20px;
}

.brand {
  font-size: 1.0625rem;
  font-weight: 600;
  letter-spacing: .04em;
}

.nav {
  display: flex;
  gap: 20px;
  font-size: .8125rem;
  letter-spacing: .1em;
  text-transform: uppercase;
  color: var(--muted);
}
.nav a:hover { color: var(--text); }

/* 목록 */
.tagline {
  max-width: var(--max);
  margin: 0 auto;
  padding: 0 var(--gutter) 40px;
  color: var(--muted);
  font-size: .875rem;
  letter-spacing: .06em;
}

.category {
  max-width: var(--max);
  margin: 0 auto;
  padding: 0 var(--gutter) 64px;
}

.category-title {
  margin: 0 0 18px;
  font-size: .75rem;
  font-weight: 600;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--muted);
}

.grid {
  display: grid;
  gap: 12px;
  grid-template-columns: 1fr;
}

@media (min-width: 560px) {
  .grid { grid-template-columns: repeat(2, 1fr); }
}
@media (min-width: 900px) {
  .grid { grid-template-columns: repeat(3, 1fr); gap: 16px; }
}

.card { display: block; }

.card-frame {
  position: relative;
  display: block;
  aspect-ratio: 16 / 9;
  overflow: hidden;
  background: var(--surface);
}

.card-frame img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  filter: brightness(.92);
  transition: filter .25s ease, transform .4s ease;
}

.card:hover .card-frame img,
.card:focus-visible .card-frame img {
  filter: brightness(1.04);
  transform: scale(1.015);
}

.badge {
  position: absolute;
  left: 10px;
  bottom: 10px;
  padding: 3px 7px;
  font-size: .625rem;
  letter-spacing: .12em;
  background: rgba(0, 0, 0, .6);
  border: 1px solid rgba(255, 255, 255, .25);
}

.card-title {
  display: block;
  padding-top: 10px;
  font-size: .875rem;
  color: var(--muted);
}
.card:hover .card-title { color: var(--text); }

/* JS가 없으면 전부 보여준다. 있으면 초과분을 숨긴다. */
.js .card.extra { display: none; }
.js .category.is-open .card.extra { display: block; }

.more {
  margin-top: 20px;
  padding: 10px 18px;
  font: inherit;
  font-size: .75rem;
  letter-spacing: .14em;
  text-transform: uppercase;
  color: var(--muted);
  background: transparent;
  border: 1px solid var(--line);
  cursor: pointer;
}
.more:hover { color: var(--text); border-color: var(--faint); }
.category.is-open .more { display: none; }

.empty {
  max-width: var(--max);
  margin: 0 auto;
  padding: 80px var(--gutter);
  color: var(--muted);
  text-align: center;
}

/* 게시물 */
.post, .page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 0 var(--gutter) 80px;
}

.player {
  aspect-ratio: 16 / 9;
  background: #000;
  margin-bottom: 36px;
}
.player iframe, .player video { width: 100%; height: 100%; border: 0; }

.player-link { margin: 0 0 36px; color: var(--muted); }
.player-link a { border-bottom: 1px solid var(--line); }

.post-head { margin-bottom: 40px; }

.post-category {
  margin: 0 0 8px;
  font-size: .6875rem;
  letter-spacing: .16em;
  text-transform: uppercase;
  color: var(--muted);
}

.post-title {
  margin: 0 0 6px;
  font-size: clamp(1.75rem, 5vw, 2.5rem);
  line-height: 1.15;
  letter-spacing: -.02em;
}

.post-date { margin: 0; font-size: .8125rem; color: var(--faint); }

.gallery { display: grid; gap: 16px; }
.shot { margin: 0; }
.shot img { width: 100%; height: auto; cursor: zoom-in; }

.post-body {
  max-width: 34rem;
  margin: 48px 0 0;
  color: var(--muted);
}
.post-body p { margin: 0 0 1.2em; }

.post-nav {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
  margin-top: 64px;
  padding-top: 20px;
  border-top: 1px solid var(--line);
  font-size: .8125rem;
  color: var(--muted);
}
.post-nav a:hover { color: var(--text); }

.page-title {
  margin: 0 0 24px;
  font-size: clamp(1.75rem, 5vw, 2.5rem);
  letter-spacing: -.02em;
}
.page p { max-width: 34rem; color: var(--muted); }

/* 푸터 */
.footer {
  max-width: var(--max);
  margin: 0 auto;
  padding: 40px var(--gutter) 64px;
  border-top: 1px solid var(--line);
  font-size: .8125rem;
  color: var(--muted);
}
.footer-name { margin: 0 0 6px; color: var(--text); }
.footer-links { margin: 0; }
.footer-links a:hover { color: var(--text); }

/* 라이트박스 — JS가 만든다 */
.lightbox {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(0, 0, 0, .94);
}
.lightbox img {
  max-width: 96vw;
  max-height: 92vh;
  width: auto;
  height: auto;
  cursor: zoom-out;
}
.lightbox button {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  padding: 14px 16px;
  font: inherit;
  color: var(--text);
  background: rgba(0, 0, 0, .5);
  border: 1px solid var(--line);
  cursor: pointer;
}
.lightbox .lb-prev { left: 12px; }
.lightbox .lb-next { right: 12px; }
.lightbox .lb-close { top: 12px; right: 12px; transform: none; }
body.lb-open { overflow: hidden; }

@media (prefers-reduced-motion: reduce) {
  * { transition: none !important; }
}
```

- [ ] **Step 2: `portfolio/assets/js/app.js` 작성**

```javascript
/* 포트폴리오 동작 — 의존성 없음.
   JS가 없어도 그리드와 게시물은 정적 HTML로 전부 보인다.
   여기서 하는 일은 (1) 초과 카드 접기 (2) 이미지 확대뿐이다. */
(function () {
  'use strict';

  // 이 클래스가 붙은 뒤에만 CSS가 초과 카드를 숨긴다.
  document.documentElement.classList.add('js');

  // 1) Show more
  document.querySelectorAll('.category .more').forEach(function (button) {
    button.addEventListener('click', function () {
      var section = button.closest('.category');
      if (section) section.classList.add('is-open');
    });
  });

  // 2) 이미지 확대
  var zoomable = Array.prototype.slice.call(document.querySelectorAll('.shot img[data-zoom]'));
  if (!zoomable.length) return;

  var overlay = null;
  var picture = null;
  var current = 0;

  function show(index) {
    current = (index + zoomable.length) % zoomable.length;
    var source = zoomable[current];
    picture.src = source.getAttribute('data-zoom');
    picture.alt = source.alt || '';
  }

  function close() {
    if (!overlay) return;
    overlay.remove();
    overlay = null;
    document.body.classList.remove('lb-open');
    document.removeEventListener('keydown', onKey);
    zoomable[current].focus({ preventScroll: true });
  }

  function onKey(event) {
    if (event.key === 'Escape') close();
    else if (event.key === 'ArrowRight') show(current + 1);
    else if (event.key === 'ArrowLeft') show(current - 1);
  }

  function open(index) {
    overlay = document.createElement('div');
    overlay.className = 'lightbox';
    overlay.setAttribute('role', 'dialog');
    overlay.setAttribute('aria-modal', 'true');

    picture = document.createElement('img');
    overlay.appendChild(picture);

    [['lb-close', '✕', close],
     ['lb-prev', '‹', function () { show(current - 1); }],
     ['lb-next', '›', function () { show(current + 1); }]
    ].forEach(function (spec) {
      var button = document.createElement('button');
      button.type = 'button';
      button.className = spec[0];
      button.textContent = spec[1];
      button.addEventListener('click', function (event) {
        event.stopPropagation();
        spec[2]();
      });
      overlay.appendChild(button);
    });

    overlay.addEventListener('click', close);
    document.body.appendChild(overlay);
    document.body.classList.add('lb-open');
    document.addEventListener('keydown', onKey);
    show(index);
  }

  zoomable.forEach(function (image, index) {
    image.tabIndex = 0;
    image.addEventListener('click', function () { open(index); });
    image.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        open(index);
      }
    });
  });
})();
```

- [ ] **Step 3: 렌더러가 CSS의 `.js` 전략과 맞는지 확인**

Task 9의 `_render_index`는 초과 카드에 `class="card extra"`를 붙인다. CSS는 `.js .card.extra { display: none }`이므로, JS가 로드되기 전이나 꺼져 있으면 전부 보인다. 이것이 의도다.

Run: `python -m pytest portfolio/tools/tests/test_render.py -k 더보기 -v`
Expected: PASS — 2 passed

- [ ] **Step 4: 커밋**

```bash
git add portfolio/assets
git commit -m "feat(portfolio): 다크 고정 무채색 스타일과 더보기·이미지 확대"
```

---

### Task 11: 링크 검증과 CLI (`linkcheck.py`, `build.py`)

생성물이 참조하는 경로가 실제로 있는지 확인하고, 전체 파이프라인을 하나의 명령으로 묶는다.

**Files:**
- Create: `portfolio/tools/linkcheck.py`
- Create: `portfolio/tools/build.py`
- Test: `portfolio/tools/tests/test_linkcheck.py`
- Test: `portfolio/tools/tests/test_build.py`

**Interfaces:**
- Consumes: `scanner.scan`, `dates.git_added_at`, `manifest.build_manifest`, `manifest.write_manifest`, `render.render_site`
- Produces:
  - `check_links(site_root: Path, pages: list[Path]) -> list[str]` — 깨진 참조 목록
  - `build(site_root: Path, repo_root: Path) -> tuple[int, list[str]]` — `(종료 코드, 메시지 목록)`
  - CLI: `python portfolio/tools/build.py [--root PATH] [--check]`

- [ ] **Step 1: 링크 검증 테스트 작성**

`portfolio/tools/tests/test_linkcheck.py`:

```python
from linkcheck import check_links


def _page(root, relative, html):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


def test_존재하는_상대경로는_통과한다(tmp_path):
    (tmp_path / "assets" / "css").mkdir(parents=True)
    (tmp_path / "assets" / "css" / "style.css").write_text("x", encoding="utf-8")
    page = _page(tmp_path, "index.html", '<link rel="stylesheet" href="assets/css/style.css">')

    assert check_links(tmp_path, [page]) == []


def test_없는_파일을_참조하면_보고한다(tmp_path):
    page = _page(tmp_path, "index.html", '<img src="media/없는사진.webp">')

    errors = check_links(tmp_path, [page])

    assert len(errors) == 1
    assert "없는사진" in errors[0]


def test_깊은_페이지의_상대경로를_해석한다(tmp_path):
    (tmp_path / "assets" / "css").mkdir(parents=True)
    (tmp_path / "assets" / "css" / "style.css").write_text("x", encoding="utf-8")
    page = _page(
        tmp_path,
        "works/화보/작업/index.html",
        '<link rel="stylesheet" href="../../../assets/css/style.css">',
    )

    assert check_links(tmp_path, [page]) == []


def test_퍼센트_인코딩된_한글_경로를_해석한다(tmp_path):
    target = tmp_path / "media" / "화보" / "cover-600.webp"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"x")
    page = _page(tmp_path, "index.html", '<img src="media/%ED%99%94%EB%B3%B4/cover-600.webp">')

    assert check_links(tmp_path, [page]) == []


def test_외부주소와_mailto와_앵커는_검사하지_않는다(tmp_path):
    page = _page(
        tmp_path,
        "index.html",
        '<a href="https://example.com">x</a>'
        '<a href="mailto:a@b.c">y</a>'
        '<a href="#main">z</a>'
        '<iframe src="//cdn.example.com/x"></iframe>',
    )

    assert check_links(tmp_path, [page]) == []


def test_디렉터리_참조는_index_html을_찾는다(tmp_path):
    target = tmp_path / "works" / "화보" / "작업" / "index.html"
    target.parent.mkdir(parents=True)
    target.write_text("x", encoding="utf-8")
    page = _page(tmp_path, "index.html", '<a href="works/화보/작업/">x</a>')

    assert check_links(tmp_path, [page]) == []
```

- [ ] **Step 2: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_linkcheck.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'linkcheck'`

- [ ] **Step 3: `linkcheck.py` 구현**

```python
"""생성된 HTML이 참조하는 로컬 경로가 실제로 있는지 확인한다.

상대경로 계산 실수는 조용히 깨진 이미지로 나타나므로,
빌드가 끝날 때마다 기계로 확인한다.
"""

from __future__ import annotations

import re
from pathlib import Path
from urllib.parse import unquote, urlparse

_REFERENCE = re.compile(r'(?:href|src|data-zoom)="([^"]+)"')
_SKIP_PREFIXES = ("http://", "https://", "//", "mailto:", "tel:", "data:", "#", "javascript:")


def check_links(site_root: Path, pages: list[Path]) -> list[str]:
    """깨진 참조를 사람이 읽을 수 있는 문장으로 돌려준다."""
    errors: list[str] = []
    for page in pages:
        html = page.read_text(encoding="utf-8")
        for raw in _REFERENCE.findall(html):
            if raw.startswith(_SKIP_PREFIXES) or not raw.strip():
                continue
            target = unquote(urlparse(raw).path)
            if not target:
                continue
            resolved = (page.parent / target).resolve()
            if target.endswith("/"):
                resolved = resolved / "index.html"
            if not resolved.exists():
                where = page.relative_to(site_root).as_posix()
                errors.append(f"{where}: 참조한 {raw} 를 찾을 수 없습니다")
    return errors
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_linkcheck.py -v`
Expected: PASS — 6 passed

- [ ] **Step 5: 전체 파이프라인 테스트 작성**

`portfolio/tools/tests/test_build.py`:

```python
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image

TOOLS = Path(__file__).resolve().parents[1]
PORTFOLIO = TOOLS.parent


def _sample_site(tmp_path):
    """templates/assets 는 실제 저장소 것을 쓰고, upload 만 픽스처로 만든다."""
    site = tmp_path / "portfolio"
    (site / "upload" / "01_화보" / "2026웨딩스냅").mkdir(parents=True)
    work = site / "upload" / "01_화보" / "2026웨딩스냅"
    Image.new("RGB", (2400, 1600), (80, 70, 60)).save(work / "cover.jpg")
    Image.new("RGB", (2400, 1600), (40, 50, 60)).save(work / "01.jpg")
    (work / "memo.txt").write_bytes("보정 메모입니다".encode("cp949"))

    video_work = site / "upload" / "02_뮤직비디오" / "TAEMIN-Guilty"
    video_work.mkdir(parents=True)
    Image.new("RGB", (1920, 1080), (20, 20, 20)).save(video_work / "cover.jpg")
    (video_work / "link.txt").write_text("https://youtu.be/dQw4w9WgXcQ", encoding="utf-8")

    for relative in ("templates", "assets"):
        _copy_tree(PORTFOLIO / relative, site / relative)
    (site / "site.config.json").write_text(
        (PORTFOLIO / "site.config.json").read_text(encoding="utf-8"), encoding="utf-8"
    )
    return site


def _copy_tree(source: Path, dest: Path):
    for item in source.rglob("*"):
        target = dest / item.relative_to(source)
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(item.read_bytes())


def _run(site, *args):
    return subprocess.run(
        [sys.executable, str(TOOLS / "build.py"), "--root", str(site), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def test_빌드가_모든_산출물을_만든다(tmp_path):
    site = _sample_site(tmp_path)

    result = _run(site)

    assert result.returncode == 0, result.stdout + result.stderr
    assert (site / "works.json").exists()
    assert (site / "index.html").exists()
    assert (site / "about.html").exists()
    assert (site / "contact.html").exists()
    assert (site / "works" / "화보" / "2026웨딩스냅" / "index.html").exists()
    assert (site / "works" / "뮤직비디오" / "TAEMIN-Guilty" / "index.html").exists()
    assert list((site / "media" / "화보" / "2026웨딩스냅").glob("*.webp"))


def test_CP949_본문이_깨지지_않는다(tmp_path):
    site = _sample_site(tmp_path)
    _run(site)

    html = (site / "works" / "화보" / "2026웨딩스냅" / "index.html").read_text(encoding="utf-8")
    assert "보정 메모입니다" in html


def test_원본_이미지를_수정하지_않는다(tmp_path):
    site = _sample_site(tmp_path)
    original = (site / "upload" / "01_화보" / "2026웨딩스냅" / "cover.jpg").read_bytes()

    _run(site)

    assert (site / "upload" / "01_화보" / "2026웨딩스냅" / "cover.jpg").read_bytes() == original


def test_카테고리_순서가_접두사를_따른다(tmp_path):
    site = _sample_site(tmp_path)
    _run(site)

    manifest = json.loads((site / "works.json").read_text(encoding="utf-8"))
    assert [c["title"] for c in manifest["categories"]] == ["화보", "뮤직비디오"]


def test_check_모드는_빌드된_사이트를_통과시킨다(tmp_path):
    site = _sample_site(tmp_path)
    _run(site)

    result = _run(site, "--check")

    assert result.returncode == 0, result.stdout + result.stderr


def test_참조가_깨지면_0이_아닌_코드로_끝난다(tmp_path):
    site = _sample_site(tmp_path)
    _run(site)
    for webp in (site / "media").rglob("*.webp"):
        webp.unlink()

    result = _run(site, "--check")

    assert result.returncode != 0
    assert "찾을 수 없습니다" in (result.stdout + result.stderr)
```

- [ ] **Step 6: 테스트가 실패하는 것을 확인**

Run: `python -m pytest portfolio/tools/tests/test_build.py -v`
Expected: FAIL — `build.py`가 없어 `returncode != 0` 이고 첫 단정이 깨진다

- [ ] **Step 7: `build.py` 구현**

```python
"""포트폴리오 빌드 진입점.

  python portfolio/tools/build.py            # 전체 빌드
  python portfolio/tools/build.py --check    # 생성물의 참조만 검증

경고는 출력하되 빌드를 멈추지 않는다. 종료 코드가 0이 아닌 경우는
설정 파일을 읽을 수 없을 때와 참조가 깨졌을 때뿐이다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from dates import git_added_at  # noqa: E402
from linkcheck import check_links  # noqa: E402
from manifest import build_manifest, write_manifest  # noqa: E402
from render import render_site  # noqa: E402
from scanner import scan  # noqa: E402

DEFAULT_ROOT = Path(__file__).resolve().parents[1]


def _load_config(site_root: Path) -> dict:
    return json.loads((site_root / "site.config.json").read_text(encoding="utf-8"))


def _collect_pages(site_root: Path) -> list[Path]:
    pages = [site_root / name for name in ("index.html", "about.html", "contact.html")]
    pages += sorted((site_root / "works").rglob("index.html"))
    return [page for page in pages if page.exists()]


def build(site_root: Path, repo_root: Path) -> tuple[int, list[str]]:
    config = _load_config(site_root)
    categories, warnings = scan(site_root / "upload")

    for category in categories:
        for work in category.works:
            work.date = git_added_at(repo_root, work.directory)

    manifest, media_warnings = build_manifest(
        categories,
        site_root / "media",
        datetime.now(timezone.utc).astimezone(),
    )
    warnings.extend(media_warnings)
    write_manifest(manifest, site_root / "works.json")

    pages, render_warnings = render_site(
        manifest, config, site_root, site_root / "templates"
    )
    warnings.extend(render_warnings)

    errors = check_links(site_root, pages)
    work_count = sum(len(category["works"]) for category in manifest["categories"])
    messages = [f"카테고리 {len(manifest['categories'])}개, 게시물 {work_count}개, 페이지 {len(pages)}개 생성"]
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
    repo_root = site_root.parent

    if arguments.check:
        code, messages = check_only(site_root)
    else:
        code, messages = build(site_root, repo_root)

    for message in messages:
        print(message)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 8: 테스트 통과 확인**

Run: `python -m pytest portfolio/tools/tests/test_build.py -v`
Expected: PASS — 6 passed

- [ ] **Step 9: 전체 테스트를 돌린다**

Run: `python -m pytest portfolio/tools/tests -v`
Expected: PASS — 전체 통과 (약 80개)

- [ ] **Step 10: 커밋**

```bash
git add portfolio/tools/linkcheck.py portfolio/tools/build.py portfolio/tools/tests/test_linkcheck.py portfolio/tools/tests/test_build.py
git commit -m "feat(portfolio): 링크 검증과 빌드 CLI"
```

---

### Task 12: 자동화와 문서, 최종 검증

Actions가 푸시마다 빌드하게 하고, 작가용 설명서를 쓰고, 실제 화면과 Jekyll 절연을 확인한다.

**Files:**
- Create: `.github/workflows/portfolio.yml`
- Modify: `portfolio/README.md` (Task 1에서 넘어온 `lab` 설명을 작가용 설명서로 교체)
- Create: `portfolio/upload/01_샘플/첫번째작업/` (확인용 샘플. 마지막 단계에서 지울지 결정)

**Interfaces:**
- Consumes: `portfolio/tools/build.py`
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: 워크플로 작성**

`.github/workflows/portfolio.yml`:

```yaml
name: Portfolio build

# 트리거 경로에 생성물(works/, media/, works.json, 루트 html)이 없으므로
# 이 워크플로가 만든 커밋으로 자신이 다시 돌지 않는다.
on:
  push:
    branches: [main]
    paths:
      - 'portfolio/upload/**'
      - 'portfolio/templates/**'
      - 'portfolio/assets/**'
      - 'portfolio/site.config.json'
      - 'portfolio/tools/**'
      - '.github/workflows/portfolio.yml'
  workflow_dispatch:

permissions:
  contents: write

concurrency:
  group: portfolio-build
  cancel-in-progress: false

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          # 게시물 정렬이 폴더 추가 커밋 시각을 읽으므로 전체 이력이 필요하다
          fetch-depth: 0

      - uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - run: pip install --quiet pillow

      - name: 테스트
        run: python -m pytest portfolio/tools/tests -q

      - name: 빌드
        run: python portfolio/tools/build.py

      - name: 결과 커밋
        run: |
          git config user.name  "github-actions[bot]"
          git config user.email "41898282+github-actions[bot]@users.noreply.github.com"
          git add portfolio/works portfolio/media portfolio/works.json \
                  portfolio/index.html portfolio/about.html portfolio/contact.html
          if git diff --cached --quiet; then
            echo "변경 없음"
            exit 0
          fi
          git commit -m "chore(portfolio): 작업물 목록 자동 갱신"
          git push
```

- [ ] **Step 2: 작가용 설명서 작성**

`portfolio/README.md` 전체를 아래로 교체한다.

````markdown
# 포트폴리오 사이트

작업물을 올리는 방법은 **폴더를 만들어 넣는 것** 하나입니다. 올리면 목록과 게시물 페이지가 자동으로 만들어집니다.

## 올리는 방법

`upload/` 안에 **카테고리 폴더 → 작업물 폴더** 2단으로 넣습니다.

```
upload/
└── 01_화보/                  ← 카테고리 (메뉴에 이 이름이 나옵니다)
    └── 2026웨딩스냅/          ← 작업물 (이 이름이 게시물 제목이 됩니다)
        ├── cover.jpg         ← 목록에 보일 대표 이미지 (없으면 첫 사진)
        ├── 01.jpg ~ 07.jpg   ← 파일명 순서대로 게시물에 나옵니다
        ├── link.txt          ← (선택) 영상 주소 한 줄
        └── memo.txt          ← (선택) 게시물 맨 아래 들어갈 글
```

- **폴더 이름이 제목입니다.** 이름 앞에 `01_`처럼 숫자를 붙이면 그 순서대로 앞에 고정됩니다. 숫자를 안 붙이면 **새로 올린 것이 위에** 옵니다.
- **영상**은 `link.txt`에 YouTube나 Vimeo 주소를 한 줄 적으면 됩니다. mp4 파일을 그냥 넣어도 되지만 25MB를 넘으면 웹에서 업로드가 막힙니다. 영상은 게시물 맨 위에 놓입니다.
- **설명글**은 아무 이름의 `.txt`에 쓰면 게시물 맨 아래에 들어갑니다. 메모장으로 저장해도 한글이 깨지지 않습니다. 빈 줄을 넣으면 단락이 나뉩니다.
- 사진도 영상도 없는 폴더는 그냥 무시됩니다.

올린 뒤 1~2분이면 사이트에 반영됩니다. 사진은 웹용으로 자동 축소되며 **원본은 그대로 보관되고 웹에는 공개되지 않습니다.**

## 이름·연락처 바꾸기

`site.config.json` 파일의 값만 고치면 모든 페이지에 반영됩니다.

## 만지지 않아도 되는 것

`works/`, `media/`, `works.json`, `index.html`은 **자동으로 만들어지는 파일**입니다. 직접 고치면 다음 업로드 때 덮어써집니다.

## 개발자용

빌드:

```bash
pip install pillow
python portfolio/tools/build.py          # 전체 빌드
python portfolio/tools/build.py --check   # 생성물 참조만 검증
python -m pytest portfolio/tools/tests -v # 테스트
```

이 폴더는 상위 Jekyll 블로그와 절연돼 있습니다. front matter와 Liquid 문법을 쓰지 않으며, 모든 참조가 상대경로라 폴더째 다른 호스팅으로 옮길 수 있습니다. 이전 절차는 [설계 문서](../docs/superpowers/specs/2026-09-27-colorist-portfolio-design.md) 12장에 있습니다.
````

- [ ] **Step 3: 확인용 샘플 작업물을 만든다**

```bash
mkdir -p "portfolio/upload/01_샘플/첫번째작업"
python - <<'PY'
from PIL import Image
from pathlib import Path
base = Path("portfolio/upload/01_샘플/첫번째작업")
for name, color in [("cover.jpg", (70, 60, 55)), ("01.jpg", (30, 40, 50)), ("02.jpg", (90, 80, 70))]:
    Image.new("RGB", (2400, 1600), color).save(base / name)
(base / "memo.txt").write_text("샘플 게시물입니다.\n\n둘째 단락.", encoding="utf-8")
PY
```

- [ ] **Step 4: 로컬에서 전체 빌드와 검증**

Run:

```bash
python portfolio/tools/build.py
python portfolio/tools/build.py --check
python -m pytest portfolio/tools/tests -q
```

Expected: 빌드가 "카테고리 1개, 게시물 1개, 페이지 4개 생성"을 출력하고, `--check`가 0으로 끝나고, 테스트가 전부 통과한다.

- [ ] **Step 5: Jekyll 절연을 다시 검증**

Run:

```bash
bundle exec jekyll build --quiet
test ! -e _site/portfolio/upload && echo "OK: 원본 미배포"
test ! -e _site/portfolio/tools && echo "OK: tools 미배포"
test ! -e _site/portfolio/templates && echo "OK: templates 미배포"
diff -r portfolio/works _site/portfolio/works && echo "OK: 게시물 바이트 동일"
diff -r portfolio/media _site/portfolio/media && echo "OK: 이미지 바이트 동일"
grep -o '<loc>[^<]*portfolio[^<]*</loc>' _site/sitemap.xml || echo "OK: sitemap에 없음"
grep -c '{{' portfolio/index.html || echo "OK: 미치환 토큰 없음"
```

Expected: `OK:`로 시작하는 줄이 모두 나온다. 하나라도 빠지면 그 원인을 먼저 해결한다.

- [ ] **Step 6: 브라우저에서 눈으로 확인**

`portfolio/index.html`을 브라우저로 직접 열고 아래를 확인한다(Jekyll 서버 불필요).

1. 목록에 샘플 카테고리와 카드가 보이고, 카드 비율이 16:9로 일정한가
2. 카드를 누르면 게시물 페이지로 이동하고, 이미지와 본문(`샘플 게시물입니다`)이 보이는가
3. 게시물의 이미지를 클릭하면 전체화면으로 확대되고, ESC로 닫히고, 좌우 키로 이동하는가
4. 창 폭을 375px로 줄였을 때 가로 스크롤이 생기지 않는가
5. About / Contact 메뉴가 동작하는가
6. 개발자도구 콘솔에 에러가 없는가

- [ ] **Step 7: 커밋**

```bash
git add -A .github/workflows/portfolio.yml portfolio
git commit -m "feat(portfolio): Actions 자동 빌드와 작가용 설명서"
```

- [ ] **Step 8: 푸시 전 확인 사항을 사용자에게 보고**

푸시하면 Actions가 처음 돌면서 생성물을 커밋한다. 푸시 전에 아래를 사용자에게 확인받는다.

1. 저장소 설정에서 Actions의 워크플로 쓰기 권한이 켜져 있는지 (Settings → Actions → General → Workflow permissions → Read and write)
2. 샘플 작업물(`portfolio/upload/01_샘플/`)을 남길지 지울지
3. `site.config.json`의 플레이스홀더(사이트 이름, 이메일)를 지인에게 받아 채울지, 우선 그대로 둘지

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 항목 | 태스크 |
|---|---|
| 2장 Jekyll 절연 / 상대경로 / `_`·`.` 접두사 / 25MB | Task 1(exclude·검증), Task 9(상대경로), Task 12 Step 5 |
| 3장 디렉터리 구조 / upload·works 분리 / 원본 미공개 | Task 1, Task 8(media 경로), Task 9(works 경로) |
| 4장 제목·접두사·정렬 | Task 2, Task 8 `sort_works` |
| 4장 영상(link.txt·mp4·우선순위) | Task 4, Task 6 |
| 4장 이미지(확장자·자연정렬·커버 우선순위) | Task 6, Task 7 |
| 4장 본문(인코딩·이스케이프·단락) | Task 3 |
| 4장 무시 규칙 / 빈 폴더 | Task 6 |
| 4장 슬러그 충돌 | Task 2, Task 6 |
| 5장 manifest 스키마 | Task 8 |
| 6장 6단계 파이프라인 | Task 6·5·7·8·9·11 각각 |
| 6장 Actions·루프 방지·실패 노출 | Task 12 |
| 7장 목록·게시물·About·Contact·더보기·라이트박스·OG·alt | Task 9, Task 10 |
| 8장 site.config.json | Task 1, Task 9 |
| 9장 다크 고정·무채색·16:9·지연로딩 | Task 10 |
| 10장 엣지 케이스 9종 | Task 6(5종), Task 7·8(이미지·썸네일), Task 9(빈 상태), Task 10(JS 비활성) |
| 11장 검증 5종 | Task 11(단위·링크), Task 12 Step 5(Jekyll·sitemap), Step 6(화면) |
| 12장 이전 절차 | Task 12 README에서 설계 문서로 연결 |

빠진 항목 없음.

**2. 플레이스홀더 점검**

"TBD", "적절히 처리", "테스트 작성" 같은 지시 없이 모든 코드 블록이 실제 내용을 담고 있다. `site.config.json`의 `"NAME"`, `"hello@example.com"`은 스펙 13장이 명시한 **의도된 플레이스홀더 값**이며, 계획의 빈칸이 아니다.

**3. 타입·이름 일관성**

- `scanner.Work`의 `date` 필드는 Task 6에서 선언하고 Task 11 `build()`에서 채우고 Task 8 `sort_works`가 읽는다 — 이름 일치.
- `images.COVER_WIDTH`는 Task 7에서 정의해 Task 8과 Task 7 테스트가 import한다 — 일치.
- `render.render_site`의 반환은 `(list[Path], list[str])`이고 Task 11 `build()`가 그 형태로 받는다 — 일치.
- Task 9가 찍는 클래스 이름과 Task 10 CSS·JS의 선택자가 일치하도록 Task 10 Interfaces에 목록을 명시했다.
- `manifest.build_manifest(categories, media_root, generated_at)`의 인자 순서가 Task 8 정의와 Task 11 호출에서 같다.

자체 검토에서 고친 것: 초안의 Task 8 `_build_work`는 `needs_rebuild`를 호출하면서도 양쪽 분기에서 `make_cover`를 불러 증분 처리가 무의미했다. `images.image_size()`를 추가해 다시 만들 필요가 없을 때는 기존 산출물의 크기만 읽도록 커버와 갤러리 양쪽을 고쳤다(Task 7 Interfaces·구현·테스트, Task 8 import·양쪽 분기).
