"""manifest와 설정을 HTML로 찍는다.

템플릿 엔진을 쓰지 않는다. templates/ 의 {{TOKEN}}을 문자열로 치환하고,
페이지 깊이에 맞는 상대경로 접두사를 계산해 넣는다. 산출물에는
{{ 가 하나도 남지 않아야 한다(test_render가 이를 검사한다).
"""

from __future__ import annotations

import hashlib
import re
from html import escape
from pathlib import Path
from urllib.parse import quote, urlparse

from textfile import body_to_html

_TOKEN = re.compile(r"\{\{([A-Z_]+)\}\}")

# 이미지도 영상 커버도 없는 게시물(비-YouTube 링크만, 커버 없는 mp4, 디코딩
# 실패한 cover.jpg)은 manifest의 cover가 null이다. null을 그대로 <img src="">에
# 넣으면 브라우저가 현재 페이지 주소를 다시 요청하고 linkcheck는 빈 참조를
# 건너뛰어 이를 못 잡는다. manifest는 진짜 데이터 계약이라 null을 유지하고,
# 렌더링 시점에만 이 무채색 플레이스홀더로 대체한다.
_PLACEHOLDER_COVER = {"src": "assets/placeholder-600.webp", "w": 600, "h": 338}


def _cover_or_placeholder(work: dict) -> dict:
    """work["cover"]가 없으면 커버 자리 전부에서 쓸 플레이스홀더를 돌려준다."""
    return work.get("cover") or _PLACEHOLDER_COVER


def render_template(text: str, values: dict[str, str]) -> str:
    """{{TOKEN}}을 치환한다. 값이 없는 토큰은 지운다."""
    return _TOKEN.sub(lambda match: values.get(match.group(1), ""), text)


def relative_prefix(depth: int) -> str:
    """페이지가 사이트 루트에서 depth만큼 깊을 때의 접두사."""
    return "../" * depth


def _url_path(path: str) -> str:
    """경로를 퍼센트 인코딩해 안전한 URL로 만든다. 슬래시는 남긴다.

    폴더 이름은 작가가 마음대로 짓는다 — 이 프로젝트의 전제 자체가
    "작가가 폴더 이름을 뭐라 짓든 그대로 URL이 된다"이다. 이름에 `#`이
    들어가면 원시 href는 그 뒤를 프래그먼트로 잘라 먹어 이미지가 조용히
    깨지고, `?`는 쿼리 스트링을 시작하고, `&`·`%`·공백도 마찬가지로
    문제를 일으킨다. html.escape는 이 문자들을 건드리지 않으므로
    이스케이프만으로는 URL을 보호하지 못한다. 그래서 파일시스템 경로나
    화면에 보이는 링크 텍스트가 아니라, HTML 안의 로컬 URL(href/src)은
    전부 이 함수를 거친다 — og:image 같은 외부 절대 URL도 마찬가지다.
    """
    return quote(path, safe="/-_.~")


def _asset_version(path: Path) -> str:
    """파일 내용에서 만든 짧은 버전. CSS·JS 주소 뒤에 ?v=로 붙인다.

    파일이 바뀌면 주소가 바뀌므로 브라우저가 예전 캐시를 계속 쓰지 못한다 —
    캐시 지시 헤더를 보내지 않는 로컬 서버와 GitHub Pages 둘 다에서 생기던
    "고쳤는데 그대로" 문제를 막는다.
    """
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()[:8]
    except OSError:
        return "0"


def _chevron(points: str) -> str:
    """이전·다음 화살표 아이콘. 글자(‹ ›)는 글꼴 안에서 아래로 처져 박스
    가운데에 맞지 않으므로 24×24 정사각형 한가운데(12, 12)를 지나는 도형으로 그린다.
    색은 currentColor라 링크 글자색(호버 포함)을 그대로 따른다.
    """
    return (
        '<svg class="post-arrow-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">'
        f'<polyline points="{points}" fill="none" stroke="currentColor" stroke-width="1.5" '
        'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )


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


def _site_title(config: dict) -> str:
    """모든 페이지의 <title>에 공용으로 들어가는 이름.

    define.json의 title이 비어 있으면 헤더의 상호(siteName)로 대신한다.
    """
    return config.get("title") or config.get("siteName", "")


def _instagram(value: str) -> tuple[str, str]:
    """(주소, 보이는 글자). 주소 전체를 적어도, @아이디만 적어도 된다."""
    if value.startswith(("http://", "https://")):
        handle = urlparse(value).path.strip("/").split("/")[0]
        return value, f"@{handle}" if handle else "Instagram"
    handle = value.lstrip("@").strip("/")
    return f"https://www.instagram.com/{handle}/", f"@{handle}"


def _copy_button(value: str) -> str:
    # 누르면 app.js가 data-copy 값을 클립보드에 넣는다.
    safe = escape(value)
    return f'<button class="copy" type="button" data-copy="{safe}">{safe}</button>'


def _map_html(address: str) -> str:
    """주소를 검색어로 넘긴 구글 지도 임베드. API 키가 필요 없는 형식이다."""
    src = f"https://maps.google.com/maps?q={quote(address)}&output=embed"
    return (
        '<div class="contact-map">'
        f'<iframe src="{escape(src)}" title="지도: {escape(address)}" '
        'loading="lazy" referrerpolicy="no-referrer-when-downgrade" allowfullscreen></iframe>'
        "</div>"
    )


def _contact_html(config: dict) -> str:
    """이름 / 이메일·전화(복사) / 인스타그램(링크) / 주소(+지도).

    값이 비어 있는 항목은 줄째 뺀다.
    """
    rows = []
    has_copy = False
    name = config.get("name") or ""
    if name:
        rows.append(("Name", f"<span>{escape(name)}</span>"))
    for key, label in (("email", "Email"), ("phone", "Phone")):
        value = config.get(key) or ""
        if value:
            rows.append((label, _copy_button(value)))
            has_copy = True
    instagram = config.get("instagram") or ""
    if instagram:
        url, text = _instagram(instagram)
        rows.append(
            ("Instagram", f'<a href="{escape(url)}" target="_blank" rel="noopener">{escape(text)}</a>')
        )
    address = config.get("address") or ""
    if address:
        rows.append(("Address", f"<span>{escape(address)}</span>"))

    parts = []
    if rows:
        items = "\n".join(
            f'    <li><span class="contact-label">{label}</span>{value}</li>'
            for label, value in rows
        )
        parts.append(f'<ul class="contact-list">\n{items}\n  </ul>')
    if has_copy:
        # 복사 결과를 알리는 토스트. 화면 하단에 떴다 사라지고(app.js),
        # role="status"라 스크린리더도 같은 문구를 읽는다.
        parts.append('<div class="toast" role="status" aria-live="polite"></div>')
    if address:
        parts.append(_map_html(address))
    return "\n  ".join(parts)


def _absolute(config: dict, relative: str) -> str | None:
    base = (config.get("siteUrl") or "").rstrip("/")
    if not base or not relative:
        return None
    return f"{base}/{relative}"


def _video_html(video: dict | None, rel: str, title: str, cover: dict) -> str:
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
        # 스펙 4장: "포스터는 커버 이미지를 쓴다". cover는 항상 실제 커버나
        # 플레이스홀더 중 하나를 갖고 있어 src가 빈 문자열일 일이 없다.
        poster = _url_path(cover.get("src", ""))
        return (
            '<div class="player">'
            f'<video controls preload="metadata" src="{rel}{source}" poster="{rel}{poster}"></video>'
            "</div>"
        )
    if kind == "link" and video.get("url"):
        return (
            '<p class="player-link">'
            f'<a href="{escape(video["url"])}" rel="noopener">영상 보기 ↗</a></p>'
        )
    return ""


def _write(path: Path, html: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    return path


# 상단 메뉴. About 페이지는 없다 — 소개는 지금 어디에도 실리지 않는다.
_NAV_ITEMS = (("index.html", "works"), ("contact.html", "contact"))


def _nav_html(rel: str, current: str) -> str:
    """현재 페이지의 탭에 표시를 남긴다.

    색만으로 상태를 알리지 않도록 aria-current도 같이 넣는다 —
    화면을 못 보는 사람에게 색은 아무 정보가 아니다.
    """
    links = []
    for href, label in _NAV_ITEMS:
        if href == current:
            links.append(
                f'<a class="is-current" aria-current="page" href="{rel}{href}">'
                f'<span class="header-text">{label}</span></a>'
            )
        else:
            links.append(f'<a href="{rel}{href}"><span class="header-text">{label}</span></a>')
    return "\n    ".join(links)


def _page(
    templates_dir: Path,
    config: dict,
    *,
    depth: int,
    title: str,
    meta: str,
    content: str,
    current: str = "",
    body_class: str = "",
) -> str:
    rel = relative_prefix(depth)
    # templates/ 옆의 assets/ 가 실제로 서빙되는 파일이다.
    assets = templates_dir.parent / "assets"
    return render_template(
        _load(templates_dir, "page.html"),
        {
            "REL": rel,
            "TITLE": escape(title),
            "META": meta,
            "SITE_NAME": escape(config.get("siteName", "")),
            "NAV": _nav_html(rel, current),
            "BODY_CLASS": f' class="{body_class}"' if body_class else "",
            "CSS_V": _asset_version(assets / "css" / "style.css"),
            "JS_V": _asset_version(assets / "js" / "app.js"),
            "CONTENT": content,
        },
    )


def _grid_html(works: list[dict], rel: str, page_size: int, templates_dir: Path) -> str:
    """작업물 카드 그리드. 목록 페이지와 게시물 페이지 아래쪽이 같이 쓴다.

    page_size를 넘는 카드에는 extra를 붙여 처음에는 숨긴다 — 스크롤이
    내려오면 JS가 한 묶음씩 풀고, JS가 없으면 전부 보인다.
    """
    if not works:
        return '<p class="empty">작업물 준비 중입니다.</p>'

    card_template = _load(templates_dir, "partials/card.html")
    cards = []
    for index, work in enumerate(works):
        cover = _cover_or_placeholder(work)
        badge = '<span class="badge">VIDEO</span>' if work.get("video") else ""
        # 장르가 없으면 구분선도 뺀다 — 제목 아래 선만 덩그러니 남지 않게.
        genre = work.get("genre") or ""
        genre_html = (
            '<span class="card-rule" aria-hidden="true"></span>'
            f'<span class="card-genre">{escape(genre)}</span>'
            if genre
            else ""
        )
        card = render_template(
            card_template,
            {
                "REL": rel,
                "URL": _url_path(work["url"]),
                "COVER": _url_path(cover.get("src", "")),
                "COVER_W": str(cover.get("w", 600)),
                "COVER_H": str(cover.get("h", 338)),
                "TITLE": escape(work["title"]),
                "BADGE": badge,
                "GENRE": genre_html,
            },
        )
        if index >= page_size:
            card = card.replace('class="card"', 'class="card extra"', 1)
        cards.append("    " + card.strip())

    has_more = len(works) > page_size
    return render_template(
        _load(templates_dir, "partials/section.html"),
        {
            "CARDS": "\n".join(cards),
            "HAS_MORE": "true" if has_more else "false",
            "MORE_BUTTON": (
                '<button class="more" type="button">Show more</button>' if has_more else ""
            ),
        },
    )


def _render_index(manifest: dict, config: dict, site_root: Path, templates_dir: Path) -> Path:
    page_size = int(config.get("gridPageSize") or 8)
    content = _grid_html(manifest["works"], "", page_size, templates_dir)

    meta = _meta_block(
        config,
        _site_title(config),
        config.get("tagline", ""),
        _absolute(config, _url_path(config.get("ogImage") or "")),
    )
    html = _page(
        templates_dir,
        config,
        depth=0,
        title=_site_title(config),
        meta=meta,
        content=content,
        current="index.html",
    )
    return _write(site_root / "index.html", html)


def _render_contact(config: dict, site_root: Path, templates_dir: Path) -> Path:
    """Contact 페이지.

    이름·이메일·전화·인스타그램·주소는 여기 본문에 들어간다. 푸터가 내용 없는 띠로
    바뀌면서 그 링크들이 실릴 곳이 사이트에 이 페이지밖에 없다.
    """
    # 페이지 제목은 모든 페이지에서 같다(define.json의 title)
    title = _site_title(config)
    body = body_to_html(config.get("contactNote", "") or "")
    # 본문 맨 위의 제목 — 각오나 마음가짐 한 줄. 비우면 빠진다.
    headline = config.get("contactTitle") or ""
    if headline:
        body = f'<h2 class="contact-title">{escape(headline)}</h2>\n  {body}'
    contact = _contact_html(config)
    links_html = f"\n  {contact}" if contact else ""
    # 화면을 반으로 나눠 왼쪽에는 심볼을 고정하고, 오른쪽 본문만 스크롤된다.
    # 제목은 화면에서 숨기되 스크린리더와 문서 구조에는 남긴다.
    # 심볼은 빌드가 assets/img/faran_symbol.png 에서 만든 웹용 사본이다(build.py).
    # 원본이 없으면 왼쪽 칸을 통째로 뺀다.
    symbol = config.get("symbol")
    symbol_html = ""
    if symbol:
        symbol_html = (
            '<div class="contact-symbol">'
            f'<img src="{_url_path(symbol["src"])}" alt="{escape(config.get("siteName", ""))}" '
            f'width="{symbol["w"]}" height="{symbol["h"]}">'
            "</div>\n"
        )
    content = (
        '<h1 class="sr-only">Contact</h1>\n'
        '<div class="contact-split">\n'
        f"{symbol_html}"
        '<section class="contact-body">\n'
        f"  {body}{links_html}\n"
        "</section>\n"
        "</div>"
    )
    html = _page(
        templates_dir,
        config,
        depth=0,
        title=title,
        meta=_meta_block(config, title, "", None),
        content=content,
        current="contact.html",
        # 넓은 화면에서 헤더와 왼쪽 심볼을 고정하는 스위치(style.css)
        body_class="is-contact",
    )
    return _write(site_root / "contact.html", html)


def _render_post(
    work: dict,
    neighbours: tuple[dict | None, dict | None],
    all_works: list[dict],
    config: dict,
    site_root: Path,
    templates_dir: Path,
) -> Path:
    depth = 2  # works/<게시물>/
    rel = relative_prefix(depth)
    figure_template = _load(templates_dir, "partials/figure.html")
    cover = _cover_or_placeholder(work)

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

    # 좌우 끝 화살표. 화면에 고정돼 있어 갤러리를 한참 내려본 뒤에도
    # 이웃 게시물로 넘어갈 수 있다 — 아래쪽 이동 링크를 없앤 자리를 대신한다.
    previous_work, next_work = neighbours
    arrows = []
    if previous_work:
        arrows.append(
            f'<a class="post-arrow post-arrow-prev" href="{rel}{_url_path(previous_work["url"])}"'
            f' aria-label="이전 작업물: {escape(previous_work["title"])}">{_chevron("15 6 9 12 15 18")}</a>'
        )
    if next_work:
        arrows.append(
            f'<a class="post-arrow post-arrow-next" href="{rel}{_url_path(next_work["url"])}"'
            f' aria-label="다음 작업물: {escape(next_work["title"])}">{_chevron("9 6 15 12 9 18")}</a>'
        )
    nav_html = f'<nav class="post-arrows">{"".join(arrows)}</nav>' if arrows else ""

    # 아래쪽에는 Works와 같은 그리드를 둔다. 보고 있는 게시물은 뺀다.
    others = [other for other in all_works if other["url"] != work["url"]]
    related = _grid_html(others, rel, int(config.get("gridPageSize") or 8), templates_dir)

    content = render_template(
        _load(templates_dir, "partials/post.html"),
        {
            "VIDEO": _video_html(work.get("video"), rel, work["title"], cover),
            "TITLE": escape(work["title"]),
            "GALLERY": "\n".join(figures),
            "BODY": work.get("body", ""),
            "POST_NAV": nav_html,
            "RELATED": related,
        },
    )

    meta = _meta_block(
        config,
        f"{work['title']} — {_site_title(config)}",
        _site_title(config),
        _absolute(config, _url_path(cover.get("src", ""))),
    )
    html = _page(
        templates_dir,
        config,
        depth=depth,
        title=_site_title(config),
        meta=meta,
        content=content,
        # 게시물은 Works에 속하므로 그 탭을 켠 상태로 둔다
        current="index.html",
    )
    return _write(site_root / "works" / work["slug"] / "index.html", html)


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
        _render_contact(config, site_root, templates_dir),
    ]

    # 화살표 순서는 목록 그리드의 순서와 같아야 한다. 카테고리는 화면에
    # 드러나지 않으므로 카테고리 안에서만 이웃을 찾으면 그리드에서 나란히
    # 있던 작업물이 서로 이웃이 아니게 된다.
    all_works = manifest["works"]

    for index, work in enumerate(all_works):
        previous_work = all_works[index - 1] if index > 0 else None
        next_work = all_works[index + 1] if index + 1 < len(all_works) else None
        if work.get("cover") is None:
            warnings.append(f"{work['title']}: 커버 이미지가 없습니다")
        pages.append(
            _render_post(
                work,
                (previous_work, next_work),
                all_works,
                config,
                site_root,
                templates_dir,
            )
        )
    return pages, warnings
