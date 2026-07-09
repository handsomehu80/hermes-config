# 1+N Digital Company — Hermes Integration USAGE

> 把 `D:\onboarding\` 的 `.claude/` 数字员工包,适配到 Hermes 体系里。
> 原始包给 Claude Code 用户用 slash command;本版本给 Hermes CLI 用户用 bash + Skill。

## 安装状态

| 组件 | 路径 | 状态 |
|---|---|---|
| Skill 主体 | `~/AppData/Local/hermes/skills/productivity/oneplusn/SKILL.md` | ✓ 已识别 (hermes skills list) |
| 4 个 Python 脚本 | `~/AppData/Local/hermes/skills/productivity/oneplusn/scripts/` | ✓ 已部署 |
| 8 个原始 command 文档 | `~/AppData/Local/hermes/skills/productivity/oneplusn/commands_oneplusn/` | ✓ 已归档(供深度参考) |
| 3 个原 skill 文档 | `~/AppData/Local/hermes/skills/productivity/oneplusn/references_{org,agent,upgrade}/` | ✓ 已归档 |
| 主 CLI | `~/AppData/Local/hermes/bin/oneplusn` | ✓ 可执行 |
| 7 个子命令 CLI | `~/AppData/Local/hermes/bin/oneplusn-{init,add,upgrade,status,edit,sync,delete}` | ✓ 软链接(实为复制) |
| 轮询 cron 脚本 | `~/AppData/Local/hermes/scripts/oneplusn-poll.sh` | ✓ 已部署 |
| 示例 cron job | `hermes cron list` 显示 | ✓ 86b8494a910d |

## 三种调用方式(任选其一)

### A) Hermes-CLI 风格(推荐)

```bash
oneplusn                                          # 帮助
oneplusn deps                                     # 检查依赖
oneplusn status --work-dir ~/my-team
oneplusn init --work-dir ~/my-team
oneplusn add --work-dir ~/my-team --role developer --name dev-01
oneplusn upgrade --work-dir ~/my-team --name dev-01 --modules hindsight,search
oneplusn edit --work-dir ~/my-team --name dev-01 --field gateway_port --value 8104
oneplusn sync --work-dir ~/my-team
oneplusn delete --work-dir ~/my-team --name dev-01 --keep-github
```

### B) Unix 软链接风格

```bash
oneplusn-init                                     # 等价于 oneplusn init
oneplusn-add                                      # 等价于 oneplusn add ...
oneplusn-status ~/my-team                         # 不需要 --work-dir
oneplusn-upgrade ~/my-team dev-01 hindsight,search
```

### C) 让 Hermes 加载 Skill 后告诉你

在 chat 里说:
- "跑 oneplusn init"
- "加一个数字员工"
- "/oneplusn:status"

Hermes 会:
1. 自动加载 `oneplusn` skill
2. 在上下文里显示 SKILL.md 的"如何执行"段
3. 按 bash 包装的形式去执行

## 跟原始 `.claude/` 包的差异

| 维度 | 原始 | 本集成 |
|---|---|---|
| 调用方式 | Claude Code slash command | Hermes CLI bash 命令 |
| 触发上下文 | 由 Claude Code 注入 | 由 Skill 匹配 / 用户直接敲命令 |
| 脚本位置 | `D:\onboarding\.claude\skills\…\scripts\` | `~/AppData/Local/hermes/skills\…\scripts\` |
| 路径查找 | 写死 `python3` | 改用 `python`(避 Windows Store 假短路) |
| gh 必需性 | README 标"推荐" | 改"必须"(实际跑通需要它) |
| 邮箱/用户名校验 | 无 | 加了基础格式校验 |
| 轮询调度 | 原生 crontab | `hermes cron` 系统 |
| 状态展示 | onboard_agent 借调 | 独立 Python 解析,更简洁 |

## 已修的 bug(对照原 README)

1. **create_org.py 依赖探测**:`python3 --version` 改成 `python -c "import sys; print(sys.version_info[0], sys.version_info[1])"`,识别 Microsoft Store 假短路
2. **gh 标"必须"**:`README` 没说,但 RULES 6 铁律 + cron 都靠它
3. **邮箱/用户名格式校验**:`ask_email()` / `ask_username()` 加了最小校验
4. **轮询 cron 路径**:`/tmp/issues-X.json` 改在 Hermes 体系下,自动 register 到 `hermes cron list`

## 实际可跑通的流程(可演示)

```bash
# 1. 装 gh(一次性)
winget install GitHub.cli    # Windows
brew install gh              # macOS

# 2. 装 pyyaml(在 hermes-agent venv)
python -m pip install pyyaml

# 3. 验证依赖
oneplusn deps
# ✓ hermes    已安装
# ✓ python    已安装  3 11
# ✓ git       已安装
# ✓ gh        已安装
# ✓ PyYAML    已安装  6.0.3

# 4. 真创建一个团队
mkdir ~/my-team
# (在浏览器注册 GitHub Org / 创建 token — 这一步必须人工)
oneplusn init --work-dir ~/my-team
# ... 按引导走 5 步 ...

# 5. 加员工
oneplusn add --work-dir ~/my-team --role developer --name dev-01
# ... 选 GitHub 账号(已有 / + alias 邮箱 / 引导注册)...

# 6. 升级能力
oneplusn upgrade --work-dir ~/my-team --name dev-01 --modules hindsight,search

# 7. 启动轮询(每 30 分钟)
#    在 Hermes chat 里:
/cron
> 每 30 分钟,跑 oneplusn-poll.sh dev-01 oneplusn-team agent_workflow

# 或者手动注册:
hermes cron create "30m" \
    --name "oneplusn-poll-dev01" \
    --script "oneplusn-poll.sh" \
    --workdir "~/my-team" \
    --no-agent
```

## 已知问题 / 待优化

1. **SOUL.md 仍从 `jnMetaCode/agency-agents-zh` 拉取**,没本地缓存。如果该仓库被删,onboarding 失败
2. **任务回收机制缺失**:员工 A 领任务后崩溃,该 issue 永远挂着。`oneplusn-poll.sh` 没做扫死任务逻辑
3. **`oneplusn sync` 没完整实现**:只重写 handoff.yaml,没真的重生成 README 推 GitHub(见 `commands_oneplusn/sync.md` 原始指令)
4. **`oneplusn edit` / `delete` 是 stub**:手改 handoff.yaml 即可,后续用 Python 完善
5. **commit 链路是空的**:config-backup 排除了 `.env`,但 `handoff.yaml` 含 token,初始化时没自动加 `.gitignore` — 需 PR 改 onboard_agent.py
6. **轮询脚本只在 cron tick 时跑**,没"硬实时"通道。紧急任务 30 分钟延迟

## 跟我已有的 Hermes Kanban 团队怎么选

| 场景 | 用 Kanban 团队 | 用 oneplusn 1+N |
|---|---|---|
| 跨主机的 agent 团队 | ✗ (本地 profiles) | ✓ (GitHub Issues 当总线) |
| 你想自己看代码 + 调试 | ✓ (本地 kanban.db) | ✗ (在 GitHub 远端) |
| 异步客户协作 | ✗ (没客户触点) | ✓ (Issue 评论即接口) |
| 跑通就能用,门槛低 | ✓ (本地 30min) | ✗ (要 GitHub Org + 员工账号 1h) |
| 多 agent 并发跑 cron | ✗ (串行 dispatcher) | ✓ (每员工独立 cron) |

**最佳实践**:用 oneplusn 做对外协作(GitHub Issues = 客户/老板面板),用 Kanban 团队做对内研发流水线。两个可以同时跑,各管各的。

## 下一步建议(按收益排序)

1. **实现 `oneplusn sync` 的 README 重生成 + git push**(2h)
2. **加 SOUL.md 本地缓存**(2h)
3. **加 task-reaper cronjob**(1h)
4. **加 .gitignore 自动加 handoff.yaml + agents/*/.env**(1h)
5. **写 evals**(对照 references/evals.md 原文,做自动验收脚本)(3h)
