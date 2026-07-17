"""信号层：把原始指标翻译成框架语言(周期阶段/泡沫颜色/剪刀差/半场哨)。"""
from __future__ import annotations

PHASES = {1: "① 启动", 2: "② 主升", 3: "③ 顶部信号", 4: "④ 崩塌", 5: "⑤ 出清", 0: "— 中性"}
CREDIT = ["green", "yellow", "orange", "red"]


def _f(row: dict, key: str, default=None):
    try:
        return float(row[key])
    except Exception:
        return default


# ---------------- 面板A：铜层周期状态机 ----------------

def copper_phase(mem: dict, flags: dict, cfg: dict) -> dict:
    ind = cfg["indicators"]
    inv = _f(mem, "inventory_weeks")
    mom = _f(mem, "price_mom_qoq_pct")
    cxs = _f(mem, "supplier_capex_sales_pct")
    wfr = _f(mem, "hbm_wafer_share_pct")
    sub = _f(mem, "substitution_penetration_pct")

    top_hits = []  # 顶部信号计票
    if cxs is not None and cxs >= ind["supplier_capex_sales_pct"]["top_signal_above"]:
        top_hits.append(f"capex/销售 {cxs:.0f}% 进入历史顶部区")
    if wfr is not None and wfr >= ind["hbm_wafer_share_pct"]["top_signal_above"]:
        top_hits.append(f"HBM晶圆份额 {wfr:.0f}% 逼近供给闸门")
    if sub is not None and sub >= ind["substitution_penetration_pct"]["top_signal_above"]:
        top_hits.append(f"替代技术渗透 {sub:.0f}% (铝替代铜定律)")
    for fl in ("per_wafer_profit_inversion", "hbm4_yield_breakthrough"):
        if fl in flags:
            top_hits.append({"per_wafer_profit_inversion": "单晶圆盈利倒挂(HBM<DDR5)",
                             "hbm4_yield_breakthrough": "HBM4良率突破,供给提前释放"}[fl])

    # 阶段判定(优先级从崩塌向下)
    if "supplier_capex_cut" in flags:
        phase = 5
    elif (inv is not None and inv >= ind["inventory_weeks"]["top_above"]) \
            or (mom is not None and mom <= ind["price_mom_qoq_pct"]["crash_below"]) \
            or "order_cancellation_wave" in flags:
        phase = 4
    elif len(top_hits) >= cfg["phase_rules"]["top_signals_needed"]:
        phase = 3
    elif inv is not None and inv < 6 and mom is not None and mom > ind["price_mom_qoq_pct"]["rally_above"]:
        phase = 2
    elif inv is not None and inv < ind["inventory_weeks"]["start_below"] and (mom or 0) > 0:
        phase = 1
    else:
        phase = 0

    return {"phase": phase, "phase_label": PHASES[phase], "top_hits": top_hits,
            "needed": cfg["phase_rules"]["top_signals_needed"],
            "metrics": {"库存周数": inv, "价格环比%": mom, "capex/销售%": cxs,
                        "HBM晶圆份额%": wfr, "替代渗透%": sub}}


# ---------------- 面板B：信用四色灯 ----------------

def credit_level(cred: dict, flags: dict, capex_ocf: dict, cfg: dict) -> dict:
    th = cfg["thresholds"]
    ir = _f(cred, "neocloud_interest_rev_pct")
    spread = _f(cred, "ai_infra_spread_bps")
    ratios = {t: v.get("ratio") for t, v in (capex_ocf or {}).items()}
    worst_ratio = max([r for r in ratios.values() if r is not None], default=None)

    reasons, level = [], 0
    if worst_ratio is not None and worst_ratio >= th["capex_ocf_yellow"]:
        level = max(level, 1); reasons.append(f"capex/OCF最高 {worst_ratio:.2f} → 依赖外部融资")
    if "vendor_financing_expansion" in flags:
        level = max(level, 1); reasons.append("供应商融资敞口继续扩大")
    if ir is not None and ir >= th["neocloud_interest_rev_orange"]:
        level = max(level, 2); reasons.append(f"Neocloud利息/收入 {ir:.1f}% (Insull杠杆区)")
    if "rated_debt_to_pensions" in flags:
        level = max(level, 2); reasons.append("评级后AI债分发进养老金/保险 (风险外溢机制)")
    if (spread is not None and spread >= th["spread_red_bps"]) \
            or "contract_renegotiation" in flags or "rating_downgrade" in flags:
        level = 3; reasons.append("长约重谈/降级/利差爆表 → Insull分红断裂对应物")

    return {"level": CREDIT[level], "level_idx": level, "reasons": reasons,
            "capex_ocf": ratios, "interest_rev_pct": ir, "spread_bps": spread}


# ---------------- 剪刀差与半场哨 ----------------

def scissors(infra_inputs: dict, load_inputs: dict, cfg: dict, credit_idx: int, copper_ph: int) -> dict:
    def wsum(vals: dict, weights: dict):
        s = w = 0.0
        for k, wt in weights.items():
            if vals.get(k) is not None:
                s += float(vals[k]) * wt; w += wt
        return round(s / w, 1) if w else None

    infra = wsum(infra_inputs, cfg["infra_weights"])
    load = wsum(load_inputs, cfg["load_weights"])
    gap = round(infra - load, 1) if infra is not None and load is not None else None
    whistle = bool(gap is not None and gap >= cfg["gap_alert"] and (credit_idx >= 2 or copper_ph >= 3))
    return {"infra": infra, "load": load, "gap": gap, "gap_alert": cfg["gap_alert"],
            "halftime_whistle": whistle,
            "note": "资本按基建进度定价,收入按负载进度到账;剪刀差=空窗期宽度=出清风险"}


# ---------------- 面板C：阈值击穿 ----------------

def threshold_breaches(token: dict, cfg: dict) -> list[dict]:
    frontier = token.get("frontier_usd_mtok")
    floor = token.get("floor_usd_mtok")
    rows = []
    for item in cfg["industry_thresholds"]:
        status, ref = "未击穿", None
        if floor is not None and floor <= item["flip_usd_per_mtok"]:
            status, ref = "底价已击穿", floor
        elif frontier is not None and frontier <= item["flip_usd_per_mtok"]:
            status, ref = "旗舰已击穿", frontier
        rows.append({**item, "status": status, "ref_price": ref})
    return rows
