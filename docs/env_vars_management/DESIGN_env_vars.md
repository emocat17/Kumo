# DESIGN: 环境变量管理系统

## 1. 整体架构

后端负责加密存储和解密注入，前端提供管理界面。

### 架构图 (Mermaid)

```mermaid
graph TD
    A[前端 EnvVars 页面] -->|GET /api/system/env-vars| B[System Router]
    A -->|POST /api/system/env-vars| B
    B -->|AES Encrypt/Decrypt| C[Encryption Utils]
    C -->|Read/Write| D[DB: environment_variables]
    
    E[Task Scheduler] -->|Trigger Job| F[Task Manager]
    F -->|Fetch & Decrypt| B
    F -->|Inject env| G[Subprocess (Crawler Script)]
```

## 2. 模块设计

### 2.1 数据库设计 (Database)

**File**: `backend/appSystem/models.py`

```python
class EnvironmentVariable(Base):
    __tablename__ = "environment_variables"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    value = Column(String, nullable=False) # Stores encrypted text if is_secret=True
    description = Column(String, nullable=True)
    is_secret = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 2.2 加密工具 (Encryption Utils)

**File**: `backend/app/security.py` (新建)

- `get_fernet()`: 获取 Fernet 实例，处理密钥加载/生成。
- `encrypt_value(value: str) -> str`: 加密。
- `decrypt_value(token: str) -> str`: 解密。

### 2.3 后端接口 (Backend API)

**File**: `backend/appSystem/env_vars_router.py` (新建)

- `GET /`: 获取列表。Secret 值的 `value` 字段返回 `******`。
- `POST /`: 创建。自动加密 Secret。
- `PUT /{id}`: 更新。如果 value 为 `******` 或空，则保持原值。
- `DELETE /{id}`: 删除。

### 2.4 任务注入 (Task Injection)

**File**: `backend/appTask/task_manager.py`

- 修改 `_run_job` 或类似执行函数。
- 获取所有 `EnvironmentVariable`。
- 解密所有值。
- `os.environ.copy()` 并 update 这些值。
- 传递给 `subprocess.Popen(env=...)`。

### 2.5 前端设计 (Frontend)

**Page**: `front/src/pages/Settings.vue` (复用设置页，增加 Tab 或 Section)

- 新增 "环境变量" 面板。
- 表格展示: Key, Value (Masked), Description, Actions.
- 模态框: 添加/编辑变量。

## 3. 接口契约

### 3.1 列表
`GET /api/system/env-vars`
```json
[
  {
    "id": 1,
    "key": "OPENAI_API_KEY",
    "value": "******",
    "is_secret": true,
    "description": "GPT Key"
  },
  {
    "id": 2,
    "key": "DEBUG",
    "value": "True",
    "is_secret": false
  }
]
```

## 4. 安全策略

- 密钥文件 `secret.key` 必须排除在 git 之外 (添加到 `.gitignore`)。
- API 永远不返回 Secret 的明文。

