# MCP_INTEGRATION.md — 麦当劳 MCP 接入说明

> 麦门军师 · MaiStrategist
> 本文说明项目实际使用的麦当劳 MCP Server、Tool、调用流程与业务价值。

## 1. MCP Server

| 项 | 值 |
|---|---|
| 服务名称 | 麦当劳 MCP（McDonald's China MCP Server） |
| 接入地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 鉴权 | 请求头 `Authorization: Bearer <MCP_TOKEN>` |
| Token 申请 | [open.mcd.cn/mcp](https://open.mcd.cn/mcp)（手机号登录 → 控制台 → 激活） |
| 限流 | 单 Token 600 次/分钟（429 时退避重试） |
| 开放平台文档 | [github.com/M-China/mcd-mcp-server](https://github.com/M-China/mcd-mcp-server) |

WorkBuddy 侧配置（`连接器 → 自定义连接器 → 配置MCP`）：

```json
{
  "mcpServers": {
    "mcd-mcp": {
      "type": "streamablehttp",
      "url": "https://mcp.mcd.cn",
      "headers": { "Authorization": "Bearer ${MCD_MCP_TOKEN}" }
    }
  }
}
```

## 2. 实际调用的 Tool 及用途

| 阶段 | Tool | 用途 | 调用方式 |
|---|---|---|---|
| 定位 | `query-nearby-stores` | 到店/得来速：按地址查附近可用门店 | 用户给地址 → 返回门店列表 → 选定门店 |
| 定位 | `delivery-query-addresses` / `delivery-query-stores` | 外送：取配送地址、查可配送门店 | 外送场景必用 |
| 菜单 | `query-meals` | 当前门店可售餐品（分类、编码、价格、标签） | 组装优化引擎 `items` 输入 |
| 菜单 | `query-meal-detail` | 套餐组成与可替换选项（换饮料/小食影响价格与用券） | 候选套餐细查 |
| 领券 | `auto-bind-coupons` | **麦麦省一键领券**（先领再比，券是弹药） | 标准流程第 4 步，一个不省 |
| 领券 | `query-my-coupons` | 我的可用券（面额、门槛、有效期） | 组装优化引擎 `coupons` 输入 |
| 领券 | `query-store-coupons` | 当前门店可用券 | 同上 |
| 领券 | `available-coupons` | 麦麦省可领券列表（领券前展示） | 可选 |
| 核价 | `calculate-price` | 商品列表（含优惠券）算金额/配送费/优惠/应付 | **每单必调**：校验引擎候选价格 |
| 下单 | `create-order` | 创建订单，返回订单详情与支付链接 | 仅用户明确确认后执行 |
| 下单 | `cancel-order` | 取消订单 | 用户反悔时 |
| 订单 | `query-order` / `order-list` | 查订单状态 / 历史订单 | 售后与复盘 |
| 彩蛋·热量 | `list-nutrition-foods` | 餐品营养（能量/蛋白质/脂肪/碳水/钠/钙） | 热量预算模式 |
| 彩蛋·活动 | `campaign-calendar` | 当月营销活动日历 | 活动雷达 |
| 彩蛋·积分 | `query-my-account` | 积分账户 | 羊毛盘点 |
| 彩蛋·抽奖 | `query-lottery-info` / `draw-lottery` / `query-my-prizes` | 积分抽奖 | 消耗积分前须用户同意 |
| 工具 | `now-time-info` | 当前时间（判断活动/早餐时段有效性） | 需要时 |

## 3. 调用流程（标准省钱点餐）

```
用户需求（预算/人数/地址/取餐方式）
  │
  ├─1─ query-nearby-stores ────────────► 门店
  ├─2─ query-meals ───────────────────► 菜单 items[]
  │      └─ query-meal-detail ────────► 套餐组成/替换项（按需）
  ├─3─ auto-bind-coupons ─────────────► 麦麦省一键领券
  │      query-my-coupons ────────────► 我的券 coupons[]
  │      query-store-coupons ─────────► 门店券（并入 coupons[]）
  ├─4─ meal_optimizer.py(items+coupons+constraints)
  │      └─ 多阵法模板 × Beam Search × 优惠券枚举 ─► 候选方案 Top-N
  ├─5─ calculate-price(最优组合+用券) ──► 官方应付价（校验，不一致以官方为准）
  └─6─ 献锦囊 ──► 用户确认 ──► create-order ──► 支付链接
```

数据流：MCP 工具返回的菜单/券由 Skill 组装成 `scripts/meal_optimizer.py`
定义的 JSON 输入；引擎输出候选；`calculate-price` 做最终核价。引擎与 MCP
解耦，可在无 Token 环境用示例数据独立运行与测试。

## 4. 业务价值

1. **真省钱**：麦麦省券自动领 + 组合优化，把"随便点"变成"最划算的一单"，
   实测场景（2 人 80 元预算）比随手点省 15–25 元。
2. **真闭环**：从"吃啥"到"支付链接"一条链路走完，不是只会查菜单的问答机器人。
3. **真合规**：价格以官方 `calculate-price` 为准；下单/支付/抽奖必须用户确认；
   Token 与隐私信息不出现在任何输出与仓库文件中（配置文件仅环境变量占位符）。
4. **真好玩**：麦门军师人设 + 段位称号 + 凑单提示，让算账变成薅羊毛的乐趣。

## 5. 实测记录（2026-10-24，天津南开·长荣大厦餐厅 storeCode=1980321）

> 以下为开发期间对 mcd-mcp 的真实调用与结果，完整日志见 `docs/live-test-log.txt`。

| 顺序 | 调用 | 关键结果 |
|---|---|---|
| 1 | `now-time-info` | 服务器时间 2026-10-24 17:48:43（Token 有效） |
| 2 | `tools/list` | **在线 35 个工具**（官方文档列 30 个，另有 query-survey-coupon 等新增） |
| 3 | `campaign-calendar` | 返回 10 月活动日历（PEACEMINUSONE 联名周边、「我就喜欢」丝巾等，含进行中/往期/未来） |
| 4 | `list-nutrition-foods` | 158 条餐品营养（能量 kJ/kcal、蛋白质、脂肪、碳水、钠、钙） |
| 5 | `query-nearby-stores` (beType=1, searchType=2, city=天津, keyword=南开大悦城) | 长荣大厦餐厅（188m）、三马路福邻荟餐厅（581m）等，含营业时间与预约时段 |
| 6 | `query-meals` (storeCode, orderType=1, beType=1) | **113 个餐品**（15 个分类，`data.meals` 字典含 currentPrice/originalPrice） |
| 7 | `query-my-coupons` | 用户钱包 3 张券：麦辣鸡腿堡三件套 ¥22.9（10/23 生效）、11.9 元麦辣鸡腿堡与 19.9 元王牌炸鸡任选 2（10/26 生效） |
| 8 | `query-store-coupons` | 门店券权威视图：三件套券 couponId=B7A9CFE8…、couponCode=MCD6204QY…、适用商品编码 **9900004002** |
| 9 | `auto-bind-coupons` | "暂无可领取"（麦麦省券均已领取，幂等安全） |
| 10 | `calculate-price`（探测） | 三件套商品 9900004002 **不在菜单中**，官方核价得出原价 ¥47.00 → 流水线自动补入菜单 |
| 11 | `calculate-price`（核价·最便宜方案） | 龙焰鸡腿堡+雪碧×2+蘸酱炸鸡：引擎 ¥46.80 = 官方 ¥46.80 ✅ |
| 12 | `calculate-price`（核价·省钱方案） | 三件套+龙焰鸡腿堡+雪碧+可乐：引擎 ¥57.80 = 官方 ¥57.80 ✅ |

### 实测中发现的 API 行为（已写进 Skill 工作流）

1. **`query-meals` 只返回编码+标签**，餐品名称与价格在响应的 `data.meals` 字典里（按 code 索引）；
2. **`calculate-price` 不挂券时返回全 0**——官方价格必须挂在券上才算得出来，裸跑无意义；
3. **券的权威适用范围以 `query-store-coupons` 的 `products[].productCode` 为准**，
   按券名模糊匹配菜单会匹配错变体（三件套券实际适用 9900004002，原价 47，
   而菜单里 9900005456 是另一个 33.5 的变体——差 13.5 元）；
4. **`orderType`/`beType` 传递矩阵**：到店自取 beType=1→orderType=1 不传 beCode；
   得来速 beType=5→orderType=1 必传 beCode；麦乐送 beType=2→orderType=2 必传 beCode；团餐 beType=6→orderType=2；
5. **券有生效日期**：`query-my-coupons` 把未生效的券也列为"可用"，流水线按 `有效期` 字段过滤；
6. **菜单中可能缺少券适用商品**：用 `calculate-price` 挂券探测官方原价后补入（探测一次，幂等）。

### 端到端验证结论

引擎候选价格与麦当劳官方 `calculate-price` **在两个测试场景下完全一致**
（¥46.80 / ¥57.80），证明"本地优化 + 官方核价"架构可靠；引擎只生成候选，
一切以官方返回为准的设计在实测中成立。
