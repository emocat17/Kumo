import os
import shutil
import zipfile
import py7zr
import rarfile
import platform
import subprocess
import time
import stat
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Request
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from core.config import settings
from core.logging import get_logger
from project_service import models, schemas
from task_service.models import Task
import datetime
from pydantic import BaseModel
from audit_service.service import create_audit_log

router = APIRouter()
logger = get_logger(__name__)

# 使用配置中的项目目录
PROJECTS_DIR = settings.projects_dir

if not os.path.exists(PROJECTS_DIR):
    os.makedirs(PROJECTS_DIR)

def get_archive_extension(filename: str):
    if not filename:
        return ""
    _, ext = os.path.splitext(filename)
    return ext.lower()

def extract_archive(archive_path: str, ext: str, dest_dir: str):
    if ext == ".zip":
        if not zipfile.is_zipfile(archive_path):
            raise Exception("Uploaded file is not a valid zip file")
        with zipfile.ZipFile(archive_path, 'r') as zip_ref:
            zip_ref.extractall(dest_dir)
        return
    if ext == ".7z":
        if not py7zr.is_7zfile(archive_path):
            raise Exception("Uploaded file is not a valid 7z file")
        with py7zr.SevenZipFile(archive_path, mode='r') as archive:
            archive.extractall(dest_dir)
        return
    if ext == ".rar":
        if not rarfile.is_rarfile(archive_path):
            raise Exception("Uploaded file is not a valid rar file")
        with rarfile.RarFile(archive_path, 'r') as archive:
            archive.extractall(dest_dir)
        return
    raise Exception("Unsupported archive format")

def read_text_file(path: str):
    for encoding in ["utf-8", "utf-8-sig", "gb18030"]:
        try:
            with open(path, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return f.read()

@router.get("", response_model=List[schemas.Project])
def list_projects(db: Session = Depends(get_db)):
    """
    获取所有项目列表
    
    返回系统中所有已创建的项目，包括项目的基本信息：
    - id: 项目 ID
    - name: 项目名称
    - path: 项目文件路径
    - work_dir: 工作目录（相对路径）
    - output_dir: 输出目录
    - description: 项目描述
    - created_at: 创建时间
    - updated_at: 更新时间
    
    **返回示例**:
    ```json
    [
        {
            "id": 1,
            "name": "MyProject",
            "path": "/path/to/projects/MyProject",
            "work_dir": "./",
            "output_dir": "/data/output",
            "description": "项目描述",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]
    ```
    """
    return db.query(models.Project).all()

@router.get("/{project_id}", response_model=schemas.Project)
def get_project(project_id: int, db: Session = Depends(get_db)):
    """
    获取指定项目的详细信息
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    
    **返回**: 项目详细信息
    
    **错误响应**:
    - `404`: 项目不存在
    
    **返回示例**:
    ```json
    {
        "id": 1,
        "name": "MyProject",
        "path": "/path/to/projects/MyProject",
        "work_dir": "./",
        "output_dir": "/data/output",
        "description": "项目描述",
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    ```
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.post("/create", response_model=schemas.Project)
def create_project(
    request: Request,
    name: str = Form(...),
    work_dir: str = Form("./"),
    output_dir: str = Form(None),
    description: str = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    创建新项目（上传并解压项目文件）
    
    通过上传压缩包（ZIP、7Z、RAR）创建新项目。系统会自动解压文件并创建项目记录。
    
    **参数**:
    - **name**: 项目名称（必填，不能重复）
    - **work_dir**: 工作目录相对路径（默认: "./"）
    - **output_dir**: 输出目录（可选）
    - **description**: 项目描述（可选）
    - **file**: 项目压缩包文件（必填，支持 .zip, .7z, .rar）
    
    **支持的压缩格式**:
    - ZIP (.zip)
    - 7Z (.7z)
    - RAR (.rar)
    
    **流程**:
    1. 验证项目名称唯一性
    2. 创建项目目录
    3. 保存并解压上传的文件
    4. 创建数据库记录
    5. 记录审计日志
    
    **错误响应**:
    - `400`: 项目名称已存在、目录已存在、不支持的压缩格式
    - `500`: 文件处理失败
    
    **返回**: 创建的项目对象
    
    **示例请求**:
    ```bash
    curl -X POST "http://localhost:8000/api/projects/create" \\
      -F "name=MyProject" \\
      -F "work_dir=./" \\
      -F "output_dir=/data/output" \\
      -F "description=项目描述" \\
      -F "file=@project.zip"
    ```
    """
    # 1. Check if name exists
    if db.query(models.Project).filter(models.Project.name == name).first():
        raise HTTPException(status_code=400, detail="Project name already exists")

    # 2. Prepare path
    # Sanitize name
    safe_name = "".join([c for c in name if c.isalpha() or c.isdigit() or c in ('-', '_')]).strip()
    project_path = os.path.join(PROJECTS_DIR, safe_name)
    
    if os.path.exists(project_path):
            raise HTTPException(status_code=400, detail="Project directory already exists")

    os.makedirs(project_path)

    # 3. Save and Unzip
    ext = get_archive_extension(file.filename)
    if ext not in [".zip", ".7z", ".rar"]:
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        raise HTTPException(status_code=400, detail="Only .zip, .7z, .rar archives are supported")

    archive_path = os.path.join(project_path, f"upload{ext}")
    try:
        with open(archive_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        extract_archive(archive_path, ext, project_path)
        os.remove(archive_path)

    except Exception as e:
        if os.path.exists(project_path):
            shutil.rmtree(project_path) # Cleanup
        raise HTTPException(status_code=500, detail=f"Failed to process archive: {str(e)}")

    # 4. Create DB Record
    db_project = models.Project(
        name=name,
        path=project_path,
        work_dir=work_dir,
        output_dir=output_dir,
        description=description,
        created_at=datetime.datetime.now(),
        updated_at=datetime.datetime.now()
    )
    db.add(db_project)
    db.commit()
    db.refresh(db_project)
    
    create_audit_log(
        db=db,
        operation_type="CREATE",
        target_type="PROJECT",
        target_id=str(db_project.id),
        target_name=db_project.name,
        details=f"Created project '{db_project.name}'",
        operator_ip=request.client.host
    )

    return db_project

@router.get("/{project_id}/detect", response_model=dict)
def detect_project_framework(project_id: int, db: Session = Depends(get_db)):
    """
    检测项目的框架类型和推荐执行命令
    
    自动检测项目使用的框架（Scrapy、Playwright、Selenium、DrissionPage 等），
    并返回推荐的任务执行命令。
    
    **参数**:
    - **project_id**: 项目 ID
    
    **检测逻辑**:
    1. **Scrapy**: 检测 `scrapy.cfg` 文件，自动查找 spider 名称
    2. **其他框架**: 扫描 `requirements.txt` 和 Python 文件中的导入语句
    3. **通用 Python**: 检测 `main.py` 或 `app.py` 文件
    
    **返回**:
    ```json
    {
        "framework": "scrapy|playwright|selenium|drissionpage|python|unknown",
        "command": "推荐执行命令",
        "description": "检测结果描述"
    }
    ```
    
    **示例返回**:
    ```json
    {
        "framework": "scrapy",
        "command": "scrapy crawl myspider",
        "description": "Detected Scrapy project"
    }
    ```
    
    **错误响应**:
    - `404`: 项目不存在
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    path = project.path
    if project.work_dir and project.work_dir != "./":
        path = os.path.join(path, project.work_dir)
        
    if not os.path.exists(path):
         return {"framework": "unknown", "command": ""}

    # 1. Check for Scrapy
    if os.path.exists(os.path.join(path, "scrapy.cfg")):
        # Try to find spider name
        spider_name = "myspider"
        # Simple heuristic: look for spiders folder
        # Usually: project_name/spiders
        # We can walk depth 2
        for root, dirs, files in os.walk(path):
            if "spiders" in dirs:
                spiders_dir = os.path.join(root, "spiders")
                for f in os.listdir(spiders_dir):
                    if f.endswith(".py") and f != "__init__.py":
                        # Try to read name
                        try:
                            with open(os.path.join(spiders_dir, f), 'r', encoding='utf-8') as pf:
                                content = pf.read()
                                import re
                                match = re.search(r"name\s*=\s*['\"](.+?)['\"]", content)
                                if match:
                                    spider_name = match.group(1)
                                    break
                        except Exception:
                            pass
                break
                
        return {
            "framework": "scrapy", 
            "command": f"scrapy crawl {spider_name}",
            "description": "Detected Scrapy project"
        }

    # 2. Advanced Detection: Check requirements.txt or imports for other frameworks
    detected_framework = None
    
    # Helper to check content
    def check_file_content(filepath, keywords):
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read().lower()
                for k in keywords:
                    if k.lower() in content:
                        return k
        except Exception:
            pass
        return None

    # Check requirements.txt
    req_path = os.path.join(path, "requirements.txt")
    if os.path.exists(req_path):
        fw = check_file_content(req_path, ["playwright", "selenium", "DrissionPage"])
        if fw:
            detected_framework = fw

    # If not found in requirements, scan python files (shallow scan)
    if not detected_framework:
        for root, dirs, files in os.walk(path):
            if root != path: continue # Only scan root for efficiency
            for f in files:
                if f.endswith(".py"):
                    fw = check_file_content(os.path.join(root, f), ["playwright", "selenium", "DrissionPage"])
                    if fw:
                        detected_framework = fw
                        break
            if detected_framework: break

    # Determine command based on file existence
    command = "python main.py"
    desc_suffix = ""
    
    if os.path.exists(os.path.join(path, "main.py")):
        command = "python main.py"
        desc_suffix = " (main.py)"
    elif os.path.exists(os.path.join(path, "app.py")):
        command = "python app.py"
        desc_suffix = " (app.py)"
    else:
        command = "python script.py"
        desc_suffix = " (Generic)"

    if detected_framework:
        # Normalize name
        fw_name = detected_framework
        if fw_name.lower() == "drissionpage": fw_name = "DrissionPage"
        elif fw_name.lower() == "playwright": fw_name = "Playwright"
        elif fw_name.lower() == "selenium": fw_name = "Selenium"
        
        return {
            "framework": fw_name.lower(),
            "command": command,
            "description": f"Detected {fw_name} project{desc_suffix}"
        }

    # 3. Fallback: Generic Python
    if os.path.exists(os.path.join(path, "main.py")):
        return {
            "framework": "python",
            "command": "python main.py",
            "description": "Detected main.py"
        }
        
    if os.path.exists(os.path.join(path, "app.py")):
        return {
            "framework": "python",
            "command": "python app.py",
            "description": "Detected app.py"
        }

    # 4. Check for requirements.txt but no main script
    if os.path.exists(os.path.join(path, "requirements.txt")):
         return {
            "framework": "python",
            "command": "python script.py",
            "description": "Detected requirements.txt"
        }

    return {"framework": "unknown", "command": ""}

@router.put("/{project_id}", response_model=schemas.Project)
def update_project(
    project_id: int,
    project_in: schemas.ProjectUpdate,
    request: Request,
    db: Session = Depends(get_db)
):
    """
    更新项目信息
    
    更新项目的名称、工作目录、输出目录和描述等信息。
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    - **project_in**: 项目更新数据（请求体）
      - name: 项目名称（可选）
      - work_dir: 工作目录（可选）
      - output_dir: 输出目录（可选）
      - description: 项目描述（可选）
    
    **验证规则**:
    - 如果更新名称，会检查新名称是否已存在（排除当前项目）
    
    **返回**: 更新后的项目对象
    
    **错误响应**:
    - `404`: 项目不存在
    - `400`: 项目名称已存在
    
    **示例请求**:
    ```json
    {
        "name": "UpdatedProjectName",
        "work_dir": "./src",
        "output_dir": "/data/new_output",
        "description": "更新后的描述"
    }
    ```
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if project_in.name is not None:
        # Check if name exists (excluding self)
        existing = db.query(models.Project).filter(models.Project.name == project_in.name).filter(models.Project.id != project_id).first()
        if existing:
            raise HTTPException(status_code=400, detail="Project name already exists")
        project.name = project_in.name

    if project_in.work_dir is not None:
        project.work_dir = project_in.work_dir
        
    if project_in.output_dir is not None:
        project.output_dir = project_in.output_dir
        
    if project_in.description is not None:
        project.description = project_in.description

    project.updated_at = datetime.datetime.now()
    db.commit()
    db.refresh(project)
    
    create_audit_log(
        db=db,
        operation_type="UPDATE",
        target_type="PROJECT",
        target_id=str(project.id),
        target_name=project.name,
        details=f"Updated project '{project.name}'",
        operator_ip=request.client.host
    )
    
    return project

# Helper to remove read-only files (fixes Windows deletion issues)
def remove_readonly(func, path, excinfo):
    os.chmod(path, stat.S_IWRITE)
    func(path)

@router.delete("/{project_id}")
def delete_project(project_id: int, request: Request, db: Session = Depends(get_db)):
    """
    删除项目
    
    删除项目及其文件目录。如果项目被任务引用，则无法删除。
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    
    **删除流程**:
    1. 检查项目是否被任务引用
    2. 记录审计日志
    3. 删除项目文件目录（支持 Windows 和 Linux）
    4. 删除数据库记录
    
    **安全措施**:
    - 防止删除被任务使用的项目
    - 使用安全的文件删除方法（处理只读文件）
    - Windows 系统使用重命名 + 多次重试策略
    
    **返回**:
    ```json
    {
        "message": "Project deleted"
    }
    ```
    
    **错误响应**:
    - `404`: 项目不存在
    - `400`: 项目正在被任务使用，无法删除
    
    **注意**: 删除操作不可逆，请谨慎操作。
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Check if used by any task
    related_tasks = db.query(Task).filter(Task.project_id == project_id).all()
    if related_tasks:
        task_names = ", ".join([t.name for t in related_tasks])
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete project: It is currently used by tasks: {task_names}"
        )

    # Audit Log
    create_audit_log(
        db=db,
        operation_type="DELETE",
        target_type="PROJECT",
        target_id=str(project.id),
        target_name=project.name,
        details=f"Deleted project '{project.name}'",
        operator_ip=request.client.host
    )

    # Remove directory with robust logic
    if os.path.exists(project.path):
        logger.info(f"Deleting project directory: {project.path}")
        
        # 1. Rename to trash (Windows trick to unlock name immediately)
        target_dir = project.path
        try:
            timestamp = int(time.time())
            trash_dir = f"{project.path}_trash_{timestamp}"
            os.rename(project.path, trash_dir)
            target_dir = trash_dir
        except Exception as e:
            logger.warning(f"Rename failed: {e}")
            
        # 2. Robust cleanup loop
        max_retries = 5
        for i in range(max_retries):
            if not os.path.exists(target_dir):
                break
            
            try:
                shutil.rmtree(target_dir, onerror=remove_readonly)
            except Exception as e:
                logger.warning(f"shutil.rmtree failed: {e}")
                
            if not os.path.exists(target_dir):
                break
                
            # Windows force delete
            if platform.system() == "Windows":
                try:
                    subprocess.run(f'icacls "{target_dir}" /grant Everyone:F /T /C /Q', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(f'del /f /s /q /a "{target_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    subprocess.run(f'rmdir /s /q "{target_dir}"', shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                except Exception:
                    pass
            
            time.sleep(1)
            
    db.delete(project)
    db.commit()
    return {"message": "Project deleted"}

def build_file_tree(base_path, rel_path=""):
    items = []
    # Ensure base_path doesn't end with slash to avoid double slash issues, though join handles it
    full_path = os.path.join(base_path, rel_path)
    
    if not os.path.exists(full_path):
        return []

    try:
        for entry in os.scandir(full_path):
            if entry.name == '__pycache__' or entry.name.startswith('.'):
                continue
                
            entry_rel_path = os.path.join(rel_path, entry.name).replace("\\", "/")
            item = {
                "label": entry.name,
                "path": entry_rel_path,
                "type": "dir" if entry.is_dir() else "file",
            }
            if entry.is_dir():
                item["children"] = build_file_tree(base_path, entry_rel_path)
            items.append(item)
    except PermissionError:
        pass # Skip unreadable directories
    
    # Sort: directories first, then files
    items.sort(key=lambda x: (0 if x["type"] == "dir" else 1, x["label"].lower()))
    return items

@router.get("/{project_id}/files")
def get_project_files(project_id: int, db: Session = Depends(get_db)):
    """
    获取项目的文件树结构
    
    返回项目的文件树结构，用于前端展示项目文件列表。
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    
    **返回格式**:
    返回树形结构，每个节点包含：
    - label: 文件/目录名称
    - path: 相对路径
    - type: "dir" 或 "file"
    - children: 子节点数组（仅目录有）
    
    **过滤规则**:
    - 自动跳过 `__pycache__` 目录
    - 自动跳过以 `.` 开头的隐藏文件/目录
    
    **排序规则**:
    - 目录优先，文件在后
    - 按名称字母顺序排序（不区分大小写）
    
    **返回示例**:
    ```json
    [
        {
            "label": "src",
            "path": "src",
            "type": "dir",
            "children": [
                {
                    "label": "main.py",
                    "path": "src/main.py",
                    "type": "file"
                }
            ]
        },
        {
            "label": "README.md",
            "path": "README.md",
            "type": "file"
        }
    ]
    ```
    
    **错误响应**:
    - `404`: 项目不存在
    
    **注意**: 如果项目目录不存在，返回空数组。
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    if not os.path.exists(project.path):
        return []
        
    return build_file_tree(project.path)

@router.get("/{project_id}/files/content")
def get_file_content(project_id: int, path: str, db: Session = Depends(get_db)):
    """
    获取项目文件的内容
    
    读取项目中的文本文件内容，支持多种编码格式自动检测。
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    - **path**: 文件相对路径（查询参数）
    
    **编码支持**:
    按顺序尝试以下编码：
    1. UTF-8
    2. UTF-8 with BOM
    3. GB18030（中文）
    4. UTF-8 with error replacement（最后兜底）
    
    **安全措施**:
    - 路径穿透保护：确保文件路径在项目目录内
    - 仅允许读取文件，不允许目录
    
    **返回**:
    ```json
    {
        "content": "文件内容..."
    }
    ```
    
    **错误响应**:
    - `404`: 项目不存在或文件不存在
    - `403`: 路径穿透尝试（安全拒绝）
    - `500`: 文件读取错误
    
    **示例请求**:
    ```
    GET /api/projects/1/files/content?path=src/main.py
    ```
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Security check: Ensure path is within project.path
    full_path = os.path.abspath(os.path.join(project.path, path))
    if not full_path.startswith(os.path.abspath(project.path)):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt")
        
    if not os.path.exists(full_path) or not os.path.isfile(full_path):
        raise HTTPException(status_code=404, detail="File not found")
        
    try:
        content = read_text_file(full_path)
        return {"content": content}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading file: {str(e)}")

@router.post("/{project_id}/files/save")
async def save_file_content(
    project_id: int, 
    body: schemas.FileSaveRequest,
    db: Session = Depends(get_db)
):
    """
    保存项目文件内容
    
    将内容写入到项目的指定文件中。用于在线编辑项目文件。
    
    **参数**:
    - **project_id**: 项目 ID（路径参数）
    - **body**: 文件保存请求（请求体）
      - path: 文件相对路径
      - content: 文件内容
    
    **安全措施**:
    - 路径穿透保护：确保文件路径在项目目录内
    - 使用 UTF-8 编码保存
    
    **返回**:
    ```json
    {
        "status": "success"
    }
    ```
    
    **错误响应**:
    - `404`: 项目不存在
    - `403`: 路径穿透尝试（安全拒绝）
    - `500`: 文件写入错误
    
    **示例请求**:
    ```json
    {
        "path": "src/main.py",
        "content": "print('Hello, World!')"
    }
    ```
    
    **注意**: 
    - 文件会被完全覆盖，请确保内容完整
    - 如果文件不存在，会自动创建
    """
    project = db.query(models.Project).filter(models.Project.id == project_id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
        
    # Security check
    full_path = os.path.abspath(os.path.join(project.path, body.path))
    if not full_path.startswith(os.path.abspath(project.path)):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt")
    
    try:
        with open(full_path, "w", encoding="utf-8") as f:
            f.write(body.content)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error writing file: {str(e)}")

# Add endpoint to browse server directories (for output_dir selection)
class DirListRequest(BaseModel):
    path: str = "/"

# Define allowed base directories for browsing
ALLOWED_BROWSE_DIRS = [
    PROJECTS_DIR,  # Project uploads directory
    os.path.abspath(os.path.join(os.getcwd(), "..", "Data")),  # Data directory (uppercase)
    os.path.abspath("/data"),  # Data directory (lowercase, docker volume mount)
    os.path.abspath(os.path.join(os.getcwd(), "envs")),  # Environments directory
    os.path.abspath(os.path.join(os.getcwd(), "logs")),  # Logs directory
]

def is_path_allowed(target_path: str) -> bool:
    """Check if the target path is within allowed directories."""
    abs_target = os.path.abspath(target_path)
    for allowed_dir in ALLOWED_BROWSE_DIRS:
        abs_allowed = os.path.abspath(allowed_dir)
        if abs_target.startswith(abs_allowed + os.sep) or abs_target == abs_allowed:
            return True
    return False

@router.post("/browse-dirs")
def browse_server_directories(request: DirListRequest):
    """
    浏览服务器允许的目录列表
    
    用于前端选择输出目录等功能，仅允许浏览指定的安全目录。
    
    **允许浏览的目录**:
    - 项目上传目录 (`projects`)
    - 数据目录 (`Data` 或 `/data`)
    - 环境目录 (`envs`)
    - 日志目录 (`logs`)
    
    **参数**:
    - **request**: 目录浏览请求（请求体）
      - path: 要浏览的路径（默认: 项目目录）
    
    **安全措施**:
    - 严格限制可浏览的目录范围
    - 路径穿透保护
    - 仅返回目录列表，不返回文件
    - 自动添加父目录（如果在允许范围内）
    
    **返回**:
    ```json
    {
        "current_path": "/path/to/directory",
        "items": [
            {
                "name": "..",
                "path": "/path/to/parent",
                "type": "dir"
            },
            {
                "name": "subdir",
                "path": "/path/to/directory/subdir",
                "type": "dir"
            }
        ]
    }
    ```
    
    **错误响应**:
    - `403`: 路径不在允许的目录范围内
    - `404`: 路径不存在
    - `500`: 目录读取错误
    
    **示例请求**:
    ```json
    {
        "path": "/data"
    }
    ```
    
    **注意**: 此接口仅用于浏览，不提供文件修改功能。
    """
    # Only allow browsing, no modification
    target_path = request.path

    # Validate path is not empty
    if not target_path or target_path == "":
        # Default to projects directory
        target_path = PROJECTS_DIR

    # Security check: ensure path is within allowed directories
    if not is_path_allowed(target_path):
        raise HTTPException(status_code=403, detail="Access denied: Path is not in allowed directories")

    # Additional check: resolve any path traversal attempts
    abs_target = os.path.abspath(target_path)
    if not is_path_allowed(abs_target):
        raise HTTPException(status_code=403, detail="Access denied: Path traversal attempt detected")

    if not os.path.exists(abs_target):
        raise HTTPException(status_code=404, detail="Path not found")

    # Don't allow going above allowed directories
    for allowed_dir in ALLOWED_BROWSE_DIRS:
        abs_allowed = os.path.abspath(allowed_dir)
        parent = abs_target
        while parent:
            parent = os.path.dirname(parent)
            if parent == abs_allowed:
                break
            if not parent or parent == os.path.dirname(parent):  # Reached root
                # Check if we're still in an allowed path
                if not is_path_allowed(abs_target):
                    raise HTTPException(status_code=403, detail="Access denied: Cannot browse outside allowed directories")
                break

    items = []
    try:
        for entry in os.scandir(abs_target):
            if entry.is_dir():
                try:
                    items.append({
                        "name": entry.name,
                        "path": entry.path,
                        "type": "dir"
                    })
                except Exception:
                    pass
    except Exception as e:
         raise HTTPException(status_code=500, detail=f"Error reading directory: {str(e)}")

    items.sort(key=lambda x: x["name"].lower())

    # Add parent dir only if it's within allowed directories
    parent = os.path.dirname(abs_target)
    if parent and is_path_allowed(parent):
         items.insert(0, {"name": "..", "path": parent, "type": "dir"})

    return {
        "current_path": abs_target,
        "items": items
    }
