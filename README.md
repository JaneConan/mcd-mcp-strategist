# 🧙 麦门军师 · MaiStrategist

> 把饭点安排明白——麦当劳怎么吃，交给 AI。
> 一句话需求进，一张最优订单出。

基于**麦当劳 MCP**（mcd.mcd.cn）的 AI 用餐决策 Skill：自动领麦麦省券、束搜索凑单优化、
官方核价校验、一键下单闭环。用 **WorkBuddy** 开发，同时参加
**WaytoAGI 1024 切磋大会 · 用餐赛道**与**麦当劳程序员创意开发大赛**。

[![MCP](https://img.shields.io/badge/McDonald's%20MCP-mcp.mcd.cn-ffc72c)](https://open.mcd.cn/mcp)
[![Built with WorkBuddy](https://img.shields.io/badge/Built%20with-WorkBuddy-0052d9)](https://www.workbuddy.cn)
[![Tests](https://img.shields.io/badge/tests-10%2F10%20passing-brightgreen)](#-测试)
[![Python](https://img.shields.io/badge/python-3.8%2B-blue)](#-快速开始)

---

## ✨ 它能做什么

| 场景 | 你说 | 军师做 |
|---|---|---|
| 🍔 **省钱点餐**（主场景） | "2 个人 80 块吃麦当劳，怎么点最划算？" | 定位门店 → 拉菜单 → **自动领麦麦省券** → 束搜索优化 → `calculate-price` 官方核价 → 献上最划算的一单 |
| 🎫 **凑单冲券** | "我这单怎么再用券？" | 自动算门槛差额，提示"再加 XX 即可用满 59 减 18，净省 N 元" |
| 🥗 **热量预算** | "减脂期，1200 千卡内吃啥？" | `list-nutrition-foods` 营养数据 + 热量约束优化 |
| 🎉 **聚餐模式** | "4 个人 150 块" | 按人数排兵布阵，输出人均价 |
| 📅 **活动雷达** | "最近麦当劳有啥活动？" | `campaign-calendar` 本月羊毛 + 积分抽奖信息 |
| 🛵 **一键下单** | "就这个，下单" | `create-order` 生成订单与支付链接（**经你确认后才执行**） |

每一单输出都带 **麦门段位** 称号：省 <10 元·麦门学徒 / 10–20 元·麦门道友 /
20–30 元·麦门长老 / ≥30 元·麦门巨佬。

## 🏗 工作原理

```
用户一句话需求
   │
   ▼
┌─────────────────────────────────────────────────────────────┐
│  WorkBuddy + 麦门军师 Skill (SKILL.md)                       │
│                                                             │
│  1. 解析需求（预算/人数/忌口/热量/取餐方式）                    │
│  2. query-nearby-stores / delivery-query-stores  定位门店    │
│  3. query-meals / query-meal-detail             拉菜单       │
│  4. auto-bind-coupons → query-my-coupons        收法宝(领券) │
│  5. scripts/meal_optimizer.py                   排兵布阵     │
│     └─ 多阵法模板 × Beam Search × 优惠券枚举（纯本地，秒级）    │
│  6. calculate-price                             官方核价     │
│  7. 献锦囊：最优一单 + 省钱金额 + 段位 + 凑单提示              │
│  8. 用户确认 → create-order → 支付链接                        │
└─────────────────────────────────────────────────────────────┘
   │
   ▼
麦当劳 MCP Server (https://mcp.mcd.cn) —— 菜单/优惠券/门店/订单/营养/活动
```

**设计原则**：优化引擎只负责生成候选，价格一律以麦当劳官方 `calculate-price`
返回为准；花用户钱的动作（下单/支付/抽奖）必须经用户明确确认。

## 🚀 快速开始

### 方式 A：零门槛演示（无需 MCP Token，30 秒）

```bash
git clone https://github.com/JaneConan/mcd-mcp-strategist.git
cd mcd-mcp-strategist
python3 scripts/demo.py
```

即可看到内置示例数据上的完整「献策」过程。

### 方式 B：完整能力（需麦当劳 MCP Token）

1. **申请 Token**：打开 [open.mcd.cn/mcp](https://open.mcd.cn/mcp) → 手机号登录 →
   右上角「控制台」→「激活」→ 复制 MCP Token
2. **配置 MCP**（WorkBuddy）：左侧边栏「专家·技能·连接器」→「连接器」→
   右上角「自定义连接器」→「配置 MCP」，填入：

   ```json
   {
     "mcpServers": {
       "mcd-mcp": {
         "type": "streamablehttp",
         "url": "https://mcp.mcd.cn",
         "headers": { "Authorization": "Bearer YOUR_MCP_TOKEN" }
       }
     }
   }
   ```

   回到「自定义连接器」启用 `mcd-mcp`。（脱敏示例见 [`mcp-config.example.json`](./mcp-config.example.json)）
3. **安装 Skill**：将本仓库放入 WorkBuddy 技能目录（`~/.workbuddy/skills/mcd-mcp-strategist/`），
   或直接在对话中对 WorkBuddy 说："用麦门军师帮我规划今天的麦当劳"。
4. **开吃**：

   > 🧙 麦门军师上线。
   > 你："2 个人，80 块，南开大悦城附近，外送"
   > 军师：定位门店 → 自动领麦麦省券 → 束搜索出 3 套锦囊 → 官方核价 →
   > "锦囊1：巨无霸×2 + 麦乐鸡(2块) + 可乐(中)×2，原价 92.5 → 实付 74.5，省 18 元，麦门长老段位！
   > 再加一包薯条(小)即可用满 59 减 18……" → 你说"下单" → 支付链接到手。

## 🧪 已验证：引擎算价 = 官方算价（分毫不差）

2026-10-24 在天津南开·长荣大厦餐厅（storeCode=1980321）用**真实 MCP Token** 全链路实测：

```
[数据] 菜单 113 餐品 | 营养 158 条 | 我的券 3 张 | 门店券 1 张
[探测] 麦辣鸡腿堡三件套 不在菜单，官方原价 ¥47.00，已补入
[用券] 今日可用 1 张: 麦辣鸡腿堡三件套（另 2 张 10/26 才生效，已自动过滤）
[优化] 候选方案 1949 套

【最大优惠】
  1. 麦辣鸡腿堡三件套x1 + 龙焰鸡腿堡x1 + 雪碧x1 + 可乐x1
     原价 ¥81.90 | 券减 ¥24.10 | 实付 ¥57.80
🏆 麦门段位: 麦门长老（立省 ¥24.10，约等于多吃 1.5 个麦香鸡）
   省钱方案官方核价: 实付 ¥57.80 ✅ 一致

【最便宜】（1 人 50 元场景）
   官方核价: 实付 ¥21.40 ✅ 一致
```

**引擎候选价与麦当劳官方 `calculate-price` 在两个场景下完全一致。**
完整日志见 [`docs/live-test-log.txt`](./docs/live-test-log.txt)，接入细节见
[`MCP_INTEGRATION.md`](./MCP_INTEGRATION.md)。

## 📁 目录结构

```
mcd-mcp-strategist/
├── SKILL.md                    # ★ Skill 主体（WorkBuddy 加载）
├── README.md
├── CONTEST_DECLARATION.md      # 参赛声明（官方模板，不可改动）
├── MCP_INTEGRATION.md          # MCP 接入说明（Server/Tool/流程/价值/实测记录）
├── mcp-config.example.json     # 脱敏 MCP 配置示例（仅环境变量占位符）
├── workbuddy.md                # WorkBuddy 开发对话记录
├── scripts/
│   ├── mcp_pipeline.py         # ★ 端到端流水线（MCP 拉数→优化→官方核价）
│   ├── meal_optimizer.py       # 凑单/用券优化引擎（束搜索+券锚定，纯标准库）
│   └── demo.py                 # 一键演示（无需 Token）
├── tests/
│   └── test_meal_optimizer.py  # 10 项单元测试
├── docs/
│   ├── usage.md                # 使用说明
│   └── live-test-log.txt       # 真实 MCP 链路实测日志
└── data/
    └── menu_sample.json        # 示例菜单/券数据（真实数据来自 MCP）
```

## 🧪 测试

```bash
python3 tests/test_meal_optimizer.py
```

```
Ran 10 tests in 0.52s — OK
```

覆盖：预算约束、热量约束、必吃品/忌口、人数缩放、门槛券生效、
单品券优于无券、凑单提示、不可行场景等。

## 🎯 目标用户

- **精打细算的麦门信徒**：每一分钱都要花出最大麦香值
- **选择困难症患者**："吃啥"这个世纪难题，一句话解决
- **健身/减脂人群**：热量预算内搭配麦当劳
- **聚餐组织者**：N 人预算一键分配
- **想薅羊毛的 everyone**：麦麦省券自动领，活动日历自动看

## 🏆 参赛信息

- **WaytoAGI 1024 切磋大会 · 用餐赛道**（把饭点安排明白）
- **麦当劳程序员创意开发大赛**（M-China/mcd-developer-innovation-challenge）
- 开发工具：腾讯 WorkBuddy + 麦当劳 MCP
- 报名 Issue：见麦当劳大赛仓库 Issue 列表

## ⚠️ 免责声明

本项目为参赛作品，由参赛者独立开发，**非麦当劳官方产品**。项目输出仅供参考，
不构成医疗、营养或其他专业建议；餐品信息、价格及供应状态以麦当劳官方渠道的
实时结果为准。优惠券叠加规则、配送费、起送价等以官方规则与 `calculate-price`
返回为准。

## 📄 License

MIT
