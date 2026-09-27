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
    # BOM이 붙어 있는데 나머지 바이트가 어느 인코딩으로도 안 풀리면,
    # "utf-8"로 복구할 경우 BOM 자체가 본문에 리터럴 ﻿로 남는다.
    recovered = raw.decode("utf-8-sig", errors="replace")
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
