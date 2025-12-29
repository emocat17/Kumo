from fastapi import APIRouter, HTTPException
import os
import platform

router = APIRouter(prefix="/system/fs", tags=["system-fs"])

@router.get("/list")
def list_directory(path: str = None):
    """
    List directories and files in the given path.
    If path is None, returns root drives (Windows) or root (Linux/Mac).
    """
    try:
        if path is None or path.strip() == "":
            # Return root drives for Windows or / for Unix
            if platform.system() == "Windows":
                drives = []
                import string
                from ctypes import windll
                drives_bitmask = windll.kernel32.GetLogicalDrives()
                for letter in string.ascii_uppercase:
                    if drives_bitmask & 1:
                        drives.append({"name": f"{letter}:\\", "type": "drive", "path": f"{letter}:\\"})
                    drives_bitmask >>= 1
                return {"current": "", "items": drives}
            else:
                path = "/"
        
        if not os.path.exists(path):
             raise HTTPException(status_code=404, detail="Path not found")
             
        if not os.path.isdir(path):
             raise HTTPException(status_code=400, detail="Not a directory")

        items = []
        # List directories first, then files
        with os.scandir(path) as it:
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
        
        # Add parent directory option if not at root (simplified)
        parent = os.path.dirname(path)
        
        return {"current": path, "parent": parent, "items": items}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
