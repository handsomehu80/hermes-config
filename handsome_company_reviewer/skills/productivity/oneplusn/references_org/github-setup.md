# GitHub 基础设施搭建详细指南

子公司创建阶段的手动操作步骤，仅包括老板本人 + Organization + 仓库的创建。

## 目录

1. [注册老板 163 邮箱](#11-注册老板-163-邮箱)
2. [创建老板 GitHub 账号](#12-创建老板-github-账号)
3. [创建 GitHub Organization](#13-创建-github-organization)
4. [创建和配置仓库](#14-创建和配置仓库)
5. [生成老板 Token](#15-生成老板-token)

---

## 1.1 注册老板 163 邮箱

老板需要一个专用邮箱来注册 GitHub 和管理组织。

### 前置条件

- 一个可用的手机号码（接收验证码）
- 建议邮箱格式：`{前缀}_boss@163.com`（如 `oneplusn_boss@163.com`）

### 注册步骤

```
1. 打开浏览器，访问 https://mail.163.com/
2. 点击页面上的"注册新账号"按钮
3. 选择"注册字母邮箱"（推荐，更专业）
4. 填写邮箱地址（如：oneplusn_boss）
5. 设置强密码（12位以上，含大小写+数字+符号）
6. 确认密码
7. 输入手机号码 → 点击"获取验证码"
8. 输入短信验证码
9. 勾选同意服务条款
10. 点击"立即注册"
11. 注册成功后记录：邮箱地址、密码
```

### 邮箱基础设置

注册后登录进行设置：

```
1. 登录 https://mail.163.com/
2. 进入"设置" → "常规设置"
3. 配置：
   - 时区：GMT+8 北京
   - 每页显示：50 封
   - 自动回复：关闭
4. 保存设置
```

---

## 1.2 创建老板 GitHub 账号

老板账号将作为 Organization 的所有者（Owner）。

### 创建步骤

```
1. 打开浏览器无痕模式，访问 https://github.com/signup
   （无痕模式避免与已有 GitHub 会话冲突）
2. 输入老板的 163 邮箱地址
3. 点击"Continue"
4. 创建密码（建议与邮箱密码不同）
5. 设置用户名（Username）：
   - 建议格式：{前缀}-boss（如 oneplusn-boss）
   - 用户名全局唯一，如被占用可加数字后缀
6. 选择"不接收产品更新邮件"
7. 完成人机验证（CAPTCHA）
8. 点击"创建账户"
9. 到 163 邮箱查收验证邮件 → 点击验证链接
10. 选择账户类型 → "个人"
11. 跳过所有个性化问题（连续点跳过）
12. 进入 GitHub 首页
```

### 完善个人资料

```
1. 点击右上角头像 → Settings（设置）
2. Profile（个人资料）：
   - Name：填写你的名字（或保持匿名）
   - Bio：1+N 数字员工团队 · Owner
   - Company：暂时留空（创建组织后自动填充）
   - Location：可留空
3. Account settings：
   - 确认邮箱已验证（显示绿色对勾）
4. 保存更改
```

### 老板信息记录

| 项目 | 内容 |
|------|------|
| GitHub 用户名 | |
| 163 邮箱 | |
| 密码 | |
| 创建状态 | |

---

## 1.3 创建 GitHub Organization

### 创建流程

```
1. 确保用老板账号登录 GitHub
2. 点击右上角头像
3. 在下拉菜单选择"Your organizations"（你的组织）
4. 点击"New organization"（新建组织）
5. 选择"Create a free organization"（创建免费组织）
6. 填写信息：
   
   步骤 1/3 - Organization name：
   - 输入组织名称（如：oneplusn-team）
   - 全局唯一，如被占用系统会提示
   - 只能包含字母、数字、连字符
   
   Contact email：
   - 输入老板的 163 邮箱
   
   Organization belongs to：
   - 选择"My personal account"
   
   步骤 2/3 - 跳过添加成员（后续阶段手动添加）
   步骤 3/3 - 完成创建
7. 进入组织页面
```

### 组织基础设置

```
1. 组织页面 → Settings（右侧标签）
2. General（常规）：
   - Description：1+N 数字员工协作团队
   - Website：可留空或填项目主页
   - Email：老板 163 邮箱
   - 启用 Issues ✓
   - 启用 Projects ✓
   - 启用 Wiki ✓
   
3. Member privileges（成员权限）：
   - Base permissions：Read（读取）
   - Repository creation：None（只有 Owner 能创建）
   - Repository forking：允许 ✓
   - Pages creation：Disabled
   
4. 保存所有更改
```

---

## 1.4 创建和配置仓库

### 创建主仓库

```
1. 组织页面 → Repositories → New
2. 填写仓库信息：
   - Repository name：agent_workflow
   - Description：团队协作文档和工作流
   - Visibility：Private（私有）
   - Initialize with README：✓ 勾选
   - .gitignore：选择适合的技术栈
   - License：选择 MIT 或其他
3. 点击"Create repository"
4. 记录仓库地址：https://github.com/{组织名}/agent_workflow
```

### 创建标签体系

```
仓库 → Issues → Labels → New label，逐个创建：

状态标签：
- status:todo       颜色 #EDEDED（灰色）
- status:in-progress 颜色 #FEF2C0（黄色）
- status:review     颜色 #C5DEF5（蓝色）
- status:done       颜色 #0E8A16（绿色）
- status:blocked    颜色 #D93F0B（红色）

优先级标签：
- priority:P1       颜色 #B60205（红色 - 紧急）
- priority:P2       颜色 #FBCA04（黄色 - 重要）
- priority:P3       颜色 #0E8A16（绿色 - 一般）

类型标签：
- type:feat         颜色 #84B6EB（蓝色）
- type:fix          颜色 #FF7619（橙色）
- type:docs         颜色 #0075CA（深蓝）
- type:refactor     颜色 #C9B1FF（紫色）

角色标签：
- role:dev          颜色 #1D76DB（蓝色）
- role:review       颜色 #5319E7（紫色）
- role:arch         颜色 #BFD4F2（浅蓝）
```

### 创建 Issue 模板

创建目录 `.github/ISSUE_TEMPLATE/`，添加文件：

**task.md**（任务模板）：

```markdown
---
name: 任务
description: 给数字员工分配新任务
title: "[任务] "
labels: ["status:todo"]
body:
  - type: textarea
    attributes:
      label: 任务描述
      description: 描述需要完成的工作
    validations:
      required: true
  - type: textarea
    attributes:
      label: 验收标准
      description: 完成此任务需要满足的条件
  - type: dropdown
    attributes:
      label: 优先级
      options:
        - P1-紧急
        - P2-重要
        - P3-一般
      default: 1
  - type: textarea
    attributes:
      label: 相关资源
      description: 链接、文档等参考资源
```

**bug.md**（Bug 模板）：

```markdown
---
name: Bug
description: 报告一个问题
title: "[fix] "
labels: ["type:fix", "status:todo"]
body:
  - type: textarea
    attributes:
      label: 问题描述
    validations:
      required: true
  - type: textarea
    attributes:
      label: 复现步骤
  - type: textarea
    attributes:
      label: 期望结果
```

### 配置分支保护

```
1. 仓库 → Settings → Branches
2. 点击"Add rule"
3. Branch name pattern：main
4. 勾选：
   - Require a pull request before merging ✓
   - Require approvals：1
   - Dismiss stale PR approvals ✓
   - Require branches to be up to date ✓
5. 保存规则
```

---

## 1.5 生成老板 Token

### 生成步骤

```
1. 老板账号 → Settings → Developer settings（页面最下方左侧）
2. Personal access tokens → Tokens (classic)
3. 点击"Generate new token" → "Generate new token (classic)"
4. 填写：
   - Note（备注）：hermes-boss-token
   - Expiration（有效期）：No expiration（永不过期）
   - Select scopes（选择权限）：
     
     必须勾选：
     ☑ repo              （完整仓库权限）
       ☑ repo:status
       ☑ repo_deployment
       ☑ public_repo
       ☑ repo:invite
       ☑ security_events
     ☑ workflow          （Actions 工作流）
     ☑ admin:org         （完整组织管理权限）
       ☑ write:org
       ☑ read:org
       
     可选：
     ☐ write:discussion   （如需要讨论区）
     
5. 滚动到底部 → 点击"Generate token"
6. 页面显示令牌：ghp_xxxxxxxxxxxxxxxxxxxx
   ⚠️ 只显示一次，立即复制保存！
```

### Token 信息记录

| 项目 | 内容 |
|------|------|
| 备注名 | hermes-boss-token |
| Token | ghp_... |
| 有效期 | 永不过期 |
| 生成日期 | |

---

## 完成后

此阶段完成后，你需要：

1. 记录以下信息（用于下一阶段"上岗"）
2. 通过参数传入子 Agent 信息

### 交接清单

```yaml
# 本阶段产出
organization:
  name: {你的组织名}
  url: https://github.com/{你的组织名}
  
boss:
  github_username: {老板用户名}
  github_email: {老板邮箱}
  token: ghp_xxx
  
repository:
  name: agent_workflow
  url: https://github.com/{组织名}/agent_workflow

# 子 Agent 信息（通过参数传入，不在此阶段创建）
# agents:
#   dad-dev:
#     github_username: oneplusn-dad-dev
#     github_email: oneplusn_dad@163.com
#   dog-rev:
#     github_username: oneplusn-dog-rev
#     github_email: oneplusn_dog@163.com
```