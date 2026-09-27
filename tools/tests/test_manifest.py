import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from PIL import Image

from manifest import build_manifest, sort_works, write_manifest
from scanner import Category, Work

NOW = datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc)


def _work(title, order=None, days_ago=0):
    return Work(
        title=title,
        slug=title,
        order=order,
        directory=Path("/tmp") / title,
        date=NOW - timedelta(days=days_ago),
    )


def test_접두사가_있는_게시물이_먼저_온다():
    works = [_work("최신", days_ago=0), _work("고정", order=1, days_ago=100)]
    assert [w.title for w in sort_works(works)] == ["고정", "최신"]


def test_접두사끼리는_숫자_오름차순():
    works = [_work("둘째", order=2), _work("첫째", order=1)]
    assert [w.title for w in sort_works(works)] == ["첫째", "둘째"]


def test_접두사가_없으면_최신순():
    works = [_work("옛것", days_ago=30), _work("새것", days_ago=1)]
    assert [w.title for w in sort_works(works)] == ["새것", "옛것"]


def _fixture_category(tmp_path):
    work_dir = tmp_path / "upload" / "화보" / "작업"
    work_dir.mkdir(parents=True)
    Image.new("RGB", (2400, 1600), (90, 90, 90)).save(work_dir / "cover.jpg")
    Image.new("RGB", (2400, 1600), (40, 40, 40)).save(work_dir / "01.jpg")
    work = Work(
        title="작업",
        slug="작업",
        order=None,
        directory=work_dir,
        images=[work_dir / "01.jpg"],
        cover=work_dir / "cover.jpg",
        video={"kind": "youtube", "id": "abcdef", "embed": "https://e/abcdef", "url": "https://youtu.be/abcdef"},
        body="<p>본문</p>",
        date=NOW,
    )
    return Category(title="화보", slug="화보", order=1, directory=work_dir.parent, works=[work])


def test_manifest에_카테고리와_게시물이_담긴다(tmp_path):
    category = _fixture_category(tmp_path)

    manifest, warnings = build_manifest([category], tmp_path / "media", NOW)

    assert manifest["generatedAt"] == NOW.isoformat()
    assert len(manifest["categories"]) == 1
    entry = manifest["categories"][0]["works"][0]
    assert entry["title"] == "작업"
    assert entry["url"] == "works/화보/작업/"
    assert entry["video"]["kind"] == "youtube"
    assert entry["body"] == "<p>본문</p>"
    assert warnings == []


def test_커버와_갤러리_이미지가_실제로_생성된다(tmp_path):
    category = _fixture_category(tmp_path)
    media_root = tmp_path / "media"

    manifest, _ = build_manifest([category], media_root, NOW)
    entry = manifest["categories"][0]["works"][0]

    cover_path = tmp_path / entry["cover"]["src"]
    assert cover_path.exists()
    # 원본 2400x1600의 비율을 지킨 채 가로만 600으로 줄인다 — 잘라내지 않는다
    assert (entry["cover"]["w"], entry["cover"]["h"]) == (600, 400)

    gallery_path = tmp_path / entry["images"][0]["src"]
    assert gallery_path.exists()
    assert entry["images"][0]["w"] == 1600


def test_이미지가_깨져도_빌드가_계속된다(tmp_path):
    category = _fixture_category(tmp_path)
    broken = category.works[0].directory / "broken.jpg"
    broken.write_bytes(b"not an image")
    category.works[0].images.append(broken)

    manifest, warnings = build_manifest([category], tmp_path / "media", NOW)

    assert len(manifest["categories"][0]["works"][0]["images"]) == 1
    assert any("broken.jpg" in w for w in warnings)


def test_manifest를_UTF8_JSON으로_쓴다(tmp_path):
    category = _fixture_category(tmp_path)
    manifest, _ = build_manifest([category], tmp_path / "media", NOW)
    out = tmp_path / "works.json"

    write_manifest(manifest, out)

    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["categories"][0]["title"] == "화보"
    # 한글이 \uXXXX로 이스케이프되지 않아야 한다
    assert "화보" in out.read_text(encoding="utf-8")


def test_이미_받은_유튜브_커버는_다시_받지_않고_실제_크기를_읽는다(tmp_path, monkeypatch):
    # 커버가 이미 디스크에 있는데도 무조건 다시 받으면, i.ytimg.com이 잠깐
    # 응답하지 않는 순간 멀쩡한 커버가 목록에서 사라진다. 파일이 있으면
    # 네트워크를 아예 타지 않아야 하고, 크기는 실제 저장된 파일에서 읽어야
    # 한다 — 여기서는 유튜브 썸네일의 16:9(600x338)가 아닌 600x400으로
    # 만들어, 어딘가에서 비율을 가정해 계산하면 드러나게 한다.
    category = _fixture_category(tmp_path)
    work = category.works[0]
    work.cover = None  # 로컬 이미지가 없어야 유튜브 분기를 탄다

    media_root = tmp_path / "media"
    cover_dest = media_root / category.slug / work.slug / "cover-600.webp"
    cover_dest.parent.mkdir(parents=True)
    Image.new("RGB", (600, 400), (10, 20, 30)).save(cover_dest, "WEBP")

    called = []

    def fake_fetch(video_id, dest, opener=None):
        called.append(video_id)
        return False  # 네트워크가 끊겼다고 가정해도 이미 있는 파일은 건드리지 않아야 한다

    monkeypatch.setattr("manifest.fetch_youtube_cover", fake_fetch)

    manifest, warnings = build_manifest([category], media_root, NOW)
    entry = manifest["categories"][0]["works"][0]

    assert called == []
    assert entry["cover"] == {
        "src": "media/화보/작업/cover-600.webp",
        "w": 600,
        "h": 400,
    }
    assert warnings == []


def test_로컬_영상_파일이_media로_복사된다(tmp_path):
    category = _fixture_category(tmp_path)
    work = category.works[0]
    work.video = {"kind": "file", "id": None, "embed": None, "url": "reel.mp4"}
    (work.directory / "reel.mp4").write_bytes(b"fake video bytes")

    manifest, warnings = build_manifest([category], tmp_path / "media", NOW)
    entry = manifest["categories"][0]["works"][0]

    video_path = tmp_path / entry["video"]["url"]
    assert video_path.exists()
    assert entry["video"]["url"] == "media/화보/작업/reel.mp4"
    assert warnings == []
