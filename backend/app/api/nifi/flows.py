"""NiFi flow import/export API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get("/{instance_id}/registry/{registry_id}/{bucket_id}/export-flow")
async def export_flow(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    flow_id: str,
    version: str = None,
    mode: str = "json",
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Export a flow from registry using nipyapi.versioning.export_flow_version"""
    import nipyapi
    from nipyapi import config, versioning

    instance = get_instance_or_404(db, instance_id)

    try:
        # Configure nipyapi for NiFi instance
        setup_nifi_connection(instance)

        # Validate mode parameter
        if mode not in ["json", "yaml"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Mode must be 'json' or 'yaml'",
            )

        # Verify the registry client exists and get its type
        registry_clients = versioning.list_registry_clients()
        registry_found = False
        registry_client = None
        registry_type = None

        if hasattr(registry_clients, 'registries') and registry_clients.registries:
            for client in registry_clients.registries:
                if client.id == registry_id:
                    registry_found = True
                    registry_client = client
                    if hasattr(client, 'component') and hasattr(client.component, 'type'):
                        registry_type = client.component.type
                    break

        if not registry_found:
            available_registries = []
            if hasattr(registry_clients, 'registries') and registry_clients.registries:
                available_registries = [f"{c.id} ({c.component.name if hasattr(c, 'component') else 'unknown'})" for c in registry_clients.registries]

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id '{registry_id}' not found. Available registries: {', '.join(available_registries) if available_registries else 'none'}",
            )

        # Check if this is a GitHub or other external registry type
        is_external_registry = registry_type and ('github' in registry_type.lower() or 'git' in registry_type.lower())

        if is_external_registry:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Export is not supported for {registry_type} registries. Please access the flow files directly from your Git repository.",
            )

        # For NiFi Registry, use nipyapi's built-in export function
        exported_content = versioning.export_flow_version(
            bucket_id=bucket_id,
            flow_id=flow_id,
            version=version,
            mode=mode
        )

        # Get flow name for filename
        flow_name = flow_id
        try:
            flow = versioning.get_flow_in_bucket(bucket_id, identifier=flow_id)
            if hasattr(flow, 'name'):
                flow_name = flow.name
        except:
            pass

        # Generate filename
        version_suffix = f"_v{version}" if version else "_latest"
        filename = f"{flow_name}{version_suffix}.{mode}"

        # Set appropriate content type
        content_type = "application/json" if mode == "json" else "application/x-yaml"

        return Response(
            content=exported_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to export flow: {error_msg}",
        )


@router.post("/{instance_id}/registry/{registry_id}/{bucket_id}/import-flow")
async def import_flow(
    instance_id: int,
    registry_id: str,
    bucket_id: str,
    file: UploadFile = File(...),
    flow_name: str = Form(None),
    flow_id: str = Form(None),
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Import a flow to registry using nipyapi.versioning.import_flow_version"""
    import nipyapi
    from nipyapi import config, versioning

    instance = get_instance_or_404(db, instance_id)

    # Validate parameters
    if not flow_name and not flow_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either flow_name (for new flow) or flow_id (for existing flow) must be provided",
        )

    # Validate file type
    if not file.filename.endswith(('.json', '.yaml', '.yml')):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File must be a JSON or YAML file",
        )

    try:
        # Configure nipyapi for NiFi instance
        setup_nifi_connection(instance)

        # Verify the registry client exists and get its type
        registry_clients = versioning.list_registry_clients()
        registry_found = False
        registry_client = None
        registry_type = None

        if hasattr(registry_clients, 'registries') and registry_clients.registries:
            for client in registry_clients.registries:
                if client.id == registry_id:
                    registry_found = True
                    registry_client = client
                    if hasattr(client, 'component') and hasattr(client.component, 'type'):
                        registry_type = client.component.type
                    break

        if not registry_found:
            available_registries = []
            if hasattr(registry_clients, 'registries') and registry_clients.registries:
                available_registries = [f"{c.id} ({c.component.name if hasattr(c, 'component') else 'unknown'})" for c in registry_clients.registries]

            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Registry client with id '{registry_id}' not found. Available registries: {', '.join(available_registries) if available_registries else 'none'}",
            )

        # Check if this is a GitHub or other external registry type
        is_external_registry = registry_type and ('github' in registry_type.lower() or 'git' in registry_type.lower())

        if is_external_registry:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail=f"Import is not supported for {registry_type} registries. Please commit the flow directly to your Git repository.",
            )

        # Read the uploaded file content
        file_content = await file.read()
        encoded_flow = file_content.decode('utf-8')

        # For NiFi Registry, use nipyapi's built-in import function
        imported_flow = versioning.import_flow_version(
            bucket_id=bucket_id,
            encoded_flow=encoded_flow,
            flow_name=flow_name,
            flow_id=flow_id
        )

        # Extract flow information from the response
        result_flow_name = flow_name
        result_flow_id = flow_id
        result_version = "unknown"

        if hasattr(imported_flow, 'snapshot_metadata'):
            metadata = imported_flow.snapshot_metadata
            if hasattr(metadata, 'flow_identifier'):
                result_flow_id = metadata.flow_identifier
            if hasattr(metadata, 'version'):
                result_version = str(metadata.version)

        if hasattr(imported_flow, 'flow'):
            if hasattr(imported_flow.flow, 'identifier'):
                result_flow_id = imported_flow.flow.identifier
            if hasattr(imported_flow.flow, 'name'):
                result_flow_name = imported_flow.flow.name

        return {
            "status": "success",
            "message": "Flow imported successfully",
            "flow_name": result_flow_name or "Unknown",
            "flow_id": result_flow_id or "Unknown",
            "version": result_version,
            "filename": file.filename,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to import flow: {error_msg}",
        )
