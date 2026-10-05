"""upload/ 를 훑어 게시물 자료구조를 만든다.

폴더 한 겹이 게시물 하나다: upload/<게시물>/. 카테고리 단계는 없다 —
화면에 드러나지도 않는 구분 때문에 작가가 폴더를 두 겹 만들어야 했고,
한 겹만 만들면 아무 경고 없이 사이트에서 사라졌다.

파일시스템을 읽기만 한다. 이미지 변환·날짜 조회·렌더링은 하지 않는다.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from naming import dedupe_slug, natural_key, strip_order_prefix
from textfile import body_to_html, join_paragraphs, read_text
from video import parse_video_url

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".avif"}
VIDEO_EXTENSIONS = {".mp4", ".webm", ".mov"}

LINK_FILENAME = "link.txt"
INFO_FILENAME = "info.json"
COVER_STEM = "cover"

# Info.json에서 읽는 항목. 비어 있거나 없는 항목은 예전 방식으로 대체한다 —
# 제목은 폴더 이름, 링크는 link.txt, 설명은 .txt 파일.
INFO_FIELDS = ("title", "genre", "description", "link")
# 단락 목록(["첫 단락", "둘째 단락"])으로도 적을 수 있는 항목
INFO_PARAGRAPH_FIELDS = ("description",)


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
    genre: str = ""


def _visible(path: Path) -> bool:
    """`.` 또는 `_`로 시작하는 항목은 없는 것으로 본다."""
    return not path.name.startswith((".", "_"))


def _sorted_children(directory: Path) -> tuple[list[Path], list[str]]:
    """directory 안의 보이는 항목을 자연 정렬해 (목록, 경고)로 돌려준다.

    깨진 심볼릭 링크는 is_dir()/is_file() 모두 False로 조용히 실패하기 때문에
    호출부가 디렉터리로 오인해 iterdir()를 호출할 수 있다. 그 경우와 권한 문제,
    스캔 중 폴더가 사라지는 경우 모두 iterdir()가 OSError를 던지므로 여기서
    잡아 경고로 바꾼다 — scan()이 예외를 던지지 않는다는 계약을 지키기 위함.
    """
    try:
        raw = list(directory.iterdir())
    except OSError as exc:
        return [], [f"{directory.name}: 폴더를 읽지 못했습니다 ({exc})"]
    visible = [child for child in raw if _visible(child)]
    return sorted(visible, key=lambda child: natural_key(child.name)), []


def _read_info(directory: Path, info_file: Path) -> tuple[dict[str, str], list[str]]:
    """Info.json을 읽어 {항목: 값}을 돌려준다. 문제가 있으면 경고만 남긴다.

    메모장으로 저장해도 깨지지 않도록 .txt와 같은 방식으로 인코딩을 판별한다.
    """
    label = f"{directory.name}/{info_file.name}"
    try:
        text, warning = read_text(info_file)
    except OSError as exc:
        return {}, [f"{label}: 파일을 읽지 못했습니다 ({exc})"]
    warnings = [warning] if warning else []
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return {}, warnings + [f"{label}: JSON 형식이 잘못되어 무시합니다 ({exc.lineno}번째 줄)"]
    if not isinstance(data, dict):
        return {}, warnings + [f"{label}: {{ }}로 감싼 형식이 아니어서 무시합니다"]

    info: dict[str, str] = {}
    for key in INFO_FIELDS:
        value = data.get(key)
        if value is None:
            continue
        if key in INFO_PARAGRAPH_FIELDS:
            value = join_paragraphs(value)
            if value is None:
                warnings.append(
                    f"{label}: {key} 값은 글자 또는 [\"단락\", \"단락\"] 목록이어야 해서 무시합니다"
                )
                continue
        elif not isinstance(value, str):
            warnings.append(f"{label}: {key} 값은 따옴표로 감싼 글자여야 해서 무시합니다")
            continue
        info[key] = value.strip()
    return info, warnings


def _read_work(directory: Path) -> tuple[Work | None, list[str]]:
    warnings: list[str] = []
    images: list[Path] = []
    videos: list[Path] = []
    body_files: list[Path] = []
    link_file: Path | None = None
    info_file: Path | None = None

    children, dir_warnings = _sorted_children(directory)
    warnings.extend(dir_warnings)
    for child in children:
        if child.is_dir():
            warnings.append(f"{directory.name}/{child.name}: 게시물 안의 하위 폴더는 무시합니다")
            continue
        suffix = child.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            images.append(child)
        elif suffix in VIDEO_EXTENSIONS:
            videos.append(child)
        elif child.name.lower() == INFO_FILENAME:
            info_file = child
        elif suffix == ".txt":
            if child.name.lower() == LINK_FILENAME:
                link_file = child
            else:
                body_files.append(child)

    info: dict[str, str] = {}
    if info_file is not None:
        info, info_warnings = _read_info(directory, info_file)
        warnings.extend(info_warnings)

    video: dict | None = None
    if info.get("link"):
        video = parse_video_url(info["link"])
        if video is None:
            warnings.append(
                f"{directory.name}/{info_file.name}: link 값이 http로 시작하는 주소가 아니어서 무시합니다"
            )
    if video is None and link_file is not None:
        try:
            text, warning = read_text(link_file)
        except OSError as exc:
            # 링크 파일 하나를 못 읽어도 mp4 파일 영상으로 대체할 수 있으니 건너뛴다.
            warnings.append(f"{directory.name}/{link_file.name}: 파일을 읽지 못했습니다 ({exc})")
        else:
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
    if info.get("description"):
        # Info.json에 설명이 있으면 그것만 쓴다. .txt까지 이어 붙이면
        # 같은 글이 두 번 들어가기 쉽다.
        body_files = []
        body_parts.append(body_to_html(info["description"]))
    for body_file in body_files:
        try:
            text, warning = read_text(body_file)
        except OSError as exc:
            # 본문 파일 하나가 읽히지 않아도 나머지 본문·이미지·영상은 살린다.
            warnings.append(f"{directory.name}/{body_file.name}: 파일을 읽지 못했습니다 ({exc})")
            continue
        if warning:
            warnings.append(warning)
        html = body_to_html(text)
        if html:
            body_parts.append(html)

    # 주소(slug)와 순서는 언제나 폴더 이름에서 온다. Info.json의 제목을
    # 고쳐도 이미 공유된 게시물 링크가 깨지지 않는다.
    order, folder_title = strip_order_prefix(directory.name)
    return (
        Work(
            title=info.get("title") or folder_title,
            slug=folder_title,
            order=order,
            directory=directory,
            images=images,
            cover=cover,
            video=video,
            body="\n".join(body_parts),
            genre=info.get("genre", ""),
        ),
        warnings,
    )


def scan(upload_dir: Path) -> tuple[list[Work], list[str]]:
    """(게시물 목록, 경고 목록)을 돌려준다. 예외를 던지지 않는다.

    upload/ 바로 아래의 폴더 하나가 게시물 하나다. 정렬은 manifest 단계에서
    한다(날짜를 그때 채우기 때문이다).
    """
    warnings: list[str] = []
    if not upload_dir.is_dir():
        return [], [f"업로드 폴더가 없습니다: {upload_dir}"]

    works: list[Work] = []
    taken_slugs: set[str] = set()
    entries, dir_warnings = _sorted_children(upload_dir)
    warnings.extend(dir_warnings)
    for entry in entries:
        if entry.is_file():
            warnings.append(f"{entry.name}: 게시물 폴더 밖의 파일은 무시합니다")
            continue

        work, work_warnings = _read_work(entry)
        warnings.extend(work_warnings)
        if work is None:
            continue

        # 주소는 전체에서 유일해야 한다. "05_광고"와 "광고"처럼 접두사만 다른
        # 폴더가 같은 제목으로 떨어지면 같은 works/media 경로를 가리켜
        # 한쪽이 조용히 가려진다.
        unique = dedupe_slug(work.slug, taken_slugs)
        if unique != work.slug:
            warnings.append(f"{entry.name}: 주소가 겹쳐 {unique}로 바꿨습니다")
        work.slug = unique
        taken_slugs.add(unique)
        works.append(work)

    return works, warnings
