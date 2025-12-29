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

## 📂 目录结构 (Project Structure)

系统采用微服务风格的模块化架构，后端代码位于 `backend/` 目录下：

```text
Kumo/
├── docker-compose.yml       # 容器编排文件
├── Data/                    # 爬虫/任务数据输出 (直接映射到宿主机)
├── backend/                 # FastAPI 后端服务
│   ├── core/                # 核心配置 (数据库连接, 安全加密)
│   ├── environment_service/ # Python 环境管理服务
│   ├── log_service/         # 日志管理服务
│   ├── project_service/     # 项目文件管理服务
│   ├── system_service/      # 系统配置与文件系统服务
│   ├── task_service/        # 任务调度与执行引擎
│   ├── projects/            # 上传的项目代码解压区
│   └── envs/                # 虚拟环境存储区
└── front/                   # Vue 3 前端应用
```

---

## 🔐 安全与持久化 (Security & Persistence)

### 数据库初始化
- 系统使用 **SQLite** 作为数据库，文件存储于 `./backend/data/TaskManage.db`。
- **自动初始化**: 当你首次克隆项目并启动时，系统会自动检测并创建一个全新的空数据库，无需手动执行 SQL 脚本。

### 密钥管理
- **Secret Key**: 系统启动时会自动在 `./backend/data/secret.key` 生成一个加密密钥。
- **用途**: 该密钥用于加密存储敏感信息（如全局环境变量中的 Secret 字段）。
- **安全策略**: `*.db` 数据库文件和 `secret.key` 密钥文件已被添加至 `.gitignore`，确保：
  1.  **代码库纯净**: 每次 `git clone` 都是一个干净的初始状态。
  2.  **数据安全**: 生产环境的敏感数据不会被误提交到版本控制系统中。

---

## 🛠️ 技术栈

- **前端**: Vue 3, TypeScript, Vite, Pinia, Lucide Icons, ECharts, Monaco Editor
- **后端**: Python 3.9+, FastAPI, SQLite, SQLAlchemy, APScheduler
- **部署**: Docker Compose

---

## 🚀 快速开始

### 方式一：Docker 部署 (推荐)

这是最简单、最快捷的启动方式。确保你的机器上安装了 Docker 和 Docker Compose。

1.  **启动服务**
    ```bash
    docker-compose up -d --build
    ```

2.  **访问服务**
    - **前端页面**: [http://localhost:6677](http://localhost:6677)
    - **后端 API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)

3.  **停止服务**
    ```bash
    docker-compose down
    ```

**数据卷说明 (Volumes):**
- `./Data`: 爬虫数据输出目录 (直接映射到宿主机)
- `./backend/data`: 数据库文件 (`TaskManage.db`) 与 密钥文件 (`secret.key`)
- `./backend/projects`: 上传的项目代码
- `./backend/envs`: 创建的虚拟环境
- `./backend/logs`: 系统运行日志

### 方式二：本地开发部署

如果你需要进行代码开发或调试，可以分别启动前后端服务。

#### 1. 启动后端服务

```bash
cd backend

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

#### 2. 启动前端服务

```bash
cd front

# 1. 安装依赖
npm install

# 2. 启动开发服务器
npm run dev
```
*前端服务默认运行在 `http://localhost:6677`*

---
