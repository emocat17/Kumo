# Kumo Docker 开发环境部署指南

本文档详细描述了如何使用 Docker 和 Docker Compose 将 Kumo 项目容器化，并建立高效的开发环境。

## 1. 项目架构分析与环境需求

### 1.1 后端 (Backend)
- **容器名称**: `backend`
- **技术栈**: FastAPI, SQLAlchemy, APScheduler, Python.
- **基础镜像**: `continuumio/miniconda3`。
    - **原因**: 项目代码 (`appEnv`) 包含 Conda 环境管理逻辑 (`is_conda`)，必须使用 Conda 基础镜像以支持完整功能。
- **关键依赖**:
    - **系统库**: `build-essential`, `git` (用于安装部分 Python 包)。
    - **数据存储**: SQLite (`backend/data/TaskManage.db`)。
    - **文件存储**: 
        - `backend/projects/`: 用户上传的项目代码。
        - `backend/envs/`: 创建的虚拟环境。
        - `backend/logs/`: 任务与安装日志。
- **开发模式**: 使用 `uvicorn --reload` 实现代码热更新。

### 1.2 前端 (Kumo)
- **容器名称**: `Kumo`
- **技术栈**: Vue 3, Vite, TypeScript.
- **基础镜像**: `node:20-alpine`。
- **开发模式**: `npm run dev` 配合 Vite HMR (热模块替换)。
- **网络代理**: 通过 `VITE_API_BASE_URL` 环境变量将 `/api` 请求转发至后端容器。

## 2. 目录结构与文件规划

为了实现容器化，我们将在项目根目录及各子目录下添加以下配置文件：

```text
Kumo/
├── docker-compose.yml          # [新增] 总控编排文件
├── .gitignore                  # [优化] 包含 Docker 和项目特定的忽略规则
├── backend/
│   ├── Dockerfile              # [新增] 后端构建文件
│   ├── .dockerignore           # [新增] 后端构建忽略规则
│   ├── requirements.txt        # [现有]
│   └── ...
├── front/
│   ├── Dockerfile              # [新增] 前端构建文件
│   ├── .dockerignore           # [新增] 前端构建忽略规则
│   ├── package.json            # [现有]
│   └── ...
└── docs/                       # 文档目录
```

## 3. 详细配置说明

### 3.1 后端配置

#### 3.1.1 Dockerfile (`backend/Dockerfile`)

```dockerfile
# 使用 Miniconda3 作为基础镜像，支持 conda 命令
FROM continuumio/miniconda3:latest

# 设置工作目录
WORKDIR /app

# 1. 安装系统级依赖
# build-essential: 编译 Python C 扩展 (如 psutil, cryptography)
# git: 用于 pip 安装 git 依赖
RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 2. 复制依赖文件
COPY requirements.txt .

# 3. 安装 Python 依赖
# 使用 base 环境直接安装，简化开发流程
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

# 4. 暴露端口
EXPOSE 8000

# 5. 启动命令
# 使用 uvicorn 命令行启动以支持 --reload (热重载)
# main:app 指向 main.py 中的 app 对象
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

#### 3.1.2 Docker 忽略文件 (`backend/.dockerignore`)

```text
__pycache__
venv/
.env
.git
.gitignore
data/
logs/
projects/
envs/
```

### 3.2 前端配置

#### 3.2.1 Dockerfile (`front/Dockerfile`)

```dockerfile
# 使用 LTS 版本 Node.js Alpine 镜像
FROM node:20-alpine

# 设置工作目录
WORKDIR /app

# 1. 安装基础工具
RUN apk add --no-cache git

# 2. 复制依赖描述文件 (利用 Docker 缓存层)
COPY package.json package-lock.json* ./

# 3. 安装依赖
RUN npm install

# 4. 暴露 Vite 默认端口
EXPOSE 6677

# 5. 启动开发服务器
# --host 0.0.0.0 允许外部访问容器
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
```

#### 3.2.2 Docker 忽略文件 (`front/.dockerignore`)

```text
node_modules
dist
.git
.gitignore
.env*
```

### 3.3 编排配置 (`docker-compose.yml`)

```yaml
version: '3.8'

services:
  # --- Backend Service ---
  backend:
    container_name: backend
    build:
      context: ./backed
      dockerfile: Dockerfile
    volumes:
      # 1. 代码映射：宿主机修改代码，容器内实时生效 (热重载)
      - ./backed:/app
      
      # 2. 数据持久化：防止重启丢失数据
      - ./backed/data:/app/data        # 数据库 (SQLite)
      - ./backed/projects:/app/projects # 上传的项目文件
      - ./backed/logs:/app/logs        # 运行日志
      - ./backed/envs:/app/envs        # 创建的虚拟环境
      
      # 3. 排除宿主机虚拟环境 (如果存在)
      # - /app/venv
    ports:
      - "8000:8000"
    environment:
      - PYTHONUNBUFFERED=1
    networks:
      - kumo-net
    restart: unless-stopped

  # --- Frontend Service (Kumo) ---
  kumo:
    container_name: Kumo
    build:
      context: ./front
      dockerfile: Dockerfile
    volumes:
      # 1. 代码映射：宿主机修改代码，容器内实时生效 (HMR)
      - ./front:/app
      
      # 2. 依赖隔离：使用匿名卷，防止宿主机 node_modules 覆盖容器内
      # 这解决了 Windows/Linux 二进制不兼容问题
      - /app/node_modules
    ports:
      - "6677:6677"
    environment:
      # 设置 API 代理地址 (指向 backend 容器名)
      - VITE_API_BASE_URL=http://backend:8000
    depends_on:
      - backend
    networks:
      - kumo-net

networks:
  kumo-net:
    driver: bridge
```

## 4. Git 与文件管理策略

为了配合 Docker 开发并保持仓库整洁，已优化 `.gitignore` 策略：

1.  **数据与日志**:
    *   `backed/data/*.db`: 数据库文件被忽略（避免提交测试数据）。
    *   `backed/logs/`: 日志目录被忽略。
    *   `backed/envs/`: 生成的虚拟环境被忽略（体积大且跨平台不兼容）。
    *   `backed/projects/`: 用户上传的项目代码被忽略。
    
    *建议*: 如果需要在仓库中保留目录结构，可以在这些目录下创建 `.gitkeep` 文件，并在 `.gitignore` 中使用 `!backed/data/.gitkeep` 例外规则。

2.  **环境配置**:
    *   `.env`: 包含敏感信息的环境变量文件应被忽略。

3.  **构建产物**:
    *   `node_modules/`, `dist/`, `__pycache__/` 等标准构建产物均已配置忽略。

## 5. 快速开始指南

### 5.1 首次启动

1.  **构建镜像并启动容器**:
    ```bash
    docker-compose up -d --build
    ```
    *   此过程会下载 Miniconda 和 Node 镜像，并安装所有依赖，耗时较长（视网络情况而定）。

2.  **验证服务状态**:
    ```bash
    docker-compose ps
    ```
    确保 `backend` 和 `Kumo` 状态均为 `Up`。

3.  **查看实时日志**:
    ```bash
    docker-compose logs -f
    ```
    *   **Backend**: 应看到 `Uvicorn running on http://0.0.0.0:8000`。
    *   **front**: 应看到 `Local: http://0.0.0.0:6677/`。

4.  **访问应用**:
    *   前端页面 (Kumo): [http://localhost:6677](http://localhost:6677)
    *   后端文档: [http://localhost:8000/docs](http://localhost:8000/docs)

### 5.2 开发工作流

*   **修改后端**: 
    *   编辑 `backed/` 下的 `.py` 文件。
    *   保存后，终端日志会显示 `WARNING: WatchFiles detected changes... Reloading...`，服务自动更新。
*   **修改前端**: 
    *   编辑 `front/src/` 下的 `.vue` 或 `.ts` 文件。
    *   浏览器会自动刷新或热替换模块。
*   **安装新依赖**:
    *   **Python**:
        1. 在 `backed/requirements.txt` 添加包名。
        2. 运行 `docker-compose up -d --build backend`。
    *   **Node**:
        1. `docker exec -it Kumo npm install <package_name>`。
        2. 宿主机的 `package.json` 会同步更新。

## 6. 常见问题排查

1.  **前端报错 "Network Error"**:
    *   检查前端容器环境变量 `VITE_API_BASE_URL` 是否正确设置为 `http://backend:8000`。
    *   在前端容器内执行 `ping backend` 确认网络连通性。

2.  **后端数据库未找到**:
    *   确认宿主机 `backed/data` 目录存在。
    *   Docker 启动时会自动挂载。如果目录为空，应用启动时的 `init_db()` 会自动创建新的 `TaskManage.db`。

3.  **Windows 权限问题**:
    *   如果遇到文件无法保存或权限拒绝，请检查 Docker Desktop 设置中的 "File Sharing" 是否包含了项目所在驱动器。
