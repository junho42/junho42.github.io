"""스캔 결과와 이미지 변환을 엮어 works.json을 만든다."""

from __future__ import annotations

import json
import shutil
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
        # 이미 받아둔 썸네일이 있으면 다시 내려받지 않는다. 무조건 다시 받으면
        # i.ytimg.com이 잠깐 응답하지 않을 때 fetch_youtube_cover가 False를
        # 돌려주고, 그 결과로 cover가 null이 되어 디스크에 있는 멀쩡한
        # 커버가 목록에서 사라진다.
        fetched = cover_dest.exists() or fetch_youtube_cover(work.video["id"], cover_dest)
        if not fetched:
            warnings.append(f"{category.title}/{work.title}: 유튜브 썸네일을 받지 못했습니다")
        else:
            try:
                # 다른 모든 미디어 경로처럼 실제 파일에서 크기를 읽는다.
                # 16:9를 다시 계산하지 않는다 — 실제 저장된 크기와 다를 수 있다.
                size = image_size(cover_dest)
            except OSError:
                warnings.append(f"{category.title}/{work.title}: 유튜브 썸네일을 읽을 수 없습니다")
            else:
                cover_entry = {"src": _relative(site_root, cover_dest), "w": size[0], "h": size[1]}

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

    # upload/ 는 _config.yml 에서 발행 대상에서 빠지므로, 로컬 mp4를 그 자리에
    # 둔 채로 링크만 걸면 재생되지 않는다. media/ 로 복사해 실제로 서빙되는
    # 경로를 만들고, 그 경로로 url을 다시 쓴다. work.video는 스캐너의 입력
    # 자료구조라 직접 고치면 build_manifest를 같은 데이터로 두 번 부르는
    # 경우 결과가 달라지므로, 새 dict를 만들어 매니페스트에만 반영한다.
    video_entry = work.video
    if work.video is not None and work.video.get("kind") == "file":
        source = work.directory / work.video["url"]
        dest = out_dir / source.name
        try:
            if needs_rebuild(source, dest):
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
            video_entry = {**work.video, "url": _relative(site_root, dest)}
        except OSError:
            warnings.append(f"{category.title}/{work.title}/{source.name}: 영상을 복사하지 못해 재생에서 제외했습니다")
            video_entry = None

    entry = {
        "title": work.title,
        "slug": work.slug,
        "url": f"works/{category.slug}/{work.slug}/",
        "date": work.date.isoformat() if work.date else None,
        "order": work.order,
        "cover": cover_entry,
        "video": video_entry,
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
