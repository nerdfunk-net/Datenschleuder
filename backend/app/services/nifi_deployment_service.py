"""NiFi deployment service layer for handling flow deployment operations."""

from typing import Optional, Tuple, Callable, Any
import logging

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from nipyapi import versioning, canvas
from nipyapi.nifi import ProcessGroupsApi, FlowApi

from app.models.nifi_instance import NiFiInstance
from app.models.registry_flow import RegistryFlow
from app.models.deployment import DeploymentRequest

logger = logging.getLogger(__name__)


class NiFiDeploymentService:
    """Service class for NiFi flow deployment operations."""

    def __init__(self, instance: NiFiInstance, last_hierarchy_attr: str = "cn") -> None:
        """
        Initialize the deployment service.

        Args:
            instance: The NiFi instance to deploy to
            last_hierarchy_attr: The last hierarchy attribute name for routing (e.g., "cn")
        """
        self.instance = instance
        self.last_hierarchy_attr = last_hierarchy_attr

    def get_registry_info(
        self, deployment: DeploymentRequest, db: Session
    ) -> Tuple[str, str, str, Optional[str]]:
        """
        Get registry information from template or direct parameters.

        Args:
            deployment: The deployment request
            db: Database session

        Returns:
            Tuple of (bucket_id, flow_id, registry_client_id, template_name)

        Raises:
            HTTPException: If template not found or required fields missing
        """
        if deployment.template_id:
            template = (
                db.query(RegistryFlow)
                .filter(RegistryFlow.id == deployment.template_id)
                .first()
            )
            if not template:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Template with ID {deployment.template_id} not found",
                )

            logger.info(f"Using template '{template.flow_name}' (ID: {deployment.template_id})")
            logger.info(f"  Registry: {template.registry_name} ({template.registry_id})")
            logger.info(f"  Bucket: {template.bucket_name} ({template.bucket_id})")
            logger.info(f"  Flow: {template.flow_name} ({template.flow_id})")

            return (
                template.bucket_id,
                template.flow_id,
                template.registry_id,
                template.flow_name,
            )
        else:
            if (
                not deployment.bucket_id
                or not deployment.flow_id
                or not deployment.registry_client_id
            ):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Either template_id or (bucket_id, flow_id, registry_client_id) must be provided",
                )

            return (
                deployment.bucket_id,
                deployment.flow_id,
                deployment.registry_client_id,
                None,
            )

    def resolve_parent_process_group(
        self, deployment: DeploymentRequest, find_or_create_func: Callable[[str], str]
    ) -> str:
        """
        Resolve parent process group ID from request.

        Args:
            deployment: The deployment request
            find_or_create_func: Function to find or create process group by path

        Returns:
            Parent process group ID

        Raises:
            HTTPException: If resolution fails
        """
        if deployment.parent_process_group_id:
            logger.info(f"Using provided parent_process_group_id: {deployment.parent_process_group_id}")
            return deployment.parent_process_group_id
        else:
            logger.info(f"Resolving path: '{deployment.parent_process_group_path}'")
            try:
                parent_pg_id = find_or_create_func(
                    deployment.parent_process_group_path or ""
                )
                logger.info(f"✓ Resolved to parent_pg_id: {parent_pg_id}")
                return parent_pg_id
            except HTTPException as e:
                logger.error(
                    f"✗ ERROR: Failed to resolve/create path '{deployment.parent_process_group_path}'"
                )
                logger.error(f"  Error: {e.detail}")
                logger.error(f"  Status Code: {e.status_code}")
                raise
            except Exception as e:
                logger.error(f"✗ UNEXPECTED ERROR during path resolution: {e}")
                import traceback
                traceback.print_exc()
                raise

    def get_bucket_and_flow_identifiers(
        self, bucket_id: str, flow_id: str, registry_client_id: str
    ) -> Tuple[str, str]:
        """
        Get bucket and flow identifiers from registry.

        Args:
            bucket_id: Bucket ID
            flow_id: Flow ID
            registry_client_id: Registry client ID

        Returns:
            Tuple of (bucket_identifier, flow_identifier)
        """
        reg_client = versioning.get_registry_client(registry_client_id, "id")
        reg_client_name = (
            reg_client.component.name
            if hasattr(reg_client, "component")
            else registry_client_id
        )
        logger.info(f"  Registry Client: {reg_client_name}")

        # Skip lookup for GitHub registries
        is_github_registry = (
            "github" in reg_client_name.lower() if reg_client_name else False
        )

        if is_github_registry:
            logger.info("GitHub registry detected, using provided bucket/flow IDs directly")
            return bucket_id, flow_id
        else:
            logger.info("Getting bucket and flow identifiers from NiFi Registry...")
            try:
                bucket = versioning.get_registry_bucket(bucket_id)
                logger.info(f"  Bucket: {bucket.name} ({bucket.identifier})")

                flow = versioning.get_flow_in_bucket(
                    bucket.identifier, identifier=flow_id
                )
                logger.info(f"  Flow: {flow.name} ({flow.identifier})")

                return bucket.identifier, flow.identifier
            except Exception as lookup_error:
                logger.warning(
                    f"  Could not lookup bucket/flow, using provided values: {lookup_error}"
                )
                return bucket_id, flow_id

    def get_deploy_version(
        self,
        deployment: DeploymentRequest,
        reg_client_id: str,
        bucket_identifier: str,
        flow_identifier: str,
    ) -> Optional[int]:
        """
        Determine version to deploy.

        Args:
            deployment: The deployment request
            reg_client_id: Registry client ID
            bucket_identifier: Bucket identifier
            flow_identifier: Flow identifier

        Returns:
            Version to deploy or None for latest
        """
        deploy_version = deployment.version

        if deploy_version is None:
            logger.info("Fetching latest version for flow...")
            try:
                flow_api = FlowApi()

                versions = flow_api.get_versions(
                    registry_id=reg_client_id,
                    bucket_id=bucket_identifier,
                    flow_id=flow_identifier,
                )

                if versions and hasattr(
                    versions, "versioned_flow_snapshot_metadata_set"
                ):
                    metadata_set = versions.versioned_flow_snapshot_metadata_set
                    if metadata_set:
                        # Get the last version (latest)
                        deploy_version = metadata_set[-1].version_control_information.version
                        logger.info(f"  Using latest version: {deploy_version}")
                else:
                    logger.warning("  No versions found, will use default (latest)")
                    deploy_version = None
            except Exception as e:
                logger.warning(f"  Warning: Could not fetch versions: {e}")
                logger.info("  Falling back to version=None")
                deploy_version = None

        return deploy_version

    def check_existing_process_group(
        self, deployment: DeploymentRequest, parent_pg_id: str
    ) -> None:
        """
        Check if process group with same name already exists.

        Args:
            deployment: The deployment request
            parent_pg_id: Parent process group ID

        Raises:
            HTTPException: If process group already exists
        """
        if not deployment.process_group_name:
            return

        logger.info(
            f"Checking if process group '{deployment.process_group_name}' already exists in parent..."
        )

        pg_api = ProcessGroupsApi()

        try:
            parent_pg_response = pg_api.get_process_groups(id=parent_pg_id)

            existing_pg = None
            if hasattr(parent_pg_response, "process_groups"):
                for pg in parent_pg_response.process_groups:
                    if (
                        hasattr(pg, "component")
                        and hasattr(pg.component, "name")
                        and pg.component.name == deployment.process_group_name
                    ):
                        existing_pg = pg
                        break

            if existing_pg:
                logger.warning(
                    f"  ⚠ Process group '{deployment.process_group_name}' already exists!"
                )
                has_version_control = False
                if hasattr(existing_pg, "component") and hasattr(
                    existing_pg.component, "version_control_information"
                ):
                    has_version_control = (
                        existing_pg.component.version_control_information is not None
                    )

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "message": f"Process group '{deployment.process_group_name}' already exists",
                        "existing_process_group": {
                            "id": existing_pg.id,
                            "name": existing_pg.component.name
                            if hasattr(existing_pg, "component")
                            else None,
                            "has_version_control": has_version_control,
                            "running_count": existing_pg.running_count
                            if hasattr(existing_pg, "running_count")
                            else 0,
                            "stopped_count": existing_pg.stopped_count
                            if hasattr(existing_pg, "stopped_count")
                            else 0,
                        },
                    },
                )
            else:
                logger.info(
                    f"  ✓ No existing process group found with name '{deployment.process_group_name}'"
                )

        except HTTPException:
            raise
        except Exception as check_error:
            logger.warning(
                f"  Warning: Could not check for existing process group: {check_error}"
            )

    def deploy_flow_version(
        self,
        parent_pg_id: str,
        deployment: DeploymentRequest,
        bucket_identifier: str,
        flow_identifier: str,
        reg_client_id: str,
        deploy_version: Optional[int],
    ) -> Any:
        """
        Deploy flow version to NiFi.

        Args:
            parent_pg_id: Parent process group ID
            deployment: The deployment request
            bucket_identifier: Bucket identifier
            flow_identifier: Flow identifier
            reg_client_id: Registry client ID
            deploy_version: Version to deploy

        Returns:
            Deployed process group object
        """
        logger.info("Deploying flow using nipyapi.versioning.deploy_flow_version:")
        logger.info(f"  Parent PG: {parent_pg_id}")
        logger.info(f"  Bucket ID: {bucket_identifier}")
        logger.info(f"  Flow ID: {flow_identifier}")
        logger.info(f"  Registry Client ID: {reg_client_id}")
        logger.info(f"  Version: {deploy_version}")
        logger.info(f"  Position: ({deployment.x_position}, {deployment.y_position})")

        deployed_pg = versioning.deploy_flow_version(
            parent_id=parent_pg_id,
            location=(float(deployment.x_position), float(deployment.y_position)),
            bucket_id=bucket_identifier,
            flow_id=flow_identifier,
            reg_client_id=reg_client_id,
            version=deploy_version,
        )

        logger.info(f"✓ Successfully deployed process group: {deployed_pg.id}")
        return deployed_pg

    def rename_process_group(self, deployed_pg: Any, new_name: str) -> Tuple[str, str]:
        """
        Rename deployed process group.

        Args:
            deployed_pg: Deployed process group object
            new_name: New name for the process group

        Returns:
            Tuple of (process_group_id, process_group_name)
        """
        pg_id = deployed_pg.id if hasattr(deployed_pg, "id") else None
        pg_name = (
            deployed_pg.component.name
            if hasattr(deployed_pg, "component")
            and hasattr(deployed_pg.component, "name")
            else None
        )

        if new_name and pg_id:
            try:
                logger.info(f"Renaming process group from '{pg_name}' to '{new_name}'...")

                updated_pg = canvas.update_process_group(
                    pg=deployed_pg, update={"name": new_name}
                )

                pg_name = updated_pg.component.name
                logger.info(f"✓ Successfully renamed process group to '{pg_name}'")

            except Exception as rename_error:
                logger.warning(f"⚠ Warning: Could not rename process group: {rename_error}")

        return pg_id, pg_name

    def extract_deployed_version(self, deployed_pg: Any) -> Optional[int]:
        """
        Extract version from deployed process group.

        Args:
            deployed_pg: Deployed process group object

        Returns:
            Deployed version or None
        """
        if hasattr(deployed_pg, "component") and hasattr(
            deployed_pg.component, "version_control_information"
        ):
            vci = deployed_pg.component.version_control_information
            if vci and hasattr(vci, "version"):
                return vci.version
        return None

    def auto_connect_ports(
        self, pg_id: str, parent_pg_id: str
    ) -> None:
        """
        Auto-connect input and output ports between child and parent process groups.

        Args:
            pg_id: Child process group ID
            parent_pg_id: Parent process group ID
        """
        logger.info("=" * 60)
        logger.info("AUTO-CONNECT PORTS: Starting auto-connection process")
        logger.info(f"  Child process group ID: {pg_id}")
        logger.info(f"  Parent process group ID: {parent_pg_id}")
        logger.info("=" * 60)
        
        pg_api = ProcessGroupsApi()

        # Connect output ports
        logger.info("\n--- Attempting OUTPUT port connections ---")
        self._connect_output_ports(pg_api, pg_id, parent_pg_id)

        # Connect input ports
        logger.info("\n--- Attempting INPUT port connections ---")
        self._connect_input_ports(pg_api, pg_id, parent_pg_id)
        
        logger.info("=" * 60)
        logger.info("AUTO-CONNECT PORTS: Completed auto-connection process")
        logger.info("=" * 60)

    def _auto_connect_port(
        self,
        pg_api: ProcessGroupsApi,
        child_pg_id: str,
        parent_pg_id: str,
        port_type: str,
    ) -> None:
        """
        Connect ports between child and parent process groups.

        Args:
            pg_api: ProcessGroupsApi instance for port operations
            child_pg_id: ID of the child (deployed) process group
            parent_pg_id: ID of the parent process group
            port_type: Type of port to connect ('input' or 'output')

        Raises:
            ValueError: If port_type is not 'input' or 'output'
        """
        if port_type not in ("input", "output"):
            raise ValueError(f"Invalid port_type: {port_type}. Must be 'input' or 'output'")

        try:
            logger.info(f"=== Auto-connect {port_type} ports ===")
            logger.info(f"  Child PG ID: {child_pg_id}")
            logger.info(f"  Parent PG ID: {parent_pg_id}")
            logger.info(f"Checking for {port_type} ports to auto-connect...")

            # Get ports from child process group
            logger.debug(f"  Fetching {port_type} ports from child process group...")
            if port_type == "output":
                child_response = pg_api.get_output_ports(id=child_pg_id)
                logger.debug(f"  Child response type: {type(child_response)}")
                logger.debug(f"  Child response has 'output_ports': {hasattr(child_response, 'output_ports')}")
                child_ports = (
                    child_response.output_ports
                    if hasattr(child_response, "output_ports")
                    else []
                )
            else:  # input
                child_response = pg_api.get_input_ports(id=child_pg_id)
                logger.debug(f"  Child response type: {type(child_response)}")
                logger.debug(f"  Child response has 'input_ports': {hasattr(child_response, 'input_ports')}")
                child_ports = (
                    child_response.input_ports
                    if hasattr(child_response, "input_ports")
                    else []
                )

            logger.info(f"  Child {port_type} ports count: {len(child_ports) if child_ports else 0}")
            if child_ports:
                for idx, port in enumerate(child_ports):
                    port_name = port.component.name if hasattr(port, 'component') and hasattr(port.component, 'name') else 'Unknown'
                    port_id = port.id if hasattr(port, 'id') else 'Unknown'
                    logger.debug(f"    Child port {idx}: '{port_name}' (ID: {port_id})")

            if not child_ports:
                logger.info(
                    f"  No {port_type} ports found in child process group - skipping {port_type} auto-connect"
                )
                return

            logger.info(
                f"  Found {len(child_ports)} {port_type} port(s) in deployed process group"
            )

            # Get ports from parent process group
            logger.debug(f"  Fetching {port_type} ports from parent process group...")
            if port_type == "output":
                parent_response = pg_api.get_output_ports(id=parent_pg_id)
                logger.debug(f"  Parent response type: {type(parent_response)}")
                logger.debug(f"  Parent response has 'output_ports': {hasattr(parent_response, 'output_ports')}")
                parent_ports = (
                    parent_response.output_ports
                    if hasattr(parent_response, "output_ports")
                    else []
                )
            else:  # input
                parent_response = pg_api.get_input_ports(id=parent_pg_id)
                logger.debug(f"  Parent response type: {type(parent_response)}")
                logger.debug(f"  Parent response has 'input_ports': {hasattr(parent_response, 'input_ports')}")
                parent_ports = (
                    parent_response.input_ports
                    if hasattr(parent_response, "input_ports")
                    else []
                )

            logger.info(f"  Parent {port_type} ports count: {len(parent_ports) if parent_ports else 0}")
            if parent_ports:
                for idx, port in enumerate(parent_ports):
                    port_name = port.component.name if hasattr(port, 'component') and hasattr(port.component, 'name') else 'Unknown'
                    port_id = port.id if hasattr(port, 'id') else 'Unknown'
                    logger.debug(f"    Parent port {idx}: '{port_name}' (ID: {port_id})")

            if not parent_ports:
                logger.info(
                    f"  No {port_type} ports found in parent process group - skipping {port_type} auto-connect"
                )
                return

            logger.info(
                f"  Found {len(parent_ports)} {port_type} port(s) in parent process group"
            )

            # Get first port from each (index 0)
            child_port = child_ports[0]
            parent_port = parent_ports[0]

            # For output ports: child -> parent
            # For input ports: parent -> child
            if port_type == "output":
                source_port = child_port
                target_port = parent_port
            else:  # input
                source_port = parent_port
                target_port = child_port

            source_name = source_port.component.name if hasattr(source_port, 'component') and hasattr(source_port.component, 'name') else 'Unknown'
            target_name = target_port.component.name if hasattr(target_port, 'component') and hasattr(target_port.component, 'name') else 'Unknown'
            
            logger.info(
                f"  Connecting {port_type}: '{source_name}' -> '{target_name}'..."
            )
            logger.debug(f"    Source port ID: {source_port.id if hasattr(source_port, 'id') else 'Unknown'}")
            logger.debug(f"    Target port ID: {target_port.id if hasattr(target_port, 'id') else 'Unknown'}")

            created_conn = canvas.create_connection(
                source=source_port,
                target=target_port,
                name=f"{source_name} to {target_name}",
            )

            logger.info(
                f"  ✓ Successfully created {port_type} connection (ID: {created_conn.id})"
            )

        except Exception as connect_error:
            logger.error(
                f"⚠ ERROR: Could not auto-connect {port_type} ports: {connect_error}"
            )
            logger.error(f"  Error type: {type(connect_error).__name__}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            logger.warning(
                f"⚠ Warning: Could not auto-connect {port_type} ports: {connect_error}"
            )

    def _connect_output_ports(
        self, pg_api: ProcessGroupsApi, child_pg_id: str, parent_pg_id: str
    ) -> None:
        """
        Connect output ports between child and parent process groups.

        Deprecated: Use _auto_connect_port() with port_type='output' instead.
        """
        self._auto_connect_port(pg_api, child_pg_id, parent_pg_id, "output")

    def _connect_input_ports(
        self, pg_api: ProcessGroupsApi, child_pg_id: str, parent_pg_id: str
    ) -> None:
        """
        Connect input ports between parent and child process groups.

        Strategy (Priority Order):
        1. Check if parent has a RouteOnAttribute processor - if yes, connect to child INPUT port
        2. If no RouteOnAttribute, try standard port-to-port connection (parent INPUT port -> child INPUT port)

        Args:
            pg_api: ProcessGroupsApi instance for port operations
            child_pg_id: ID of the child (deployed) process group
            parent_pg_id: ID of the parent process group
        """
        try:
            logger.info("=== Connecting INPUT ports ===")
            logger.info(f"  Child PG ID: {child_pg_id}")
            logger.info(f"  Parent PG ID: {parent_pg_id}")
            
            # Get child input ports
            logger.debug("  Fetching input ports from child process group...")
            child_response = pg_api.get_input_ports(id=child_pg_id)
            child_ports = (
                child_response.input_ports
                if hasattr(child_response, "input_ports")
                else []
            )
            
            logger.info(f"  Child input ports count: {len(child_ports) if child_ports else 0}")
            
            if not child_ports:
                logger.info("  No input ports found in child process group - skipping input auto-connect")
                return
            
            child_port = child_ports[0]
            child_port_name = child_port.component.name if hasattr(child_port, 'component') and hasattr(child_port.component, 'name') else 'Unknown'
            logger.info(f"  Child input port: '{child_port_name}' (ID: {child_port.id})")

            # Strategy 1 (PRIORITY): Check for RouteOnAttribute processor in parent
            logger.info("  Strategy 1 (Priority): Looking for RouteOnAttribute processor in parent...")
            logger.debug("  Fetching processors from parent process group...")
            processors_list = canvas.list_all_processors(pg_id=parent_pg_id)
            
            if not processors_list:
                logger.warning("  No processors found in parent process group")
                return
            
            logger.info(f"  Found {len(processors_list)} processor(s) in parent")
            
            # Find RouteOnAttribute processor
            route_processor = None
            for processor in processors_list:
                processor_type = (
                    processor.component.type
                    if hasattr(processor, "component") and hasattr(processor.component, "type")
                    else None
                )
                processor_name = (
                    processor.component.name
                    if hasattr(processor, "component") and hasattr(processor.component, "name")
                    else "Unknown"
                )
                processor_pg_id = (
                    processor.component.parent_group_id
                    if hasattr(processor, "component") and hasattr(processor.component, "parent_group_id")
                    else "Unknown"
                )
                
                logger.debug(f"    Processor: '{processor_name}' (Type: {processor_type}, Parent PG: {processor_pg_id})")
                
                # CRITICAL: Only consider processors that are DIRECTLY in the parent PG
                # Exclude processors from child process groups (like the newly deployed one)
                if processor_pg_id != parent_pg_id:
                    logger.debug(f"      -> Skipping - not in parent PG (expected: {parent_pg_id})")
                    continue
                
                if processor_type == "org.apache.nifi.processors.standard.RouteOnAttribute":
                    route_processor = processor
                    logger.info(f"  ✓ Found RouteOnAttribute processor in PARENT: '{processor_name}' (ID: {processor.id})")
                    break
            
            if not route_processor:
                logger.info("  No RouteOnAttribute processor found in parent")
                logger.info("  Strategy 2 (Fallback): Trying parent INPUT port -> child INPUT port connection")

                # Fallback: Try to get parent INPUT ports
                logger.debug("  Fetching INPUT ports from parent process group...")
                parent_input_response = pg_api.get_input_ports(id=parent_pg_id)
                parent_input_ports = (
                    parent_input_response.input_ports
                    if hasattr(parent_input_response, "input_ports")
                    else []
                )

                logger.info(f"  Parent INPUT ports count: {len(parent_input_ports) if parent_input_ports else 0}")

                if parent_input_ports:
                    logger.info("  Connecting parent INPUT port -> child INPUT port")
                    parent_input_port = parent_input_ports[0]
                    parent_port_name = parent_input_port.component.name if hasattr(parent_input_port, 'component') and hasattr(parent_input_port.component, 'name') else 'Unknown'

                    logger.info(f"  Connecting: '{parent_port_name}' (parent INPUT) -> '{child_port_name}' (child INPUT)...")

                    created_conn = canvas.create_connection(
                        source=parent_input_port,
                        target=child_port,
                        name=f"{parent_port_name} to {child_port_name}",
                    )

                    logger.info(f"  ✓ Successfully created input connection (ID: {created_conn.id})")
                    return
                else:
                    logger.warning("  No parent INPUT port found either - cannot auto-connect")
                    return
            
            # Get the child process group name to use as relationship name
            logger.debug("  Fetching child process group details for relationship name...")
            child_pg = pg_api.get_process_group(id=child_pg_id)
            child_pg_name = (
                child_pg.component.name
                if hasattr(child_pg, "component") and hasattr(child_pg.component, "name")
                else "Unknown"
            )
            
            logger.info(f"  Child PG name: '{child_pg_name}'")
            
            # Get RouteOnAttribute processor configuration to check properties
            route_processor_id = route_processor.id
            logger.info(f"  Checking RouteOnAttribute processor configuration...")
            logger.debug(f"    Processor ID: {route_processor_id}")
            
            # Get processor configuration
            route_config = canvas.get_processor(route_processor_id, "id")
            config_obj = route_config.component.config if hasattr(route_config, "component") else None
            properties = {}
            
            if config_obj and hasattr(config_obj, "properties") and config_obj.properties:
                properties = dict(config_obj.properties)
                logger.info(f"  Current properties: {list(properties.keys())}")
                logger.info(f"  ===== FULL PROPERTY DUMP =====")
                for prop_key, prop_value in properties.items():
                    logger.info(f"    '{prop_key}': '{prop_value}'")
                logger.info(f"  ==============================")
            else:
                logger.warning("  No properties found in RouteOnAttribute processor")
            
            # Check if property for child PG exists
            property_exists = child_pg_name in properties
            logger.info(f"  Looking for property: '{child_pg_name}'")
            logger.info(f"  Property exists: {property_exists}")
            
            # Check if Routing Strategy is correctly set
            routing_strategy = properties.get("Routing Strategy", "")
            logger.debug(f"  Current Routing Strategy: '{routing_strategy}'")
            
            needs_update = False
            if not property_exists:
                logger.info(f"  Property '{child_pg_name}' does NOT exist - will add it")
                needs_update = True
            else:
                logger.info(f"  ✓ Property '{child_pg_name}' already exists with value: {properties[child_pg_name]}")
            
            if routing_strategy != "Route to Property name":
                logger.warning(f"  Routing Strategy is '{routing_strategy}' but should be 'Route to Property name'")
                needs_update = True
            
            if needs_update:
                # Get current processor state
                current_state = route_processor.component.state if hasattr(route_processor, "component") else "STOPPED"
                logger.info(f"  Current processor state: {current_state}")
                
                # Stop processor if running (required for configuration changes)
                if current_state == "RUNNING":
                    logger.info(f"  Stopping processor before configuration update...")
                    try:
                        canvas.schedule_processor(route_processor, scheduled=False)
                        logger.info(f"  ✓ Processor stopped")
                        import time
                        time.sleep(0.5)  # Wait for processor to stop
                    except Exception as stop_error:
                        logger.warning(f"  Could not stop processor: {stop_error}")
                
                # Add/update properties
                if not property_exists:
                    properties[child_pg_name] = f"${{{self.last_hierarchy_attr}:equalsIgnoreCase('{child_pg_name}')}}"
                    logger.info(f"  Added property: '{child_pg_name}' = '{properties[child_pg_name]}'")
                
                if routing_strategy != "Route to Property name":
                    properties["Routing Strategy"] = "Route to Property name"
                    logger.info(f"  Set Routing Strategy to 'Route to Property name'")
                
                logger.info(f"  ===== PROPERTIES TO UPDATE =====")
                logger.info(f"  Total properties: {len(properties)}")
                for prop_key, prop_value in properties.items():
                    logger.info(f"    '{prop_key}': '{prop_value}'")
                logger.info(f"  =================================")
                logger.info(f"  Updating processor configuration...")
                
                # Update processor with new properties
                try:
                    # Create a proper ProcessorConfigDTO object
                    from nipyapi.nifi import ProcessorConfigDTO
                    
                    logger.debug(f"  Creating ProcessorConfigDTO with {len(properties)} properties")
                    
                    # Create updated config with new properties
                    updated_config = ProcessorConfigDTO(properties=properties)
                    
                    logger.debug(f"  Calling canvas.update_processor...")
                    updated_processor = canvas.update_processor(
                        processor=route_processor,
                        update=updated_config,
                    )
                    
                    if updated_processor:
                        logger.info(f"  ✓ Successfully updated RouteOnAttribute processor properties")
                        logger.debug(f"    Updated processor ID: {updated_processor.id}")
                        
                        # Refresh the processor object to get the new relationships
                        # NiFi will validate and register dynamic relationships automatically
                        logger.debug(f"  Refreshing processor to get updated relationships...")
                        import time
                        time.sleep(0.5)  # Wait briefly for NiFi to process the update
                        route_processor = canvas.get_processor(route_processor_id, "id")
                        logger.debug(f"  Processor refreshed successfully")
                    else:
                        logger.error("  ✗ Failed to update processor (returned None)")
                        raise Exception("Processor update returned None")
                        
                except Exception as update_error:
                    logger.error(f"  ✗ Failed to update RouteOnAttribute processor: {update_error}")
                    import traceback
                    logger.error(f"    Traceback: {traceback.format_exc()}")
                    raise
            else:
                logger.info(f"  Configuration is correct - no update needed")
                # Still refresh to get current state
                logger.debug(f"  Refreshing processor to get current relationships...")
                route_processor = canvas.get_processor(route_processor_id, "id")
                logger.debug(f"  Processor refreshed successfully")
            
            # Log available relationships before creating connection
            if hasattr(route_processor, "component") and hasattr(route_processor.component, "relationships"):
                available_rels = [rel.name for rel in route_processor.component.relationships]
                logger.info(f"  ===== RELATIONSHIPS DUMP =====")
                logger.info(f"  Available relationships: {available_rels}")
                logger.info(f"  Number of relationships: {len(available_rels)}")
                for idx, rel in enumerate(route_processor.component.relationships):
                    logger.info(f"    Relationship {idx}: name='{rel.name}', autoTerminate={getattr(rel, 'auto_terminate', 'N/A')}")
                logger.info(f"  ==============================")
                logger.info(f"  Looking for relationship: '{child_pg_name}'")
                logger.info(f"  Relationship '{child_pg_name}' in list: {child_pg_name in available_rels}")
            else:
                logger.warning(f"  Could not retrieve available relationships from processor")
            
            # Create connection from RouteOnAttribute to child input port
            route_processor_name = (
                route_processor.component.name
                if hasattr(route_processor, "component") and hasattr(route_processor.component, "name")
                else "RouteOnAttribute"
            )
            
            logger.info(f"  Creating connection with relationship: '{child_pg_name}'")
            logger.info(f"  Connecting: '{route_processor_name}' -> '{child_port_name}'...")
            logger.debug(f"    Connection parameters: name='{child_pg_name}', relationships=['{child_pg_name}']")
            
            created_conn = canvas.create_connection(
                source=route_processor,
                target=child_port,
                name=child_pg_name,
                relationships=[child_pg_name],
            )
            
            logger.info(f"  ✓ Successfully created RouteOnAttribute connection (ID: {created_conn.id})")
            logger.info(f"    Connection name: '{child_pg_name}'")
            logger.info(f"    Relationship: '{child_pg_name}'")
            
        except Exception as connect_error:
            logger.error(f"⚠ ERROR: Could not auto-connect input ports: {connect_error}")
            logger.error(f"  Error type: {type(connect_error).__name__}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            logger.warning(f"⚠ Warning: Could not auto-connect input ports: {connect_error}")

    def stop_version_control(self, pg_id: str) -> None:
        """
        Stop version control for a deployed process group.

        Args:
            pg_id: Process group ID to remove from version control
        """
        try:
            logger.info(f"=" * 60)
            logger.info(f"STOP VERSION CONTROL: Starting for process group {pg_id}")
            logger.info(f"=" * 60)

            # Get the process group
            pg = canvas.get_process_group(pg_id, 'id')

            if not pg:
                logger.warning(f"  Process group {pg_id} not found")
                return

            # Check if process group is under version control
            logger.info(f"  Checking if process group has version control information...")
            logger.info(f"  - Has 'component' attribute: {hasattr(pg, 'component')}")
            if hasattr(pg, 'component'):
                logger.info(f"  - Has 'version_control_information' attribute: {hasattr(pg.component, 'version_control_information')}")
                if hasattr(pg.component, 'version_control_information'):
                    version_info = pg.component.version_control_information
                    logger.info(f"  - version_control_information is not None: {version_info is not None}")
                    if version_info:
                        logger.info(f"  - Version control info: bucket={getattr(version_info, 'bucket_id', 'N/A')}, flow={getattr(version_info, 'flow_id', 'N/A')}, version={getattr(version_info, 'version', 'N/A')}")

            if not hasattr(pg, 'component') or not hasattr(pg.component, 'version_control_information'):
                logger.info(f"  Process group {pg_id} is not under version control (no version_control_information attribute)")
                return

            version_info = pg.component.version_control_information
            if not version_info:
                logger.info(f"  Process group {pg_id} is not under version control (version_control_information is None)")
                return

            # Stop version control
            logger.info(f"  Removing process group from version control...")
            versioning.stop_flow_ver(pg, refresh=True)

            logger.info(f"  ✓ Version control stopped for process group {pg_id}")
            logger.info(f"=" * 60)

        except Exception as e:
            logger.error(f"  ✗ Failed to stop version control for {pg_id}: {e}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            # Don't raise - this is a non-critical operation
            logger.warning(f"  Warning: Could not stop version control: {e}")

    def stop_process_group(self, pg_id: str) -> None:
        """
        Disable all components in a process group.

        This sets all processors, input ports, and output ports to DISABLED state.
        DISABLED state means components cannot be started (locked/prevented from starting).
        This recursively disables all components within the process group and its child process groups.

        Note: NiFi deploys flows in STOPPED state by default. This method is used when you want
        to go further and DISABLE (lock) the flow to prevent it from being started accidentally.

        Args:
            pg_id: Process group ID to stop
        """
        try:
            from nipyapi.nifi import (
                ProcessorsApi, ProcessorRunStatusEntity, RevisionDTO,
                InputPortsApi, OutputPortsApi, PortRunStatusEntity
            )

            logger.info(f"=" * 60)
            logger.info(f"DISABLE PROCESS GROUP: Starting for process group {pg_id}")
            logger.info(f"=" * 60)

            # Verify the process group exists first
            pg = canvas.get_process_group(pg_id, 'id')

            if not pg:
                logger.warning(f"  Process group {pg_id} not found")
                return

            logger.info(f"  Process group found: {pg.status.name if hasattr(pg, 'status') else 'Unknown'}")
            logger.info(f"  Note: NiFi deploys flows in STOPPED state. This will DISABLE (lock) them.")

            # Get all processors in the process group (recursively)
            processors = canvas.list_all_processors(pg_id)
            logger.info(f"  Found {len(processors)} processor(s) to disable")

            processors_api = ProcessorsApi()
            disabled_processors = 0

            for processor in processors:
                try:
                    processor_id = processor.id
                    current_revision = processor.revision
                    current_state = processor.status.run_status if hasattr(processor, 'status') else 'UNKNOWN'
                    processor_name = processor.status.name if hasattr(processor, 'status') else processor_id

                    logger.info(f"    - Processor: {processor_name} (current state: {current_state})")

                    # Skip if already stopped or disabled
                    if current_state == 'DISABLED':
                        logger.info(f"      Already disabled, skipping")
                        continue

                    run_status = ProcessorRunStatusEntity(
                        revision=RevisionDTO(version=current_revision.version),
                        state="DISABLED"
                    )

                    # Use the correct API method name: update_run_status4
                    processors_api.update_run_status4(body=run_status, id=processor_id)
                    disabled_processors += 1
                    logger.info(f"      ✓ Disabled (locked - cannot be started)")

                except Exception as e:
                    logger.warning(f"      ✗ Failed to disable processor {processor_id}: {e}")
                    logger.error(f"      Error details: {type(e).__name__}")
                    # Continue with other processors

            logger.info(f"  Disabled {disabled_processors} processor(s)")

            # Get all input ports (recursively)
            input_ports = canvas.list_all_input_ports(pg_id)
            logger.info(f"  Found {len(input_ports)} input port(s) to disable")

            input_ports_api = InputPortsApi()
            disabled_input_ports = 0

            for port in input_ports:
                try:
                    port_id = port.id
                    current_revision = port.revision
                    current_state = port.status.run_status if hasattr(port, 'status') else 'UNKNOWN'
                    port_name = port.status.name if hasattr(port, 'status') else port_id

                    logger.info(f"    - Input Port: {port_name} (current state: {current_state})")

                    # Skip if already stopped or disabled
                    if current_state == 'DISABLED':
                        logger.info(f"      Already disabled, skipping")
                        continue

                    run_status = PortRunStatusEntity(
                        revision=RevisionDTO(version=current_revision.version),
                        state="DISABLED"
                    )

                    # Use the correct API method name: update_run_status2
                    input_ports_api.update_run_status2(body=run_status, id=port_id)
                    disabled_input_ports += 1
                    logger.info(f"      ✓ Disabled")

                except Exception as e:
                    logger.warning(f"      ✗ Failed to disable input port {port_id}: {e}")
                    logger.error(f"      Error details: {type(e).__name__}")
                    # Continue with other ports

            logger.info(f"  Disabled {disabled_input_ports} input port(s)")

            # Get all output ports (recursively)
            output_ports = canvas.list_all_output_ports(pg_id)
            logger.info(f"  Found {len(output_ports)} output port(s) to disable")

            output_ports_api = OutputPortsApi()
            disabled_output_ports = 0

            for port in output_ports:
                try:
                    port_id = port.id
                    current_revision = port.revision
                    current_state = port.status.run_status if hasattr(port, 'status') else 'UNKNOWN'
                    port_name = port.status.name if hasattr(port, 'status') else port_id

                    logger.info(f"    - Output Port: {port_name} (current state: {current_state})")

                    # Skip if already stopped or disabled
                    if current_state == 'DISABLED':
                        logger.info(f"      Already disabled, skipping")
                        continue

                    run_status = PortRunStatusEntity(
                        revision=RevisionDTO(version=current_revision.version),
                        state="DISABLED"
                    )

                    # Use the correct API method name: update_run_status3
                    output_ports_api.update_run_status3(body=run_status, id=port_id)
                    disabled_output_ports += 1
                    logger.info(f"      ✓ Disabled")

                except Exception as e:
                    logger.warning(f"      ✗ Failed to stop output port {port_id}: {e}")
                    logger.error(f"      Error details: {type(e).__name__}")
                    # Continue with other ports

            logger.info(f"  Disabled {disabled_output_ports} output port(s)")

            total_disabled = disabled_processors + disabled_input_ports + disabled_output_ports
            logger.info(f"  ✓ Process group disabled successfully (total: {total_disabled} components)")
            logger.info(f"  Components are DISABLED (locked - cannot be started)")
            logger.info(f"=" * 60)

        except Exception as e:
            logger.error(f"  ✗ Failed to disable process group {pg_id}: {e}")
            import traceback
            logger.error(f"  Traceback: {traceback.format_exc()}")
            # Don't raise - this is a non-critical operation
            logger.warning(f"  Warning: Could not disable process group: {e}")
