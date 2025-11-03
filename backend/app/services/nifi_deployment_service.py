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

    def __init__(self, instance: NiFiInstance) -> None:
        """
        Initialize the deployment service.

        Args:
            instance: The NiFi instance to deploy to
        """
        self.instance = instance

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

        Deprecated: Use _auto_connect_port() with port_type='input' instead.
        """
        self._auto_connect_port(pg_api, child_pg_id, parent_pg_id, "input")
