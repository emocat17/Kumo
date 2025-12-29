# Kumo Backend Directory Structure

```text
D:\GitWorks\Kumo\backend
├── Dockerfile                  # Backend container definition
├── requirements.txt            # Python dependencies
├── main.py                     # Application entry point
├── core/                       # Core infrastructure
│   ├── database.py             # Database connection & session
│   └── security.py             # Encryption & security utils
├── environment_service/        # Python environment management
│   ├── env_router.py           # Environment CRUD API
│   ├── python_version_router.py# Python version API
│   └── models.py               # Environment database models
├── project_service/            # Project file management
│   ├── project_router.py       # Project upload/management API
│   └── models.py               # Project database models
├── task_service/               # Task scheduling & execution
│   ├── task_manager.py         # APScheduler integration
│   ├── task_router.py          # Task control API
│   └── models.py               # Task database models
├── log_service/                # Logging system
│   └── logs_router.py          # Log retrieval API
├── system_service/             # System configuration
│   ├── system_router.py        # System config API
│   ├── env_vars_router.py      # Global environment variables API
│   └── fs_router.py            # File system operations
├── data/                       # Persistent data storage
│   ├── TaskManage.db           # SQLite database
│   └── secret.key              # Encryption key
├── projects/                   # Uploaded project files (unzipped)
├── envs/                       # Created Conda environments
└── logs/                       # Execution logs
```

## Directory Description

- **core/**: Essential infrastructure components like database connections and security utilities.
- **environment_service/**: Manages Python environments (Conda) and Python versions. Handles creation, deletion, and path resolution.
- **project_service/**: Handles project file uploads, storage, and metadata management.
- **task_service/**: Core scheduling engine using APScheduler. Manages task execution, monitoring, and history.
- **log_service/**: Provides access to task execution logs.
- **system_service/**: Manages system-wide configurations, global environment variables, and file system interactions.
- **data/**: Stores persistent data including the SQLite database and encryption keys.
