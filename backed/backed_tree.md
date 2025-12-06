# TaskManage App Directory Structure

```
D:\GitWorks\TaskManage\app
├─.dockerignore
├─.gitignore
├─main.py
├─requirements.txt
├─app
│   ├─config.py
│   ├─database.py
│   ├─init_data.py
│   ├─main.py
│   ├─scheduler.py
│   ├─update_database.py
│   ├─utils.py
│   └─__init__.py
├─appAuth
│   ├─auth_manager.py
│   ├─auth_router.py
│   └─__init__.py
├─appDistribution
│   ├─distribution_router.py
│   ├─machine_models.py
│   ├─master_service.py
│   └─__init__.py
├─appEnv
│   ├─env_manager.py
│   ├─env_router.py
│   ├─python_version_manager.py
│   ├─python_version_router.py
│   └─__init__.py
├─appLogs
│   ├─logs_router.py
│   ├─log_manager.py
│   └─__init__.py
├─appMetrics
│   ├─metrics_manager.py
│   ├─metrics_router.py
│   └─__init__.py
├─appProject
│   ├─project_manager.py
│   ├─project_router.py
│   └─__init__.py
├─appSettings
│   ├─settings_manager.py
│   ├─settings_router.py
│   └─__init__.py
├─appTask
│   ├─task_manager.py
│   ├─task_router.py
│   └─__init__.py
├─data
│   └─data.db
├─pytransform
│   ├─_pytransform.so
│   └─__init__.py
├─temp
├─utils
│   ├─email_manager.py
│   ├─license_manager.py
│   ├─log_manager.py
│   └─notification_manager.py
```

## Directory Description

- **app/**: Main application directory containing core configuration and functionality modules
- **appAuth/**: Authentication module for user and system authentication
- **appDistribution/**: Distributed management module for handling multiple machines
- **appEnv/**: Environment management module for managing Python environments and versions
- **appLogs/**: Log management module for application logging
- **appMetrics/**: Metrics monitoring module for performance tracking
- **appProject/**: Project management module for handling user projects
- **appSettings/**: Settings management module for application configurations
- **appTask/**: Task management module for handling job execution
- **data/**: Data storage directory containing database files
- **pytransform/**: Encryption-related directory
- **temp/**: Temporary files directory
- **utils/**: Utility functions directory for common helpers
