"""NiFi parameter contexts API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.parameter_context import (
    ParameterContext,
    ParameterEntity,
    ParameterContextListResponse,
    ParameterContextCreate,
    ParameterContextUpdate,
)
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get(
    "/{instance_id}/get-parameters", response_model=ParameterContextListResponse
)
async def get_parameter_contexts(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Get list of parameter contexts configured in NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi import FlowApi

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Get parameter contexts using the FlowApi
        flow_api = FlowApi()
        param_contexts_entity = flow_api.get_parameter_contexts()

        # Convert to our response model
        contexts_list = []
        if (
            hasattr(param_contexts_entity, "parameter_contexts")
            and param_contexts_entity.parameter_contexts
        ):
            for context in param_contexts_entity.parameter_contexts:
                # Extract parameters
                parameters = []
                if hasattr(context, "component") and hasattr(
                    context.component, "parameters"
                ):
                    for param in context.component.parameters:
                        param_data = ParameterEntity(
                            name=param.parameter.name
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "name")
                            else "Unknown",
                            description=param.parameter.description
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "description")
                            else None,
                            sensitive=param.parameter.sensitive
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "sensitive")
                            else False,
                            value=param.parameter.value
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "value")
                            and not param.parameter.sensitive
                            else None,
                            provided=param.parameter.provided
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "provided")
                            else False,
                            referenced_attributes=param.parameter.referenced_attributes
                            if hasattr(param, "parameter")
                            and hasattr(param.parameter, "referenced_attributes")
                            else None,
                            parameter_context_id=context.id
                            if hasattr(context, "id")
                            else None,
                        )
                        parameters.append(param_data)

                # Extract bound process groups
                bound_groups = []
                if hasattr(context, "component") and hasattr(
                    context.component, "bound_process_groups"
                ):
                    for pg in context.component.bound_process_groups:
                        if hasattr(pg, "to_dict"):
                            bound_groups.append(pg.to_dict())

                # Extract inherited parameter contexts
                inherited_contexts = []
                if hasattr(context, "component") and hasattr(
                    context.component, "inherited_parameter_contexts"
                ):
                    for ipc in context.component.inherited_parameter_contexts:
                        if hasattr(ipc, "id"):
                            inherited_contexts.append(ipc.id)

                context_data = ParameterContext(
                    id=context.id if hasattr(context, "id") else "Unknown",
                    name=context.component.name
                    if hasattr(context, "component")
                    and hasattr(context.component, "name")
                    else "Unknown",
                    description=context.component.description
                    if hasattr(context, "component")
                    and hasattr(context.component, "description")
                    else None,
                    parameters=parameters,
                    bound_process_groups=bound_groups if bound_groups else None,
                    inherited_parameter_contexts=inherited_contexts
                    if inherited_contexts
                    else None,
                    component_revision=context.revision.to_dict()
                    if hasattr(context, "revision")
                    and hasattr(context.revision, "to_dict")
                    else None,
                    permissions=context.permissions.to_dict()
                    if hasattr(context, "permissions")
                    and hasattr(context.permissions, "to_dict")
                    else None,
                )
                contexts_list.append(context_data)

        return ParameterContextListResponse(
            status="success",
            parameter_contexts=contexts_list,
            count=len(contexts_list),
        )

    except Exception as e:
        error_msg = str(e)
        return ParameterContextListResponse(
            status="error",
            parameter_contexts=[],
            count=0,
            message=f"Failed to get parameter contexts: {error_msg}",
        )


@router.post("/{instance_id}/parameter-contexts")
async def create_parameter_context(
    instance_id: int,
    data: ParameterContextCreate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Create a new parameter context in NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi
        from nipyapi.nifi.models import (
            ParameterContextEntity,
            ParameterContextDTO,
            ParameterEntity as NiFiParameterEntity,
            ParameterDTO,
        )

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Build parameters list
        parameters = []
        for param in data.parameters:
            param_dto = ParameterDTO(
                name=param.name,
                description=param.description,
                sensitive=param.sensitive,
                value=param.value,
            )
            param_entity = NiFiParameterEntity(parameter=param_dto)
            parameters.append(param_entity)

        # Create parameter context DTO
        param_context_dto = ParameterContextDTO(
            name=data.name,
            description=data.description,
            parameters=parameters if parameters else None,
        )

        # Create parameter context entity
        param_context_entity = ParameterContextEntity(
            component=param_context_dto,
            revision={"version": 0},
        )

        # Create parameter context
        param_api = ParameterContextsApi()
        result = param_api.create_parameter_context(body=param_context_entity)

        return {
            "status": "success",
            "message": "Parameter context created successfully",
            "parameter_context": {
                "id": result.id if hasattr(result, "id") else None,
                "name": result.component.name
                if hasattr(result, "component")
                else data.name,
            },
        }

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create parameter context: {error_msg}",
        )


@router.put("/{instance_id}/parameter-contexts/{context_id}")
async def update_parameter_context(
    instance_id: int,
    context_id: str,
    data: ParameterContextUpdate,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Update an existing parameter context in NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi
        from nipyapi.nifi.models import (
            ParameterEntity as NiFiParameterEntity,
            ParameterDTO,
        )
        import time

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Get existing parameter context to get current revision
        param_api = ParameterContextsApi()
        existing_context = param_api.get_parameter_context(id=context_id)

        print(
            f"Existing context has {len(existing_context.component.parameters) if existing_context.component.parameters else 0} parameters"
        )
        print(
            f"Update data has {len(data.parameters) if data.parameters else 0} parameters"
        )

        # Get the names of parameters we want to keep
        desired_param_names = set()
        if data.parameters is not None:
            desired_param_names = {param.name for param in data.parameters}

        print(f"Desired parameters: {desired_param_names}")

        # Build complete parameters list - merge existing with updates and mark deletions
        parameters = []
        existing_param_map = {}

        # First, map existing parameters
        if existing_context.component.parameters:
            for existing_param in existing_context.component.parameters:
                param_name = existing_param.parameter.name
                existing_param_map[param_name] = existing_param

        print(f"Existing parameters: {set(existing_param_map.keys())}")

        # Now build the final parameter list
        if data.parameters is not None:
            # Add/update parameters that are in the desired list
            for param in data.parameters:
                print(f"Adding/updating parameter: {param.name} = {param.value}")

                # For updates to existing parameters, we need to preserve the parameter reference
                if param.name in existing_param_map:
                    # Updating existing parameter - modify it
                    existing_param = existing_param_map[param.name]
                    existing_param.parameter.description = param.description
                    existing_param.parameter.sensitive = param.sensitive
                    if (
                        not param.sensitive
                    ):  # Only update value for non-sensitive parameters
                        existing_param.parameter.value = param.value
                    parameters.append(existing_param)
                else:
                    # New parameter - create fresh
                    param_dto = ParameterDTO(
                        name=param.name,
                        description=param.description,
                        sensitive=param.sensitive,
                        value=param.value,
                    )
                    param_entity = NiFiParameterEntity(parameter=param_dto)
                    parameters.append(param_entity)

            # Mark parameters for deletion (exist in NiFi but not in desired list)
            for param_name in existing_param_map.keys():
                if param_name not in desired_param_names:
                    print(f"Marking parameter for deletion: {param_name}")
                    # Create a parameter entity with value_removed=True to mark for deletion
                    delete_param_dto = ParameterDTO(
                        name=param_name,
                        value_removed=True,
                    )
                    delete_param_entity = NiFiParameterEntity(
                        parameter=delete_param_dto
                    )
                    parameters.append(delete_param_entity)
        else:
            # Keep all existing parameters if not provided
            parameters = list(existing_param_map.values())

        print(
            f"Final parameters list has {len(parameters)} parameters (including deletions)"
        )
        for p in parameters:
            if hasattr(p.parameter, "value_removed") and p.parameter.value_removed:
                print(f"  - {p.parameter.name} (MARKED FOR DELETION)")
            else:
                print(f"  - {p.parameter.name}")

        # Now modify the existing context in place
        existing_context.component.parameters = parameters
        if data.name is not None:
            existing_context.component.name = data.name
        if data.description is not None:
            existing_context.component.description = data.description

        # Submit update request with the modified existing context
        update_response = param_api.submit_parameter_context_update(
            context_id=context_id, body=existing_context
        )

        # Wait for update to complete (poll the update request)
        request_id = update_response.request.request_id
        print(f"Update request submitted, request_id: {request_id}")
        max_attempts = 30
        attempt = 0

        while attempt < max_attempts:
            status_response = param_api.get_parameter_context_update(
                context_id=context_id, request_id=request_id
            )

            # Log detailed status information
            percent = (
                status_response.request.percent_completed
                if hasattr(status_response.request, "percent_completed")
                else 0
            )
            state = (
                status_response.request.state
                if hasattr(status_response.request, "state")
                else "unknown"
            )
            print(
                f"Attempt {attempt}: complete={status_response.request.complete}, state={state}, percent={percent}%"
            )

            # Also check for affected components
            if hasattr(status_response.request, "update_steps"):
                print(f"  Update steps: {len(status_response.request.update_steps)}")
                for step in status_response.request.update_steps:
                    if hasattr(step, "description") and hasattr(step, "complete"):
                        print(
                            f"    - {step.description}: {'complete' if step.complete else 'pending'}"
                        )

            if status_response.request.complete:
                # Check if there was a failure
                if (
                    hasattr(status_response.request, "failure_reason")
                    and status_response.request.failure_reason
                ):
                    print(f"Update failed: {status_response.request.failure_reason}")
                    raise Exception(
                        f"Update failed: {status_response.request.failure_reason}"
                    )

                # Verify it's truly complete (100%)
                if percent < 100:
                    print(f"Warning: Marked complete but only {percent}% done")

                print(f"Update completed successfully at {percent}%")

                # Delete the update request
                param_api.delete_update_request(
                    context_id=context_id, request_id=request_id
                )

                # Verify the update by fetching the context again
                print("Verifying update by fetching context...")
                updated_context = param_api.get_parameter_context(id=context_id)
                actual_param_count = (
                    len(updated_context.component.parameters)
                    if updated_context.component.parameters
                    else 0
                )
                expected_param_count = len(parameters)

                print(
                    f"Expected {expected_param_count} parameters, got {actual_param_count}"
                )
                if updated_context.component.parameters:
                    for p in updated_context.component.parameters:
                        print(
                            f"  - {p.parameter.name if hasattr(p, 'parameter') else 'unknown'}"
                        )

                return {
                    "status": "success",
                    "message": "Parameter context updated successfully",
                    "parameter_context": {
                        "id": context_id,
                        "name": data.name or existing_context.component.name,
                        "actual_parameter_count": actual_param_count,
                        "expected_parameter_count": expected_param_count,
                    },
                }

            time.sleep(0.5)
            attempt += 1

        # If we get here, update timed out
        print(f"Update request timed out after {max_attempts} attempts")
        raise Exception("Update request timed out")

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update parameter context: {error_msg}",
        )


@router.delete("/{instance_id}/parameter-contexts/{context_id}")
async def delete_parameter_context(
    instance_id: int,
    context_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """Delete a parameter context from NiFi instance"""
    instance = get_instance_or_404(db, instance_id)

    try:
        from nipyapi.nifi.apis.parameter_contexts_api import ParameterContextsApi

        # Configure nipyapi with authentication
        setup_nifi_connection(instance)

        # Get existing parameter context to get current revision
        param_api = ParameterContextsApi()
        existing_context = param_api.get_parameter_context(id=context_id)

        # Delete parameter context
        param_api.delete_parameter_context(
            id=context_id,
            version=existing_context.revision.version,
        )

        return {
            "status": "success",
            "message": "Parameter context deleted successfully",
        }

    except Exception as e:
        error_msg = str(e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete parameter context: {error_msg}",
        )
