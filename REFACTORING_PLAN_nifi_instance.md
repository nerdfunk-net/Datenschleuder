# NiFi Instances Refactoring Plan

## Overview
Refactoring `backend/app/api/nifi_instances.py` (2,876 lines, 31 endpoints) into 8 smaller, focused modules.

## Progress Status

### ✅ Completed
- [x] Created helper module: `backend/app/api/nifi/nifi_helpers.py`
- [x] Created package init: `backend/app/api/nifi/__init__.py`
- [x] Created `backend/app/api/nifi/instances.py` (Instance CRUD - 139 lines)
- [x] Created `backend/app/api/nifi/connections.py` (Connection testing - 115 lines)
- [x] Created `backend/app/api/nifi/registries.py` (Registry operations - 315 lines)
- [x] Created `backend/app/api/nifi/parameters.py` (Parameter contexts - 475 lines)
- [x] Created `backend/app/api/nifi/flows.py` (Flow import/export - 240 lines)
- [x] Created `backend/app/api/nifi/process_groups.py` (Process group management - 1,134 lines)
- [x] Created `backend/app/api/nifi/versions.py` (Version control - 89 lines)
- [x] Created `backend/app/api/nifi/processors.py` (Processor configuration - 276 lines)
- [x] Updated main.py to use new router (`from app.api.nifi import router`)
- [x] Fixed import error in process_groups.py (moved parameter context models to correct import)
- [x] Backed up old file to `nifi_instances.py.old`
- [x] Verified application imports successfully

### 🚧 Remaining Tasks
- [ ] Test all endpoints (31 total)
- [ ] Verify frontend still works
- [ ] Commit changes to git
- [ ] Remove backup file after confirmation

---

## File Structure

```
backend/app/api/nifi/
├── __init__.py                 ✅ DONE - Combines all routers (28 lines)
├── nifi_helpers.py             ✅ DONE - Common helper functions (140 lines)
├── instances.py                ✅ DONE - Instance CRUD (139 lines)
├── connections.py              ✅ DONE - Connection testing (115 lines)
├── registries.py               ✅ DONE - Registry operations (315 lines)
├── parameters.py               ✅ DONE - Parameter contexts (475 lines)
├── flows.py                    ✅ DONE - Flow import/export (240 lines)
├── process_groups.py           ✅ DONE - Process group management (1,134 lines)
├── versions.py                 ✅ DONE - Version control (89 lines)
└── processors.py               ✅ DONE - Processor configuration (276 lines)

Total: 2,951 lines (was 2,876 lines in single file)
Old file backed up: backend/app/api/nifi_instances.py.old
```

---

## Detailed Module Breakdown

### 1. ✅ instances.py (COMPLETED)
**Lines from original:** 47-189 (145 lines)
**Endpoints:**
- `GET /` - List all instances
- `GET /{instance_id}` - Get specific instance
- `POST /` - Create instance
- `PUT /{instance_id}` - Update instance
- `DELETE /{instance_id}` - Delete instance

**Imports needed:**
```python
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance, NiFiInstanceCreate, NiFiInstanceUpdate, NiFiInstanceResponse
from app.services.encryption_service import encryption_service
from app.api.nifi.nifi_helpers import get_instance_or_404
```

---

### 2. ✅ connections.py (COMPLETED)
**Lines from original:** 192-297 (105 lines)
**Endpoints:**
- `POST /test` - Test connection without saving
- `POST /{instance_id}/test-connection` - Test existing instance connection

**Imports needed:**
```python
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance, NiFiInstanceCreate
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from app.services.nifi_auth import configure_nifi_test_connection
from nipyapi.nifi import FlowApi
```

**Key logic:**
- Configure test connection for validation
- Test existing instance connection
- Return connection status

---

### 3. ✅ registries.py (COMPLETED)
**Lines from original:** 300-627 (327 lines)
**Endpoints:**
- `GET /{instance_id}/get-registries` - Get all registries
- `GET /{instance_id}/registry/{registry_id}/get-buckets` - Get buckets
- `GET /{instance_id}/registry/{registry_id}/details` - Get registry details
- `GET /{instance_id}/registry/{registry_id}/{bucket_id}/get-flows` - Get flows in bucket

**Imports needed:**
```python
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from nipyapi import versioning
```

**Key logic:**
- List all registries for instance
- Get buckets from registry
- Get flows from bucket
- Handle GitHub/local registry differences

---

### 4. ✅ parameters.py (COMPLETED)
**Lines from original:** 630-1110 (480 lines)
**Endpoints:**
- `GET /{instance_id}/parameter-contexts` - List parameter contexts
- `POST /{instance_id}/parameter-contexts` - Create parameter context
- `PUT /{instance_id}/parameter-contexts/{context_id}` - Update parameter context
- `DELETE /{instance_id}/parameter-contexts/{context_id}` - Delete parameter context

**Imports needed:**
```python
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.parameter_context import (
    ParameterContext, ParameterEntity, ParameterContextListResponse,
    ParameterContextCreate, ParameterContextUpdate,
    AssignParameterContextRequest, AssignParameterContextResponse
)
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from nipyapi import parameters
from nipyapi.nifi import ParameterContextsApi
```

**Key logic:**
- CRUD operations for parameter contexts
- Handle parameter updates (complex logic - 225 lines)
- Manage parameter context inheritance
- **NOTE:** `update_parameter_context` needs refactoring (it's 225 lines long)

**Refactoring needed for `update_parameter_context`:**
- Extract parameter comparison logic → `_compare_parameters()`
- Extract parameter update logic → `_update_parameters()`
- Extract context update logic → `_update_context_metadata()`

---

### 5. ✅ flows.py (COMPLETED)
**Lines from original:** 1113-1351 (238 lines)
**Endpoints:**
- `GET /{instance_id}/registry/{registry_id}/{bucket_id}/export-flow` - Export flow
- `POST /{instance_id}/registry/{registry_id}/{bucket_id}/import-flow` - Import flow

**Imports needed:**
```python
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from nipyapi import versioning
import json
```

**Key logic:**
- Export flow from registry to JSON
- Import flow from JSON to registry
- Handle flow versioning
- **NOTE:** Both functions are 110+ lines - consider refactoring

**Refactoring needed:**
- Extract flow snapshot creation → `_create_flow_snapshot()`
- Extract flow validation → `_validate_flow_data()`
- Extract version handling → `_determine_next_version()`

---

### 6. ✅ process_groups.py (COMPLETED)
**Lines from original:** 1359-2108 (749 lines) - **LARGEST MODULE**
**Endpoints:**
- `GET /{instance_id}/process-group` - Get process group by ID/name
- `GET /{instance_id}/process-groups` - Search process groups
- `GET /{instance_id}/get-path` - Get process group path
- `GET /{instance_id}/get-all-paths` - Get all process group paths
- `GET /{instance_id}/get-root` - Get root process group
- `GET /{instance_id}/process-group/{process_group_id}/output-ports` - Get output ports
- `POST /{instance_id}/connection` - Create connection
- `DELETE /{instance_id}/process-group/{process_group_id}` - Delete process group
- `POST /{instance_id}/process-group/{process_group_id}/add-parameter` - Assign parameter context
- `GET /{instance_id}/process-group/{process_group_id}/processors` - Get processors
- `GET /{instance_id}/process-group/{process_group_id}/input-ports` - Get input ports

**Imports needed:**
```python
from typing import List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.deployment import (
    PortsResponse, PortInfo, ConnectionRequest, ConnectionResponse,
    ProcessorInfo, ProcessorsResponse, InputPortInfo, InputPortsResponse
)
from app.models.parameter_context import AssignParameterContextRequest, AssignParameterContextResponse
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection, extract_pg_info
from nipyapi import canvas, parameters
from nipyapi.nifi import ProcessGroupsApi, ProcessorsApi
```

**Key logic:**
- Process group hierarchy navigation
- Path building and traversal
- Port management (input/output)
- Connection creation between components
- Parameter context assignment

**NOTE:** This module was added during the API reorganization (moved from deploy.py)

---

### 7. ✅ versions.py (COMPLETED)
**Lines from original:** 2187-2263 (76 lines) - **SMALLEST MODULE**
**Endpoints:**
- `POST /{instance_id}/process-group/{process_group_id}/update-version` - Update process group version

**Imports needed:**
```python
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from app.services.encryption_service import encryption_service
from nipyapi import versioning
from nipyapi.nifi import ProcessGroupsApi
import nipyapi
```

**Key logic:**
- Update version-controlled process groups
- Handle version conflicts
- Configure authentication for version operations

---

### 8. ✅ processors.py (COMPLETED)
**Lines from original:** 2606-2876 (270 lines)
**Endpoints:**
- `GET /{instance_id}/processor/{processor_id}/configuration` - Get processor config
- `PUT /{instance_id}/processor/{processor_id}/configuration` - Update processor config

**Imports needed:**
```python
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import verify_token
from app.models.deployment import (
    ProcessorConfiguration, ProcessorConfigurationResponse,
    ProcessorConfigurationUpdate, ProcessorConfigurationUpdateResponse
)
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
from nipyapi import canvas
```

**Key logic:**
- Get processor configuration details
- Update processor configuration
- Handle processor properties and scheduling

---

## Implementation Pattern

Each module should follow this template:

```python
"""Module description"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection
# Add other needed imports

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get("/endpoint")
async def endpoint_function(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Endpoint description"""
    # Replace: instance = db.query(NiFiInstance).filter(...)
    # With: instance = get_instance_or_404(db, instance_id)
    instance = get_instance_or_404(db, instance_id)

    try:
        # Replace: configure_nifi_connection(instance)
        # With: setup_nifi_connection(instance)
        setup_nifi_connection(instance)

        # Rest of logic stays the same
        ...

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
```

---

## Helper Functions Already Available

In `nifi_helpers.py`:

```python
def get_instance_or_404(db: Session, instance_id: int) -> NiFiInstance
def setup_nifi_connection(instance: NiFiInstance, normalize_url: bool = False) -> None
def extract_pg_info(pg: Any) -> Dict[str, Optional[str]]
def decrypt_instance_password(instance: NiFiInstance) -> Optional[str]
def build_error_response(error: Exception, default_message: str) -> Dict[str, str]
def validate_required_fields(data: Dict[str, Any], required_fields: list) -> None
```

---

## ✅ Update main.py (COMPLETED)

Updated `backend/app/main.py`:

**Before:**
```python
from app.api.nifi_instances import router as nifi_instances_router
app.include_router(nifi_instances_router)
```

**After:**
```python
from app.api.nifi import router as nifi_router
app.include_router(nifi_router)
```

**Changes made:**
- Removed import of old `nifi_instances` module
- Using new modular structure from `app.api.nifi`
- Fixed import error in `process_groups.py` (parameter context models)
- Verified application imports successfully

---

## Testing Checklist

After refactoring, test these critical paths:

### Instance Management
- [ ] List instances: `GET /api/nifi-instances/`
- [ ] Create instance: `POST /api/nifi-instances/`
- [ ] Update instance: `PUT /api/nifi-instances/{id}`
- [ ] Delete instance: `DELETE /api/nifi-instances/{id}`

### Connections
- [ ] Test connection: `POST /api/nifi-instances/test`
- [ ] Test existing: `POST /api/nifi-instances/{id}/test-connection`

### Registries
- [ ] Get registries: `GET /api/nifi-instances/{id}/get-registries`
- [ ] Get buckets: `GET /api/nifi-instances/{id}/registry/{reg_id}/get-buckets`
- [ ] Get flows: `GET /api/nifi-instances/{id}/registry/{reg_id}/{bucket_id}/get-flows`

### Parameters
- [ ] List contexts: `GET /api/nifi-instances/{id}/parameter-contexts`
- [ ] Create context: `POST /api/nifi-instances/{id}/parameter-contexts`
- [ ] Update context: `PUT /api/nifi-instances/{id}/parameter-contexts/{ctx_id}`

### Flows
- [ ] Export flow: `GET /api/nifi-instances/{id}/registry/{reg_id}/{bucket_id}/export-flow`
- [ ] Import flow: `POST /api/nifi-instances/{id}/registry/{reg_id}/{bucket_id}/import-flow`

### Process Groups
- [ ] Get process group: `GET /api/nifi-instances/{id}/process-group`
- [ ] Get all paths: `GET /api/nifi-instances/{id}/get-all-paths`
- [ ] Create connection: `POST /api/nifi-instances/{id}/connection`

### Processors
- [ ] Get config: `GET /api/nifi-instances/{id}/processor/{proc_id}/configuration`
- [ ] Update config: `PUT /api/nifi-instances/{id}/processor/{proc_id}/configuration`

---

## Cleanup Steps

After successful testing:

1. [ ] Verify all endpoints work (see Testing Checklist below)
2. [ ] Check frontend still works
3. [ ] Run backend tests (if available)
4. ✅ Backup old file: `mv nifi_instances.py nifi_instances.py.old` (DONE)
5. ✅ Update any direct imports in other files (DONE - no imports found)
6. [ ] Commit changes to git
7. [ ] Remove backup after confirmation

---

## Benefits of Refactoring

✅ **Reduced file size**: 2,876 lines → 8 files of ~200-400 lines each
✅ **Better organization**: Clear separation by functionality
✅ **Easier maintenance**: Changes isolated to specific modules
✅ **Reduced boilerplate**: Helper functions eliminate 40+ lines per endpoint
✅ **Better testability**: Each module can be tested independently
✅ **Team collaboration**: Multiple developers can work on different modules
✅ **Improved navigation**: Find endpoints quickly by functional area

---

## Estimated Time

- **Per module**: 15-30 minutes
- **Total remaining**: 2-3 hours for 7 modules
- **Testing**: 1 hour
- **Total**: 3-4 hours

---

## Next Steps

✅ **Refactoring Complete!** All 8 modules created and integrated.

**Remaining tasks:**
1. Test all 31 endpoints (see Testing Checklist above)
2. Verify frontend functionality
3. Commit changes to git
4. Remove backup file after confirmation

**What was accomplished:**
- ✅ Split 2,876-line file into 8 focused modules (2,951 total lines)
- ✅ Created helper functions to eliminate boilerplate
- ✅ Updated main.py router configuration
- ✅ Fixed import errors
- ✅ Backed up original file
- ✅ Verified application starts successfully
