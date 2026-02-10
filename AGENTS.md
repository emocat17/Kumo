# Kumo 开发规范
# 当重要的相关配置发生变化的时候,合适的调整本文件:`AGENTS.md`
## 项目定位
- Kumo 是一个 Python 脚本管理平台，用于调度与运行 Python 脚本项目（如简单脚本、Playwright、Selenium 等）
- 平台支持创建隔离的 Python 环境（Conda），并以任务为核心进行执行与日志记录

## 技术栈
- 后端：FastAPI + SQLAlchemy + APScheduler + SQLite + Psutil
- 前端：Vue 3 + Vite + TypeScript + Pinia
- 运行环境：Docker + Docker Compose + Conda

## 运行方式与热重载
- 当前项目已经使用 docker-compose up -d --build 启动
- 项目使用热重载和文件映射，所以当前修改的文件内容会直接同步到容器，无需重复启动前后端
- 默认端口：前端 6677，后端 8000

## 目录结构约定
- backend：后端服务与业务模块
- front：前端应用
- Data：任务产出数据目录（容器内 /data）
- backend/data：SQLite 数据库与备份目录
- backend/projects：上传项目解压目录
- backend/envs：Conda 环境目录
- backend/logs：任务与安装日志

## 后端模块划分
- main.py：应用入口，初始化数据库、任务调度与系统调度
- core/database.py：SQLAlchemy 引擎与 Session
- core/security.py：密钥与加解密
- environment_service：Python 版本与环境管理
- project_service：项目上传、解析与目录管理
- task_service：任务调度与执行逻辑
- log_service：任务日志读取
- system_service：系统配置、系统统计、备份、文件系统浏览
- audit_service：审计日志

## 数据模型与配置
- Project：项目名称、路径、工作目录、输出目录
- PythonVersion：解释器路径、版本、Conda 标记
- Task：执行命令、触发器、重试与超时配置
- EnvironmentVariable：系统级环境变量，支持 SECRET 加密
- SystemConfig：系统配置（备份、代理、PyPI 镜像等）

## 任务执行流程
- 任务由 APScheduler 调度，通过 task_manager 执行
- 执行前注入全局环境变量、代理与 OUTPUT_DIR
- 任务执行使用 subprocess.Popen，输出统一写入 logs/tasks
- 超时与失败自动进入重试逻辑
- 执行时同步记录 CPU 与内存峰值

## 环境管理规则
- Conda 环境创建通过后台线程执行并记录状态
- 安装依赖时优先使用 python -m pip，必要时切换 conda install
- 执行命令如以 python 开头会替换为环境对应解释器

## 项目管理规则
- 项目上传只接受 ZIP，解压后进入 backend/projects
- work_dir 作为执行目录相对路径
- output_dir 用于任务输出目录注入与映射
- 支持项目框架检测（scrapy/playwright/selenium 等）

## 日志与审计
- 任务日志：backend/logs/tasks
- 安装日志：backend/logs/install
- 关键操作写入审计表 audit_logs

## 安全与路径规范
- SECRET 类型环境变量只存储加密文本
- 密钥优先读取 KUMO_SECRET_KEY，其次读取 data/secret.key
- 文件保存与浏览必须做路径穿透保护与存在性校验

## 前端结构规则
- 页面路由集中在 src/router/index.ts
- 页面组件集中在 src/pages
- 公共组件集中在 src/components
- API 基址默认 http://localhost:8000/api

## 编码规范
### 通用规范
- 避免不必要的对象复制或克隆
- 避免多层嵌套，提前返回
- 使用适当的并发控制机制

### 代码可读性
#### 命名约定
- 使用有意义的、描述性的名称
- 遵循项目或语言的命名规范
- 避免缩写和单字母变量（除非是约定俗成的，如循环中的 i）

#### 代码组织
- 相关代码放在一起
- 一个函数只做一件事
- 保持适当的抽象层次

#### 注释与文档
- 注释应该解释为什么，而不是做什么
- 为公共 API 提供清晰的文档
- 更新注释以反映代码变化

### 性能优化
#### 内存优化
- 避免不必要的对象创建
- 及时释放不再需要的资源
- 注意内存泄漏问题

#### 计算优化
- 避免重复计算
- 使用适当的数据结构和算法
- 延迟计算直到必要时

#### 并行优化
- 识别可并行化的任务
- 避免不必要的同步
- 注意线程安全问题

## 开发一致性规则
- 后端新增功能需同步更新 schemas、models 与路由
- 前端新增页面需路由注册并复用既有组件样式
- 输出目录与文件系统操作必须兼容 Docker 路径映射
