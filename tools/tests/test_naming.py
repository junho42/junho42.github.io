from naming import strip_order_prefix, natural_key, dedupe_slug


def test_밑줄_접두사를_떼고_숫자를_돌려준다():
    assert strip_order_prefix("01_화보") == (1, "화보")


def test_점과_하이픈_접두사도_인식한다():
    assert strip_order_prefix("10.뮤직비디오") == (10, "뮤직비디오")
    assert strip_order_prefix("2-단편영화") == (2, "단편영화")


def test_접두사가_없으면_이름을_그대로_돌려준다():
    assert strip_order_prefix("TAEMIN-Guilty") == (None, "TAEMIN-Guilty")


def test_구분자_없는_숫자로_시작하는_이름은_접두사가_아니다():
    # "2026웨딩스냅"의 2026은 제목의 일부다
    assert strip_order_prefix("2026웨딩스냅") == (None, "2026웨딩스냅")


def test_접두사_뒤_공백을_제거한다():
    assert strip_order_prefix("03_ 화보 ") == (3, "화보")


def test_접두사를_떼면_점두개만_남으면_원래_이름으로_돌아간다():
    # ".."가 슬러그가 되면 렌더러가 works/../.../index.html을 써서
    # 트리 밖으로 나간다. 원래 폴더 이름 그대로를 제목으로 되돌려야 한다.
    assert strip_order_prefix("1_..") == (None, "1_..")


def test_접두사를_떼면_빈_문자열만_남으면_원래_이름으로_돌아간다():
    # "1_ "에서 숫자·구분자·공백을 떼면 제목이 빈 문자열이 되어
    # works/<카테고리>// 같은 깨진 경로가 된다.
    assert strip_order_prefix("1_ ") == (None, "1_ ")


def test_자연_정렬은_숫자를_수로_비교한다():
    names = ["10.jpg", "2.jpg", "1.jpg"]
    assert sorted(names, key=natural_key) == ["1.jpg", "2.jpg", "10.jpg"]


def test_자연_정렬은_영문_대소문자를_구분하지_않는다():
    assert sorted(["b.jpg", "A.jpg"], key=natural_key) == ["A.jpg", "b.jpg"]


def test_자연_정렬은_숫자와_문자가_섞여도_예외를_내지_않는다():
    names = ["cover.jpg", "2.jpg", "img10.jpg", "img2.jpg"]
    assert sorted(names, key=natural_key) == ["2.jpg", "cover.jpg", "img2.jpg", "img10.jpg"]


def test_슬러그가_비어있으면_그대로_통과한다():
    assert dedupe_slug("화보", set()) == "화보"


def test_슬러그가_충돌하면_번호를_붙인다():
    assert dedupe_slug("화보", {"화보"}) == "화보-2"
    assert dedupe_slug("화보", {"화보", "화보-2"}) == "화보-3"
