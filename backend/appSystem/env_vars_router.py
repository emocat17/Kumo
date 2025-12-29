from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from appSystem import models, schemas
from app.security import encrypt_value, decrypt_value

router = APIRouter()

MASK_VALUE = "******"

@router.get("", response_model=List[schemas.EnvVarResponse])
async def list_env_vars(db: Session = Depends(get_db)):
    """List all environment variables. Secret values are masked."""
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
    """Create a new environment variable. Encrypts if is_secret is True."""
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
    """Update environment variable."""
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
    """Delete environment variable."""
    db_item = db.query(models.EnvironmentVariable).filter(models.EnvironmentVariable.id == var_id).first()
    if not db_item:
        raise HTTPException(status_code=404, detail="Environment variable not found")
    
    db.delete(db_item)
    db.commit()
    return {"message": "Deleted successfully"}
