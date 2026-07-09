# GitHub 基础设施搭建详细指南

老板开子公司的完整操作步骤。每一步都分为两个分支：**已有则复用** 或 **需要创建**。

---

## 目录

1. [老板邮箱](#老板邮箱)
2. [老板 GitHub 账号](#老板-github-账号)
3. [GitHub Organization](#github-organization)
4. [团队仓库](#团队仓库)
5. [生成 Token（可选）](#生成-token)

---

## 老板邮箱

### 已有邮箱 → 复用

如果你已有可用的邮箱（推荐 163，国内收发 GitHub 邮件稳定）：

```
只需确认以下信息：
- 邮箱地址：________________
- 能否正常接收邮件：是 / 否
```

### 需要注册 → 新建

推荐注册 163 邮箱：

```
1. 访问 https://mail.163.com/
2. 点击"注册新账号"
3. 选择"注册字母邮箱"（更专业）
4. 填写邮箱地址（如 yourname_boss@163.com）
5. 设置密码（12位以上，含大小写+数字+符号）
6. 输入手机号 → 获取短信验证码
7. 同意条款 → 完成注册
8. 登录后进入"设置" → "常规设置"
9. 时区设为 GMT+8（北京），每页显示 50 封
```

---

## 老板 GitHub 账号

### 已有账号 → 复用

如果你已有 GitHub 账号：

```
只需确认以下信息：
- GitHub 用户名：________________
- 该账号的登录邮箱是否已验证：是 / 否
- 是否需要生成新的 Personal Access Token：是 / 否
```

### 需要创建 → 新建

```
1. 打开浏览器无痕模式，访问 https://github.com/signup
   （无痕模式避免与已有 GitHub 会话冲突）
2. 输入上一步的邮箱地址
3. 创建密码（建议与邮箱密码不同）
4. 设置用户名（如 yourname-boss）
   - 全局唯一，如被占用可加数字后缀
5. 选择"不接收产品更新邮件"
6. 完成人机验证（CAPTCHA）
7. 点击"创建账户"
8. 到邮箱查收验证邮件 → 点击验证链接
9. 选择账户类型 → "个人"
10. 跳过所有个性化问题
11. 进入 GitHub 首页
```

**创建后完善资料（可选）**：

```
头像 → Settings → Profile：
  - Name：你的名字（或保持匿名）
  - Bio：1+N 数字员工团队 · Owner
  - Company：留空（创建组织后自动关联）
```

---

## GitHub Organization

### 已有组织 → 复用

如果你已有 GitHub Organization：

```
只需确认以下信息：
- 组织名称：________________
- 当前 GitHub 账号是否为该组织的 Owner：是 / 否
- 组织的基础权限是否已配置（成员基础权限为 Read）：是 / 否
```

如果权限未配置，补做以下步骤：

```
1. 进入组织 → Settings（右侧标签）
2. Member privileges（成员权限）：
   - Base permissions：Read（读取）
   - Repository creation：None（只有 Owner 能创建）
3. General（常规）：
   - Description：1+N 数字员工协作团队
   - Email：老板邮箱
   - 启用 Issues ✓、Projects ✓
4. 保存更改
```

### 需要创建 → 新建

```
1. 确保用老板 GitHub 账号登录
2. 头像 → 你的组织 → 新建组织
3. 选择"创建免费组织"
4. 填写信息：
   
   步骤 1：
   - Organization name：如 yourname-team（全局唯一）
   - Contact email：老板邮箱
   - 归属：我的个人账户
   
   步骤 2：跳过添加成员
   步骤 3：完成创建
   
5. 进入组织 → Settings → General：
   - Description：1+N 数字员工协作团队
   - Email：老板邮箱
   - 启用 Issues ✓、Projects ✓、Wiki ✓
   
6. Settings → Member privileges：
   - Base permissions：Read
   - Repository creation：None
   - Repository forking：允许 ✓
   
7. 保存所有更改
```

---

## 团队仓库

### 已有仓库 → 复用

如果组织下已有仓库：

```
只需确认以下信息：
- 仓库名称：________________
- 是否已初始化 README：是 / 否
- 是否已配置标签体系：是 / 否
```

如果缺少标签，补做：

```
仓库 → Issues → Labels → New label：
  status:todo      #EDEDED（灰色）
  status:in-progress #FEF2C0（黄色）
  status:review    #C5DEF5（蓝色）
  status:done      #0E8A16（绿色）
  status:blocked   #D93F0B（红色）
  priority:P1      #B60205（红 - 紧急）
  priority:P2      #FBCA04（黄 - 重要）
  priority:P3      #0E8A16（绿 - 一般）
  type:feat        #84B6EB（蓝色）
  type:fix         #FF7619（橙色）
  type:docs        #0075CA（深蓝）
  type:refactor    #C9B1FF（紫色）
```

### 需要创建 → 新建

```
1. 组织 → Repositories → New
2. 填写：
   - Repository name：agent_workflow（可自定义）
   - Description：团队协作空间
   - Visibility：Private
   - Initialize with README：✓
3. 创建
4. 设置标签体系（同上）
5. 可选：配置分支保护
   Settings → Branches → Add rule → main
   - Require a pull request before merging ✓
   - Require approvals：1
```

**README 模板**：参见本目录下的 `readme-template.md`，填入你的组织名和用户名即可。

---

## 生成 Token

此步骤为可选，可以在后续阶段生成。如果需要现在生成：

```
1. GitHub → Settings → Developer settings（页面最下方）
2. Personal access tokens → Tokens (classic)
3. Generate new token (classic)
4. 填写：
   - Note：hermes-boss-token
   - Expiration：No expiration
   - 权限：
     ☑ repo（完整仓库权限）
     ☑ workflow
     ☑ admin:org（完整组织管理权限）
5. Generate → 立即复制保存（只显示一次）
```

---

## 完成后

以上四步完成后，记录以下信息用于生成交接文件：

```
邮箱：________________
GitHub 用户名：________________
Organization 名称：________________
仓库名称：________________
Token（如已生成）：ghp_...
```

使用 `scripts/create_org.py` 生成 `handoff.yaml`。