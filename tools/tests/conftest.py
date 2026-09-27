"""테스트가 tools/ 모듈을 import할 수 있게 경로를 넣는다."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
