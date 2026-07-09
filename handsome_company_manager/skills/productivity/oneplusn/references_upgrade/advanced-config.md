# 数字员工高级配置

数字员工基础配置完成后的进阶配置，用于将 Agent 升级为具备搜索能力、语音交互、记忆增强的"超级员工"。

> **Agent 框架支持**：目前以下配置仅适用于 **Hermes Agent**。
> 未来将增加对 **OpenClaw**、**Claude Code**、**Cursor Agent** 等框架的支持，请关注版本更新。

## 配置概览

```
基础配置（上岗阶段）     高级配置（本文档）
├─ Profile 创建          ├─ Hindsight 记忆增强
├─ GitHub 绑定           ├─ 感知工具（搜索）
├─ 灵魂注入              ├─ 语音（STT/TTS）
├─ README 入职           └─ 效率优化
├─ Gateway 启动
└─ 定时任务
```

## 前置条件

- 已完成数字员工基础配置（Profile + Gateway 正常运行）
- Python 3.11+
- `uv` 包管理器：
  - macOS/Linux: `curl -LsSf https://astral.sh/uv/install.sh | sh`
  - Windows: `powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`
- Hermes Agent 已安装

---

## 1. Hindsight 记忆系统（local embedded 模式）

增强数字员工的长期记忆能力，使其能够回忆历史经验、提取可复用模式。

### 安装

```bash
# macOS/Linux
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python hindsight-all

# Windows
uv pip install --python "$env:USERPROFILE\.hermes\hermes-agent\venv\Scripts\python.exe" hindsight-all
```

### 配置

创建 `~/.hermes/hindsight/config.json`：

```json
{
  "mode": "local_embedded",
  "llm_provider": "openai_compatible",
  "llm_base_url": "https://api.deepseek.com/v1",
  "llm_model": "deepseek-v4-flash",
  "bank_id": "hermes",
  "recall_budget": "mid",
  "timeout": 120,
  "idle_timeout": 300
}
```

### 设置 API Key

```bash
echo "HINDSIGHT_LLM_API_KEY=你的DeepSeekKey" >> ~/.hermes/.env
echo "HINDSIGHT_API_KEY=local-embedded-mode" >> ~/.hermes/.env
```

### 启用

```bash
hermes config set memory.provider hindsight
hermes gateway restart
hermes memory status
# 预期: Provider: hindsight, Status: available ✓
```

---

## 2. 感知工具（搜索能力）

赋予数字员工搜索网络信息的能力。

### DuckDuckGo（免费备用）

```bash
# macOS/Linux
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python ddgs
cp -r ~/.hermes/hermes-agent/optional-skills/research/duckduckgo-search ~/.hermes/skills/

# Windows
xcopy /E /I "$env:USERPROFILE\.hermes\hermes-agent\optional-skills\research\duckduckgo-search" "$env:USERPROFILE\.hermes\skills\duckduckgo-search"
```

### Tavily（搜索+抓取+爬取）

```bash
# 1. 注册获取 Key: https://app.tavily.com
# 2. 配置
echo "TAVILY_API_KEY=tvly-dev-你的Key" >> ~/.hermes/.env
hermes config set web.backend tavily
hermes config set web.search_backend tavily
hermes config set web.extract_backend tavily

hermes gateway restart
```

---

## 3. 语音交互

使数字员工支持语音输入和输出。

### 安装

```bash
# macOS/Linux
uv pip install --python ~/.hermes/hermes-agent/venv/bin/python faster-whisper edge-tts

# Windows
uv pip install --python "$env:USERPROFILE\.hermes\hermes-agent\venv\Scripts\python.exe" faster-whisper edge-tts
```

### 配置

编辑 `config.yaml`：

```yaml
stt:
  enabled: true
  provider: local

tts:
  provider: edge
  edge:
    voice: zh-CN-XiaoxiaoNeural  # 中文女声
```

```bash
hermes gateway restart
```

---

## 4. 效率优化

### 成本显示

```bash
hermes config set display.show_cost true
# 使用 /usage 查看 Token 用量
```

### 对话压缩

编辑 `config.yaml`：

```yaml
compression:
  enabled: true
  threshold: 0.5
  target_ratio: 0.2
```

### Curator 自我进化

```yaml
curator:
  enabled: true
  interval_hours: 168  # 每周一次技能进化
```

```bash
# 查看状态
hermes curator status
hermes insights --days 7
```

---

## 验证清单

```bash
# 1. 记忆系统
hermes memory status

# 2. 搜索能力
# 对 Agent 说: "搜索最新 AI 新闻"

# 3. 语音（CLI 中）
# hermes
# /voice on
# 说话测试

# 4. 效率
hermes insights --days 7
```

---

## 依赖总览

| 组件 | 包 | 安装位置 | 用途 |
|------|-----|---------|------|
| Hindsight | hindsight-all | Hermes venv | 长期记忆增强 |
| DDGS | ddgs | Hermes venv | 免费搜索 |
| STT | faster-whisper | Hermes venv | 语音转文字 |
| TTS | edge-tts | Hermes venv | 文字转语音 |
| Tavily | 无（API） | 远程调用 | 高级搜索 |
| Curator | 内置 | 内置 | 技能自我进化 |
| Compression | 内置 | 内置 | 对话压缩省 token |

---

## 故障排查

| 问题 | 解决 |
|------|------|
| Hindsight not available | 检查 hindsight-all 是否装到 Hermes venv |
| 搜索无结果 | 检查 TAVILY_API_KEY 是否正确 |
| 语音不工作 | 检查 faster-whisper 和 edge-tts 是否安装 |
| DDGS 不可用 | `uv pip install --python <hermes-venv-python> --reinstall ddgs` |
| Windows BOM 报错 | 不要用记事本编辑 config.yaml，用 VS Code 或 `hermes config edit` |