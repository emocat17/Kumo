# ALIGNMENT: 环境变量管理系统

## 1. 项目上下文分析

Kumo 作为一个爬虫任务管理平台，用户需要经常配置各种 API Key（如 OpenAI Key, 代理服务 Key, 数据库连接串等）供爬虫脚本使用。
目前缺乏统一管理这些变量的机制，用户可能不得不硬编码在脚本中，既不安全也不方便切换环境。

### 现有架构
- **Backend**: FastAPI + SQLAlchemy + SQLite.
- **Task Execution**: `appTask/task_manager.py` 使用 `subprocess` 运行 Python 脚本。
- **Security**: 已包含 `cryptography` 和 `bcrypt` 依赖。

## 2. 需求理解

### 原始需求
1.  **全局环境变量配置界面**: 管理 Key-Value 对。
2.  **脚本级环境变量继承机制**: 自动注入到 Task 进程。
3.  **敏感信息加密存储**: 保护 Secret Key。

### 核心功能
1.  **CRUD API**: 管理环境变量 (Key, Value, Description, IsSecret)。
2.  **加密存储**: 对于标记为 `IsSecret` 的变量，数据库存储密文。
3.  **脱敏展示**: API 返回时，Secret 变量的值显示为 `******`，仅在运行时解密。
4.  **自动注入**: 任务启动时，解密所有变量并注入子进程 `env`。

## 3. 智能决策策略

### 关键决策点

1.  **加密方案**:
    -   使用 `cryptography.fernet.Fernet` 进行对称加密。
    -   **密钥管理**: 为了简化部署，生成一个密钥存储在 `.env` 文件或 `backend/data/secret.key` 中。如果不存在则自动生成。
    -   *决策*: 优先检查环境变量 `KUMO_SECRET_KEY`，若无则在 `backend/data` 下生成并读取 `secret.key` 文件。

2.  **数据模型**:
    -   新建表 `environment_variables`。
    -   字段: `id`, `key` (Unique), `value` (Encrypted text), `description`, `is_secret` (Bool), `created_at`, `updated_at`.

3.  **注入时机**:
    -   在 `task_manager.py` 的 `_run_job` 方法中，构建 `subprocess.Popen` 的 `env` 参数时注入。
    -   注入优先级: 系统环境变量 < Kumo 全局环境变量 < 任务特定环境变量 (未来扩展)。目前只需实现 Kumo 全局覆盖系统变量。

## 4. 疑问与澄清

- **Q1**: 是否允许非 Secret 变量？
  - *A1*: 是的，有些配置如 `MAX_RETRIES` 不需要加密，方便直接查看。

- **Q2**: 前端如何处理 Secret 值的编辑？
  - *A2*: Secret 值在前端显示为掩码。编辑时，如果用户不修改（留空或保留掩码），则后端不更新该字段；如果输入新值，则加密覆盖。

## 5. 待确认事项

无。

