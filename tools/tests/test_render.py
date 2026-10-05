import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

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
                "url": f"works/작업{index}/",
                "date": NOW.isoformat(),
                "order": None,
                "cover": {"src": f"media/작업{index}/cover-600.webp", "w": 600, "h": 338},
                "video": None,
                "images": [{"src": f"media/작업{index}/01-a-1600.webp", "w": 1600, "h": 1067}],
                "body": "<p>본문</p>",
            }
        )
    return {"generatedAt": NOW.isoformat(), "works": works}


def test_토큰을_치환한다():
    assert render_template("<p>{{A}}-{{B}}</p>", {"A": "1", "B": "2"}) == "<p>1-2</p>"


def test_없는_토큰은_빈_문자열로_지운다():
    assert render_template("<p>{{A}}{{MISSING}}</p>", {"A": "1"}) == "<p>1</p>"


def test_상대경로_접두사():
    # 함수 자체는 깊이와 무관하게 동작해야 한다.
    # 게시물 페이지가 쓰는 깊이는 2(works/<게시물>/)다.
    assert relative_prefix(0) == ""
    assert relative_prefix(1) == "../"
    assert relative_prefix(2) == "../../"
    assert relative_prefix(3) == "../../../"


def test_목록과_게시물과_고정페이지를_만든다(tmp_path):
    pages, warnings = render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)

    names = {page.relative_to(tmp_path).as_posix() for page in pages}
    assert "index.html" in names
    assert "contact.html" in names
    assert "works/작업1/index.html" in names
    assert warnings == []


def test_생성물에_치환되지_않은_토큰이_남지_않는다(tmp_path):
    pages, _ = render_site(_manifest(3), CONFIG, tmp_path, TEMPLATES)
    for page in pages:
        assert "{{" not in page.read_text(encoding="utf-8"), page


def test_게시물_페이지는_상대경로로_자산을_참조한다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    # works/작업1/ 은 2단 깊이다
    assert "../../assets/css/style.css" in html
    # 폴더 이름은 작가 마음대로라 #, ?, & 같은 문자가 원시 href를 깨뜨릴 수
    # 있다. 로컬 URL도 퍼센트 인코딩되므로, 손으로 값을 타이핑하지 않고
    # 같은 규칙(quote(..., safe="/-_.~"))으로 직접 계산해 비교한다.
    encoded_media = quote("media/작업1/01-a-1600.webp", safe="/-_.~")
    assert f"../../{encoded_media}" in html
    assert "/assets/css" not in html.replace("../../assets/css", "")


def test_목록_페이지는_접두사_없이_참조한다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    # 뒤에 ?v=버전이 붙으므로 여는 따옴표부터 경로까지만 본다
    assert 'href="assets/css/style.css?v=' in html
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
    html = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert 'property="og:title"' in html
    # 사이트 내부 링크와 같은 규칙으로 퍼센트 인코딩된다
    assert (
        quote("https://example.com/portfolio/media/작업1/cover-600.webp", safe=":/-_.~")
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


def test_영상_게시물은_영상이_갤러리와_본문보다_먼저_온다(tmp_path):
    # 제목은 Contact처럼 어두운 헤더 띠가 되어 맨 위에 온다. 영상은 그
    # 헤더 아래에서 첫 콘텐츠다 — 갤러리와 본문보다 앞이다.
    manifest = _manifest()
    manifest["works"][0]["video"] = {
        "kind": "youtube",
        "id": "abcdef",
        "embed": "https://www.youtube-nocookie.com/embed/abcdef",
        "url": "https://youtu.be/abcdef",
    }
    render_site(manifest, CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert html.index("youtube-nocookie") < html.index('class="gallery"')
    assert html.index("youtube-nocookie") < html.index('class="post-body"')


def test_작업물이_없으면_빈_상태를_보여준다(tmp_path):
    empty = {"generatedAt": NOW.isoformat(), "works": []}
    render_site(empty, CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert "준비 중" in html


def test_커버가_없으면_빈_src_대신_플레이스홀더를_쓴다(tmp_path):
    # 이미지도 유튜브 썸네일도 없는 게시물(비-YouTube 링크, 커버 없는 mp4,
    # 디코딩 실패한 cover.jpg)은 manifest의 cover가 null이다. 그대로 두면
    # 카드가 <img src="">를 찍어 브라우저가 페이지 자신을 다시 요청한다.
    manifest = _manifest()
    manifest["works"][0]["cover"] = None
    pages, _ = render_site(manifest, CONFIG, tmp_path, TEMPLATES)

    found_placeholder = False
    for page in pages:
        html = page.read_text(encoding="utf-8")
        assert 'src=""' not in html, page
        if "placeholder-600" in html:
            found_placeholder = True
    assert found_placeholder


def test_커버가_없으면_경고를_남긴다(tmp_path):
    manifest = _manifest()
    manifest["works"][0]["cover"] = None
    _, warnings = render_site(manifest, CONFIG, tmp_path, TEMPLATES)

    assert any("커버 이미지가 없습니다" in w for w in warnings)


def test_로컬_영상은_커버를_포스터로_쓴다(tmp_path):
    # 스펙 4장: "포스터는 커버 이미지를 쓴다".
    manifest = _manifest()
    manifest["works"][0]["video"] = {
        "kind": "file",
        "id": None,
        "embed": None,
        "url": "reel.mp4",
    }
    render_site(manifest, CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    encoded_cover = quote("media/작업1/cover-600.webp", safe="/-_.~")
    assert f'poster="../../{encoded_cover}"' in html


def test_좌우_화살표가_이웃_게시물로_연결된다(tmp_path):
    # 제목만으로 단정하면 아래쪽 작업물 그리드에도 그 제목이 있어서
    # 화살표가 깨져도 통과한다. href를 직접 확인한다.
    render_site(_manifest(2), CONFIG, tmp_path, TEMPLATES)
    first = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")
    second = (tmp_path / "works" / "작업2" / "index.html").read_text(encoding="utf-8")

    next_url = quote("works/작업2/", safe="/-_.~")
    prev_url = quote("works/작업1/", safe="/-_.~")

    # 첫 게시물에는 다음만, 마지막에는 이전만 있다
    assert f'class="post-arrow post-arrow-next" href="../../{next_url}"' in first
    assert "post-arrow-prev" not in first
    assert f'class="post-arrow post-arrow-prev" href="../../{prev_url}"' in second
    assert "post-arrow-next" not in second


def test_게시물_아래에_다른_작업물_그리드가_온다(tmp_path):
    # 하단 이동 링크를 없앤 자리에 Works와 같은 그리드가 들어간다.
    # 보고 있는 게시물은 그 그리드에서 빠진다.
    render_site(_manifest(3), CONFIG, tmp_path, TEMPLATES)
    first = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    assert '<div class="grid">' in first
    own_url = quote("works/작업1/", safe="/-_.~")
    assert f'href="../../{own_url}"' not in first
    for other in ("작업2", "작업3"):
        assert f'href="../../{quote(f"works/{other}/", safe="/-_.~")}"' in first


def test_카드에_장르가_있으면_구분선과_함께_제목_아래에_나온다(tmp_path):
    manifest = _manifest(1)
    manifest["works"][0]["genre"] = "뮤직<비디오>"
    render_site(manifest, CONFIG, tmp_path, TEMPLATES)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert '<span class="card-name">작업1</span>' in index
    assert '<span class="card-rule" aria-hidden="true"></span>' in index
    assert '<span class="card-genre">뮤직&lt;비디오&gt;</span>' in index


def test_카드에_장르가_없으면_구분선도_없다(tmp_path):
    render_site(_manifest(1), CONFIG, tmp_path, TEMPLATES)
    index = (tmp_path / "index.html").read_text(encoding="utf-8")

    assert '<span class="card-name">작업1</span>' in index
    assert "card-rule" not in index
    assert "card-genre" not in index


def _page_title(html):
    return html.split("<title>", 1)[1].split("</title>", 1)[0]


def test_title이_있으면_모든_페이지_제목이_그_값으로_고정된다(tmp_path):
    config = dict(CONFIG, title="공용 제목")
    render_site(_manifest(), config, tmp_path, TEMPLATES)

    # 페이지 이름이나 작업물 제목을 앞에 붙이지 않는다
    assert _page_title((tmp_path / "index.html").read_text(encoding="utf-8")) == "공용 제목"
    assert _page_title((tmp_path / "contact.html").read_text(encoding="utf-8")) == "공용 제목"
    post = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")
    assert _page_title(post) == "공용 제목"
    # 헤더의 상호는 title이 아니라 siteName이다
    assert '<a class="brand" href="index.html"><span class="header-text">NAME</span></a>' in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_title이_없으면_siteName을_페이지_제목에_쓴다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)

    assert _page_title((tmp_path / "index.html").read_text(encoding="utf-8")) == "NAME"


def test_Contact에_이름_이메일_전화_인스타그램이_들어간다(tmp_path):
    config = dict(CONFIG, name="홍길동", phone="010-1234-5678")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    # 이름도 다른 항목처럼 '이름표 값' 한 줄이고, 목록의 맨 앞이다
    assert '<ul class="contact-list">\n    <li><span class="contact-label">Name</span><span>홍길동</span></li>' in html
    # 이메일과 전화는 누르면 복사되는 버튼이다(app.js)
    assert '<button class="copy" type="button" data-copy="hello@example.com">hello@example.com</button>' in html
    assert '<button class="copy" type="button" data-copy="010-1234-5678">010-1234-5678</button>' in html
    assert '<a href="https://instagram.com/x" target="_blank" rel="noopener">@x</a>' in html
    assert 'role="status"' in html


def test_인스타그램을_아이디로만_적어도_주소가_된다(tmp_path):
    config = dict(CONFIG, instagram="@faran.color")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert '<a href="https://www.instagram.com/faran.color/" target="_blank" rel="noopener">@faran.color</a>' in html


def test_연락처_값이_비어_있으면_그_줄은_빠진다(tmp_path):
    config = dict(CONFIG, email="", instagram="", name="", phone="")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "contact-list" not in html
    assert ">Name</span>" not in html
    assert 'role="status"' not in html


def test_연락처_값은_이스케이프된다(tmp_path):
    config = dict(CONFIG, name="<b>이름</b>", phone='"010"')
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "<b>이름</b>" not in html
    assert 'data-copy="&quot;010&quot;"' in html


def test_주소가_있으면_주소와_지도가_나온다(tmp_path):
    config = dict(CONFIG, address="서울특별시 중구 세종대로 110")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert '<span class="contact-label">Address</span><span>서울특별시 중구 세종대로 110</span>' in html
    q = quote("서울특별시 중구 세종대로 110")
    assert f'src="https://maps.google.com/maps?q={q}&amp;output=embed"' in html
    assert 'title="지도: 서울특별시 중구 세종대로 110"' in html
    assert 'loading="lazy"' in html


def test_주소가_없으면_주소_줄과_지도가_없다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "Address" not in html
    assert "contact-map" not in html


def test_주소만_있어도_주소와_지도가_나온다(tmp_path):
    config = dict(CONFIG, email="", instagram="", name="", phone="", address="부산")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "<span>부산</span>" in html
    assert "contact-map" in html
    # 복사할 버튼이 없으니 복사 알림 자리도 없다
    assert 'role="status"' not in html


def test_복사_버튼이_없으면_복사_알림_자리도_없다(tmp_path):
    config = dict(CONFIG, email="", phone="")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "@x</a>" in html
    assert 'role="status"' not in html


def test_CSS와_JS_주소에_내용_기반_버전이_붙는다(tmp_path):
    # 파일이 바뀌면 주소가 바뀌어 브라우저가 예전 캐시를 쓰지 못한다.
    import hashlib

    def version(relative):
        data = (TEMPLATES.parent / relative).read_bytes()
        return hashlib.sha1(data).hexdigest()[:8]

    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")
    post = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")

    css = version("assets/css/style.css")
    js = version("assets/js/app.js")
    assert f'href="assets/css/style.css?v={css}"' in html
    assert f'src="assets/js/app.js?v={js}"' in html
    assert f'href="../../assets/css/style.css?v={css}"' in post


SYMBOL = {"src": "media/site/faran_symbol-880.webp", "w": 880, "h": 447}


def test_Contact는_좌측_심볼과_우측_본문으로_나뉜다(tmp_path):
    render_site(_manifest(), dict(CONFIG, symbol=SYMBOL), tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    # 예전의 어두운 제목 블록은 없다
    assert "page-contact" not in html
    split = html.index('<div class="contact-split">')
    symbol = html.index('<div class="contact-symbol">')
    body = html.index('<section class="contact-body">')
    assert split < symbol < body
    assert 'src="media/site/faran_symbol-880.webp"' in html
    # 제목은 화면에서만 숨기고 스크린리더에는 남긴다
    assert '<h1 class="sr-only">Contact</h1>' in html


def test_Contact_페이지에만_body_클래스가_붙는다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)

    assert '<body id="top" class="is-contact">' in (tmp_path / "contact.html").read_text(encoding="utf-8")
    assert '<body id="top">' in (tmp_path / "index.html").read_text(encoding="utf-8")


def test_Contact_본문_맨_위에_contactTitle이_온다(tmp_path):
    config = dict(CONFIG, contactTitle="빛을 <다루는> 마음")
    render_site(_manifest(), config, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    title = html.index('<h2 class="contact-title">빛을 &lt;다루는&gt; 마음</h2>')
    assert html.index('<section class="contact-body">') < title < html.index("메일로 연락 주세요")


def test_contactTitle이_비어_있으면_제목이_없다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "contact-title" not in html


def test_맨_위로_목적지는_고정되지_않는_body다(tmp_path):
    # Contact에서는 헤더가 sticky라 화면 맨 위에 늘 보인다. 목적지가 헤더면
    # 브라우저가 "이미 보인다"며 스크롤하지 않아 맨 위로 버튼이 먹통이 된다.
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    for name in ("index.html", "contact.html"):
        html = (tmp_path / name).read_text(encoding="utf-8")
        assert '<header class="masthead">' in html
        assert html.count('id="top"') == 1
        assert '<a class="to-top" href="#top"' in html


def test_심볼은_빌드가_만든_웹용_사본의_실제_크기로_들어간다(tmp_path):
    render_site(_manifest(), dict(CONFIG, symbol=SYMBOL), tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert '<img src="media/site/faran_symbol-880.webp" alt="NAME" width="880" height="447">' in html


def test_심볼이_없으면_좌측_칸도_없다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert "contact-symbol" not in html
    assert '<section class="contact-body">' in html


def test_헤더_글자는_세로_축소용_span에_담긴다(tmp_path):
    # 세로 80%는 transform으로 준다. 메뉴의 <a>에 직접 걸면 타원 테두리까지
    # 찌그러지므로 글자만 감싼 span에 건다.
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)
    html = (tmp_path / "contact.html").read_text(encoding="utf-8")

    assert '<a class="brand" href="index.html"><span class="header-text">NAME</span></a>' in html
    assert '<a href="index.html"><span class="header-text">works</span></a>' in html
    assert '<a class="is-current" aria-current="page" href="contact.html"><span class="header-text">contact</span></a>' in html


def test_모든_페이지에_파비콘이_상대경로로_들어간다(tmp_path):
    render_site(_manifest(), CONFIG, tmp_path, TEMPLATES)

    index = (tmp_path / "index.html").read_text(encoding="utf-8")
    post = (tmp_path / "works" / "작업1" / "index.html").read_text(encoding="utf-8")
    assert '<link rel="icon" href="assets/img/faran_favicon.ico">' in index
    assert '<link rel="icon" href="../../assets/img/faran_favicon.ico">' in post


def test_이전_다음_화살표는_글자가_아니라_SVG_아이콘이다(tmp_path):
    # ‹ › 글자는 글꼴 안에서 소문자 높이쯤에 그려져 박스 가운데보다 아래로
    # 처진다. 도형은 박스 정중앙에 놓인다.
    render_site(_manifest(3), CONFIG, tmp_path, TEMPLATES)
    middle = (tmp_path / "works" / "작업2" / "index.html").read_text(encoding="utf-8")

    assert "‹</a>" not in middle and "›</a>" not in middle
    assert middle.count('<svg class="post-arrow-icon"') == 2
    assert 'aria-hidden="true"' in middle
