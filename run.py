#!/usr/bin/env python3
"""python run.py → 刷新自动数据(可断网,自动降级缓存) + 读人工CSV → 生成 dashboard.html"""
import os, sys, yaml
sys.path.insert(0, os.path.dirname(__file__))
from monitor import collectors as co, signals as sg, history as hs
from monitor.report import render

BASE = os.path.dirname(os.path.abspath(__file__))
cfg = yaml.safe_load(open(os.path.join(BASE, "config.yaml")))

# ---- 采集 ----
capex = co.fetch_capex_ocf(cfg["credit_panel"]["tickers_hyperscaler"])
token = co.fetch_token_prices(cfg["threshold_panel"]["frontier_models"])
gpu = co.load_gpu_spot(os.path.join(BASE, cfg["copper_panel"]["gpu_spot_hook"]["csv_path"]))

mem = co.latest(co.load_manual("memory_cycle.csv"))
cred = co.latest(co.load_manual("credit_metrics.csv"))
org = co.latest(co.load_manual("org_metrics.csv"))
sci = co.latest(co.load_manual("scissors_inputs.csv"))
ev_rows = co.load_manual("events.csv")
flags = co.active_flags(ev_rows)

# ---- 信号 ----
copper = sg.copper_phase(mem, flags, cfg["copper_panel"])
credit = sg.credit_level(cred, flags, capex.get("data", {}), cfg["credit_panel"])
sciss = sg.scissors(
    {k: sci.get(k) for k in cfg["scissors"]["infra_weights"]},
    {k: sci.get(k) for k in cfg["scissors"]["load_weights"]},
    cfg["scissors"], credit["level_idx"], copper["phase"])
thr = sg.threshold_breaches(token.get("data", {}), cfg["threshold_panel"])

state = {
    "copper": copper, "credit": credit, "scissors": sciss, "thresholds": thr,
    "org": {"industrial_token_share": sg._f(org, "industrial_token_share"),
            "rev_per_employee_ratio": sg._f(org, "rev_per_employee_ratio"),
            "middle_mgmt_layoff_share": sg._f(org, "middle_mgmt_layoff_share")},
    "events": [e for e in ev_rows if str(e.get("active", "")).strip() in ("1", "true", "True")],
    "meta": {"token": token.get("data", {}), "gpu_spot": gpu,
             "data_asof": mem.get("date", "—")},
}

# ---- 历史记录:每日一行,同日重跑覆盖 ----
import datetime as _dt
hist_rows = hs.append_daily(BASE, {
    "date": _dt.date.today().isoformat(),
    "frontier_usd_mtok": token.get("data", {}).get("frontier_usd_mtok", ""),
    "floor_usd_mtok": token.get("data", {}).get("floor_usd_mtok", ""),
    "gpu_usd_per_hour": gpu.get("usd_per_hour", ""),
    "gap": sciss.get("gap", ""),
    "industrial_token_share": state["org"].get("industrial_token_share", ""),
    "copper_phase": copper["phase"], "credit_idx": credit["level_idx"], "note": ""})
state["meta"]["history"] = {
    "frontier": hs.series(hist_rows, "frontier_usd_mtok"),
    "floor": hs.series(hist_rows, "floor_usd_mtok"),
    "gpu": hs.series(hist_rows, "gpu_usd_per_hour"),
    "gap": hs.series(hist_rows, "gap"),
    "load": hs.series(hist_rows, "industrial_token_share")}
state["meta"]["hist_n"] = len(hist_rows)
state["meta"]["hist_last"] = hist_rows[-1]["date"] if hist_rows else "—"

out = os.path.join(BASE, "dashboard.html")
open(out, "w").write(render(state))
print(f"copper={copper['phase_label']}  credit={credit['level']}  "
      f"gap={sciss['gap']}  whistle={sciss['halftime_whistle']}\n→ {out}")
