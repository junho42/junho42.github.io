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
