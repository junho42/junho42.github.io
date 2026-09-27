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
