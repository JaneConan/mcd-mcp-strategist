# 使用说明 · 麦门军师

> 三种玩法，从 30 秒体验到完整能力。

## 玩法 A：零门槛演示（无需 MCP Token，30 秒）

```bash
git clone https://github.com/JaneConan/mcd-mcp-strategist.git
cd mcd-mcp-strategist
python3 scripts/demo.py
```

输出示例（内置示例数据）：

```
🧙 麦门军师上线。需求：2 人用餐，预算 80 元（示例数据）

【最便宜】
  锦囊1: 麦香鸡x2 + 可口可乐(小)x2
    原价 ¥39.00 | 券减 ¥10.00 | 实付 ¥29.00 | 1080 kcal | 用券: 麦麦省·满39减10
...
🏆 麦门段位: 麦门道友（省下 ¥10.00，约等于多吃 0.8 个麦香鸡）
```

跑测试：

```bash
python3 tests/test_meal_optimizer.py   # Ran 10 tests — OK
```

## 玩法 B：完整能力（需麦当劳 MCP Token）

1. **申请 Token**：[open.mcd.cn/mcp](https://open.mcd.cn/mcp) → 手机号登录 →
   「控制台」→「激活」→ 复制
2. **配置 MCP**（WorkBuddy）：连接器 → 自定义连接器 → 配置 MCP：

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

3. **端到端跑通**（脚本内含 MCP 直连探针，自动拉真实菜单/券并官方核价）：

   ```bash
   python3 scripts/mcp_pipeline.py --store 1980321 --budget 80 --people 2
   ```

   输出四个视角的锦囊：最便宜 / 最大优惠 / 最性价比 / 最贴近预算，
   并以麦当劳官方 `calculate-price` 核价校验（实测完全一致）。

4. **在 WorkBuddy 里当 Skill 用**：把本仓库放入
   `~/.workbuddy/skills/mcd-mcp-strategist/`，然后直接说：

   > "用麦门军师帮我规划今天的麦当劳，2 个人 80 块，南开大悦城附近"

   Skill 会按 SKILL.md 的 8 步工作流自动调用 mcd-mcp 工具。

## 玩法 C：作为 WorkBuddy Skill 嵌入日常

典型对话：

```
你：    军师，今晚 3 个人 150 块吃麦当劳，外送到公司
军师：  📍 定位到 3 家可配送门店 → 🍔 拉取菜单 113 款 →
        🎫 麦麦省自动领券 → 🧮 优化 2000+ 组合 →
        【最大优惠】三件套券后立省 24.1 元……官方核价一致 ✅
你：    就这个，下单
军师：  （经你确认后）create-order → 支付链接 → 你扫码支付
```

## 常见问题

| 问题 | 处理 |
|---|---|
| 401 Token 无效 | 去 open.mcd.cn/mcp 重新激活 |
| 429 限流 | 单 Token 600 次/分钟，脚本已控制节奏；稍等重试 |
| "暂无可领取" | 麦麦省券已领过，幂等正常 |
| 券显示可用但用不了 | 未到生效日期，流水线按有效期自动过滤 |
| 引擎价与官方价不一致 | 以官方 `calculate-price` 为准（设计如此） |

## 安全边界

- 下单、支付、抽奖等花用户钱/积分的动作，**必须用户明确确认后才执行**；
- 脚本与仓库中不出现任何真实 Token（`mcp.json` 已在 .gitignore）；
- 营养与价格数据仅供参考，以麦当劳官方实时结果为准。
