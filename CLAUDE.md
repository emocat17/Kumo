# CLAUDE.md - Kumo 开发助手规范

## 项目概述
Kumo 是一个 Python 脚本管理平台，用于调度与运行 Python 脚本项目（如 Scrapy、Playwright、Selenium 等）。平台支持创建隔离的 Python 环境（Conda），并以任务为核心进行执行与日志记录。

## 技术栈
- **后端**: FastAPI + SQLAlchemy + APScheduler + SQLite + Psutil
- **前端**: Vue 3 + Vite + TypeScript + Pinia + Monaco Editor
- **运行环境**: Docker + Docker Compose + Conda

## 目录结构
```
Kumo/
├── backend/               # 后端服务
│   ├── main.py            # 应用入口
│   ├── core/              # 核心模块
│   │   ├── database.py    # 数据库连接
│   │   └── security.py   # 加解密工具
│   ├── task_service/      # 任务调度服务
│   ├── project_service/   # 项目管理服务
│   ├── environment_service/# 环境管理服务
│   ├── system_service/    # 系统服务
│   ├── log_service/       # 日志服务
│   └── audit_service/     # 审计服务
├── front/                 # 前端应用
│   ├── src/
│   │   ├── pages/        # 页面组件
│   │   ├── components/   # 公共组件
│   │   ├── router/       # 路由配置
│   │   ├── stores/       # Pinia 状态
│   │   └── styles/       # 样式文件
│   └── package.json
├── docker-compose.yml     # 容器编排
└── AGENTS.md             # 项目规范
```

## API 端点规范
| 路由前缀 | 服务 |
|---------|------|
| `/api/tasks` | 任务管理 |
| `/api/projects` | 项目管理 |
| `/api/python/versions` | Python 版本 |
| `/api/python/environments` | Python 环境 |
| `/api/system` | 系统配置 |
| `/api/system/env-vars` | 环境变量 |
| `/api/logs` | 日志管理 |
| `/api/audit` | 审计日志 |

## 后端开发规范

### 1. 模块结构
每个服务模块应包含：
- `__init__.py`: 导出接口
- `models.py`: SQLAlchemy 模型
- `schemas.py`: Pydantic schemas
- `service.py`: 业务逻辑
- `router.py`: FastAPI 路由

### 2. 数据库操作
```python
# 使用依赖注入获取数据库会话
from core.database import get_db
from sqlalchemy.orm import Session

@router.get("/items")
def get_items(db: Session = Depends(get_db)):
    return db.query(Item).all()
```

### 3. 任务执行
- 使用 `task_manager` 添加/移除任务
- 任务执行函数需在 `task_manager.py` 中定义
- 使用 `subprocess.Popen` 执行命令
- 日志写入 `backend/logs/tasks/`

### 4. 路径安全
- 文件操作必须防止路径穿透
- 使用 `os.path.abspath` 和 `startswith` 验证

### 5. 环境变量加密
```python
from core.security import encrypt_value, decrypt_value

# 加密
encrypted = encrypt_value("secret_value")
# 解密
decrypted = decrypt_value(encrypted)
```

## 前端开发规范

### 1. 组件结构
```
src/
├── pages/              # 页面级组件
│   └── [module]/
│       └── *.vue
├── components/         # 公共组件
│   ├── common/        # 通用组件
│   ├── project/       # 项目相关
│   └── task/          # 任务相关
└── stores/            # Pinia 状态
```

### 2. API 调用
```typescript
const API_BASE = '/api'

// GET
const data = await fetch(`${API_BASE}/tasks`)

// POST
const res = await fetch(`${API_BASE}/tasks`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(payload)
})
```

### 3. 响应处理
```typescript
if (res.ok) {
  const data = await res.json()
  // 处理数据
} else {
  const err = await res.json()
  alert(`错误: ${err.detail}`)
}
```

### 4. 状态管理
使用 Pinia 管理全局状态：
```typescript
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', {
  state: () => ({
    loading: false
  })
})
```

## 编码规范

### Python (后端)
- 使用类型注解
- 函数单一职责
- 异常处理要具体
- 日志记录使用 `logging` 模块
- 避免魔法数字，使用常量

### TypeScript/Vue (前端)
- 使用 TypeScript 类型
- 组件 props 使用 interface 定义
- 避免使用 `any`
- 使用组合式 API (`<script setup>`)
- 样式使用 scoped

## 常见任务指南

### 添加新功能
1. **后端**: 
   - 在对应 service 创建 models/schemas/router
   - 在 main.py 注册路由
   - 添加审计日志（关键操作）

2. **前端**:
   - 在 pages/ 创建页面组件
   - 在 router/index.ts 注册路由
   - 复用现有组件样式

### 数据库迁移
对于 SQLite，使用原生 SQL 检查并添加列：
```python
def ensure_columns():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("PRAGMA table_info(table_name)")
        columns = [info[1] for info in cursor.fetchall()]
        if "new_column" not in columns:
            cursor.execute("ALTER TABLE table_name ADD COLUMN new_column VARCHAR")
        conn.commit()
    finally:
        conn.close()
```

### 任务调试
查看任务日志：
```bash
# 容器内日志
tail -f backend/logs/tasks/task_1_exec_1.log
```

### 前端调试
浏览器开发者工具 Network 面板查看 API 请求

## 部署注意事项
- 修改代码后无需重启容器（热重载）
- 前后端通过 Docker 网络通信
- 端口：前端 18080，后端 8000
- 数据库和项目文件通过卷持久化
