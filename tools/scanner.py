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


def _read_work(directory: Path) -> tuple[Work | None, list[str]]:
    warnings: list[str] = []
    images: list[Path] = []
    videos: list[Path] = []
    body_files: list[Path] = []
    link_file: Path | None = None

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
        elif suffix == ".txt":
            if child.name.lower() == LINK_FILENAME:
                link_file = child
            else:
                body_files.append(child)

    video: dict | None = None
    if link_file is not None:
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
    taken_category_slugs: set[str] = set()
    entries, dir_warnings = _sorted_children(upload_dir)
    warnings.extend(dir_warnings)
    for entry in entries:
        if entry.is_file():
            warnings.append(f"{entry.name}: 카테고리 폴더 밖의 파일은 무시합니다")
            continue

        order, title = strip_order_prefix(entry.name)
        category = Category(title=title, slug=title, order=order, directory=entry)

        taken_slugs: set[str] = set()
        children, child_warnings = _sorted_children(entry)
        warnings.extend(child_warnings)
        for child in children:
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
            # 카테고리 슬러그는 전체 스캔에서 유일해야 한다. "05_광고"와 "광고"처럼
            # 접두사만 다른 폴더가 같은 제목으로 떨어지면 같은 works/media 경로를
            # 가리켜 한쪽이 조용히 가려진다.
            unique = dedupe_slug(category.slug, taken_category_slugs)
            if unique != category.slug:
                warnings.append(f"{entry.name}: 카테고리 주소가 겹쳐 {unique}로 바꿨습니다")
            category.slug = unique
            taken_category_slugs.add(unique)
            categories.append(category)
        else:
            warnings.append(f"{entry.name}: 게시물이 없어 건너뜁니다")

    categories.sort(key=_category_sort_key)
    return categories, warnings
