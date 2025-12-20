# Kumo 开发指南

## 1. 快速启动 (Quick Start)

```bash
# 启动/构建 (全栈容器化)
docker-compose up -d --build

# 重启后端 (Python代码变更生效)
docker-compose restart backend

# 查看日志
docker-compose logs -f backend
```

*   **Frontend**: http://localhost:6677
*   **Backend API**: http://localhost:8000/docs

---

## 2. 技术栈与端口

*   **Backend**: Python 3.9+, FastAPI, SQLAlchemy, APScheduler (Port: **8000**)
*   **Frontend**: Vue 3, Vite, TypeScript, ECharts (Port: **6677**)
*   **Database**: SQLite (`TaskManage.db` inside `/backend/data`)

---

## 3. 核心目录与卷映射

| 宿主机路径 | 容器路径 | 说明 |
| :--- | :--- | :--- |
| `./backend` | `/app` | 后端代码 (热重载) |
| `./front` | `/app` | 前端代码 (热重载) |
| `./Data` | `/data` | **爬虫数据输出** (持久化) |
| `./backend/data` | `/app/data` | 数据库文件存储 |

---

## 4. 开发规范 (AI 维护指南)

1.  **路径处理**: 必须使用 `os.path.join`，严格区分 **Host路径** (Windows) 与 **Container路径** (Linux)。
2.  **文件删除**: 严禁直接使用 `shutil.rmtree`。必须复用 `appEnv` 中的“重命名+延迟删除”逻辑，防止 Windows 文件锁。
3.  **Shell执行**: `subprocess` 调用必须使用 `list` 形式 (如 `['pip', 'install']`)，**禁止** `shell=True`。
4.  **数据库**: 修改 `models.py` 后，需手动在启动逻辑中添加 SQL 同步 Schema (本项目无 Alembic)。
5.  **引用保护**: 删除 Project/Environment 前，**必须先查询 Task 表**。若被引用，后端需返回 400 拒绝操作。
6.  **前端扩展**: 新功能优先扩展 Dashboard Tab 或侧边栏。
7.  **文档更新**: 遇到环境或逻辑变更，必须同步更新此文档。

---

## 5. 核心逻辑速查

*   **Dashboard**: 基于 Tab (`Overview`/`Performance`)，ECharts 图表展示每日任务统计。
*   **Project**: 上传 ZIP 自动解压，`output_dir` 写入数据库，任务执行时自动注入环境变量。
*   **Task**: APScheduler 调度，支持环境自动降级 (Custom Env -> System Python)。
