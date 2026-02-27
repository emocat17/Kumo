from fastapi import APIRouter, HTTPException
import os
import platform

router = APIRouter(prefix="/system/fs", tags=["system-fs"])

# Define allowed base directories for browsing (within the container/app context)
# These should be relative to the backend working directory
BACKEND_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ALLOWED_BROWSE_DIRS = [
    os.path.abspath(os.path.join(BACKEND_DIR, "projects")),  # Project uploads
    os.path.abspath(os.path.join(BACKEND_DIR, "..", "Data")),  # Data directory (container /data)
    os.path.abspath(os.path.join(BACKEND_DIR, "envs")),  # Environments directory
    os.path.abspath(os.path.join(BACKEND_DIR, "logs")),  # Logs directory
    os.path.abspath(os.path.join(BACKEND_DIR, "data")),  # Database and backup directory
]

def is_path_allowed(target_path: str) -> bool:
    """Check if the target path is within allowed directories."""
    abs_target = os.path.abspath(target_path)
    for allowed_dir in ALLOWED_BROWSE_DIRS:
        abs_allowed = os.path.abspath(allowed_dir)
        if abs_target.startswith(abs_allowed + os.sep) or abs_target == abs_allowed:
            return True
    return False

@router.get("/list")
def list_directory(path: str = None):
    """
    List directories and files in the given path.
    Restricted to allowed directories only for security.
    """
    try:
        # Default to projects directory if no path specified
        if path is None or path.strip() == "":
            path = ALLOWED_BROWSE_DIRS[0]  # Default to projects directory

        # Resolve absolute path
        abs_path = os.path.abspath(path)

        # Security check: ensure path is within allowed directories
        if not is_path_allowed(abs_path):
            raise HTTPException(
                status_code=403,
                detail=f"Access denied: Path must be within allowed directories. Allowed: {', '.join([os.path.basename(d) for d in ALLOWED_BROWSE_DIRS])}"
            )

        # Check if path exists
        if not os.path.exists(abs_path):
            raise HTTPException(status_code=404, detail="Path not found")

        # Verify it's a directory
        if not os.path.isdir(abs_path):
            raise HTTPException(status_code=400, detail="Not a directory")

        # Additional check: prevent directory traversal beyond allowed roots
        # Walk up the tree to ensure we never escape allowed directories
        current = abs_path
        while current:
            parent = os.path.dirname(current)
            if parent == current:  # Reached root
                break
            # If parent is not allowed but current is, that's a traversal attempt
            if not is_path_allowed(parent) and current != abs_path:
                raise HTTPException(status_code=403, detail="Access denied: Cannot browse outside allowed directories")
            current = parent

        items = []
        # List directories first, then files
        with os.scandir(abs_path) as it:
            for entry in it:
                try:
                    item_type = "dir" if entry.is_dir() else "file"
                    items.append({
                        "name": entry.name,
                        "type": item_type,
                        "path": entry.path
                    })
                except PermissionError:
                    continue

        # Sort: directories first, then files, alphabetically
        items.sort(key=lambda x: (x["type"] != "dir", x["name"].lower()))

        # Add parent directory option only if parent is also allowed
        parent = os.path.dirname(abs_path)
        if parent and is_path_allowed(parent) and parent != abs_path:
            return {"current": abs_path, "parent": parent, "items": items}

        return {"current": abs_path, "parent": None, "items": items}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
