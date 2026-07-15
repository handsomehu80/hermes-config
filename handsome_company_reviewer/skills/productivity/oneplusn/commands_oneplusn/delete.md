# /oneplusn:delete — 删除/停用数字员工

<task>
从团队中移除数字员工。可选：停用 Gateway、保留 GitHub 账号、备份配置。
</task>

<context>
## 使用场景

- 员工不再需要（项目结束）
- 替换员工（重新创建）
- 临时停用（保留配置，后续恢复）

## 参数

`$ARGUMENTS` — 可选，`--work-dir <目录> --name <员工名> --keep-profile --keep-github`

- `--keep-profile`：保留 Hermes Profile，不删除
- `--keep-github`：保留 GitHub 账号，不解绑
</context>

<instructions>
## 步骤 1：选择员工

读取 handoff.yaml，列出所有员工：
```
已上岗的数字员工：
  1. dev-01 (developer) [hermes]
  2. rev-01 (reviewer) [hermes]
  3. pm-01 (project-manager) [hermes]
```

如果 `$ARGUMENTS` 有 `--name`，直接使用。否则交互式询问。

## 步骤 2：确认信息

展示该员工的完整信息：
```
将要删除: dev-01
  角色: developer
  GitHub: @myteam-dev-01
  Agent: Hermes
  Profile: dev-01
  Gateway: port 8100
  模块: hindsight,search
  上岗时间: 2026-06-04
```

询问："确认删除 dev-01？（y/n）" → n 则取消

## 步骤 3：选择删除范围

询问（多选）：
```
删除范围：
  [✓] 从 handoff.yaml 移除记录
  [✓] 停用 Gateway（如果运行中）
  [ ] 删除 Hermes Profile（不可逆）
  [ ] 删除 GitHub 账号关联（保留账号本身）
  [ ] 删除本地配置目录（{work-dir}/agents/dev-01/）
  [✓] 同步更新 README
```

如果带有 `--keep-profile`，默认不勾选删除 Profile。
如果带有 `--keep-github`，默认不勾选删除 GitHub 关联。

## 步骤 4：执行删除

按选项执行：
1. 从 handoff.yaml 移除 `agents.dev-01`
2. 如果 Gateway 运行中：`hermes profile use dev-01 && hermes gateway stop`
3. 如果选删除 Profile：`hermes profile remove dev-01`
4. 如果选删除本地目录：`rm -rf {work-dir}/agents/dev-01/`

## 步骤 5：更新 README

如果勾选同步，重新生成 README.md 并提交。

## 输出

```
[✓] dev-01 已从团队移除
    已执行：
      - handoff.yaml 已更新
      - Gateway 已停用
      - README 已同步
    
    如需重新上岗：/oneplusn:add --work-dir {work-dir}/
```
</instructions>

<output_format>
- 删除前展示完整信息，让用户二次确认
- 列出已执行的操作清单
- 提示如何恢复
</output_format>
