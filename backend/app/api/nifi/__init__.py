"""NiFi API endpoints organized by functional area"""

from fastapi import APIRouter

# Import all sub-routers
from .instances import router as instances_router
# from .connections import router as connections_router  # Disabled: Duplicate /test endpoint conflicts with nifi_monitoring
from .registries import router as registries_router
from .parameters import router as parameters_router
from .flows import router as flows_router
from .process_groups import router as process_groups_router
from .versions import router as versions_router
from .processors import router as processors_router

# Create main router that combines all sub-routers
# Using /api/nifi prefix to avoid conflict with /api/nifi-instances (from nifi_monitoring.py)
router = APIRouter(prefix="/api/nifi", tags=["nifi-operations"])

# Include all sub-routers without prefix (prefix is already set in main router)
router.include_router(instances_router)
# router.include_router(connections_router)  # Disabled: Conflicts with nifi_monitoring /test endpoint
router.include_router(registries_router)
router.include_router(parameters_router)
router.include_router(flows_router)
router.include_router(process_groups_router)
router.include_router(versions_router)
router.include_router(processors_router)

__all__ = ["router"]
