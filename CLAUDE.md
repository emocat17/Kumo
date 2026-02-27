# Kumo 开发助手配置 (CLAUDE.md)

本文件定义了与 Kumo 项目开发相关的规范和上下文，帮助 AI 助手更高效地进行开发工作。

---

## 项目概览

**Kumo** 是一个基于 Docker 的现代化 Python 任务调度与全栈环境管理平台。

- **定位**: Python 脚本管理平台，用于调度与运行 Python 脚本项目（如简单脚本、Playwright、Selenium 等）
- **架构**: 单机版，支持任务调度、项目管理、环境隔离、日志审计
- **状态**: 积极开发中 (WIP)

---

## 技术栈详情

### 后端
- **框架**: FastAPI
- **ORM**: SQLAlchemy
- **调度器**: APScheduler
- **数据库**: SQLite
- **监控**: Psutil
- **依赖管理**: Conda / Pip

### 前端
- **框架**: Vue 3 + TypeScript
- **构建**: Vite
- **状态管理**: Pinia
- **UI**: Ant Design Vue / Tailwind
- **图标**: Lucide Icons
- **图表**: ECharts

### 部署
- **容器化**: Docker + Docker Compose
- **端口**: 前端 18080，后端 8000

---

## 目录结构约定

```
Kumo/
├── backend/                  # 后端服务
│   ├── core/                 # 核心模块
│   │   ├── database.py       # SQLAlchemy 引擎与 Session
│   │   └── security.py       # 密钥与加解密
│   ├── task_service/         # 任务调度与执行
│   ├── project_service/      # 项目上传、解析
│   ├── environment_service/  # Python 版本与环境管理
│   ├── system_service/       # 系统配置、备份
│   ├── log_service/         # 任务日志
│   ├── audit_service/       # 审计日志
│   ├── data/                 # SQLite 数据库与备份
│   ├── projects/             # 上传项目解压目录
│   ├── envs/                # Conda 环境目录
│   ├── logs/                # 任务与安装日志
│   └── main.py              # 应用入口
├── front/                    # 前端应用
│   ├── src/
│   │   ├── pages/           # 页面组件
│   │   ├── components/      # 公共组件
│   │   ├── router/          # 路由配置
│   │   ├── stores/          # Pinia 状态管理
│   │   └── styles/          # 全局样式
├── Data/                     # 任务产出数据目录
├── docker-compose.yml       # 容器编排
└── AGENTS.md                # 项目开发规范
```

---

## API 约定

### 基础 URL
- 后端 API: `http://localhost:8000/api`
- 前端应用: `http://localhost:18080`

### 路由前缀规范
| 服务 | 路由前缀 |
|------|----------|
| 任务 | `/api/tasks` |
| 项目 | `/api/projects` |
| 环境 | `/api/python/environments` |
| 版本 | `/api/python/versions` |
| 系统 | `/api/system` |
| 日志 | `/api/logs` |
| 审计 | `/api/audit` |

---

## 数据模型概览

### Task (任务)
```python
- id: int
- name: str
- status: str (active/paused/error)
- command: str
- project_id: int (FK)
- env_id: int (FK, nullable)
- trigger_type: str (interval/cron/date/immediate)
- trigger_value: str (JSON 字符串)
- retry_count: int
- retry_delay: int
- timeout: int
- priority: int
```

### TaskExecution (任务执行)
```python
- id: int
- task_id: int (FK)
- status: str (success/failed/running/timeout/stopped)
- attempt: int
- start_time: datetime
- end_time: datetime
- duration: float
- log_file: str
- output: text
- max_cpu_percent: float
- max_memory_mb: float
```

### Project (项目)
```python
- id: int
- name: str
- path: str
- work_dir: str
- output_dir: str
- description: str
```

### PythonVersion / PythonEnvironment
```python
- id: int
- name: str
- version: str
- path: str
- is_default: bool
- status: str
- is_conda: bool
```

---

## 任务执行流程

1. **调度触发**: APScheduler 根据 trigger_type 和 trigger_value 触发任务
2. **环境准备**: 加载项目配置，注入环境变量、代理、OUTPUT_DIR
3. **命令执行**: 使用 subprocess.Popen 执行命令
4. **日志记录**: stdout/stderr 写入 logs/tasks 目录
5. **资源监控**: 后台线程使用 psutil 监控 CPU/内存
6. **结果处理**: 
   - 成功: status = "success"
   - 失败: status = "failed"，进入重试逻辑
   - 超时: status = "timeout"

---

## 开发规范

### 后端开发
1. **新增功能**: 同步更新 `schemas`、`models` 与 `routers`
2. **路径安全**: 文件保存与浏览必须做路径穿透保护
3. **加密存储**: SECRET 类型环境变量必须加密存储
4. **错误处理**: 使用 try-except 包装关键操作，记录日志
5. **审计日志**: 关键操作需写入 audit_logs 表

### 前端开发
1. **路由注册**: 新增页面需在 `src/router/index.ts` 注册
2. **组件复用**: 优先复用既有组件样式
3. **API 调用**: 使用 `/api` 前缀，参考现有页面实现
4. **状态管理**: 复杂状态使用 Pinia，简单状态使用 ref/reactive
5. **类型定义**: 使用 TypeScript 定义接口类型

### Docker 开发
1. **热重载**: 修改代码后自动同步到容器，无需重启
2. **日志查看**: `docker-compose logs -f backend/front`
3. **数据库**: SQLite 文件位于 `backend/data/TaskManage.db`

---

## 常用命令

### 启动服务
```bash
docker-compose up -d --build
```

### 查看日志
```bash
docker-compose logs -f backend
docker-compose logs -f front
```

### 重启服务
```bash
docker-compose restart backend
docker-compose restart front
```

### 进入容器
```bash
docker exec -it backend bash
docker exec -it front sh
```

---

## 注意事项

1. **Windows 开发**: 项目运行在 Windows 宿主机，使用 Docker Desktop
2. **路径映射**: Windows 路径在容器内会自动转换
3. **环境变量**: 容器内使用 Linux 路径 (如 `/app/projects`)
4. **前端代理**: 开发环境通过 Vite 代理解决跨域

---

## 性能优化要点

1. **任务并发**: 通过 `MAX_CONCURRENT_TASKS` 环境变量控制
2. **资源监控**: 后台线程每 1 秒采样，每 3 秒写入数据库
3. **日志截断**: 执行日志默认保存最后 4KB 到数据库
4. **数据库**: 使用 SQLite，适合单机场景

---

## 安全注意事项

1. **密钥管理**: 优先读取 `KUMO_SECRET_KEY` 环境变量
2. **路径遍历**: 所有文件操作需校验路径合法性
3. **命令执行**: 避免 shell=True，使用 shlex.split
4. **敏感信息**: 环境变量中 is_secret=True 的值需加密存储
