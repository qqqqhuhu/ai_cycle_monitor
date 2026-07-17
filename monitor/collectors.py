"""数据采集层：能自动的自动，不能自动的留人工CSV接口，断网时全部优雅降级到缓存。"""
from __future__ import annotations
import csv, json, os, datetime as dt

DATA = os.path.join(os.path.dirname(__file__), "..", "data")
AUTO = os.path.join(DATA, "auto")
MANUAL = os.path.join(DATA, "manual")


def _cache_path(name: str) -> str:
    return os.path.join(AUTO, name)


def _save_cache(name: str, obj) -> None:
    os.makedirs(AUTO, exist_ok=True)
    with open(_cache_path(name), "w") as f:
        json.dump({"asof": dt.date.today().isoformat(), "data": obj}, f, ensure_ascii=False, indent=1)


def _load_cache(name: str):
    try:
        with open(_cache_path(name)) as f:
            return json.load(f)
    except Exception:
        return None


# ---------------- 自动采集 ----------------

def fetch_capex_ocf(tickers: list[str]) -> dict:
    """capex / 经营现金流 (TTM近似)。yfinance可用则刷新，否则用缓存。"""
    try:
        import yfinance as yf
        out = {}
        for t in tickers:
            cf = yf.Ticker(t).cashflow
            capex = abs(float(cf.loc["Capital Expenditure"].iloc[0]))
            ocf = float(cf.loc["Operating Cash Flow"].iloc[0])
            out[t] = {"capex": capex, "ocf": ocf, "ratio": round(capex / ocf, 2)}
        _save_cache("capex_ocf.json", out)
        return {"asof": dt.date.today().isoformat(), "data": out}
    except Exception:
        return _load_cache("capex_ocf.json") or {"asof": None, "data": {}}


def fetch_token_prices(frontier_prefixes: list[str]) -> dict:
    """OpenRouter公开模型定价 → 旗舰均价与最低可用价 (USD / 百万token, 混合in+out按1:3)。"""
    try:
        import requests
        r = requests.get("https://openrouter.ai/api/v1/models", timeout=15)
        rows = r.json().get("data", [])
        frontier, floor = [], []
        for m in rows:
            p = m.get("pricing", {})
            try:
                mix = (float(p["prompt"]) + 3 * float(p["completion"])) / 4 * 1_000_000
            except Exception:
                continue
            if mix <= 0:
                continue
            floor.append(mix)
            if any(m.get("id", "").startswith(px) for px in frontier_prefixes):
                frontier.append(mix)
        out = {
            "frontier_usd_mtok": round(sum(frontier) / len(frontier), 3) if frontier else None,
            "floor_usd_mtok": round(sorted(floor)[max(0, len(floor)//20)], 4) if floor else None,  # P5价作"可用底价"
        }
        _save_cache("token_prices.json", out)
        return {"asof": dt.date.today().isoformat(), "data": out}
    except Exception:
        return _load_cache("token_prices.json") or {"asof": None, "data": {}}


def load_gpu_spot(csv_path: str) -> dict:
    """钩子：读取 gpu_monitor 导出的现货价CSV，取最近两期算环比。"""
    try:
        with open(csv_path) as f:
            rows = list(csv.DictReader(f))
        if not rows:
            return {}
        latest = rows[-1]
        prev = rows[-2] if len(rows) > 1 else rows[-1]
        chg = (float(latest["usd_per_hour"]) / float(prev["usd_per_hour"]) - 1) * 100
        return {"asof": latest["date"], "usd_per_hour": float(latest["usd_per_hour"]),
                "chg_pct": round(chg, 1), "gpu_model": latest.get("gpu_model", "")}
    except Exception:
        return {}


# ---------------- 人工数据接口 ----------------

def load_manual(name: str) -> list[dict]:
    """通用CSV加载。文件不存在返回空列表。"""
    path = os.path.join(MANUAL, name)
    try:
        with open(path) as f:
            return list(csv.DictReader(f))
    except Exception:
        return []


def latest(rows: list[dict]) -> dict:
    """按date列取最新一行。"""
    if not rows:
        return {}
    return sorted(rows, key=lambda r: r.get("date", ""))[-1]


def active_flags(rows: list[dict]) -> dict:
    """events.csv → {flag_name: {'date':..., 'note':...}} 仅收 active=1 的事件。"""
    out = {}
    for r in rows:
        if str(r.get("active", "")).strip() in ("1", "true", "True"):
            out[r["flag"]] = {"date": r.get("date", ""), "note": r.get("note", "")}
    return out
