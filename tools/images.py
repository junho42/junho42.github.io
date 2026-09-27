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


def _resize_to_width(image: Image.Image, width: int) -> Image.Image:
    """가로만 맞추고 비율은 건드리지 않는다. 원본보다 크게 늘리지 않는다."""
    if image.width <= width:
        return image
    height = max(1, round(image.height * width / image.width))
    return image.resize((width, height), Image.LANCZOS)


def make_cover(source: Path, dest: Path, width: int = COVER_WIDTH) -> tuple[int, int]:
    """가로 600px로만 줄이고 원본 비율을 지킨다.

    목록 그리드는 열 폭만 같고 높이는 작업물마다 다르다. 그래서 커버를
    한 비율로 잘라내지 않는다 — 세로 사진은 세로로, 파노라마는 납작하게
    그리드에 놓인다. 잘라내면 작가가 잡은 구도가 사라진다.
    """
    return _save(_resize_to_width(_load(source), width), dest)


def make_gallery(source: Path, dest: Path, width: int = GALLERY_WIDTH) -> tuple[int, int]:
    """비율을 유지한 채 가로를 맞춘다. 원본보다 크게 늘리지 않는다."""
    return _save(_resize_to_width(_load(source), width), dest)


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
            # 유튜브 썸네일은 이미 16:9이므로 가로만 맞추면 된다.
            # 저장 실패(디스크 부족, 권한 등)도 이 함수의 다른 모든 실패처럼
            # False를 돌려줘야 한다 — try 밖에 있으면 이 함수를 감싸지 않는
            # 호출부(manifest.py)까지 예외가 그대로 새어나간다.
            _save(_resize_to_width(image, COVER_WIDTH), dest)
        except (OSError, ValueError):
            continue
        return True
    return False
