"""스크립트 공통 헬퍼 — 출력 폴더 생성, 컨텍스트 JSON 저장."""
from __future__ import annotations

import json
import sys
from pathlib import Path

# 프로젝트 루트를 sys.path에 추가 (lib import용)
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

POSTS_DIR = ROOT / "posts"
DATA_CACHE_DIR = ROOT / "data"


def post_dir(slug: str) -> Path:
    """글 출력 폴더 생성·반환."""
    d = POSTS_DIR / slug
    d.mkdir(parents=True, exist_ok=True)
    return d


def write_context(out_dir: Path, context: dict, name: str = "context.json") -> Path:
    """LLM이 글 쓸 때 읽을 컨텍스트 JSON 저장."""
    path = out_dir / name
    path.write_text(
        json.dumps(context, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8",
    )
    return path


def cache_path(lawd_cd: str, deal_ymd: str) -> Path:
    """월별 자치구 데이터 캐시 경로."""
    DATA_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    return DATA_CACHE_DIR / f"{lawd_cd}-{deal_ymd}.csv"


def df_to_records(df) -> list[dict]:
    """DataFrame → JSON 직렬화 가능 records (datetime → ISO date)."""
    if df is None or df.empty:
        return []
    import pandas as pd

    df = df.copy()
    for col in df.columns:
        if pd.api.types.is_datetime64_any_dtype(df[col]):
            df[col] = df[col].dt.strftime("%Y-%m-%d")
    return df.reset_index(drop=True).to_dict(orient="records")
