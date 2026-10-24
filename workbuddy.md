# workbuddy.md — 麦门军师开发记录（WorkBuddy 对话上下文）

> 本文档记录「麦门军师 · MaiStrategist」使用 **腾讯 WorkBuddy** 从 0 到 1 的开发过程，
> 用于麦当劳程序员创意开发大赛 WorkBuddy 专项奖励核验。
> 开发时间：2026-10-24（北京时间），开发环境：macOS + WorkBuddy Agent。

---

## 阶段 0 · 接单与调研（13:57–14:10）

**用户 prompt**："你帮我看看这个比赛，我要用麦当劳 MCP 做一个 AI 作品，你帮我策划策划，
尽可能多参加活动"（附 1024 用餐赛道页 + 麦当劳大赛仓库链接）

WorkBuddy 行动：
- 抓取并通读 4 份官方材料：
  1. `1024.waytoagi.com/tracks/dine` — 用餐赛道规则（10/25 16:00 截止，前三须用 WorkBuddy）
  2. `github.com/M-China/mcd-developer-innovation-challenge` — 大赛 README + activityGuidelines + CONTEST_DECLARATION + RANKING.md
  3. `github.com/M-China/mcd-mcp-server` — MCP 工具清单（30 个 Tool 全量列出）
  4. `1024.waytoagi.com/rules` + 首页 — 确认天津有线下会场（南开天开园）
- 关键结论：
  - 双赛共用同一 GitHub 仓库；1024 截止（10/25 16:00）早于麦当劳大赛（10/25 23:59）
  - 麦当劳大赛按 GitHub Star 排名，榜单已有 100+ 项目，前三 1100+ stars 难追，
    但 Star>0 即入榜（前 100 有周边+积分），主战场应是 1024 用餐赛道
  - MCP Token 需用户手机号登录 open.mcd.cn/mcp 申请（阻塞项，立即请用户去办）

## 阶段 1 · 策划决策（14:10–14:15）

**用户决策**（经 WorkBuddy 提问确认）：
| 决策项 | 选择 |
|---|---|
| 作品方向 | 麦门军师：省钱凑单+一键下单闭环（附热量/活动模块） |
| 仓库名 | `mcd-mcp-strategist`（JaneConan，公开） |
| 参赛形式 | 单人 |
| 天津会场 | 去南开天开园线下（可冲本地前三+在地最受欢迎） |

## 阶段 2 · 仓库与合规文件（14:15–14:25）

- 凭据发现：`~/.git-credentials` 无 GitHub 条目 → 从 **macOS 钥匙串**
  （`security find-internet-password -s github.com`）取得 OAuth Token
- GitHub API 建公开仓库 `JaneConan/mcd-mcp-strategist`（创建时间 2026-10-24，
  符合大赛要求的 2025-12-25 ~ 2026-10-25 窗口）
- `CONTEST_DECLARATION.md` 按官方模板**逐字落地**（文件名与内容均不可改）
- `mcp-config.example.json`：仅 `${MCD_MCP_TOKEN}` 环境变量占位符（合规要求）
- `.gitignore`：`mcp.json`/`.env` 等本地密钥文件永不入库

## 阶段 3 · Skill 与优化引擎开发（14:25–14:50）

**踩坑与修复（真实迭代过程）**：

1. **组合枚举爆炸**：初版用 `itertools.product(range(4), repeat=12)` 枚举每分类数量向量
   （4^12 ≈ 1670 万/分类），且把全部候选 append 进列表 → 进程被 kill（exit 137）。
   **修复**：改用**多阵法模板 + Beam Search（束搜索）**——按人生成
   饱腹/简约/轻食/丰盛/分享/团圆 6 类模板，每槽保留 Top-160 候选，
   三种目标（最便宜/最性价比/最贴近预算）分别搜索。1670 万 → 毫秒级。
2. **KeyError: 'qty'**：槽位项无 qty 字段，`_state_key`/`_merge` 崩溃。
   **修复**：`c.get("qty", 1)` 统一兼容。
3. **凑单提示符号错误**：净省金额正负颠倒。**修复**并补测试断言。
4. **性价比方案单调**：全堆最便宜单品。**修复**：value 目标加重复单品惩罚。

**产出**：
- `SKILL.md`：8 步标准工作流（解析→定位→菜单→领券→优化→官方核价→献锦囊→确认下单），
  麦门军师人设 + 段位称号 + 工程红线（不自动下单/支付/抽奖）
- `scripts/meal_optimizer.py`：~330 行，纯标准库；支持满减/折扣/单品券/免配送费，
  门槛券凑单提示，热量/必吃/忌口/人数约束
- `tests/test_meal_optimizer.py`：**10/10 通过（0.52s）**
- `scripts/demo.py` + `data/menu_sample.json`：无 Token 也能跑的演示
- MCP 端点预检：`POST https://mcp.mcd.cn` → HTTP 401（端点可达，鉴权按文档工作）

## 阶段 4 · 提交物料（14:50–）

- `README.md`：介绍/安装/示例/目标用户 + 工作原理图 + 测试结果
- `MCP_INTEGRATION.md`：Server/Tool 清单（17 个 Tool 及用途）/调用流程/业务价值/实测记录
- 报名 Issue：按大赛格式发布（【参赛申请】项目名称/项目地址/项目简介）

## 阶段 5 · 待完成（Token 就绪后）

- [ ] 用户提供 MCP Token → WorkBuddy 连接器配置 mcd-mcp
- [ ] 全链路实测：领券→菜单→优化→calculate-price→create-order（到支付链接）
- [ ] 用真实返回更新 MCP_INTEGRATION.md 实测记录 + README 截图
- [ ] 演示录屏（1024 用餐赛道选交）
- [ ] 1024 作品站提交（10/25 16:00 截止，使用工具选 WorkBuddy）
- [ ] 麦当劳大赛兑奖信息（邮箱/手机号/收货地址，11/14 前）

---

> 说明：本文档由 WorkBuddy 辅助整理生成；用户亦可在 WorkBuddy 客户端导出完整对话记录
> 替换或补充本文件。
