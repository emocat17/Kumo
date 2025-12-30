# Kumo 开发文档

## 1. 系统架构

*   **技术栈**:
    *   **Backend**: Python 3.9+, FastAPI, SQLAlchemy, APScheduler, Conda. (Port: 8000)
    *   **Frontend**: Vue 3, Vite, TypeScript, Pinia. (Port: 6677)
    *   **Deploy**: Docker Compose (全栈容器化).
---

## 2. 目录结构

```text
D:/GitWorks/Spider_front/
├── docker-compose.yml     # 编排文件
├── Data/                  # 爬虫数据输出
├── backend/               # FastAPI
│   ├── core/              # 核心配置 (database.py, security.py)
│   ├── environment_service/ # 环境管理 (Conda/Python)
│   ├── log_service/       # 日志管理
│   ├── project_service/   # 项目管理 (Project model, Upload)
│   ├── system_service/    # 系统管理 (Config, FS)
│   ├── task_service/      # 任务调度 (APScheduler)
│   ├── projects/          # 项目代码解压区
│   └── envs/              # Conda 环境区
└── front/                 # Vue 3
    ├── src/pages/         # 页面 (Dashboard, Project, Task...)
    ├── src/styles/        # 全局样式 (common.css)
```

---

## 3. 核心机制与实现细节

### 3.1 环境管理 (`environment_service`)
*   **路径处理**: 自动识别宿主机与容器路径差异。
*   **安全删除**: 采用“重命名 (`_trash`) + 延迟删除”策略，解决 Windows 文件锁问题。
*   **删除保护**: **禁止删除**被定时任务引用的环境。

### 3.2 项目管理 (`project_service`)
*   **存储**: ZIP 上传自动解压。
*   **输出路径**: `output_dir` 字段持久化存储于数据库。
*   **环境变量**: 任务执行时自动注入 `OUTPUT_DIR`, `DATA_DIR`。
*   **删除保护**: **禁止删除**被定时任务引用的项目 (Backend 校验 + Frontend 禁用)。

### 3.3 任务调度 (`task_service`)
*   **引擎**: APScheduler (`BackgroundScheduler`)。
*   **流程**: 数据库加载 -> 注入 Env/Path -> `subprocess` 执行 -> 日志重定向。
*   **容错**: 环境路径失效时自动降级为系统默认 Python。

### 3.4 仪表盘 (`Dashboard`)
*   **架构**: 基于 Tab 栏设计 ("系统概览" / "性能配置")。
*   **状态**: 容器内部指标及**任务执行状态**（如正在运行的任务数）每 3 秒自动刷新。

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
8.  **验证**: 每次修改完前端代码后，自己使用chrome mcp工具打开浏览器 http://localhost:6677访问对应修改的页面， 验证功能是否正常。
9.  **测试**: 每次开发完或者修改完一个功能点后就停止测试，确保功能正常，然后停止和我对话说明开发进程。

---

## 6. 前端样式规范 (Frontend Style Guide)

为保持界面一致性，所有页面必须遵循以下样式规范。核心样式定义在 `front/src/styles/common.css` 中。

### 6.1 按钮样式 (Buttons)

所有按钮应使用以下 CSS 类，禁止内联样式或自定义尺寸。

| 类型 | CSS 类 | 适用场景 | 颜色 (Default -> Hover) |
| :--- | :--- | :--- | :--- |
| **主按钮** | `.btn .btn-primary` | 页面主要操作 (新建、保存、确认) | `#1890ff` -> `#40a9ff` |
| **次要按钮** | `.btn .btn-secondary` | 辅助操作 (取消、刷新、上传) | White -> Border `#40a9ff` |
| **危险按钮** | `.btn .btn-danger` | 删除、清理、停止等破坏性操作 | White (Red Border) -> Red |
| **文本按钮** | `.btn-text` | 表格行内操作 (编辑、删除) | Transparent -> `#e6f7ff` |
| **图标按钮** | `.btn-icon` | 紧凑工具栏、卡片操作区 | White -> Border `#1890ff` |

**通用参数**:
*   **高度**: 默认 `36px` (`.btn`), 小号 `32px` (`.btn-sm`), 图标 `32x32px` (`.btn-icon`)
*   **圆角**: `6px` (`.btn`), `4px` (`.btn-icon`)
*   **字体**: `14px`, Weight `500`
*   **阴影**: `box-shadow: 0 2px 0 rgba(0,0,0,0.015)`
*   **交互**: Hover 时 `transform: translateY(-1px)` (除了 Disabled 状态)

**代码示例**:
```html
<!-- 主按钮 -->
<button class="btn btn-primary">
  <PlusIcon :size="18" /> 新建任务
</button>

<!-- 危险操作 -->
<button class="btn btn-danger">
  <Trash2Icon :size="16" /> 删除
</button>

<!-- 表格内操作 -->
<button class="btn-text" @click="edit">编辑</button>
<button class="btn-text text-red" @click="remove">删除</button>
```

### 6.2 Tab 样式 (Tabs)

Tab 组件用于页面内模块切换，样式必须统一。

*   **布局**: 顶部水平排列，底部边框分隔。
*   **交互**: 点击切换，选中项底部有蓝色高亮条 (`#1890ff`)。
*   **过渡**: 内容区域建议使用 `<transition name="fade" mode="out-in">` 实现平滑切换。

**CSS 类**:
*   `.tabs`: 容器，`display: flex; gap: 32px;`
*   `.tab-btn`: 按钮，无背景，选中时加粗并显示底部高亮。

**代码示例**:
```html
<div class="tabs">
  <button 
    :class="['tab-btn', { active: activeTab === 'python' }]" 
    @click="activeTab = 'python'"
  >
    Python 环境配置
  </button>
  <button 
    :class="['tab-btn', { active: activeTab === 'env' }]" 
    @click="activeTab = 'env'"
  >
    全局环境变量
  </button>
</div>
```

### 6.3 维护流程

1.  **新增样式**: 优先复用 `common.css` 中的类。若需新增全局组件样式，必须添加到 `common.css` 并在此文档记录。
2.  **样式变更**: 修改 `common.css` 后，必须检查所有受影响页面 (`Tasks`, `Projects`, `Settings`, `Logs`) 确保无视觉回归。
3.  **文档更新**: 每次样式重构后，立即更新此章节。
