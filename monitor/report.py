"""报告层:控制室看板 v2 — 趋势图(内嵌SVG)、色带标尺、每面板"怎么读"说明。零JS依赖。"""
from __future__ import annotations
import datetime as dt

C = {"bg": "#141A24", "panel": "#1B2330", "line": "#2A3547", "txt": "#D8DEE9", "dim": "#7C8798",
     "amber": "#F2A623", "teal": "#3FBF9F", "coral": "#E8593C", "blue": "#5B8DD9",
     "green": "#3FBF9F", "yellow": "#F2A623", "orange": "#E88A3C", "red": "#E8593C"}

CSS = f"""
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:{C['bg']};color:{C['txt']};font-family:'IBM Plex Mono','SF Mono',Menlo,'PingFang SC','Microsoft YaHei',monospace;
     font-size:14px;line-height:1.65;padding:28px;max-width:1180px;margin:0 auto}}
header{{display:flex;justify-content:space-between;align-items:baseline;border-bottom:2px solid {C['amber']};
       padding-bottom:14px;margin-bottom:22px;flex-wrap:wrap;gap:8px}}
h1{{font-size:19px;font-weight:600;letter-spacing:.12em}} h1 span{{color:{C['amber']}}}
.sub{{color:{C['dim']};font-size:12px}}
.panel{{background:{C['panel']};border:1px solid {C['line']};border-radius:10px;padding:18px 20px;margin-bottom:18px}}
.plabel{{font-size:11px;letter-spacing:.22em;color:{C['dim']};text-transform:uppercase;margin-bottom:12px;
        display:flex;justify-content:space-between}}
.lamps{{display:flex;gap:10px;flex-wrap:wrap;margin:6px 0 14px}}
.lamp{{padding:5px 13px;border-radius:20px;border:1px solid {C['line']};color:{C['dim']};font-size:12.5px}}
.lamp.on{{background:{C['amber']};color:#1A1206;border-color:{C['amber']};font-weight:600;
         box-shadow:0 0 14px rgba(242,166,35,.45)}}
.chips{{display:flex;gap:10px;flex-wrap:wrap}}
.chip{{border:1px solid {C['line']};border-radius:8px;padding:8px 12px;min-width:118px}}
.chip .k{{font-size:11px;color:{C['dim']}}} .chip .v{{font-size:17px;font-weight:600}}
.gauge{{margin:8px 0 4px}}
.track{{position:relative;height:14px;background:#0E1420;border:1px solid {C['line']};border-radius:7px;margin:7px 0 3px}}
.fill{{position:absolute;top:0;left:0;bottom:0;border-radius:7px}}
.tlabel{{display:flex;justify-content:space-between;font-size:11.5px;color:{C['dim']}}}
.banner{{border-radius:8px;padding:10px 14px;font-weight:600;letter-spacing:.06em;margin-bottom:12px;color:#141A24}}
table{{width:100%;border-collapse:collapse;font-size:13px}}
th{{text-align:left;color:{C['dim']};font-weight:400;font-size:11.5px;letter-spacing:.08em;
   border-bottom:1px solid {C['line']};padding:6px 8px}}
td{{padding:7px 8px;border-bottom:1px solid {C['line']};vertical-align:top}}
.ok{{color:{C['teal']}}} .warn{{color:{C['amber']}}} .bad{{color:{C['coral']}}}
ul{{list-style:none}} li{{padding:3px 0}} li::before{{content:"▸ ";color:{C['amber']}}}
.grid2{{display:grid;grid-template-columns:1fr 1fr;gap:18px}}
.grid4{{display:grid;grid-template-columns:repeat(auto-fit,minmax(255px,1fr));gap:14px}}
@media(max-width:800px){{.grid2{{grid-template-columns:1fr}}}}
footer{{color:{C['dim']};font-size:11.5px;border-top:1px solid {C['line']};padding-top:12px;margin-top:6px}}
.mk{{position:absolute;top:-4px;bottom:-4px;width:2px;background:{C['coral']}}}
details{{margin-top:12px;border-top:1px dashed {C['line']};padding-top:8px}}
summary{{cursor:pointer;color:{C['blue']};font-size:12px;letter-spacing:.06em}}
details p, details li{{font-size:12.5px;color:{C['dim']};margin:6px 0}}
details b{{color:{C['txt']};font-weight:600}}
.chart{{background:#0E1420;border:1px solid {C['line']};border-radius:8px;padding:10px 12px 6px}}
.chart .t{{font-size:11.5px;color:{C['dim']};letter-spacing:.06em;margin-bottom:2px}}
.bands{{position:relative;height:26px;display:flex;border-radius:6px;overflow:visible;margin:22px 0 6px}}
.bands div{{height:14px;margin-top:6px}}
.bmk{{position:absolute;top:-8px;transform:translateX(-50%);color:{C['txt']};font-size:11px;text-align:center}}
.bmk::after{{content:"▼";display:block;color:{C['coral']};font-size:10px;line-height:.6}}
.blab{{display:flex;font-size:10.5px;color:{C['dim']}}}
"""


def _bar(pct, color, label_l, label_r, marker_pct=None):
    mk = f'<div class="mk" style="left:{marker_pct}%"></div>' if marker_pct else ""
    p = max(0, min(100, pct or 0))
    return (f'<div class="gauge"><div class="tlabel"><span>{label_l}</span><span>{p:.0f}</span></div>'
            f'<div class="track"><div class="fill" style="width:{p}%;background:{color}"></div>{mk}</div>'
            f'<div class="tlabel"><span></span><span>{label_r}</span></div></div>')


def _chart(title: str, series_list: list[dict], w=300, h=96) -> str:
    """极简折线图。series_list: [{name,color,points:[(date,val)]}] 共享x轴(日期并集)。"""
    dates = sorted({d for s in series_list for d, _ in s["points"]})
    vals = [v for s in series_list for _, v in s["points"]]
    if not dates or not vals:
        return f'<div class="chart"><div class="t">{title}</div><div class="sub">暂无历史数据</div></div>'
    lo, hi = min(vals), max(vals)
    pad = (hi - lo) * 0.12 or abs(hi) * 0.1 or 1
    lo, hi = lo - pad, hi + pad
    xi = {d: i for i, d in enumerate(dates)}
    n = max(1, len(dates) - 1)

    def xy(d, v):
        return 34 + xi[d] / n * (w - 44), h - 16 - (v - lo) / (hi - lo) * (h - 26)

    svg = ""
    legend = ""
    for s in series_list:
        pts = [xy(d, v) for d, v in sorted(s["points"])]
        path = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
        svg += f'<polyline points="{path}" fill="none" stroke="{s["color"]}" stroke-width="1.8"/>'
        ex, ey = pts[-1]
        svg += f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="2.6" fill="{s["color"]}"/>'
        legend += (f'<tspan fill="{s["color"]}">● {s["name"]} '
                   f'{sorted(s["points"])[-1][1]:g}</tspan>  ')
    grid = "".join(f'<line x1="34" y1="{y}" x2="{w-8}" y2="{y}" stroke="{C["line"]}" stroke-width="0.5"/>'
                   f'<text x="30" y="{y+3}" text-anchor="end" font-size="9" fill="{C["dim"]}">{v:g}</text>'
                   for v, y in [(hi - pad, xy(dates[0], hi - pad)[1]), (lo + pad, xy(dates[0], lo + pad)[1])])
    return (f'<div class="chart"><div class="t">{title}</div>'
            f'<svg viewBox="0 0 {w} {h}" width="100%">{grid}{svg}'
            f'<text x="34" y="{h-3}" font-size="9.5" fill="{C["dim"]}">{dates[0]}</text>'
            f'<text x="{w-8}" y="{h-3}" text-anchor="end" font-size="9.5" fill="{C["dim"]}">{dates[-1]}</text>'
            f'<text x="34" y="10" font-size="10">{legend}</text></svg></div>')


def _bands(value: float, segs: list[tuple], vmax: float, unit="%") -> str:
    """色带标尺: segs=[(起,止,颜色,标签)], 三角标记当前值。"""
    cells = lab = ""
    for a, b, col, name in segs:
        wpc = (b - a) / vmax * 100
        cells += f'<div style="width:{wpc}%;background:{col};opacity:.75"></div>'
        lab += f'<span style="width:{wpc}%">{name}<br>{a}–{b}{unit}</span>'
    mk = f'<div class="bmk" style="left:{min(99, value / vmax * 100):.1f}%">{value}{unit}</div>' if value is not None else ""
    return f'<div class="bands">{cells}{mk}</div><div class="blab">{lab}</div>'


def render(state: dict) -> str:
    cu, cr, sc, th, org, ev, meta = (state[k] for k in
                                     ("copper", "credit", "scissors", "thresholds", "org", "events", "meta"))
    hist = meta.get("history", {})

    lamps = "".join(f'<span class="lamp{" on" if cu["phase"] == i else ""}">{lbl}</span>'
                    for i, lbl in [(1, "① 启动"), (2, "② 主升"), (3, "③ 顶部信号"), (4, "④ 崩塌"), (5, "⑤ 出清")])
    chips = "".join(f'<div class="chip"><div class="k">{k}</div><div class="v">{("—" if v is None else v)}</div></div>'
                    for k, v in cu["metrics"].items())
    hits = "".join(f"<li>{h}</li>" for h in cu["top_hits"]) or "<li class='sub'>暂无</li>"
    gpu = meta.get("gpu_spot") or {}
    gpu_row = (f'<div class="chip"><div class="k">GPU现货 {gpu.get("gpu_model","")}</div>'
               f'<div class="v">${gpu["usd_per_hour"]}/h <span class="sub">({gpu["chg_pct"]:+}%)</span></div></div>') if gpu else ""

    lv = cr["level"]
    reasons = "".join(f"<li>{r}</li>" for r in cr["reasons"]) or "<li>无触发</li>"
    ratios = "".join(f"<tr><td>{t}</td><td class={'\"bad\"' if (r or 0)>=1 else '\"ok\"'}>{r}</td></tr>"
                     for t, r in (cr["capex_ocf"] or {}).items())
    ir_bands = _bands(cr["interest_rev_pct"], [
        (0, 10, C["teal"], "公用事业常态"), (10, 25, C["amber"], "关注"),
        (25, 40, C["orange"], "Insull区"), (40, 50, C["coral"], "危险(环球电讯路径)")], 50)

    whistle = ('<span class="lamp on">半场哨预警</span>' if sc["halftime_whistle"]
               else '<span class="lamp">半场哨:未触发</span>')

    trs = ""
    for r in th:
        breached = "击穿" in r["status"]
        cls = "ok" if breached else "warn"
        how = (f'最低可用价${r["ref_price"]} ≤ 阈值' if r["status"] == "底价已击穿"
               else f'旗舰价${r["ref_price"]} ≤ 阈值' if r["status"] == "旗舰已击穿" else "价格仍高于阈值")
        meaning = "成本已不是瓶颈→看产品/监管" if breached else "等待降价"
        trs += (f'<tr><td>{r["name"]}</td><td>${r["flip_usd_per_mtok"]}/Mtok</td>'
                f'<td class="{cls}">{r["status"]}<br><span class="sub">{how}</span></td>'
                f'<td class="sub">{meaning}。{r["note"]}</td></tr>')

    evs = "".join(f'<tr><td>{e["date"]}</td><td>{e["flag"]}</td><td class="sub">{e["note"]}</td></tr>'
                  for e in ev) or "<tr><td colspan=3 class='sub'>无</td></tr>"
    tokp = meta.get("token", {})
    load_pct = org.get("industrial_token_share")

    charts = f"""<div class="grid4">
{_chart("Token价格 $/Mtok", [{"name": "旗舰", "color": C['amber'], "points": hist.get('frontier', [])},
                              {"name": "底价", "color": C['teal'], "points": hist.get('floor', [])}])}
{_chart("GPU现货 $/h (gpu_monitor)", [{"name": "H100", "color": C['blue'], "points": hist.get('gpu', [])}])}
{_chart("剪刀差(空窗宽度)", [{"name": "gap", "color": C['coral'], "points": hist.get('gap', [])}])}
{_chart("工业负载占比 %", [{"name": "load", "color": C['teal'], "points": hist.get('load', [])}])}
</div>"""

    return f"""<!doctype html><html lang="zh"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>四次革命周期监测 · 控制室</title><style>{CSS}</style></head><body>
<header><h1>四次革命周期监测 <span>CONTROL ROOM</span></h1>
<div class="sub">正厅窗口锚点 2032–2037 ｜ 生成 {dt.date.today()} ｜ 历史数据点 {meta.get('hist_n', 0)} 个
(最近 {meta.get('hist_last', '—')})</div></header>

<div class="panel"><div class="plabel"><span>历史趋势(每日记录)</span>
<span>今天没新点=任务没跑,这就是"更新没"的答案</span></div>{charts}</div>

<div class="panel"><div class="plabel"><span>剪刀差 · 空窗期宽度(半场哨)</span><span>gap≥{sc['gap_alert']} 且 信用≥橙 → 预警</span></div>
{_bar(sc['infra'], C['amber'], "基础设施进度(capex/电力/HBM产能)", "100=正厅基建完工")}
{_bar(sc['load'], C['teal'], "工业负载进度(agent渗透/人均产值拐点)", "100=正厅满载")}
<div class="chips" style="margin-top:10px"><div class="chip"><div class="k">剪刀差</div><div class="v">{sc['gap']}</div></div>{whistle}</div>
<details><summary>怎么读这个面板</summary>
<p><b>逻辑</b>:资本按基建进度定价,收入按负载进度到账,两者之差=空窗期宽度。1847/1929/2000的金融出清全部发生在空窗内。</p>
<p><b>gap走阔</b>=基建跑得比应用快→出清风险上升;<b>gap收窄</b>=应用追上来→泡沫获得收入证据。方向比水平重要,盯上面的趋势图。</p></details></div>

<div class="panel"><div class="plabel"><span>面板A · 铜层周期(HBM/光模块/封装/电力设备)</span><span>顶部信号 {len(cu['top_hits'])}/{cu['needed']}</span></div>
<div class="lamps">{lamps}</div>
<div class="chips">{chips}{gpu_row}</div>
<div style="margin-top:10px"><span class="sub">顶部信号计票:</span><ul>{hits}</ul></div>
<details><summary>怎么读这个面板(各指标定义与来源)</summary>
<p><b>库存周数</b>(财报电话会/TrendForce):原厂+渠道库存÷周销量。&lt;4周=紧缺确认(2018/2025低点均3.3周),回升破10周=过剩确认。</p>
<p><b>capex/销售%</b>(三大厂财报):供给响应强度。≥35%进入历史存储周期的顶部区——高利润驱动的扩产总在1-2年后变成过剩。</p>
<p><b>HBM晶圆份额%</b>(TrendForce):产能分配闸门,路径18%(25)→22%(26)→30%(27)。逼近28%="新矿群到位",供给洪峰在途。</p>
<p><b>替代渗透%</b>:CPO占新增光互连端口比。≥10%=铝替代铜时刻——历史上替代总在价格峰值处加速,毛利率最好看时最危险。</p>
<p><b>单晶圆盈利倒挂</b>(事件flag,TrendForce 1Q26):同一片晶圆做HBM的收益低于做DDR5——"主矿不如副产品赚钱",
厂商产能回切动机出现,供给结构松动的早期信号。<b>它不预示立刻见顶,但计入顶部信号票。</b></p></details></div>

<div class="grid2">
<div class="panel"><div class="plabel"><span>面板B · 融资结构(泡沫形状)</span></div>
<div class="banner" style="background:{C[lv]}">信用状态: {lv.upper()}</div>
<ul>{reasons}</ul>
<div class="sub" style="margin-top:12px">Neocloud利息/收入 与 安全区间:</div>{ir_bands}
<table style="margin-top:12px"><tr><th>超大规模厂商</th><th>capex/OCF</th></tr>{ratios}</table>
<details><summary>怎么读这个面板</summary>
<p><b>利息/收入色带</b>:&lt;10%是公用事业/数据中心REIT的正常杠杆水位;25-40%=Insull区(1932控股金字塔崩塌前的负担水平);
≥40%对应环球电讯1999-2001破产前路径。当前值取CRWV口径。</p>
<p><b>capex/OCF&gt;1</b>=经营现金流不够花,必须发债/发股维持扩张——泡沫从"现金流游戏"变"融资游戏"的分界线。</p>
<p><b>红灯项</b>(长约重谈/降级/利差≥400bps)=Insull分红断裂对应物,触发即强制半场哨。</p></details></div>

<div class="panel"><div class="plabel"><span>面板C-1 · 台灯→电机交叉点</span></div>
{_bar(load_pct, C['teal'], "工业负载占token消耗比(agent/API vs 聊天)", "交叉点=照明时代结束", marker_pct=50)}
<div class="chips" style="margin-top:8px">
<div class="chip"><div class="k">旗舰均价</div><div class="v">${tokp.get('frontier_usd_mtok','—')}/Mtok</div></div>
<div class="chip"><div class="k">最低可用价(P5)</div><div class="v">${tokp.get('floor_usd_mtok','—')}/Mtok</div></div>
<div class="chip"><div class="k">人均产值比</div><div class="v">{org.get('rev_per_employee_ratio','—')}×</div></div>
<div class="chip"><div class="k">裁员中层占比</div><div class="v">{org.get('middle_mgmt_layoff_share','—')}%</div></div></div>
<details><summary>怎么读:过线是好是坏?</summary>
<p><b>这不是涨跌信号,是需求性质的证据线。</b>越过50%意味着:①capex拿到收入证据,需求从可选订阅变生产刚需→剪刀差收窄→
出清风险<b>下降</b>;②token加速商品化,单价继续跌但量补价(电力公司剧本,利好卖铲人、压缩模型层毛利)。</p>
<p><b>坏的情形是迟迟不过线</b>而基建继续堆——空窗拉宽,1929剧本概率上升。所以关注的是这条线的<b>斜率</b>,不是它本身的涨跌含义。</p>
<p><b>人均产值比/中层占比</b>=福特识别器:前者是AI原生篮子÷传统SaaS中位数(现20×),后者衡量组织拓扑是否真在变更(亚马逊样本78%)。</p></details></div>
</div>

<div class="panel"><div class="plabel"><span>面板C-2 · 行业阈值击穿进度(二阶产业着火表)</span></div>
<table><tr><th>行业翻转点</th><th>阈值价</th><th>状态</th><th>含义</th></tr>{trs}</table>
<div class="sub" style="margin-top:8px">旗舰均价=前沿模型混合价(输入:输出按1:3);最低可用价=OpenRouter第5百分位模型价,
代表"最便宜但能用"。<b style="color:{C['txt']}">击穿≠产业已爆发</b>,只表示token成本不再是瓶颈,剩下的是产品/监管/信任——
参照Netflix等到2007年而非2000年。</div></div>

<div class="panel"><div class="plabel"><span>事件日志(状态机布尔输入)</span></div>
<table><tr><th>日期</th><th>事件</th><th>备注/来源</th></tr>{evs}</table></div>

<footer>面板A=时序 B=泡沫形状 C=传导/正厅点亮 ｜ 自动源每日记录进 data/history/daily.csv,人工源季度更新。
历史类比框架,非投资建议。</footer></body></html>"""
