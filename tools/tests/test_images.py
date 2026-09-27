import io

import pytest
from PIL import Image

from images import (
    COVER_WIDTH,
    fetch_youtube_cover,
    image_size,
    make_cover,
    make_gallery,
    needs_rebuild,
)


def _write_image(path, size, color=(120, 90, 60)):
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", size, color).save(path)
    return path


def test_커버는_자르지_않고_원본_비율을_지킨다(tmp_path):
    # 목록 그리드가 열 폭만 맞추고 높이는 작업물마다 다르게 두므로,
    # 커버를 한 비율로 잘라내면 작가가 잡은 구도가 사라진다.
    source = _write_image(tmp_path / "src.jpg", (2000, 2000))
    dest = tmp_path / "out" / "cover-600.webp"

    size = make_cover(source, dest)

    assert size == (600, 600)
    with Image.open(dest) as image:
        assert image.size == (600, 600)
        assert image.format == "WEBP"


def test_커버는_세로_사진도_세로로_남긴다(tmp_path):
    source = _write_image(tmp_path / "tall.jpg", (1200, 1800))
    dest = tmp_path / "out" / "cover-600.webp"

    assert make_cover(source, dest) == (600, 900)


def test_커버는_원본보다_크게_늘리지_않는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (320, 320))
    dest = tmp_path / "out" / "cover-600.webp"

    size = make_cover(source, dest)

    assert size[0] == 320


def test_갤러리는_비율을_유지한다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (3000, 2000))
    dest = tmp_path / "out" / "01-1600.webp"

    size = make_gallery(source, dest)

    assert size == (1600, 1067)


def test_갤러리도_원본보다_크게_늘리지_않는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (800, 600))
    dest = tmp_path / "out" / "01-1600.webp"

    assert make_gallery(source, dest) == (800, 600)


def test_깨진_이미지는_예외를_던진다(tmp_path):
    broken = tmp_path / "broken.jpg"
    broken.write_bytes(b"not an image")

    with pytest.raises(OSError):
        make_gallery(broken, tmp_path / "out.webp")


def test_산출물이_없으면_다시_만들어야_한다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (100, 100))
    assert needs_rebuild(source, tmp_path / "없음.webp") is True


def test_이미_만든_산출물의_크기를_읽는다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (2400, 1600))
    dest = tmp_path / "out" / "cover-600.webp"
    make_cover(source, dest)

    assert image_size(dest) == (600, 400)


def test_산출물이_원본보다_새것이면_건너뛴다(tmp_path):
    source = _write_image(tmp_path / "src.jpg", (100, 100))
    dest = tmp_path / "out.webp"
    make_gallery(source, dest)
    import os

    os.utime(dest, (source.stat().st_mtime + 10, source.stat().st_mtime + 10))

    assert needs_rebuild(source, dest) is False


def test_유튜브_썸네일을_받아_저장한다(tmp_path):
    buffer = io.BytesIO()
    Image.new("RGB", (1280, 720), (10, 10, 10)).save(buffer, format="JPEG")
    payload = buffer.getvalue()

    def fake_opener(url, timeout=0):
        assert "dQw4w9WgXcQ" in url

        class Response:
            def read(self):
                return payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Response()

    dest = tmp_path / "out" / "cover-600.webp"
    assert fetch_youtube_cover("dQw4w9WgXcQ", dest, opener=fake_opener) is True
    with Image.open(dest) as image:
        assert image.size == (COVER_WIDTH, 338)


def test_유튜브_썸네일_저장이_실패해도_예외없이_False(tmp_path, monkeypatch):
    # 다운로드는 성공했지만 저장(디스크 부족, 권한 등)이 실패하는 경우다.
    # _save가 try 밖에 있으면 여기서 OSError가 그대로 새어나가
    # manifest.py까지 감싸지 않은 예외로 번진다.
    buffer = io.BytesIO()
    Image.new("RGB", (1280, 720), (10, 10, 10)).save(buffer, format="JPEG")
    payload = buffer.getvalue()

    def fake_opener(url, timeout=0):
        class Response:
            def read(self):
                return payload

            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

        return Response()

    def failing_save(image, dest):
        raise OSError("disk full")

    monkeypatch.setattr("images._save", failing_save)

    dest = tmp_path / "out" / "cover-600.webp"
    assert fetch_youtube_cover("dQw4w9WgXcQ", dest, opener=fake_opener) is False


def test_유튜브_썸네일을_못_받으면_False(tmp_path):
    def failing_opener(url, timeout=0):
        raise OSError("404")

    dest = tmp_path / "out" / "cover-600.webp"
    assert fetch_youtube_cover("dQw4w9WgXcQ", dest, opener=failing_opener) is False
    assert not dest.exists()
