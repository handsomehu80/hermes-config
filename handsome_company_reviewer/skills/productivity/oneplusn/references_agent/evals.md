# 评估测试规范

单数字员工上岗的测试套件。每次上岗后运行，验证该 Agent 是否配置正确。

## 测试分类

| 分类 | 测试数 | 说明 |
|------|-------|------|
| Profile 隔离 | 3 | Profile 创建、配置独立、目录结构 |
| GitHub 绑定 | 3 | Token 有效、API 访问、组织成员 |
| 灵魂注入 | 2 | SOUL.md 存在、角色认知 |
| Gateway | 2 | 进程运行、端口绑定 |
| README 入职 | 2 | README 加载、角色确认 |
| 定时任务 | 2 | 任务注册、格式有效 |
| 记忆操作 | 2 | 记忆写入、记忆检索 |

**总计：16 个测试用例**

---

## Profile 隔离

### PI-01: Profile 创建
**类型**: 自动

```bash
hermes profile create {name} --clone
hermes profile list | grep {name}
```

**期望**: Profile 出现在列表中

---

### PI-02: 配置独立性
**类型**: 自动

```bash
# 检查 .env 存在且内容正确
cat ~/.hermes/profiles/{name}/.env | grep GITHUB_USERNAME
```

**期望**: 包含正确的用户名和 Token

---

### PI-03: 目录结构完整
**类型**: 自动

```bash
ls ~/.hermes/profiles/{name}/
```

**期望**: 包含 config.yaml、.env、SOUL.md

---

## GitHub 绑定

### GA-01: Token 有效
**类型**: 自动

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/user | jq -r '.login'
```

**期望**: 返回正确的用户名

---

### GA-02: 仓库访问
**类型**: 自动

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/repos/{org}/{repo}
```

**期望**: HTTP 200

---

### GA-03: 组织成员
**类型**: 自动

```bash
curl -s -H "Authorization: token $TOKEN" https://api.github.com/orgs/{org}/members | grep {username}
```

**期望**: 用户名在成员列表中

---

## 灵魂注入

### SP-01: SOUL.md 存在
**类型**: 自动

```bash
test -f ~/.hermes/profiles/{name}/SOUL.md && test $(stat -c%s ~/.hermes/profiles/{name}/SOUL.md) -gt 100
```

**期望**: 文件存在且大于 100 字节

---

### SP-02: 角色认知
**类型**: 手动

**步骤**: 问 Agent "你的角色和核心技能是什么？"

**期望**: 准确回答配置的角色和对应技能

---

## Gateway

### GW-01: 进程运行
**类型**: 自动

```bash
hermes gateway status | grep running
```

**期望**: 显示 running 状态

---

### GW-02: 端口绑定
**类型**: 自动

```bash
lsof -i :{port} | grep hermes
```

**期望**: 端口被 hermes 进程占用

---

## README 入职

### RO-01: README 加载确认
**类型**: 手动

**步骤**: 问 Agent "团队的工作流程是什么？"

**期望**: 能描述 README 中的协作协议

---

### RO-02: 角色确认
**类型**: 手动

**步骤**: 问 Agent "你的角色是什么？向谁汇报？"

**期望**: 准确回答自己的角色和汇报对象（老板）

---

## 定时任务

### CE-01: 任务注册
**类型**: 自动

```bash
hermes cron list | grep task-polling
```

**期望**: 显示已注册的定时任务

---

### CE-02: 调度格式
**类型**: 自动

```bash
hermes cron list | grep "\*/30 \* \* \* \*"
```

**期望**: Cron 表达式格式正确

---

## 记忆操作

### MO-01: 记忆写入
**类型**: 手动

**步骤**:
1. 告诉 Agent "请记住：我们使用 Python 3.11"
2. 稍后问 "我们用什么 Python 版本？"

**期望**: 正确回答 "Python 3.11"

---

### MO-02: 上下文保留
**类型**: 手动

**步骤**: 重启 Gateway 后问 "你之前的任务是什么？"

**期望**: 能回忆之前的任务

---

## 运行测试

### 全部测试

```bash
python3 scripts/onboard_agent.py --handoff handoff.yaml --name {name} --test
```

### 单独测试

```bash
# Profile 测试
python3 scripts/onboard_agent.py --handoff handoff.yaml --name {name} --test profile

# GitHub 测试
python3 scripts/onboard_agent.py --handoff handoff.yaml --name {name} --test github

# 手动测试
python3 scripts/onboard_agent.py --handoff handoff.yaml --name {name} --test manual
```

### 结果判定

| 通过率 | 状态 |
|--------|------|
| 100% | 上岗完成 |
| >= 85% | 基本可用，需修复失败项 |
| < 85% | 不可用，需排查问题 |