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
        # 앞쪽 숫자를 그냥 잡으면 채널·유저 ID를 영상 ID로 오인한다.
        # vimeo.com/channels/32846/76979871 의 32846은 채널 ID,
        # 76979871이 실제 영상 ID다 — 경로의 마지막 숫자 세그먼트를 쓴다.
        segments = [segment for segment in parsed.path.split("/") if segment.isdigit()]
        if segments:
            video_id = segments[-1]
            return {
                "kind": "vimeo",
                "id": video_id,
                "embed": f"https://player.vimeo.com/video/{video_id}",
                "url": url,
            }

    return {"kind": "link", "id": None, "embed": None, "url": url}
