"""Settings management API endpoints."""

import json
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator

from app.core.database import get_db
from app.core.security import verify_token
from app.models.setting import Setting, NifiSettings, RegistrySettings
from app.services.encryption_service import encryption_service

router = APIRouter(prefix="/api/settings", tags=["settings"])


# Data Format Schemas
class HierarchyAttribute(BaseModel):
    """Single attribute in the hierarchy"""

    name: str  # e.g., "CN", "O", "OU", "DC"
    label: str  # e.g., "Common Name", "Organization"
    order: int  # Position in hierarchy (0 = top level)


class HierarchySettings(BaseModel):
    """Hierarchical data format configuration"""

    hierarchy: List[HierarchyAttribute]

    @validator("hierarchy")
    def validate_unique_names(cls, v):
        """Ensure all attribute names are unique"""
        names = [attr.name for attr in v]
        if len(names) != len(set(names)):
            raise ValueError("Attribute names must be unique")
        return v


def get_setting_value(db: Session, key: str) -> Optional[dict]:
    """Get a setting value by key and return as dict"""
    setting = db.query(Setting).filter(Setting.key == key).first()
    if setting:
        return json.loads(setting.value)
    return None


def upsert_setting(
    db: Session, key: str, value: dict, category: str = None, description: str = None
):
    """Create or update a setting"""
    setting = db.query(Setting).filter(Setting.key == key).first()

    # Encrypt password if present
    if "password" in value and value["password"]:
        value["password"] = encryption_service.encrypt_to_string(value["password"])

    value_json = json.dumps(value)

    if setting:
        # Update existing
        setting.value = value_json
        if description:
            setting.description = description
    else:
        # Create new
        setting = Setting(
            key=key, value=value_json, category=category, description=description
        )
        db.add(setting)

    db.commit()
    db.refresh(setting)
    return setting


@router.get("/nifi")
async def get_nifi_settings(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get NiFi connection settings"""
    settings = get_setting_value(db, "nifi_config")

    if not settings:
        # Return default settings
        return {
            "nifiUrl": "",
            "username": "",
            "password": "",
            "useSSL": True,
            "verifySSL": True,
        }

    # Decrypt password if present
    if settings.get("password"):
        try:
            settings["password"] = encryption_service.decrypt_from_string(
                settings["password"]
            )
        except Exception:
            settings["password"] = ""

    return settings


@router.post("/nifi")
async def save_nifi_settings(
    settings: NifiSettings,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Save NiFi connection settings"""
    try:
        settings_dict = settings.dict()
        upsert_setting(
            db,
            key="nifi_config",
            value=settings_dict,
            category="nifi",
            description="NiFi connection configuration",
        )
        return {"message": "NiFi settings saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}",
        )


@router.get("/registry")
async def get_registry_settings(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get NiFi Registry settings"""
    settings = get_setting_value(db, "registry_config")

    if not settings:
        # Return default settings
        return {
            "registryUrl": "",
            "username": "",
            "password": "",
            "useSSL": True,
            "verifySSL": True,
        }

    # Decrypt password if present
    if settings.get("password"):
        try:
            settings["password"] = encryption_service.decrypt_from_string(
                settings["password"]
            )
        except Exception:
            settings["password"] = ""

    return settings


@router.post("/registry")
async def save_registry_settings(
    settings: RegistrySettings,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Save NiFi Registry settings"""
    try:
        settings_dict = settings.dict()
        upsert_setting(
            db,
            key="registry_config",
            value=settings_dict,
            category="registry",
            description="NiFi Registry connection configuration",
        )
        return {"message": "Registry settings saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}",
        )


@router.get("/hierarchy")
async def get_data_format_settings(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get hierarchical data format settings"""
    settings = get_setting_value(db, "hierarchy_config")

    if not settings:
        # Return default hierarchy (X.509 DN style)
        return {
            "hierarchy": [
                {"name": "CN", "label": "Common Name", "order": 0},
                {"name": "O", "label": "Organization", "order": 1},
                {"name": "OU", "label": "Organizational Unit", "order": 2},
                {"name": "DC", "label": "Domain Component", "order": 3},
            ]
        }

    return settings


@router.post("/hierarchy")
async def save_data_format_settings(
    settings: HierarchySettings,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Save hierarchical data format settings"""
    try:
        # Validate that orders are sequential
        orders = [attr.order for attr in settings.hierarchy]
        if sorted(orders) != list(range(len(orders))):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Order values must be sequential starting from 0",
            )

        settings_dict = settings.dict()
        upsert_setting(
            db,
            key="hierarchy_config",
            value=settings_dict,
            category="hierarchy",
            description="Hierarchical data format configuration",
        )
        return {"message": "Data format settings saved successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}",
        )


@router.get("/hierarchy/values/{attribute_name}")
async def get_attribute_values(
    attribute_name: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get all values for a specific attribute"""
    from app.models.hierarchy import HierarchyValue

    values = (
        db.query(HierarchyValue)
        .filter(HierarchyValue.attribute_name == attribute_name)
        .all()
    )

    return {"attribute_name": attribute_name, "values": [v.value for v in values]}


@router.post("/hierarchy/values")
async def save_attribute_values(
    data: dict,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Save/replace all values for a specific attribute"""
    from app.models.hierarchy import HierarchyValue

    attribute_name = data.get("attribute_name")
    values = data.get("values", [])

    if not attribute_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="attribute_name is required"
        )

    # Delete existing values for this attribute
    db.query(HierarchyValue).filter(
        HierarchyValue.attribute_name == attribute_name
    ).delete()

    # Insert new values
    for value in values:
        if value.strip():  # Only insert non-empty values
            db_value = HierarchyValue(
                attribute_name=attribute_name, value=value.strip()
            )
            db.add(db_value)

    db.commit()

    return {"message": f"Saved {len(values)} values for {attribute_name}"}


@router.delete("/hierarchy/values/{attribute_name}")
async def delete_attribute_values(
    attribute_name: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete all values for a specific attribute"""
    from app.models.hierarchy import HierarchyValue

    deleted_count = (
        db.query(HierarchyValue)
        .filter(HierarchyValue.attribute_name == attribute_name)
        .delete()
    )

    db.commit()

    return {"message": f"Deleted {deleted_count} values for {attribute_name}"}


@router.get("/deploy")
async def get_deployment_settings(
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get deployment settings (both global and per-instance paths)"""
    # Get global deployment settings
    global_settings = get_setting_value(db, "deployment_config")

    if not global_settings:
        # Return defaults
        global_settings = {
            "process_group_name_template": "{last_hierarchy_value}",
            "disable_after_deploy": False,
            "stop_versioning_after_deploy": False,
        }

    # Get per-instance path settings
    path_settings = get_setting_value(db, "deployment_paths") or {}

    return {"global": global_settings, "paths": path_settings}


@router.post("/deploy")
async def save_deployment_settings(
    data: dict,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Save deployment settings"""
    try:
        # Save global settings
        if "global" in data:
            upsert_setting(
                db,
                key="deployment_config",
                value=data["global"],
                category="deployment",
                description="Global deployment configuration",
            )

        # Save path settings
        if "paths" in data:
            upsert_setting(
                db,
                key="deployment_paths",
                value=data["paths"],
                category="deployment",
                description="Deployment path settings per instance",
            )

        return {"message": "Deployment settings saved successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save settings: {str(e)}",
        )
