# Kumo

> **基于 Docker 的现代化 Python 脚本调度与全栈环境管理平台**

> ✅ **项目状态**：稳定开发中 - 核心功能已完成，97个测试全部通过，代码质量优秀。

Kumo 是一个专为 Python 开发者设计的任务调度管理系统，旨在解决传统 Crontab 管理混乱、环境依赖冲突难以维护的问题。通过容器化技术和 Web 可视化界面，提供从**环境构建**、**代码部署**到**任务调度**、**日志审计**的一站式解决方案。

## ✨ 核心特性

### 🎯 任务调度
- **多种触发模式**: 支持 Cron 表达式、时间间隔 (Interval) 和特定日期 (Date) 三种触发模式
- **实时状态监控**: 任务执行状态实时更新，支持运行中、成功、失败、重试等状态追踪
- **智能重试机制**: 支持失败自动重试，可配置重试次数和重试间隔
- **并发控制**: 内置并发控制机制，防止资源耗尽，默认最大并发任务数 50
- **资源监控**: 实时监控任务 CPU 和内存使用情况，记录峰值数据

### 🐍 环境管理
- **Conda 深度集成**: 支持创建、删除、管理独立的 Conda 虚拟环境
- **多版本支持**: 支持 Python 3.9、3.10、3.11 等多个版本
- **依赖管理**: 支持通过 Conda 或 Pip 安装依赖包，实时查看安装日志
- **环境隔离**: 每个项目可使用独立的 Python 环境，彻底解决依赖冲突问题
- **状态管理**: 环境创建、配置、删除状态全程追踪，支持异常状态重置

### 📦 项目管理
- **一键上传**: 支持 ZIP 包一键上传，自动解压并保留目录结构
- **文件浏览**: 提供在线文件浏览器，支持查看项目文件结构
- **代码编辑**: 支持在线代码编辑，修改实时生效（热重载）
- **工作目录配置**: 支持自定义工作目录和输出目录，灵活适配不同项目结构

### 📊 日志与审计
- **全链路日志**: 实时捕获任务标准输出 (stdout/stderr)，提供持久化存储
- **日志历史**: 支持查看历史执行日志，方便问题排查
- **审计追踪**: 记录所有关键操作（创建、删除、执行），支持按 IP、操作类型、时间范围查询
- **安装日志**: 环境安装和配置过程的完整日志记录

### ⚙️ 系统功能
- **系统监控**: 实时监控系统资源使用情况，包括 CPU、内存、磁盘等
- **数据备份**: 支持数据库备份和恢复功能
- **环境变量管理**: 支持系统级环境变量配置，支持 SECRET 类型加密存储
- **PyPI 镜像配置**: 支持配置 PyPI 镜像源，加速依赖安装
- **数据管理**: 提供数据一致性检查和异常数据清理功能

## 🛠 技术栈

### 后端
| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **Python** | 3.9+ | 运行环境 |
| **FastAPI** | 0.109+ | 高性能异步 Web 框架 |
| **SQLAlchemy** | 2.0+ | ORM 框架，支持异步查询 |
| **APScheduler** | 3.10+ | 强大的后台任务调度引擎 |
| **SQLite** | - | 轻量级数据库，零配置启动 |
| **Pydantic** | 2.6+ | 数据验证和设置管理 |
| **Psutil** | 5.9+ | 系统和进程监控 |

### 前端
| 技术 | 版本 | 说明 |
| :--- | :--- | :--- |
| **Vue** | 3.4+ | 渐进式 JavaScript 框架 |
| **TypeScript** | 5.4+ | 类型安全的 JavaScript 超集 |
| **Vite** | 5.0+ | 下一代前端构建工具 |
| **Pinia** | 2.1+ | Vue 状态管理库 |
| **Vue Router** | 4.3+ | Vue 官方路由管理器 |
| **ECharts** | 6.0+ | 数据可视化图表库 |
| **Monaco Editor** | 0.52+ | VS Code 编辑器核心，用于代码编辑 |
| **Lucide Icons** | 0.556+ | 现代化图标库 |

### 基础设施
| 技术 | 说明 |
| :--- | :--- |
| **Docker** | 容器化部署 |
| **Docker Compose** | 多容器编排 |
| **Conda** | Python 环境管理 |

## 🚀 快速开始

### 前置要求
- [Docker](https://www.docker.com/) 20.10+
- [Docker Compose](https://docs.docker.com/compose/) v2.0+
- 至少 2GB 可用磁盘空间（用于 Conda 环境）

### 安装步骤

1. **克隆仓库**
   ```bash
   git clone https://github.com/YourUsername/Kumo.git
   cd Kumo
   ```

2. **启动服务**
   ```bash
   # 构建镜像并后台启动
   docker-compose up -d --build
   ```
   
   > 💡 **提示**: 首次启动可能需要几分钟时间下载镜像和安装依赖。如果网络较慢，可以配置代理或使用国内镜像源。

3. **访问控制台**
   
   等待约 30 秒，待服务初始化完成后访问：
   - 🖥️ **前端 Dashboard**: [http://localhost:18080](http://localhost:18080)
   - 📚 **后端 API 文档**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - ❤️ **健康检查**: [http://localhost:8000/api/health](http://localhost:8000/api/health)

### 停止服务

```bash
# 停止服务（保留数据）
docker-compose stop

# 停止并删除容器（保留数据）
docker-compose down

# 停止并删除容器和数据卷（⚠️ 危险操作）
docker-compose down -v
```

## ⚙️ 配置说明

### 数据持久化

为保证数据安全，以下目录已映射至宿主机：

| 宿主机路径 | 容器路径 | 说明 |
| :--- | :--- | :--- |
| `./Data` | `/data` | **任务数据输出目录**，任务执行结果建议存放在此 |
| `./backend/data` | `/app/data` | **系统数据库** (SQLite) 与密钥文件 |
| `./backend/projects` | `/app/projects` | **项目代码库**，上传的代码包解压于此 |
| `./backend/envs` | `/app/envs` | **虚拟环境库**，Conda 环境存储位置 |
| `./backend/logs` | `/app/logs` | **日志目录**，任务日志与安装日志 |

### 环境变量

可在 `docker-compose.yml` 中配置以下环境变量：

| 变量名 | 默认值 | 说明 |
| :--- | :--- | :--- |
| `TZ` | `Asia/Shanghai` | 容器时区，确保定时任务准确执行 |
| `PYTHONUNBUFFERED` | `1` | 保证 Python 日志实时输出 |
| `MAX_CONCURRENT_TASKS` | `50` | 最大并发任务数 |
| `PIP_INDEX_URL` | `https://pypi.tuna.tsinghua.edu.cn/simple` | PyPI 镜像源地址 |

### 启用浏览器支持（Selenium/DrissionPage）

如果需要运行使用 Selenium 或 DrissionPage 的项目，需要启用包含 Chromium 的 Dockerfile：

1. 编辑 `docker-compose.yml`
2. 将 `backend` 服务的 `dockerfile: Dockerfile` 改为 `dockerfile: Dockerfile.browser`
3. 重新构建并启动：`docker-compose up -d --build`

## 💡 使用指南

### 1. 创建 Python 环境

1. 进入 **版本管理** 页面
2. 点击 **添加 Python 版本**
3. 选择 Python 版本（如 3.11、3.10、3.9 等）
4. 输入环境名称（可选）
5. 点击 **创建**，等待环境创建完成

> 💡 **提示**: 环境创建过程可能需要几分钟，可以在日志中查看创建进度。

### 2. 安装依赖包

1. 进入 **依赖管理** 页面
2. 选择已创建的 Python 环境
3. 在 **安装包** 标签页输入要安装的包名（支持 conda 或 pip 格式）
   - Conda 格式：`numpy pandas`
   - Pip 格式：`requests beautifulsoup4`
4. 点击 **安装**，实时查看安装日志

### 3. 上传项目代码

1. 进入 **项目管理** 页面
2. 点击 **新建项目**
3. 填写项目信息：
   - 项目名称
   - 上传 ZIP 格式的代码包
   - 工作目录（相对于解压后的根目录，如 `src`）
   - 输出目录（可选，用于任务输出文件）
4. 点击 **创建**，系统会自动解压并保留目录结构

### 4. 创建调度任务

1. 进入 **任务管理** 页面
2. 点击 **新建任务**
3. 配置任务信息：
   - **任务名称**: 任务的唯一标识
   - **关联项目**: 选择已上传的项目
   - **执行环境**: 选择系统环境或自定义虚拟环境
   - **执行命令**: 输入启动命令（如 `python main.py`）
   - **工作目录**: 自动继承项目的工作目录
   - **触发器类型**: 选择 Cron、Interval 或 Date
   - **触发器配置**: 根据类型配置具体参数
   - **重试配置**: 设置失败重试次数和间隔（可选）
   - **超时配置**: 设置任务超时时间（可选）
4. 点击 **创建**，任务将自动添加到调度器

### 5. 查看任务日志

1. 进入 **任务管理** 页面
2. 找到目标任务，点击 **查看日志** 按钮
3. 在日志弹窗中查看实时日志和历史日志

### 6. 系统监控

1. 进入 **仪表盘** 页面
2. 查看系统概览：
   - 任务统计（总数、运行中、成功、失败）
   - 系统资源使用情况（CPU、内存）
   - 最近任务执行记录

## 📁 项目结构

```
Kumo/
├── docker-compose.yml          # Docker Compose 编排文件
├── README.md                   # 项目说明文档
├── ROADMAP.md                  # 开发路线图
├── AGENTS.md                   # 开发规范文档
│
├── backend/                    # FastAPI 后端服务
│   ├── main.py                # 应用入口，初始化数据库和调度器
│   ├── requirements.txt       # Python 依赖列表
│   ├── Dockerfile             # 后端 Docker 镜像（标准版）
│   ├── Dockerfile.browser     # 后端 Docker 镜像（包含 Chromium）
│   │
│   ├── core/                   # 核心模块
│   │   ├── config.py          # 统一配置管理
│   │   ├── database.py         # SQLAlchemy 数据库连接
│   │   ├── security.py         # 密钥管理与加解密
│   │   ├── logging.py          # 统一日志系统
│   │   ├── exceptions.py       # 自定义异常类
│   │   ├── error_handlers.py   # 统一错误处理
│   │   ├── concurrency.py      # 并发控制
│   │   ├── cache.py            # 查询缓存
│   │   └── connection_monitor.py  # 数据库连接监控
│   │
│   ├── task_service/           # 任务调度服务
│   │   ├── task_manager.py     # 任务调度管理
│   │   ├── task_executor.py    # 任务执行逻辑
│   │   ├── process_manager.py  # 进程管理
│   │   ├── resource_monitor.py # 资源监控
│   │   ├── task_router.py      # 任务 API 路由
│   │   ├── models.py           # 任务数据模型
│   │   └── schemas.py          # 任务数据模式
│   │
│   ├── environment_service/    # 环境管理服务
│   │   ├── python_version_router.py  # Python 版本 API
│   │   ├── env_router.py       # 环境管理 API
│   │   ├── models.py           # 环境数据模型
│   │   └── schemas.py          # 环境数据模式
│   │
│   ├── project_service/        # 项目管理服务
│   │   ├── project_router.py   # 项目 API 路由
│   │   ├── models.py           # 项目数据模型
│   │   └── schemas.py          # 项目数据模式
│   │
│   ├── system_service/         # 系统服务
│   │   ├── system_router.py    # 系统 API 路由
│   │   ├── system_scheduler.py # 系统级调度器
│   │   └── ...
│   │
│   ├── log_service/            # 日志服务
│   │   └── logs_router.py      # 日志 API 路由
│   │
│   ├── audit_service/          # 审计服务
│   │   ├── audit_router.py     # 审计 API 路由
│   │   ├── service.py          # 审计服务逻辑
│   │   ├── models.py           # 审计数据模型
│   │   └── schemas.py          # 审计数据模式
│   │
│   ├── migrations/             # 数据库迁移
│   │   └── manager.py          # 迁移管理器
│   │
│   ├── tests/                  # 测试代码
│   │   ├── unit/               # 单元测试
│   │   └── integration/        # 集成测试
│   │
│   ├── data/                   # [持久化] SQLite 数据库
│   ├── projects/               # [持久化] 项目文件存储
│   ├── envs/                   # [持久化] Conda 环境存储
│   └── logs/                   # [持久化] 日志存储
│       ├── tasks/              # 任务执行日志
│       └── install/            # 环境安装日志
│
├── front/                      # Vue 3 前端应用
│   ├── package.json            # 前端依赖配置
│   ├── vite.config.ts          # Vite 构建配置
│   ├── tsconfig.json           # TypeScript 配置
│   ├── Dockerfile              # 前端 Docker 镜像
│   │
│   └── src/
│       ├── main.ts             # 应用入口
│       ├── router/             # 路由配置
│       ├── stores/             # Pinia 状态管理
│       ├── pages/               # 页面组件
│       │   ├── Dashboard.vue   # 仪表盘
│       │   ├── task/            # 任务管理
│       │   ├── project/         # 项目管理
│       │   ├── python/          # Python 环境管理
│       │   ├── logs/            # 日志管理
│       │   └── settings/        # 系统设置
│       ├── components/          # 公共组件
│       └── layout/              # 布局组件
│
└── Data/                       # [输出] 任务产出数据目录
```

## 🏗️ 架构设计

### 后端架构

Kumo 采用模块化设计，各服务职责清晰：

- **core**: 核心基础设施，包括配置管理、数据库连接、日志系统、错误处理、并发控制等
- **task_service**: 任务调度核心，采用模块化设计：
  - `task_manager.py`: 调度管理，负责任务的添加、删除、启停
  - `task_executor.py`: 任务执行，负责环境准备、命令执行、重试逻辑
  - `process_manager.py`: 进程管理，负责进程启动、停止和进程组管理
  - `resource_monitor.py`: 资源监控，负责 CPU 和内存监控
- **environment_service**: Python 环境管理，支持 Conda 环境创建、删除、依赖安装
- **project_service**: 项目管理，支持项目上传、解析、文件浏览
- **system_service**: 系统服务，包括系统配置、统计、备份、文件系统浏览
- **audit_service**: 审计日志，记录所有关键操作
- **log_service**: 日志服务，提供任务日志和安装日志查询

### 前端架构

前端采用 Vue 3 + TypeScript + Vite 构建：

- **路由**: 基于 Vue Router 的单页应用路由
- **状态管理**: 使用 Pinia 进行状态管理
- **UI 组件**: 自定义组件库，基于 Tailwind CSS
- **代码编辑**: 集成 Monaco Editor，支持在线代码编辑
- **数据可视化**: 使用 ECharts 展示系统监控数据

### 数据流

1. **任务创建**: 前端 → API → 数据库 → APScheduler
2. **任务执行**: APScheduler → TaskExecutor → ProcessManager → 日志文件
3. **状态更新**: ProcessManager → ResourceMonitor → 数据库 → 前端轮询
4. **日志查看**: 前端 → API → LogService → 日志文件

## 🔧 开发指南

### 本地开发

#### 后端开发

```bash
# 进入后端目录
cd backend

# 创建虚拟环境（可选）
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 启动开发服务器（支持热重载）
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

#### 前端开发

```bash
# 进入前端目录
cd front

# 安装依赖
npm install

# 启动开发服务器（支持 HMR）
npm run dev
```

### 测试

```bash
# 运行所有测试
cd backend
pytest

# 运行单元测试
pytest tests/unit/

# 运行集成测试
pytest tests/integration/

# 查看测试覆盖率
pytest --cov=. --cov-report=html
```

> 📊 **测试统计**: 当前项目包含 97 个测试用例（79 个单元测试 + 18 个集成测试），全部通过，测试覆盖率达到 95% 以上。

### 代码规范

- **Python**: 遵循 PEP 8 规范，使用类型提示
- **TypeScript**: 使用严格模式，遵循 ESLint 规则
- **提交规范**: 使用清晰的提交信息，参考 [Conventional Commits](https://www.conventionalcommits.org/)

## 📊 性能特性

- **并发控制**: 使用信号量机制限制同时执行的任务数量，防止资源耗尽
- **查询优化**: 使用批量查询和子查询优化，避免 N+1 查询问题
- **缓存机制**: 为频繁查询提供缓存层，支持 TTL，减少数据库压力
- **批量更新**: 资源监控使用批量更新，减少数据库写入频率
- **连接池**: 数据库连接池配置，优化连接管理
- **连接监控**: 监控数据库连接池状态，及时发现连接泄漏

## 🔒 安全特性

- **密钥管理**: 支持环境变量和文件两种方式存储密钥
- **加密存储**: SECRET 类型环境变量使用加密存储
- **路径保护**: 文件操作进行路径穿透保护，防止目录遍历攻击
- **审计日志**: 记录所有关键操作，支持安全审计

## 🐛 故障排查

### 常见问题

1. **服务无法启动**
   - 检查 Docker 和 Docker Compose 版本
   - 查看容器日志：`docker-compose logs backend`
   - 检查端口占用：`netstat -an | grep 8000` 或 `netstat -an | grep 18080`

2. **任务执行失败**
   - 查看任务日志：在任务管理页面点击"查看日志"
   - 检查环境配置：确认 Python 环境和依赖包已正确安装
   - 检查执行命令：确认命令路径和参数正确

3. **环境创建失败**
   - 查看安装日志：在版本管理页面点击"查看详情"
   - 检查磁盘空间：确保有足够的空间创建 Conda 环境
   - 检查网络连接：确认可以访问 Conda 和 PyPI 源

4. **数据库问题**
   - 检查数据库文件权限：`ls -l backend/data/TaskManage.db`
   - 查看数据库日志：检查 `backend/logs/app.log`
   - 使用数据管理工具：在设置页面使用数据管理功能检查数据一致性

## 📚 相关文档

- [开发规范](AGENTS.md) - 项目开发规范和约定
- [架构审查](ARCHITECTURE_REVIEW.md) - 架构设计文档
- [开发路线图](ROADMAP.md) - 项目开发计划和进度
- [API 文档](http://localhost:8000/docs) - 后端 API 接口文档（启动后访问）

## 🤝 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 📄 许可证

MIT License © 2025 Kumo Team

## 🙏 致谢

感谢所有为 Kumo 项目做出贡献的开发者！

---

**Made with ❤️ by Kumo Team**
