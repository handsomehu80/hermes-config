# /oneplusn:status — 查看数字员工状态

<task>
查看 1+N 数字员工团队的完整状态，包括所有员工的角色、Agent类型、Gateway端口、升级模块等信息。
</task>

<context>
## 使用场景

- 日常巡检，确认所有员工正常工作
- 排查问题（谁没启动？端口冲突？）
- 查看团队整体配置

## 参数

`$ARGUMENTS` — 可选，`--work-dir <目录>`

如果未提供，自动查找当前目录下的 handoff.yaml。
</context>

<instructions>
## 步骤 1：定位 handoff.yaml

如果 `$ARGUMENTS` 包含 `--work-dir`，使用该目录下的 `handoff.yaml`。
否则在当前目录及子目录中搜索 `handoff.yaml`，找到后使用。
如果找不到，提示："未找到 handoff.yaml，请先运行 /oneplusn:init"

## 步骤 2：读取并展示状态

读取 `handoff.yaml`，输出格式化的状态表格：

```
============================================================
  📊 1+N 数字员工团队状态
============================================================

🏢 Organization: {org-name}
📦 仓库: {repo-name}
👤 老板: {boss-username}
📅 创建: {created_at} | 更新: {updated_at}

------------------------------------------------------------
  员工状态
------------------------------------------------------------

  {名字:<16} {角色:<18} {Agent:<12} {端口:<8} {模块:<20} {状态}
  ---------------- ------ ---------- ----- ------------------ ------
  dev-01           developer        hermes     8100    hindsight,search   ✅ active
  rev-01           reviewer         hermes     8101    hindsight          ✅ active
  pm-01            project-manager  hermes     8102    (基础)             ⏸️ paused
  sec-01           security-engineer hermes    8103    hindsight,search   ✅ active

  总计: 4 个员工 | ✅ 3 活跃 | ⏸️ 1 暂停

------------------------------------------------------------
  协作链路
------------------------------------------------------------

  任务流转: 老板创建 Issue → PM 分派 → 开发执行 → 审查验证 → 老板终审 → 关闭
  
  当前规则文件: {work-dir}/rules.md
  团队 README: {work-dir}/README.md
  handoff 配置: {work-dir}/handoff.yaml

============================================================
```

## 步骤 3：健康检查（可选）

如果用户输入 `--health` 或 `--check`，额外执行：

1. **Gateway 检测**：检查每个活跃员工的 Gateway 是否可连接
   ```
   dev-01: Gateway port 8100 ... ✅ 响应正常
   rev-01: Gateway port 8101 ... ⚠️ 无响应
   ```

2. **GitHub 账号检测**：验证每个员工的 GitHub 账号是否可访问
   ```
   dev-01: GitHub @myteam-dev-01 ... ✅ 正常
   ```

3. **Cron 状态**：检查定时任务是否配置
   ```
   dev-01: Cron (*/30 * * * *) ... ✅ 已配置
   ```

## 步骤 4：输出建议

根据状态给出建议：

```
💡 建议：
  1. rev-01 Gateway 无响应，建议检查: ./{work-dir}/agents/rev-01/start.sh
  2. pm-01 已暂停，如需恢复: /oneplusn:edit --work-dir {work-dir} --name pm-01
```
</instructions>

<output_format>
- 表格对齐，便于阅读
- 状态图标：✅ active / ⏸️ paused / ❌ error
- 模块用逗号分隔，基础配置显示 "(基础)"
</output_format>
