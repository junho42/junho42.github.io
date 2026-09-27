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


def test_업로드_바로_아래_폴더_하나가_게시물이다(tmp_path):
    # 카테고리 단계는 없다. 폴더 한 겹이 게시물 하나다.
    _make(tmp_path, "2026웨딩스냅/01.jpg")
    _make(tmp_path, "2026웨딩스냅/02.jpg")

    works, warnings = scan(tmp_path)

    assert [w.title for w in works] == ["2026웨딩스냅"]
    assert len(works[0].images) == 2
    assert warnings == []


def test_숫자_접두사는_순서용이고_제목에서_빠진다(tmp_path):
    _make(tmp_path, "01_대표작/01.jpg")

    works, _ = scan(tmp_path)

    assert works[0].title == "대표작"
    assert works[0].order == 1


def test_이미지는_자연_정렬된다(tmp_path):
    _make(tmp_path, "작업/10.jpg")
    _make(tmp_path, "작업/2.jpg")

    works, _ = scan(tmp_path)

    assert [p.name for p in works[0].images] == ["2.jpg", "10.jpg"]


def test_cover_파일이_있으면_커버로_쓴다(tmp_path):
    _make(tmp_path, "작업/01.jpg")
    _make(tmp_path, "작업/cover.jpg")

    works, _ = scan(tmp_path)

    assert works[0].cover.name == "cover.jpg"
    # 커버는 갤러리에서 빠진다
    assert [p.name for p in works[0].images] == ["01.jpg"]


def test_cover가_없으면_첫_이미지가_커버다(tmp_path):
    _make(tmp_path, "작업/02.jpg")
    _make(tmp_path, "작업/01.jpg")

    works, _ = scan(tmp_path)

    assert works[0].cover.name == "01.jpg"
    # 커버로 쓰였어도 갤러리에는 남는다
    assert [p.name for p in works[0].images] == ["01.jpg", "02.jpg"]


def test_link_txt는_영상이_되고_본문에서_빠진다(tmp_path):
    _make(tmp_path, "작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")
    _make(tmp_path, "작업/memo.txt", "본문입니다".encode("utf-8"))

    works, _ = scan(tmp_path)

    assert works[0].video["kind"] == "youtube"
    assert "본문입니다" in works[0].body
    assert "youtu.be" not in works[0].body


def test_mp4가_있으면_파일_영상으로_인식한다(tmp_path):
    _make(tmp_path, "작업/reel.mp4")

    works, _ = scan(tmp_path)

    assert works[0].video["kind"] == "file"


def test_link_txt가_mp4보다_우선한다(tmp_path):
    _make(tmp_path, "작업/reel.mp4")
    _make(tmp_path, "작업/link.txt", b"https://youtu.be/dQw4w9WgXcQ")

    works, _ = scan(tmp_path)

    assert works[0].video["kind"] == "youtube"


def test_비어있는_폴더는_건너뛰고_경고한다(tmp_path):
    (tmp_path / "빈작업").mkdir(parents=True)
    _make(tmp_path, "정상작업/01.jpg")

    works, warnings = scan(tmp_path)

    assert [w.title for w in works] == ["정상작업"]
    assert any("빈작업" in w for w in warnings)


def test_업로드_루트에_낱개로_놓인_파일은_경고한다(tmp_path):
    # 폴더에 담지 않고 사진만 올린 경우다. 게시물이 되지 않는다.
    _make(tmp_path, "떠도는사진.jpg")

    works, warnings = scan(tmp_path)

    assert works == []
    assert any("떠도는사진.jpg" in w for w in warnings)


def test_점과_밑줄로_시작하는_항목은_무시한다(tmp_path):
    _make(tmp_path, "작업/01.jpg")
    _make(tmp_path, "작업/.DS_Store")
    _make(tmp_path, "작업/_임시메모.txt", "무시".encode("utf-8"))
    _make(tmp_path, "_숨긴작업/01.jpg")

    works, _ = scan(tmp_path)

    assert [w.title for w in works] == ["작업"]
    assert [p.name for p in works[0].images] == ["01.jpg"]
    assert works[0].body == ""


def test_슬러그가_충돌하면_번호를_붙인다(tmp_path):
    # "05_광고"와 "광고"는 접두사를 떼면 둘 다 제목이 "광고"라, 다른 폴더인데도
    # 같은 works/media/광고/... 경로를 가리켜 한쪽이 조용히 가려진다.
    _make(tmp_path, "05_광고/01.jpg")
    _make(tmp_path, "광고/01.jpg")

    works, warnings = scan(tmp_path)

    slugs = [w.slug for w in works]
    assert slugs == ["광고", "광고-2"]
    assert len(set(slugs)) == len(slugs)
    assert any("광고" in w and "주소가 겹쳐" in w for w in warnings)


def test_게시물_안의_하위_폴더는_무시하고_경고한다(tmp_path):
    _make(tmp_path, "작업/01.jpg")
    _make(tmp_path, "작업/더하위/02.jpg")

    works, warnings = scan(tmp_path)

    assert [p.name for p in works[0].images] == ["01.jpg"]
    assert any("더하위" in w for w in warnings)


def test_업로드_폴더가_없으면_빈_결과와_경고(tmp_path):
    works, warnings = scan(tmp_path / "없음")

    assert works == []
    assert len(warnings) == 1


def test_게시물_위치의_깨진_심볼릭_링크는_경고로_건너뛴다(tmp_path):
    # 깨진 심볼릭 링크는 is_dir()/is_file() 모두 False라서 게시물 폴더로
    # 오인해 내려가다가 iterdir()가 실제 OSError를 던지는 실제 상황이다.
    _make(tmp_path, "작업/01.jpg")
    _broken_symlink(tmp_path / "깨진링크")

    works, warnings = scan(tmp_path)

    assert [w.title for w in works] == ["작업"]
    assert any("깨진링크" in w for w in warnings)


def test_link_txt가_깨진_심볼릭_링크면_경고하고_영상없이_진행한다(tmp_path):
    _make(tmp_path, "작업/01.jpg")
    _broken_symlink(tmp_path / "작업" / "link.txt")

    works, warnings = scan(tmp_path)

    assert works[0].video is None
    assert any("link.txt" in w for w in warnings)


def test_본문_txt가_깨진_심볼릭_링크면_경고하고_건너뛴다(tmp_path):
    _make(tmp_path, "작업/01.jpg")
    _broken_symlink(tmp_path / "작업" / "memo.txt")

    works, warnings = scan(tmp_path)

    assert works[0].body == ""
    assert any("memo.txt" in w for w in warnings)
