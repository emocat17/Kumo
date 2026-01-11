# Kumo

> **基于 Docker 的现代化 Python 任务调度与全栈环境管理平台**
>
> 🚧 **项目状态**：处于积极开发状态(WIP) - api和功能可能会更改。

Kumo 是一个专为 Python 开发者设计的任务调度管理系统，旨在解决传统 Crontab 管理混乱、环境依赖冲突难以维护的问题。通过容器化技术和 Web 可视化界面，提供从**环境构建**、**代码部署**到**任务调度**、**日志审计**的一站式解决方案。

## ✨ 核心特性 (Features)

- **可视化任务编排**: 基于 APScheduler，支持 Cron 表达式、时间间隔 (Interval) 和特定日期 (Date) 三种触发模式，任务状态实时监控。
- **多环境隔离**: 深度集成的 Conda/Venv 环境管理。支持为每个项目创建独立的 Python 虚拟环境，彻底告别 `Dependency Hell`。
- **项目化管理**: 支持 ZIP 包一键上传解压，提供在线文件浏览器，支持代码热更新与在线编辑。
- **全链路日志**: 实时捕获标准输出 (stdout/stderr)，提供任务执行日志持久化存储与历史回溯。
- **系统级审计**: 记录所有关键操作（创建、删除、执行），支持按 IP、操作类型、时间范围进行审计追踪。
- **开箱即用**: 全栈 Docker Compose 编排，内置 SQLite 数据库，数据全量持久化。

## 🛠 技术栈 (Tech Stack)

| 模块 | 技术选型 | 说明 |
| :--- | :--- | :--- |
| **Frontend** | Vue 3, TypeScript | Vite 构建，Pinia 状态管理 |
| **UI Framework** | Ant Design Vue / Tailwind | 响应式布局，Monaco Editor 代码编辑 |
| **Backend** | Python 3.9+, FastAPI | 高性能异步框架 |
| **Scheduling** | APScheduler | 强大的后台任务调度引擎 |
| **Database** | SQLite / SQLAlchemy | 轻量级，零配置启动 |
| **Infrastructure** | Docker & Compose | 容器化部署，环境一致性保证 |

## 🚀 快速开始 (Getting Started)

### 前置要求
- [Docker](https://www.docker.com/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/) v2.0+

### 安装步骤

1.  **克隆仓库**
    ```bash
    git clone https://github.com/YourUsername/Kumo.git
    cd Kumo
    ```

2.  **启动服务**
    ```bash
    # 构建镜像并后台启动
    docker-compose up -d --build
    ```

3.  **访问控制台**
    等待约 30 秒，待服务初始化完成后访问：
    - 🖥️ **前端 Dashboard**: [http://localhost:6677](http://localhost:6677)
    - 📚 **后端 API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)

## ⚙️ 配置说明 (Configuration)

核心配置位于 `docker-compose.yml`，通常无需修改即可运行。

### 数据持久化 (Volumes)
为保证数据安全，以下目录已映射至宿主机：

| 宿主机路径 | 容器路径 | 说明 |
| :--- | :--- | :--- |
| `./Data` | `/app/Data` | **任务数据输出目录**，爬虫结果建议存放在此 |
| `./backend/data` | `/app/backend/data` | **系统数据库** (SQLite) 与密钥文件 |
| `./backend/projects` | `/app/backend/projects` | **项目代码库**，上传的代码包解压于此 |
| `./backend/envs` | `/app/backend/envs` | **虚拟环境库**，Conda/Venv 环境存储位置 |

### 环境变量
- `TZ=Asia/Shanghai`: 指定容器时区，确保定时任务准确执行。
- `PYTHONUNBUFFERED=1`: 保证 Python 日志实时输出。

## � 使用指南

### 1. 创建 Python 环境
进入 **环境管理** 页面，点击“新建环境”。
- **Conda**: 适合需要特定 Python 版本或系统级依赖的场景。
- **Venv**: 轻量级，适合纯 Python 依赖项目。

### 2. 上传项目代码
进入 **项目管理** 页面，上传 `.zip` 格式的代码包。系统会自动解压并保留目录结构。

### 3. 创建调度任务
进入 **任务管理** 页面：
1. 选择关联的项目。
2. 指定执行环境（系统环境或自定义虚拟环境）。
3. 输入启动命令（如 `python main.py`）。
4. 设置触发器（Cron/Interval）。

## �� 目录结构

```text
Kumo/
├── docker-compose.yml       # 容器编排入口
├── Data/                    # [Output] 任务产出数据
├── backend/                 # FastAPI 后端服务
│   ├── core/                # 核心配置
│   ├── task_service/        # 调度引擎核心逻辑
│   ├── projects/            # [Persist] 项目文件存储
│   └── envs/                # [Persist] 虚拟环境存储
└── front/                   # Vue 3 前端应用
    ├── src/pages/           # 页面组件
    └── src/styles/          # 全局样式
```

## 🖼️ 系统预览

![Dashboard](image/README/1767279439951.png)
![Tasks](image/README/1767279462549.png)

## 📄 许可证

MIT License © 2025 Kumo Team
