# ACCEPTANCE: 环境变量管理系统

## 任务概览
**任务**: 1.1 环境管理模块 - 环境变量管理系统
**状态**: 已完成
**日期**: 2025-12-29

## 验收清单

### 1. 安全模块
- [x] **加密工具**: `backend/app/security.py` 实现了基于 Fernet 的加密/解密。
- [x] **密钥管理**: 自动生成 `secret.key` 存储于 `backend/data/` 目录。

### 2. 数据库模型
- [x] **表结构**: `environment_variables` 表已创建，包含 `key`, `value` (加密), `is_secret` 等字段。
- [x] **迁移**: `main.py` 重启时自动建表。

### 3. 后端 API
- [x] **CRUD**: 实现了 `/api/system/env-vars` 的增删改查。
- [x] **脱敏**: 对于 `is_secret=True` 的变量，GET 请求返回 `******`。
- [x] **更新逻辑**: 只有在提供非空/非Mask值时才更新 Value，支持 Secret 状态切换。

### 4. 任务注入
- [x] **Task Manager**: 修改 `task_manager.py`，在 `subprocess.Popen` 前查询并解密所有环境变量注入 `env` 参数。
- [x] **优先级**: 注入的变量会覆盖系统原有同名变量。

### 5. 前端界面
- [x] **管理表格**: 在设置页面新增"全局环境变量"板块。
- [x] **操作**: 支持新增、编辑、删除。
- [x] **体验**: Secret 变量显示 Badge 和 Mask 值。

## 验证记录

### API 测试
```bash
# 创建 Secret 变量
Invoke-RestMethod -Uri "http://localhost:8000/api/system/env-vars" -Method Post -Body '{"key":"TEST_SECRET","value":"my_secret_key","is_secret":true,"description":"Secret Test"}' -ContentType "application/json"
# 响应: value: ******

# 创建 Public 变量
Invoke-RestMethod -Uri "http://localhost:8000/api/system/env-vars" -Method Post -Body '{"key":"TEST_PUBLIC","value":"public_val","is_secret":false,"description":"Public Test"}' -ContentType "application/json"
# 响应: value: public_val
```

### 注入逻辑审查
代码片段 `backend/appTask/task_manager.py`:
```python
kumo_env_vars = db.query(system_models.EnvironmentVariable).all()
for ev in kumo_env_vars:
    if ev.is_secret:
        val = decrypt_value(ev.value)
    else:
        val = ev.value
    env_vars[ev.key] = val
```
逻辑正确，且包含异常捕获。

## 结论
环境变量管理系统开发完成，满足所有验收标准。
