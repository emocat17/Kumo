# Kumo (Spider_front) 开发文档

## 1. 系统架构

*   **技术栈**:
    *   **Backend**: Python 3.9+, FastAPI, SQLAlchemy, APScheduler, Conda. (Port: 8000)
    *   **Frontend**: Vue 3, Vite, TypeScript, Pinia. (Port: 6677)
    *   **Deploy**: Docker Compose (全栈容器化).

*   **核心卷映射 (Volume Mapping)**:
    | 宿主机路径       | 容器路径    | 用途                                |
    | :--------------- | :---------- | :---------------------------------- |
    | `./backend`      | `/app`      | 后端代码热重载                      |
    | `./front`        | `/app`      | 前端代码热重载                      |
    | `./Data`         | `/data`     | **爬虫数据输出** (直接映射到宿主机) |
    | `./backend/data` | `/app/data` | SQLite 数据库 (`TaskManage.db`)     |

---

## 2. 目录结构

```text
D:/GitWorks/Spider_front/
├── docker-compose.yml     # 编排文件
├── Data/                  # 爬虫数据输出
├── backend/               # FastAPI
│   ├── app/               # 核心配置 (database.py)
│   ├── appEnv/            # 环境管理 (Conda/Python)
│   ├── appProject/        # 项目管理 (Project model, Upload)
│   ├── appTask/           # 任务调度 (APScheduler)
│   ├── projects/          # 项目代码解压区
│   └── envs/              # Conda 环境区
└── front/                 # Vue 3
    ├── src/pages/         # 页面 (Dashboard, Project, Task...)
```

---

## 3. 核心机制与实现细节

### 3.1 环境管理 (`appEnv`)
*   **路径处理**: 自动识别宿主机与容器路径差异。
*   **安全删除**: 采用“重命名 (`_trash`) + 延迟删除”策略，解决 Windows 文件锁问题。
*   **删除保护**: **禁止删除**被定时任务引用的环境。

### 3.2 项目管理 (`appProject`)
*   **存储**: ZIP 上传自动解压。
*   **输出路径**: `output_dir` 字段持久化存储于数据库。
*   **环境变量**: 任务执行时自动注入 `OUTPUT_DIR`, `DATA_DIR`。
*   **删除保护**: **禁止删除**被定时任务引用的项目 (Backend 校验 + Frontend 禁用)。

### 3.3 任务调度 (`appTask`)
*   **引擎**: APScheduler (`BackgroundScheduler`)。
*   **流程**: 数据库加载 -> 注入 Env/Path -> `subprocess` 执行 -> 日志重定向。
*   **容错**: 环境路径失效时自动降级为系统默认 Python。

### 3.4 仪表盘 (`Dashboard`)
*   **架构**: 基于 Tab 栏设计 ("系统概览" / "性能配置")。
*   **状态**: 容器内部指标每 3 秒自动刷新。

---

## 4. 开发与运行

```bash
# 启动/构建
docker-compose up -d --build

# 重启后端 (配置变更)
docker-compose restart backend

# 查看日志
docker-compose logs -f backend
```
*   **Frontend**: http://localhost:6677
*   **API Docs**: http://localhost:8000/docs

---

## 5. 开发规范 (AI 维护指南)

1.  **路径兼容**: 必须使用 `os.path.join`。注意区分 Host 路径与 Container 路径。
2.  **文件操作**: 严禁直接使用 `shutil.rmtree` 删除被占用的目录，必须复用现有的安全删除逻辑。
3.  **Shell 安全**: 执行系统命令 (`pip`, `python`) 必须使用 `list` 参数形式，禁止 `shell=True`。
4.  **数据库变更**: 修改 `models.py` 后，需在 Router 启动逻辑中添加 SQL 语句手动同步 Schema (无 Alembic)。
5.  **引用完整性**: 删除 Project/Environment 前，**必须查询 Task 表**。若存在引用，后端抛出 400，前端阻断操作。
6.  **前端扩展**: 新增功能模块建议扩展 Dashboard Tab 或侧边栏，保持 UI 结构一致。
7.  **不断进化完善**: 若开发过程中根据此文档开发遇到错误，在正确修复后，**必须更新此文档**，记录修复过程，保持此文档永久真确。将所有修复过程记录在`/dev`中，确保后续开发人员能够正确理解并避免相同错误。
