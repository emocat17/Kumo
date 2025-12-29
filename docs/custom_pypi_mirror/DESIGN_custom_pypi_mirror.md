# DESIGN: 自定义 PyPI 镜像源配置

## 1. 整体架构

本功能涉及后端数据库变更、API 扩展以及前端界面新增。核心逻辑是在执行 `pip install` 时注入镜像源参数。

### 架构图 (Mermaid)

```mermaid
graph TD
    A[前端 Settings 页面] -->|GET /api/system/config| B[后端 System Router]
    A -->|POST /api/system/config| B
    B -->|CRUD| C[TaskManage.db (system_configs 表)]
    
    D[前端 Environments 页面] -->|POST /api/env/{id}/packages| E[后端 Env Router]
    E -->|查询| C
    E -->|拼接 -i mirror_url| F[subprocess.Popen]
    F -->|执行安装| G[Python 环境]
```

## 2. 模块设计

### 2.1 数据库设计 (Database)

在 `backend/appSystem/models.py` 中新增 `SystemConfig` 模型。

```python
class SystemConfig(Base):
    __tablename__ = "system_configs"

    key = Column(String, primary_key=True, index=True) # e.g., "pypi_mirror"
    value = Column(String) # e.g., "https://mirrors.aliyun.com/pypi/simple/"
    description = Column(String, nullable=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

### 2.2 后端接口 (Backend API)

**Location**: `backend/appSystem/system_router.py`

1.  `GET /system/config`: 获取所有配置或特定配置。
    *   Response: `{"pypi_mirror": "..."}`
2.  `POST /system/config`: 更新配置。
    *   Body: `{"key": "pypi_mirror", "value": "..."}`

**Location**: `backend/appEnv/env_router.py`

*   修改 `install_packages` 函数，查询 `SystemConfig` 表获取 `pypi_mirror`，若存在则在命令中添加 `-i <url>`。

### 2.3 前端设计 (Frontend)

1.  **新增页面**: `src/pages/Settings.vue`
    *   包含 "常规设置" 面板。
    *   表单项: "PyPI 镜像源地址" (Input text).
    *   常用源快捷选择 (阿里云, 清华, 豆瓣, 官方).
2.  **路由注册**: `src/router/index.ts` 添加 `/settings`.
3.  **导航栏**: `src/layout/MainLayout.vue` 添加 "设置" 菜单入口。

## 3. 接口契约

### 3.1 获取配置
**GET** `/api/system/config`
Response:
```json
[
  {
    "key": "pypi_mirror",
    "value": "https://mirrors.aliyun.com/pypi/simple/",
    "description": "PyPI Mirror URL"
  }
]
```

### 3.2 更新配置
**POST** `/api/system/config`
Request:
```json
{
  "key": "pypi_mirror",
  "value": "https://mirrors.aliyun.com/pypi/simple/"
}
```

## 4. 异常处理

- **数据库读取失败**: 记录日志，使用默认官方源。
- **配置格式错误**: 前端校验 URL 格式。
- **镜像源不可用**: `pip install` 会报错，用户需自行排查或更换源。

