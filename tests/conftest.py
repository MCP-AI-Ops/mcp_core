# tests/conftest.py

"""
pytest 설정 및 공통 fixture.
"""

import sys
from pathlib import Path

# 프로젝트 루트를 PYTHONPATH에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

