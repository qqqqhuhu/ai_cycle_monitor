# AI Cycle Monitor — 四次革命框架周期监测看板

把此前推演的框架(2×2矩阵 + 上下半场 + 奠基石 + 回写)翻译成一个可运行的监测系统。
三个面板对应框架的三种能力：**A=时序(铜层周期)，B=泡沫形状(融资结构)，C=传导(正厅点亮)**，
顶部的**剪刀差量表**监测"基建进度 vs 工业负载进度"的空窗宽度——历史上金融出清(1847/1929/2000)全部发生在这个空窗里。

## 快速开始
```bash
pip install pyyaml yfinance requests   # yfinance/requests可选,断网自动降级缓存
python run.py                          # 生成 dashboard.html,浏览器打开
```

## 面板逻辑

**剪刀差/半场哨**：infra(累计capex、并网电力、HBM产能爬坡)与load(工业token占比、agent渗透、
人均产值拐点)各加权到0-100。`gap ≥ 30 且 信用面板 ≥ 橙` 触发半场哨预警。

**面板A 铜层周期**：五阶段状态机(启动→主升→顶部信号→崩塌→出清)。
- 启动：库存周数 < 4 且价格环比为正(2018/2025样本低点均3.3周)
- 主升：库存 < 6 且环比 > +10%
- 顶部信号：以下凑满2票——capex/销售≥35%、HBM晶圆份额≥28%(供给闸门)、替代渗透≥10%(CPO=铝替代铜)、
  单晶圆盈利倒挂flag、HBM4良率突破flag
- 崩塌：库存回破10周 或 环比 < -15% 或 订单取消潮flag
- 出清：厂商削减capex flag
- 已对接 `qqqqhuhu/gpu_monitor`：把现货价导出为 `data/auto/gpu_spot.csv`(date,gpu_model,usd_per_hour)即自动上板

**面板B 融资结构(四色灯)**：
- 黄：任一超大规模厂商 capex/OCF ≥ 1.0(依赖外债) 或 供应商融资敞口扩大
- 橙：neocloud 利息/收入 ≥ 25%(Insull杠杆区) 或 评级后AI债分发进养老金flag
- 红：算力长约重谈 / 降级 / 利差 ≥ 400bps —— Insull分红断裂的对应物,红灯即半场哨强制项

**面板C 正厅点亮**：
- 台灯→电机交叉点：工业负载(agent/API)占token消耗比,50%为照明时代终结线
- 行业阈值击穿表：token价格(OpenRouter自动)对照各行业经济学翻转价
- 福特识别器：AI原生/传统SaaS人均产值比、裁员中层占比

## 每日更新与历史序列
- 每次 `python run.py` 会把当日自动数据(token价格/GPU现货/剪刀差/负载占比/阶段状态)追加到
  `data/history/daily.csv`(同日重跑覆盖),看板顶部的四张趋势图由它驱动。
- **判断"更新没"**:看板header显示历史点数与最近日期;今天没新点=任务没跑。
- 每日自动化:仓库已含 `.github/workflows/daily.yml`,push到GitHub后每天UTC13:20自动运行并
  commit历史+看板;开启GitHub Pages(Settings→Pages→指向main分支)后收藏
  `https://<user>.github.io/<repo>/dashboard.html` 即可。当前daily.csv中2026上半年为示例回填,可删。

## 数据源分工
| 数据 | 方式 | 更新节奏 |
|---|---|---|
| capex/OCF、token价格 | 自动(yfinance/OpenRouter),断网用缓存 | 每次运行 |
| GPU现货价 | gpu_monitor钩子CSV | 随你现有看板 |
| 库存周数/capex销售比/晶圆份额 | data/manual/memory_cycle.csv | 季度(财报+TrendForce) |
| neocloud利息比/利差/评级事件 | credit_metrics.csv + events.csv | 季度+事件驱动 |
| 组织与负载指标 | org_metrics.csv / scissors_inputs.csv | 季度估算 |

事件flag(events.csv 的 active 列 0/1)是状态机的布尔输入——**发生即置1**,这是整个系统里
最需要人工判断也最值钱的部分。

当前CSV内为2026年7月的示例值(来源标注在note列),请核实后作为第一期基线。
历史类比框架,非投资建议。
