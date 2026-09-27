from textfile import read_text, body_to_html


def test_UTF8_한글을_읽는다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("utf-8"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_BOM이_붙은_UTF8도_읽는다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("utf-8-sig"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_CP949_한글을_읽는다(tmp_path):
    # 윈도우 메모장이 'ANSI'로 저장하면 이 인코딩이 된다
    path = tmp_path / "memo.txt"
    path.write_bytes("색보정 메모".encode("cp949"))
    text, warning = read_text(path)
    assert text == "색보정 메모"
    assert warning is None


def test_BOM과_판별불가_바이트가_섞이면_BOM이_본문에_남지_않는다(tmp_path):
    # utf-8-sig도 cp949도 실패하면 마지막 수단이 "utf-8"이 아니라
    # "utf-8-sig"여야 한다. "utf-8"로 복구하면 BOM 세 바이트가
    # 리터럴 U+FEFF로 본문에 남는다.
    path = tmp_path / "memo.txt"
    path.write_bytes(b"\xef\xbb\xbf\xffbroken")
    text, warning = read_text(path)
    assert warning is not None
    assert "﻿" not in text


def test_판별_불가_바이트는_경고와_함께_복구한다(tmp_path):
    path = tmp_path / "memo.txt"
    path.write_bytes(b"\xff\xfe\x00broken")
    text, warning = read_text(path)
    assert warning is not None
    assert "memo.txt" in warning
    assert text  # 빈 문자열이 아니어야 한다


def test_빈_줄이_단락을_나눈다():
    html = body_to_html("첫 단락\n\n두 번째 단락")
    assert html == "<p>첫 단락</p>\n<p>두 번째 단락</p>"


def test_단일_줄바꿈은_br이_된다():
    assert body_to_html("한 줄\n다음 줄") == "<p>한 줄<br>\n다음 줄</p>"


def test_HTML을_이스케이프한다():
    html = body_to_html('<script>alert("x")</script>')
    assert "<script>" not in html
    assert "&lt;script&gt;" in html


def test_CRLF를_정규화한다():
    assert body_to_html("첫 단락\r\n\r\n두 번째") == "<p>첫 단락</p>\n<p>두 번째</p>"


def test_빈_본문은_빈_문자열():
    assert body_to_html("   \n\n  ") == ""
