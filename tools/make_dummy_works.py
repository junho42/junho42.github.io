"""그리드 확인용 더미 작업물 생성기. 제품 코드가 아니다.

100개쯤의 게시물을 다양한 원본 비율로 만들어 목록 그리드가 실제로
어떻게 쌓이는지 눈으로 보기 위한 도구다. 지우는 방법은 --clean 참고.

  python portfolio/tools/make_dummy_works.py          # 생성
  python portfolio/tools/make_dummy_works.py --clean  # 생성한 것만 삭제
"""

from __future__ import annotations

import argparse
import colorsys
import shutil
from pathlib import Path

from PIL import Image, ImageDraw

UPLOAD = Path(__file__).resolve().parents[1] / "upload"
CATEGORY = "99_그리드확인"

# 세로 / 가로 / 정방형 / 파노라마 / 살짝 다른 것들이 섞이게 한다.
RATIOS = [
    (1200, 1800),   # 2:3 세로
    (1600, 2400),   # 2:3 세로 (큼)
    (1800, 1200),   # 3:2 가로
    (2400, 1350),   # 16:9 가로
    (1400, 1400),   # 1:1
    (2400, 1000),   # 12:5 파노라마
    (1000, 2000),   # 1:2 아주 긴 세로
    (2000, 1500),   # 4:3
    (1500, 2000),   # 3:4 세로
    (2600, 900),    # 아주 납작한 파노라마
]

TITLES = [
    "야간 인터뷰", "바닷가 스냅", "웨딩 본식", "브랜드 필름", "제품 컷",
    "무대 조명", "겨울 산", "도심 야경", "카페 화보", "반려동물",
    "뮤직비디오 컷", "다큐 인서트", "패션 룩북", "드론 항공", "실내 인테리어",
    "스튜디오 인물", "노을 풍경", "행사 기록", "요리 클로즈업", "새벽 거리",
]


def _swatch(width: int, height: int, seed: int) -> Image.Image:
    """보정된 사진처럼 보이게 그라데이션 + 밴드를 그린다."""
    hue = (seed * 0.137) % 1.0
    top = colorsys.hsv_to_rgb(hue, 0.42, 0.78)
    bottom = colorsys.hsv_to_rgb((hue + 0.08) % 1.0, 0.55, 0.22)
    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(round(255 * (top[i] + (bottom[i] - top[i]) * t)) for i in range(3)),
        )
    # 크기를 눈으로 구분할 수 있게 비율을 적어 넣는다
    draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 255, 255), width=4)
    draw.text((20, 20), f"{width}x{height}", fill=(255, 255, 255))
    return image


def generate(count: int = 100) -> None:
    root = UPLOAD / CATEGORY
    root.mkdir(parents=True, exist_ok=True)
    for index in range(1, count + 1):
        width, height = RATIOS[index % len(RATIOS)]
        title = f"{TITLES[index % len(TITLES)]} {index:03d}"
        folder = root / title
        folder.mkdir(exist_ok=True)
        _swatch(width, height, index).save(folder / "cover.jpg", quality=80)
        # 게시물 페이지도 볼 수 있게 갤러리 이미지를 한두 장 넣는다
        for shot in range(1, (index % 3) + 2):
            shot_w, shot_h = RATIOS[(index + shot) % len(RATIOS)]
            _swatch(shot_w, shot_h, index * 7 + shot).save(
                folder / f"{shot:02d}.jpg", quality=80
            )
        (folder / "memo.txt").write_text(
            f"{title} 더미 본문입니다.\n\n원본 {width}x{height}.", encoding="utf-8"
        )
    print(f"generated {count} works under upload/{CATEGORY}")


def clean() -> None:
    root = UPLOAD / CATEGORY
    if root.exists():
        shutil.rmtree(root)
        print(f"removed upload/{CATEGORY}")
    else:
        print("nothing to remove")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="그리드 확인용 더미 작업물")
    parser.add_argument("--clean", action="store_true", help="생성한 더미만 삭제")
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()
    clean() if args.clean else generate(args.count)
