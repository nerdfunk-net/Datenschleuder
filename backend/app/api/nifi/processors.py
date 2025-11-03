"""NiFi processor configuration API endpoints"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.deployment import (
    ProcessorConfiguration,
    ProcessorConfigurationResponse,
    ProcessorConfigurationUpdate,
    ProcessorConfigurationUpdateResponse,
)
from app.api.nifi.nifi_helpers import get_instance_or_404, setup_nifi_connection

logger = logging.getLogger(__name__)

router = APIRouter(tags=["nifi-instances"])


@router.get(
    "/{instance_id}/processor/{processor_id}/configuration",
    response_model=ProcessorConfigurationResponse,
)
def get_processor_configuration(
    instance_id: int,
    processor_id: str,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get processor configuration details.

    This endpoint retrieves the configuration of a specific processor including:
    - Processor properties (key-value pairs)
    - Scheduling configuration (period, strategy, execution node)
    - Runtime settings (penalty, yield duration)
    - Auto-terminated relationships
    - Concurrent tasks and run duration

    Args:
        instance_id: ID of the NiFi instance
        processor_id: ID of the processor
        current_user: Authenticated user
        db: Database session

    Returns:
        ProcessorConfigurationResponse: Processor configuration details

    Raises:
        HTTPException:
            - 404: Instance or processor not found
            - 403: Insufficient permissions
            - 500: Configuration retrieval failed
    """
    logger.info("=" * 80)
    logger.info(f"GET PROCESSOR CONFIGURATION REQUEST")
    logger.info(f"User: {current_user.get('sub', 'unknown')}")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Processor ID: {processor_id}")
    logger.info("=" * 80)

    try:
        # Get instance from DB
        instance = get_instance_or_404(db, instance_id)

        logger.info(f"Found instance: {instance.hierarchy_value}")

        # Initialize NiFi connection
        from nipyapi import canvas

        setup_nifi_connection(instance)

        logger.info(f"Retrieving processor {processor_id} configuration")

        # Get processor object
        processor = canvas.get_processor(processor_id, "id")

        if not processor:
            logger.warning(f"Processor {processor_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processor {processor_id} not found",
            )

        logger.info(f"Found processor: {processor.component.name}")
        logger.info(f"Processor type: {processor.component.type}")
        logger.info(f"Processor state: {processor.component.state}")

        # Extract configuration details
        component = processor.component
        config_obj = component.config

        # Build properties dict
        properties = {}
        if config_obj and config_obj.properties:
            properties = dict(config_obj.properties)
            logger.info(f"Processor has {len(properties)} properties")

        # Extract scheduling and runtime configuration
        scheduling_period = config_obj.scheduling_period if config_obj else None
        scheduling_strategy = config_obj.scheduling_strategy if config_obj else None
        execution_node = config_obj.execution_node if config_obj else None
        penalty_duration = config_obj.penalty_duration if config_obj else None
        yield_duration = config_obj.yield_duration if config_obj else None
        bulletin_level = config_obj.bulletin_level if config_obj else None
        comments = config_obj.comments if config_obj else None
        auto_terminated_relationships = (
            list(config_obj.auto_terminated_relationships)
            if config_obj and config_obj.auto_terminated_relationships
            else []
        )
        run_duration_millis = config_obj.run_duration_millis if config_obj else None
        concurrent_tasks = (
            config_obj.concurrently_schedulable_task_count if config_obj else None
        )

        logger.info(f"Scheduling: {scheduling_strategy} - {scheduling_period}")
        logger.info(f"Concurrent tasks: {concurrent_tasks}")
        logger.info(f"Auto-terminated relationships: {auto_terminated_relationships}")

        # Create configuration model
        processor_config = ProcessorConfiguration(
            id=component.id,
            name=component.name,
            type=component.type,
            state=component.state,
            properties=properties,
            scheduling_period=scheduling_period,
            scheduling_strategy=scheduling_strategy,
            execution_node=execution_node,
            penalty_duration=penalty_duration,
            yield_duration=yield_duration,
            bulletin_level=bulletin_level,
            comments=comments,
            auto_terminated_relationships=auto_terminated_relationships,
            run_duration_millis=run_duration_millis,
            concurrent_tasks=concurrent_tasks,
        )

        logger.info("Successfully retrieved processor configuration")
        logger.info("=" * 80)

        return ProcessorConfigurationResponse(
            status="success",
            processor=processor_config,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to get processor configuration: {error_msg}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get processor configuration: {error_msg}",
        )


@router.put(
    "/{instance_id}/processor/{processor_id}/configuration",
    response_model=ProcessorConfigurationUpdateResponse,
)
def update_processor_configuration(
    instance_id: int,
    processor_id: str,
    config_update: ProcessorConfigurationUpdate,
    current_user: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Update processor configuration.

    This endpoint updates the configuration of a specific processor. You can update:
    - Processor properties (key-value pairs)
    - Scheduling configuration (period, strategy, execution node)
    - Runtime settings (penalty, yield duration)
    - Auto-terminated relationships
    - Concurrent tasks and run duration
    - Processor name and comments

    Only the fields provided in the request will be updated. Omitted fields remain unchanged.

    Args:
        instance_id: ID of the NiFi instance
        processor_id: ID of the processor
        config_update: Configuration updates to apply
        current_user: Authenticated user
        db: Database session

    Returns:
        ProcessorConfigurationUpdateResponse: Update status and processor details

    Raises:
        HTTPException:
            - 404: Instance or processor not found
            - 403: Insufficient permissions
            - 500: Configuration update failed
    """
    logger.info("=" * 80)
    logger.info(f"UPDATE PROCESSOR CONFIGURATION REQUEST")
    logger.info(f"User: {current_user.get('sub', 'unknown')}")
    logger.info(f"Instance ID: {instance_id}")
    logger.info(f"Processor ID: {processor_id}")
    logger.info(f"Config update: {config_update.dict(exclude_none=True)}")
    logger.info("=" * 80)

    try:
        # Get instance from DB
        instance = get_instance_or_404(db, instance_id)

        logger.info(f"Found instance: {instance.hierarchy_value}")

        # Initialize NiFi connection
        from nipyapi import canvas

        setup_nifi_connection(instance)

        logger.info(f"Retrieving processor {processor_id} for update")

        # Get current processor object
        processor = canvas.get_processor(processor_id, "id")

        if not processor:
            logger.warning(f"Processor {processor_id} not found")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Processor {processor_id} not found",
            )

        logger.info(f"Found processor: {processor.component.name}")
        logger.info(f"Current state: {processor.component.state}")

        # Build update payload - only include fields that are provided
        update_dict = config_update.dict(exclude_none=True)
        logger.info(f"Updating {len(update_dict)} configuration fields")

        # Use nipyapi.canvas.update_processor
        updated_processor = canvas.update_processor(
            processor=processor,
            update=update_dict,
        )

        if not updated_processor:
            logger.error("Processor update returned None")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update processor configuration",
            )

        logger.info(f"Successfully updated processor: {updated_processor.component.name}")
        logger.info("=" * 80)

        return ProcessorConfigurationUpdateResponse(
            status="success",
            message=f"Processor configuration updated successfully",
            processor_id=updated_processor.component.id,
            processor_name=updated_processor.component.name,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Failed to update processor configuration: {error_msg}")
        import traceback

        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update processor configuration: {error_msg}",
        )
