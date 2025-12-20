# Kumo (Spider_front) 项目开发文档

本文档详细描述了 Kumo 项目的架构、功能模块、运行方式及开发规范。旨在为后续的开发人员（包括 AI 智能体）提供全面的上下文参考。

---

## 1. 项目概述

**项目名称**: Kumo (前身 Spider_front)
**核心功能**: 一个基于 Docker 的可视化爬虫管理与任务调度平台。
**主要特性**:
- **Python 环境管理**: 支持添加现有解释器、创建/删除 Conda 环境、安装/卸载依赖包。
- **项目管理**: 支持上传 ZIP 格式的爬虫项目代码，自动解压，支持在线编辑和文件查看。
- **任务调度**: 基于 APScheduler 的定时任务系统（Cron/Interval/Date），支持任务日志实时查看。
- **数据持久化**: 支持将爬虫产生的数据直接映射到宿主机，方便本地查看和处理。
- **Docker 化**: 全栈容器化部署，支持开发模式下的热重载 (Hot Reload)。

---

## 2. 系统架构

项目采用前后端分离架构，通过 Docker Compose 进行编排。

### 2.1 容器服务
*   **Backend (`backend`)**:
    *   **镜像**: 基于 Python 3.9+ (具体见 `backend/Dockerfile`)
    *   **端口**: 8000
    *   **技术栈**: FastAPI, SQLAlchemy, SQLite, APScheduler, Conda
    *   **职责**: 提供 REST API，管理数据库，执行后台任务，管理 Python 环境。
*   **Frontend (`front`)**:
    *   **镜像**: 基于 Node.js (具体见 `front/Dockerfile`)
    *   **端口**: 6677
    *   **技术栈**: Vue 3, Vite, TypeScript, Pinia
    *   **职责**: 提供用户交互界面。

### 2.2 网络与通信
*   **Docker 网络**: `kumo-net` (Bridge 模式)
*   **通信方式**: 前端通过 `http://backend:8000` (Docker 内部 DNS) 或 `http://localhost:8000` (浏览器侧) 访问后端 API。

### 2.3 数据卷映射 (Volume Mapping)
为了支持开发便利性和数据持久化，做了以下关键映射：

| 宿主机路径 | 容器路径 | 说明 |
| :--- | :--- | :--- |
| `./backend` | `/app` | 后端代码热重载 |
| `./front` | `/app` | 前端代码热重载 |
| `./Data` | `/data` | **核心数据输出目录** (爬虫结果) |
| `./backend/data` | `/app/data` | SQLite 数据库文件 (`TaskManage.db`) |
| `./backend/projects` | `/app/projects` | 上传的项目文件存储 |
| `./backend/logs` | `/app/logs` | 系统日志与任务运行日志 |
| `./backend/envs` | `/app/envs` | 项目内部创建的 Conda 环境 |

---

## 3. 目录结构详解

```text
D:/GitWorks/Spider_front/
├── .gitignore             # Git 忽略配置 (已优化，忽略运行时文件)
├── docker-compose.yml     # 核心编排文件
├── reset_project.py       # (可选) 项目重置脚本
├── Data/                  # [数据] 爬虫数据输出目录 (映射到容器 /data)
├── backend/               # [后端] FastAPI 项目根目录
│   ├── main.py            # 应用入口 (Lifespan 配置)
│   ├── requirements.txt   # 后端依赖
│   ├── Dockerfile         # 后端构建文件
│   ├── backend_tree.md    # 旧的目录结构说明 (参考)
│   ├── app/               # 核心配置
│   │   ├── database.py    # 数据库连接 (SQLite)
│   │   └── ...
│   ├── appEnv/            # [模块] Python 环境管理
│   │   ├── env_router.py  # 依赖包安装/卸载 API
│   │   ├── python_version_router.py # 解释器增删查改 API
│   │   └── models.py      # PythonVersion 模型
│   ├── appProject/        # [模块] 项目管理
│   │   ├── project_router.py # 项目上传/编辑/删除 API
│   │   └── models.py      # Project 模型 (含 output_dir)
│   ├── appTask/           # [模块] 任务调度
│   │   ├── task_manager.py # APScheduler 封装 (核心调度逻辑)
│   │   ├── task_router.py  # 任务增删改查 API
│   │   └── models.py      # Task, TaskExecution 模型
│   ├── appLogs/           # [模块] 日志读取
│   ├── data/              # SQLite 数据库存放 (.db)
│   ├── projects/          # 上传的项目解压目录
│   ├── envs/              # 内部管理的 Conda 环境目录
│   └── logs/              # 运行日志目录
└── front/                 # [前端] Vue 3 项目根目录
    ├── index.html
    ├── package.json
    ├── vite.config.ts
    ├── src/
    │   ├── main.ts
    │   ├── App.vue
    │   ├── pages/         # 页面组件
    │   │   ├── project/   # Projects.vue (项目管理)
    │   │   ├── python/    # Versions.vue, Environments.vue
    │   │   ├── task/      # Tasks.vue
    │   │   └── ...
    │   └── components/    # 通用组件 (BaseModal, etc.)
```

---

## 4. 核心功能模块

### 4.1 Python 环境管理 (`appEnv`)
*   **添加解释器**: 支持添加指定路径的 Python (`python.exe` 或二进制文件)。
*   **Conda 集成**:
    *   支持创建 Conda 环境（优先使用 `conda create -n name`）。
    *   **路径兼容性**: 自动检测宿主机路径与容器路径的差异。
    *   **删除策略**: 采用“重命名后删除” (`_trash`) 策略，解决 Windows 文件锁问题。
*   **依赖管理**:
    *   支持 `pip` 和 `conda` 安装。
    *   **安全执行**: 使用列表参数 (`subprocess.Popen(['pip', ...])`) 防止 Shell 注入。
    *   **实时日志**: 前端可实时查看安装日志流。

### 4.2 项目管理 (`appProject`)
*   **上传**: 接受 ZIP 文件，后端自动解压到 `backend/projects/{project_name}`。
*   **输出目录 (`output_dir`)**:
    *   每个项目可配置一个数据输出目录。
    *   **浏览功能**: 前端提供文件浏览器选择服务器（容器）内的目录（推荐选择 `/data`）。
    *   **环境变量注入**: 任务运行时，会自动将该路径注入为环境变量 `OUTPUT_DIR`, `DATA_DIR`, `BASE_DATA_DIR`。
*   **删除**: 级联删除数据库记录和磁盘上的项目文件夹（同样采用强力删除策略）。

### 4.3 任务调度 (`appTask`)
*   **调度器**: `BackgroundScheduler` (APScheduler)。
*   **触发器**: 支持 Cron (CronTrigger), Interval (IntervalTrigger), Date (DateTrigger)。
*   **执行流程**:
    1.  从数据库加载任务 (`load_jobs_from_db`)。
    2.  创建执行记录 (`TaskExecution`)，状态为 `running`。
    3.  **环境准备**: 注入项目路径、Python 路径、输出目录环境变量。
    4.  **执行**: 使用 `subprocess` 启动进程，日志重定向到文件。
    5.  **完成**: 更新执行记录状态 (`success`/`failed`)。
*   **容错**: 如果指定的 Python 环境路径不存在（如 Docker 路径差异），自动降级使用系统默认 `python`。

---

## 5. 运行与部署

### 5.1 启动环境
确保已安装 Docker 和 Docker Compose。

```bash
# 在项目根目录执行
docker-compose up -d --build
```

### 5.2 访问服务
*   **前端页面**: http://localhost:6677
*   **后端文档**: http://localhost:8000/docs

### 5.3 常用命令
```bash
# 重启后端 (代码修改后通常会自动重载，但配置修改可能需要重启)
docker-compose restart backend

# 查看日志
docker-compose logs -f backend

# 停止服务
docker-compose down
```

---

## 6. 数据持久化与 Docker 映射

为了确保在 Windows 宿主机上开发时能方便地访问爬虫数据，项目配置了特殊的卷映射：

*   **配置**: `docker-compose.yml` 中映射 `./Data:/data`。
*   **使用**:
    1.  在前端“编辑项目”中，将“数据输出路径”设置为 `/data` 或 `/data/subfolder`。
    2.  爬虫代码中读取环境变量 `os.getenv('OUTPUT_DIR')` 作为保存路径。
    3.  爬取的文件将直接出现在宿主机的 `D:/GitWorks/Spider_front/Data/` 文件夹中。

---

## 7. AI 维护指南 (注意事项)

后续 AI 智能体在维护本项目时，请务必注意以下几点：

1.  **路径兼容性 (Path Compatibility)**:
    *   项目同时运行在 Windows (宿主机开发) 和 Linux (Docker 容器) 环境。
    *   涉及文件路径的代码必须使用 `os.path.join`。
    *   注意 `python_version` 表中的路径可能是宿主机路径（开发时录入），在容器内运行时需做存在性检查或降级处理（参考 `task_manager.py` 中的修复逻辑）。

2.  **文件删除 (File Deletion)**:
    *   Windows 下删除文件夹常遇到 `PermissionError` 或 `WinError 5`。
    *   **必须**使用已实现的“改名+重试+强力删除”逻辑（参考 `project_router.py` 和 `python_version_router.py` 中的实现）。不要简单使用 `shutil.rmtree`。

3.  **Shell 注入防护**:
    *   执行 `pip install` 或其他系统命令时，**严禁**使用字符串拼接且 `shell=True`。
    *   **必须**使用列表形式传递参数，例如 `cmd = [python_exe, "-m", "pip", "install", pkg_name]`，并设置 `shell=False`。

4.  **数据库迁移**:
    *   目前使用 SQLite，且未引入 Alembic。
    *   修改模型 (`models.py`) 后，需要在 Router 启动时编写手动 SQL (`ALTER TABLE ...`) 来保证旧数据库兼容性（参考 `ensure_columns` 函数）。

5.  **前端交互**:
    *   前端使用 Vue 3 组合式 API。
    *   注意“配置中/安装中”等长耗时状态的 UI 反馈，不要简单禁用按钮，应允许用户查看进度日志。

---
*文档最后更新时间: 2025-12-20*
