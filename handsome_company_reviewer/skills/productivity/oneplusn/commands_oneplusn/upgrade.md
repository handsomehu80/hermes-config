# /oneplusn:upgrade — 升级数字员工能力

<task>
升级已有数字员工的高级能力。加载 oneplusn-agent-upgrade skill，为员工开启 Hindsight 记忆、搜索感知、语音交互、效率优化等增强功能。
</task>

<context>
## 升级模块说明

| 模块 | 说明 | 默认 |
|------|------|------|
| `hindsight` | Hindsight 记忆系统 — 从错误中学习，避免重复犯错 | ✅ 开启 |
| `search` | 搜索感知增强 — 自动识别需要搜索的任务，调用搜索工具 | ✅ 开启 |
| `voice` | 语音交互 — 支持语音输入/输出（需配置语音服务） | ❌ 手动 |
| `efficiency` | 效率优化 — 任务预判、批量处理、快捷键 | ❌ 手动 |

## 前置要求

- 已完成 `/oneplusn:init`，存在 `{org-name}/handoff.yaml`
- 已加载 oneplusn-agent-upgrade skill

## 参数

`$ARGUMENTS` — 可选，格式：`--work-dir <目录> --name <员工名> --modules <模块列表>`

如果未提供参数，进入交互式引导。
</context>

<instructions>
## 步骤 1：定位工作目录

如果 `$ARGUMENTS` 包含 `--work-dir`，直接使用。
否则交互式询问：列出当前目录下包含 `handoff.yaml` 的候选文件夹。

检查 `handoff.yaml` 是否存在，不存在则提示先运行 `/oneplusn:init`。

## 步骤 2：选择升级对象

读取 handoff.yaml 中的 agents 列表，展示：

```
可升级的数字员工：
  1. dev-01 (developer) [hermes] 当前模块: hindsight,search
  2. rev-01 (reviewer) [hermes] 当前模块: hindsight
  3. pm-01 (project-manager) [hermes] 当前模块: (无)
```

如果 `$ARGUMENTS` 包含 `--name`，直接指定该员工。
如果 `--all`，批量升级所有员工。

询问："要升级哪个员工？"（输入编号或名字）

## 步骤 3：选择升级模块

展示该员工当前已开启的模块和可选模块：

```
dev-01 当前已开启: hindsight,search

可选模块：
  [✓] hindsight — Hindsight 记忆系统（已开启）
  [✓] search — 搜索感知增强（已开启）
  [ ] voice — 语音交互
  [ ] efficiency — 效率优化

选择要开启/关闭的模块（输入编号，空格分隔，已开启的会关闭）：
```

如果 `$ARGUMENTS` 包含 `--modules`，直接使用（如 `--modules hindsight,search,voice`）。

## 步骤 4：执行升级（调用 upgrade_agent.py）

```bash
python3 scripts/upgrade_agent.py --handoff {work-dir}/handoff.yaml --name {agent-name} --modules {modules}
```

### 各模块配置详情

#### hindsight 模块

配置内容（写入 agent 的 config）：
```yaml
hindsight:
  enabled: true
  max_memories: 100
  auto_reflect: true          # 任务完成后自动反思
  reflection_trigger: "on_error" # 触发条件: always / on_error / manual
  learning_mode: "incremental"   # 学习方式: incremental / batch
```

#### search 模块

配置内容：
```yaml
search:
  enabled: true
  auto_detect: true           # 自动识别需要搜索的任务
  search_tools:
    - web_search
    - code_search
    - doc_search
  max_results: 10
  cache_duration: 3600        # 搜索结果缓存 1 小时
```

#### voice 模块

配置内容：
```yaml
voice:
  enabled: true
  input: true                 # 语音输入
  output: true                # 语音输出
  language: "zh-CN"
  wake_word: "hey {name}"     # 唤醒词
```

提示：语音模块需要额外配置语音服务 API Key，询问用户是否已配置。

#### efficiency 模块

配置内容：
```yaml
efficiency:
  enabled: true
  task_prediction: true       # 任务预判
  batch_processing: true      # 批量处理相似任务
  shortcuts: true             # 快捷键支持
  auto_label: true            # 自动打标签
```

## 步骤 5：更新 handoff.yaml

记录升级后的模块：
```yaml
agents:
  dev-01:
    # ... 原有字段
    upgrade_modules:
      - hindsight
      - search
      - voice
    upgraded_at: 2026-06-04T14:00:00
```

更新 `metadata.updated_at`。

## 步骤 6：重启 Gateway（如需要）

如果该员工的 Gateway 正在运行，提示重启以应用新配置：

```bash
hermes profile use {name}
hermes gateway restart
```

## 输出

```
[✓] dev-01 升级完成
    已开启模块: hindsight, search, voice
    配置已写入: {work-dir}/agents/dev-01/config.yaml
    
    [⚠] voice 模块需要语音服务 API Key
          请在配置文件中设置: voice.api_key
    
    [→] 重启 Gateway 以应用: hermes gateway restart
```
</instructions>

<output_format>
- 每步操作前输出 `[→] 步骤说明`
- 成功用 `[✓]`，警告用 `[⚠]`，需要用户操作 `[✎]`
- 模块状态用 `[✓]` 开启 `[ ]` 关闭
</output_format>

<example>
用户输入：/oneplusn:upgrade --work-dir oneplusn-team/ --name dev-01 --modules hindsight,search,voice

输出：
[→] 工作目录: oneplusn-team/
[✓] 找到 dev-01，当前模块: hindsight,search
[→] 升级模块: +voice
[✓] hindsight 已配置
[✓] search 已配置
[✓] voice 已配置
[⚠] voice 需要语音 API Key
[✓] handoff.yaml 已更新
[✓] 升级完成
</example>

<human_review_needed>
- [ ] voice 模块的语音服务 API Key 是否已配置
- [ ] 升级后是否需要重启 Gateway
- [ ] 批量升级时是否会影响正在运行的任务
</human_review_needed>
