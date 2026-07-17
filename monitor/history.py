"""历史序列：每次运行把自动数据+信号状态记一行,同日重跑则覆盖。图表和'更新没'都靠它。"""
from __future__ import annotations
import csv, os, datetime as dt

COLS = ["date", "frontier_usd_mtok", "floor_usd_mtok", "gpu_usd_per_hour",
        "gap", "industrial_token_share", "copper_phase", "credit_idx", "note"]


def _path(base: str) -> str:
    return os.path.join(base, "data", "history", "daily.csv")


def load(base: str) -> list[dict]:
    try:
        with open(_path(base)) as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def append_daily(base: str, row: dict) -> list[dict]:
    """追加/覆盖今日行,返回完整历史。"""
    rows = [r for r in load(base) if r.get("date") != row["date"]]
    rows.append({c: row.get(c, "") for c in COLS})
    rows.sort(key=lambda r: r["date"])
    os.makedirs(os.path.dirname(_path(base)), exist_ok=True)
    with open(_path(base), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS)
        w.writeheader()
        w.writerows(rows)
    return rows


def series(rows: list[dict], col: str) -> list[tuple[str, float]]:
    out = []
    for r in rows:
        try:
            out.append((r["date"], float(r[col])))
        except Exception:
            continue
    return out
