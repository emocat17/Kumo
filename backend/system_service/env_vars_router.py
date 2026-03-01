from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from core.database import get_db
from system_service import models, schemas
from core.security import encrypt_value, decrypt_value

router = APIRouter()

MASK_VALUE = "******"

@router.get("", response_model=List[schemas.EnvVarResponse])
async def list_env_vars(db: Session = Depends(get_db)):
    """
    列出所有环境变量
    
    返回系统中所有环境变量，SECRET 类型的值会被掩码显示。
    
    **安全措施**:
    - SECRET 类型的值显示为 `******`
    - 普通环境变量的值正常显示
    
    **返回**: 环境变量列表，每个变量包含：
    - id: 变量 ID
    - key: 变量键名
    - value: 变量值（SECRET 类型显示为 `******`）
    - description: 变量描述
    - is_secret: 是否为 SECRET 类型
    - created_at: 创建时间
    - updated_at: 更新时间
    
    **返回示例**:
    ```json
    [
        {
            "id": 1,
            "key": "API_KEY",
            "value": "******",
            "description": "API 密钥",
            "is_secret": true,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        },
        {
            "id": 2,
            "key": "DEBUG",
            "value": "false",
            "description": "调试模式",
            "is_secret": false,
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00"
        }
    ]
    ```
    """
    env_vars = db.query(models.EnvironmentVariable).all()
    
    result = []
    for var in env_vars:
        # Mask value if secret
        display_value = MASK_VALUE if var.is_secret else var.value
        result.append(schemas.EnvVarResponse(
            id=var.id,
            key=var.key,
            value=display_value,
            description=var.description,
            is_secret=var.is_secret,
            created_at=var.created_at,
            updated_at=var.updated_at
        ))
    return result

@router.post("", response_model=schemas.EnvVarResponse)
async def create_env_var(env_var: schemas.EnvVarCreate, db: Session = Depends(get_db)):
    """
    创建新的环境变量
    
    创建新的环境变量，如果 `is_secret` 为 `true`，值会被加密存储。
    
    **参数**:
    - **key**: 变量键名（必填，必须唯一）
    - **value**: 变量值（必填）
    - **description**: 变量描述（可选）
    - **is_secret**: 是否为 SECRET 类型（默认: false）
    
    **加密处理**:
    - 如果 `is_secret` 为 `true`，值会使用系统密钥加密后存储
    - 返回时 SECRET 类型的值会被掩码显示
    
    **返回**: 创建的环境变量对象（SECRET 值已掩码）
    
    **错误响应**:
    - `400`: 变量键名已存在
    
    **示例请求**:
    ```json
    {
        "key": "API_KEY",
        "value": "secret123456",
        "description": "API 密钥",
        "is_secret": true
    }
    ```
    
    **返回示例**:
    ```json
    {
        "id": 1,
        "key": "API_KEY",
        "value": "******",
        "description": "API 密钥",
        "is_secret": true,
        "created_at": "2024-01-01T00:00:00",
        "updated_at": "2024-01-01T00:00:00"
    }
    ```
    """
    # Check if key exists
    existing = db.query(models.EnvironmentVariable).filter(models.EnvironmentVariable.key == env_var.key).first()
    if existing:
        raise HTTPException(status_code=400, detail="Environment variable with this Key already exists")

    final_value = env_var.value
    if env_var.is_secret:
        final_value = encrypt_value(env_var.value)

    db_item = models.EnvironmentVariable(
        key=env_var.key,
        value=final_value,
        description=env_var.description,
        is_secret=env_var.is_secret
    )
    db.add(db_item)
    db.commit()
    db.refresh(db_item)

    # Return response with masked value if needed
    display_value = MASK_VALUE if db_item.is_secret else db_item.value
    
    # Manually construct response to avoid re-querying or decrypting unnecessarily
    return schemas.EnvVarResponse(
        id=db_item.id,
        key=db_item.key,
        value=display_value,
        description=db_item.description,
        is_secret=db_item.is_secret,
        created_at=db_item.created_at,
        updated_at=db_item.updated_at
    )

@router.put("/{var_id}", response_model=schemas.EnvVarResponse)
async def update_env_var(var_id: int, env_var: schemas.EnvVarUpdate, db: Session = Depends(get_db)):
    """
    更新环境变量
    
    更新环境变量的键名、值、描述或 SECRET 状态。
    
    **参数**:
    - **var_id**: 环境变量 ID（路径参数）
    - **env_var**: 更新数据（请求体）
      - key: 变量键名（可选）
      - value: 变量值（可选）
      - description: 变量描述（可选）
      - is_secret: 是否为 SECRET 类型（可选）
    
    **特殊处理**:
    - 如果更新键名，会检查新键名是否已存在（排除当前变量）
    - 如果变量是 SECRET 类型且值为 `******` 或空字符串，则保持原值不变
    - 如果从普通类型改为 SECRET 类型，当前值会被加密
    - 如果从 SECRET 类型改为普通类型，当前值会被解密
    
    **返回**: 更新后的环境变量对象（SECRET 值已掩码）
    
    **错误响应**:
    - `404`: 环境变量不存在
    - `400`: 新键名已存在
    
    **示例请求**:
    ```json
    {
        "value": "new_secret_value",
        "description": "更新后的描述"
    }
    ```
    
    **注意**: 
    - 更新 SECRET 类型的值时，必须提供新的明文值
    - 如果不想更改 SECRET 值，可以发送 `******` 或省略 `value` 字段
    """
    db_item = db.query(models.EnvironmentVariable).filter(models.EnvironmentVariable.id == var_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Environment variable not found")

    if env_var.key:
        # Check uniqueness if key changed
        if env_var.key != db_item.key:
            existing = db.query(models.EnvironmentVariable).filter(models.EnvironmentVariable.key == env_var.key).first()
            if existing:
                raise HTTPException(status_code=400, detail="Environment variable with this Key already exists")
        db_item.key = env_var.key

    if env_var.description is not None:
        db_item.description = env_var.description

    # Handle value update
    if env_var.value is not None:
        # If user sent MASK_VALUE or empty string for a secret, assume no change intended
        if db_item.is_secret and (env_var.value == MASK_VALUE or env_var.value == ""):
            pass # Keep existing encrypted value
        else:
            # Encrypt if it is (or becomes) a secret
            is_secret_now = env_var.is_secret if env_var.is_secret is not None else db_item.is_secret
            if is_secret_now:
                db_item.value = encrypt_value(env_var.value)
            else:
                db_item.value = env_var.value
    
    # Handle is_secret toggle
    if env_var.is_secret is not None:
        old_secret = db_item.is_secret
        new_secret = env_var.is_secret
        db_item.is_secret = new_secret
        
        # If changing from secret to public, we need to decrypt current value (unless value was also updated above)
        # But wait, if value was updated above, it's already set correctly based on is_secret_now.
        # So we only need to handle the case where value was NOT updated but secret status changed.
        if env_var.value is None or (old_secret and env_var.value == MASK_VALUE):
            if old_secret and not new_secret:
                # Decrypt current value
                db_item.value = decrypt_value(db_item.value)
            elif not old_secret and new_secret:
                # Encrypt current value
                db_item.value = encrypt_value(db_item.value)

    db.commit()
    db.refresh(db_item)

    display_value = MASK_VALUE if db_item.is_secret else db_item.value
    return schemas.EnvVarResponse(
        id=db_item.id,
        key=db_item.key,
        value=display_value,
        description=db_item.description,
        is_secret=db_item.is_secret,
        created_at=db_item.created_at,
        updated_at=db_item.updated_at
    )

@router.delete("/{var_id}")
async def delete_env_var(var_id: int, db: Session = Depends(get_db)):
    """
    删除环境变量
    
    **参数**:
    - **var_id**: 环境变量 ID（路径参数）
    
    **返回**:
    ```json
    {
        "message": "Deleted successfully"
    }
    ```
    
    **错误响应**:
    - `404`: 环境变量不存在
    
    **注意**: 删除操作不可逆，请谨慎操作。
    """
    db_item = db.query(models.EnvironmentVariable).filter(models.EnvironmentVariable.id == var_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    db.delete(db_item)
    db.commit()
    return {"message": "Deleted successfully"}
