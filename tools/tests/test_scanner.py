import pytest

from scanner import scan


def _make(root, relative, content=b"x"):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)
    return path


def _broken_symlink(path):
    """path 위치에 존재하지 않는 대상을 가리키는 심볼릭 링크를 만든다.

    is_dir()/is_file()가 조용히 False를 돌려주는 실제 OSError 트리거다.
    심볼릭 링크 생성 권한이 없는 환경(예: 개발자 모드가 꺼진 Windows CI)에서는
    스킵한다 — 목만들어 통과시키는 대신 실제로 검증 가능한 곳에서만 검증한다.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    try:
        path.symlink_to(path.parent / "존재하지-않는-대상")
    except OSError as exc:
        pytest.skip(f"이 환경에서는 심볼릭 링크를 만들 수 없습니다: {exc}")


def test_카테고리와_게시물을_2단으로_읽는다(tmp_path):
    _make(tmp_path, "01_화보/2026웨딩스냅/01.jpg")
    _make(tmp_path, "01_화보/2026웨딩스냅/02.jpg")

    categories, warnings = scan(tmp_path)

    assert [c.title for c in categories] == ["화보"]
    assert categories[0].order == 1
    assert [w.title for w in categories[0].works] == ["2026웨딩스냅"]
    assert len(categories[0].works[0].images) == 2
    assert warnings == []


def test_이미지는_자연_정렬된다(tmp_path):
    _make(tmp_path, "화보/작업/10.jpg")
    _make(tmp_path, "화보/작업/2.jpg")

    categories, _ = scan(tmp_path)

    names = [p.name for p in categories[0].works[0].images]
    assert names == ["2.jpg", "10.jpg"]


def test_cover_파일이_있으면_커버로_쓴다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _make(tmp_path, "화보/작업/cover.jpg")

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.cover.name == "cover.jpg"
    # 커버는 갤러리에서 빠진다
    assert [p.name for p in work.images] == ["01.jpg"]


def test_cover가_없으면_첫_이미지가_커버다(tmp_path):
    _make(tmp_path, "화보/작업/02.jpg")
    _make(tmp_path, "화보/작업/01.jpg")

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.cover.name == "01.jpg"
    # 커버로 쓰였어도 갤러리에는 남는다
    assert [p.name for p in work.images] == ["01.jpg", "02.jpg"]


def test_link_txt는_영상이_되고_본문에서_빠진다(tmp_path):
    _make(tmp_path, "뮤비/작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")
    _make(tmp_path, "뮤비/작업/memo.txt", "본문입니다".encode("utf-8"))

    categories, _ = scan(tmp_path)
    work = categories[0].works[0]

    assert work.video["kind"] == "youtube"
    assert "본문입니다" in work.body
    assert "youtu.be" not in work.body


def test_mp4가_있으면_파일_영상으로_인식한다(tmp_path):
    _make(tmp_path, "뮤비/작업/reel.mp4")

    categories, _ = scan(tmp_path)

    assert categories[0].works[0].video["kind"] == "file"


def test_link_txt가_mp4보다_우선한다(tmp_path):
    _make(tmp_path, "뮤비/작업/reel.mp4")
    _make(tmp_path, "뮤비/작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")

    categories, _ = scan(tmp_path)

    assert categories[0].works[0].video["kind"] == "youtube"


def test_비어있는_게시물_폴더는_건너뛰고_경고한다(tmp_path):
    (tmp_path / "화보" / "빈작업").mkdir(parents=True)
    _make(tmp_path, "화보/정상작업/01.jpg")

    categories, warnings = scan(tmp_path)

    assert [w.title for w in categories[0].works] == ["정상작업"]
    assert any("빈작업" in w for w in warnings)


def test_카테고리_없이_업로드_루트에_놓인_파일은_경고한다(tmp_path):
    _make(tmp_path, "떠도는사진.jpg")

    categories, warnings = scan(tmp_path)

    assert categories == []
    assert any("떠도는사진.jpg" in w for w in warnings)


def test_점과_밑줄로_시작하는_항목은_무시한다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _make(tmp_path, "화보/작업/.DS_Store")
    _make(tmp_path, "화보/작업/_임시메모.txt", "무시".encode("utf-8"))
    _make(tmp_path, "_숨긴카테고리/작업/01.jpg")

    categories, _ = scan(tmp_path)

    assert [c.title for c in categories] == ["화보"]
    assert [p.name for p in categories[0].works[0].images] == ["01.jpg"]
    assert categories[0].works[0].body == ""


def test_같은_카테고리_안에서_슬러그가_충돌하면_번호를_붙인다(tmp_path):
    _make(tmp_path, "화보/01_작업/01.jpg")
    _make(tmp_path, "화보/02_작업/01.jpg")

    categories, warnings = scan(tmp_path)

    slugs = [w.slug for w in categories[0].works]
    assert slugs == ["작업", "작업-2"]
    assert any("작업" in w for w in warnings)


def test_카테고리_슬러그가_충돌하면_번호를_붙인다(tmp_path):
    # "05_광고"와 "광고"는 접두사를 떼면 둘 다 제목이 "광고"라, 다른 카테고리인데도
    # 같은 works/media/광고/... 경로를 가리켜 한쪽 게시물이 조용히 가려진다.
    _make(tmp_path, "05_광고/작업/01.jpg")
    _make(tmp_path, "광고/작업/01.jpg")

    categories, warnings = scan(tmp_path)

    slugs = [c.slug for c in categories]
    assert slugs == ["광고", "광고-2"]
    assert len(set(slugs)) == len(slugs)
    assert any("카테고리" in w and "광고" in w for w in warnings)


def test_업로드_폴더가_없으면_빈_결과와_경고(tmp_path):
    categories, warnings = scan(tmp_path / "없음")

    assert categories == []
    assert len(warnings) == 1


def test_카테고리는_접두사_순서로_정렬된다(tmp_path):
    _make(tmp_path, "02_뮤비/작업/01.jpg")
    _make(tmp_path, "01_화보/작업/01.jpg")
    _make(tmp_path, "잡다한것/작업/01.jpg")

    categories, _ = scan(tmp_path)

    # 접두사가 있는 것이 먼저, 그 뒤는 이름 순
    assert [c.title for c in categories] == ["화보", "뮤비", "잡다한것"]


def test_카테고리_위치의_깨진_심볼릭_링크는_경고로_건너뛴다(tmp_path):
    # 깨진 심볼릭 링크는 is_dir()/is_file() 모두 False라서 카테고리 폴더로
    # 오인해 내려가다가 iterdir()가 실제 OSError를 던지는 실제 상황이다.
    _make(tmp_path, "화보/작업/01.jpg")
    _broken_symlink(tmp_path / "깨진링크")

    categories, warnings = scan(tmp_path)

    assert [c.title for c in categories] == ["화보"]
    assert any("깨진링크" in w for w in warnings)


def test_link_txt가_깨진_심볼릭_링크면_경고하고_영상없이_진행한다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _broken_symlink(tmp_path / "화보" / "작업" / "link.txt")

    categories, warnings = scan(tmp_path)
    work = categories[0].works[0]

    assert work.video is None
    assert any("link.txt" in w for w in warnings)


def test_본문_txt가_깨진_심볼릭_링크면_경고하고_건너뛴다(tmp_path):
    _make(tmp_path, "화보/작업/01.jpg")
    _broken_symlink(tmp_path / "화보" / "작업" / "memo.txt")

    categories, warnings = scan(tmp_path)
    work = categories[0].works[0]

    assert work.body == ""
    assert any("memo.txt" in w for w in warnings)
