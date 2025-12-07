# Kumo - Python 任务调度与管理平台

Kumo 是一个基于 Web 的现代化 Python 任务调度与环境管理平台。它允许用户通过友好的图形界面管理 Python 版本、虚拟环境、项目文件以及自动化任务调度。

## 🌟 主要功能

### 1. 仪表盘 (Dashboard)
- **系统监控**: 实时监控服务器 CPU、内存、磁盘和网络使用情况。
- **概览**: 快速查看 Python 环境数量、项目数量和系统运行时间。

### 2. Python 环境管理
- **版本管理**: 查看和管理已安装的 Python 版本。
- **环境隔离**: 创建和管理虚拟环境（Virtualenv / Conda）。
- **包管理**: 在指定环境中搜索、安装和卸载 Python 依赖包。
- **依赖导入**: 支持通过 `requirements.txt` 批量安装依赖。

### 3. 项目管理
- **工作区**: 以项目为单位隔离代码和资源。
- **文件上传**: 支持通过 ZIP 包上传项目代码。
- **在线配置**: 在线修改项目名称、描述和工作路径。
- **文件浏览**: 在线查看项目内的文件结构和文件内容。

### 4. 任务调度 (Task Scheduling)
- **多种触发器**: 支持 Cron 表达式、时间间隔 (Interval) 和特定日期 (Date) 触发。
- **环境绑定**: 指定任务运行所需的 Python 环境和项目上下文。
- **任务控制**: 随时暂停、恢复、立即执行或停止任务。
- **日志与历史**: 查看任务的历史运行记录和实时执行日志。

---

## 🛠️ 技术栈

- **前端**: Vue 3, TypeScript, Vite, Pinia, Lucide Icons
- **后端**: Python, FastAPI, SQLite, SQLAlchemy, APScheduler

---

## 🚀 开发环境部署

### 前置要求
- Node.js (v16+)
- Python (v3.8+)

### 1. 启动后端服务

```bash
cd backed

# 1. 创建并激活虚拟环境 (可选但推荐)
python -m venv venv
# Windows:
.\venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python main.py
```
*后端服务默认运行在 `http://localhost:8000`*

### 2. 启动前端服务

```bash
cd front

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
```
*前端服务默认运行在 `http://localhost:6677`*

---

## 📦 生产环境部署

### 1. 构建前端资源

```bash
cd front
npm run build
```
构建完成后，生成的静态文件位于 `front/dist` 目录。

### 2. 部署建议

建议使用 **Nginx** 作为反向代理服务器，同时托管前端静态文件和转发后端 API 请求。

**Nginx 配置示例:**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 前端静态文件
    location / {
        root /path/to/kumo/front/dist;
        try_files $uri $uri/ /index.html;
    }

    # 后端 API 转发
    location /api {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 3. 后端生产运行

建议使用 `gunicorn` (Linux) 或保持 `python main.py` (仅限简单场景) 配合进程守护工具 (如 Supervisor 或 Systemd) 运行后端服务。

```bash
cd backed
# 示例：直接运行
python main.py
```

---

## 📂 目录结构

```
Kumo/
├── backed/                         # 后端代码 (FastAPI)
│   ├── app/                        # 核心配置
│   │   └── database.py             # 数据库连接配置
│   ├── appEnv/                     # Python 环境管理模块
│   │   ├── env_router.py           # 环境 API 路由
│   │   ├── python_version_router.py # Python 版本 API 路由
│   │   ├── models.py               # 数据库模型 (Environment, Package)
│   │   └── schemas.py              # Pydantic 数据验证模型
│   ├── appProject/                 # 项目管理模块
│   │   ├── project_router.py       # 项目 API 路由
│   │   ├── models.py               # 数据库模型 (Project)
│   │   └── schemas.py              # Pydantic 数据验证模型
│   ├── appTask/                    # 任务调度模块
│   │   ├── task_manager.py         # APScheduler 调度管理器
│   │   ├── task_router.py          # 任务 API 路由
│   │   ├── models.py               # 数据库模型 (Task, TaskExecution)
│   │   └── schemas.py              # Pydantic 数据验证模型
│   ├── appSystem/                  # 系统监控模块
│   │   ├── system_router.py        # 系统信息 API 路由
│   │   └── fs_router.py            # 文件系统 API 路由
│   ├── projects/                   # 用户上传的项目文件存储目录 (运行时生成)
│   ├── main.py                     # 后端应用入口
│   └── requirements.txt            # Python 依赖列表
│
├── front/                          # 前端代码 (Vue 3 + Vite)
│   ├── src/
│   │   ├── assets/                 # 静态资源 (图片等)
│   │   ├── components/             # 公共组件
│   │   │   ├── common/             # 通用 UI 组件 (Modal, Header 等)
│   │   │   ├── project/            # 项目相关组件 (FileTree, Editor 等)
│   │   │   └── task/               # 任务相关组件 (History, Log 等)
│   │   ├── layout/                 # 页面布局组件
│   │   ├── pages/                  # 页面视图
│   │   │   ├── project/            # 项目管理页面
│   │   │   ├── python/             # Python 环境页面
│   │   │   ├── task/               # 任务管理页面
│   │   │   └── Dashboard.vue       # 仪表盘页面
│   │   ├── router/                 # Vue Router 路由配置
│   │   ├── stores/                 # Pinia 状态管理
│   │   ├── styles/                 # 全局样式
│   │   ├── App.vue                 # 根组件
│   │   └── main.ts                 # 前端入口文件
│   ├── package.json                # 前端依赖配置
│   └── vite.config.ts              # Vite 配置文件
│
└── README.md                       # 项目说明文档
```
