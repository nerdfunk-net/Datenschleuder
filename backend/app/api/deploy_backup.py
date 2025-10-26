"""Flow deployment API endpoints"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_token
from app.models.nifi_instance import NiFiInstance
from app.models.registry_flow import RegistryFlow
from app.models.deployment import DeploymentRequest, DeploymentResponse
from app.services.encryption_service import encryption_service

router = APIRouter()


@router.post("/{instance_id}/flow", response_model=DeploymentResponse)
async def deploy_flow(
    instance_id: int,
    deployment: DeploymentRequest,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Deploy a flow from the registry to a NiFi instance.

    This endpoint deploys a versioned flow from a NiFi Registry to the specified
    NiFi instance as a new process group in the specified parent process group.

    Args:
        instance_id: ID of the NiFi instance to deploy to
        deployment: Deployment configuration with either:
            - template_id: Registry flow template ID (will lookup bucket_id, flow_id, registry_id)
            - OR bucket_id, flow_id, registry_client_id: Direct registry information
        parent_process_group_id: Target process group ID (required)

    Returns:
        DeploymentResponse with status and process group information
    """
    # Get the NiFi instance
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    # Determine registry information
    bucket_id = None
    flow_id = None
    registry_client_id = None
    template_name = None

    if deployment.template_id:
        # Lookup registry flow from template_id
        template = db.query(RegistryFlow).filter(RegistryFlow.id == deployment.template_id).first()

        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Template with ID {deployment.template_id} not found",
            )

        bucket_id = template.bucket_id
        flow_id = template.flow_id
        registry_client_id = template.registry_id
        template_name = template.flow_name

        print(f"Using template '{template_name}' (ID: {deployment.template_id})")
        print(f"  Registry: {template.registry_name} ({registry_client_id})")
        print(f"  Bucket: {template.bucket_name} ({bucket_id})")
        print(f"  Flow: {template.flow_name} ({flow_id})")
    else:
        # Use directly provided registry information
        if not deployment.bucket_id or not deployment.flow_id or not deployment.registry_client_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Either template_id or (bucket_id, flow_id, registry_client_id) must be provided",
            )

        bucket_id = deployment.bucket_id
        flow_id = deployment.flow_id
        registry_client_id = deployment.registry_client_id

        print(f"Using direct registry parameters")
        print(f"  Registry Client: {registry_client_id}")
        print(f"  Bucket: {bucket_id}")
        print(f"  Flow: {flow_id}")

    # Validate parent process group is provided
    if not deployment.parent_process_group_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="parent_process_group_id is required",
        )

    try:
        import nipyapi
        from nipyapi import config, security, versioning, canvas

        # Configure nipyapi for this instance
        # nipyapi expects the base URL without /nifi-api
        nifi_base_url = instance.nifi_url.rstrip("/")
        if nifi_base_url.endswith('/nifi-api'):
            nifi_base_url = nifi_base_url[:-9]  # Remove /nifi-api suffix

        config.nifi_config.host = f"{nifi_base_url}/nifi-api"
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials and login to get token
        access_token = None
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            try:
                # Login and get access token
                access_token = security.service_login(service='nifi', username=instance.username, password=password)
                if access_token:
                    print(f"Successfully obtained access token")
                else:
                    print(f"service_login returned None, using credentials directly")
            except Exception as login_error:
                print(f"Login error: {login_error}, will try with credentials")

        print(f"Deploying flow to NiFi instance {instance_id} ({instance.hierarchy_attribute}={instance.hierarchy_value})")
        print(f"  Target process group: {deployment.parent_process_group_id}")
        print(f"  Bucket ID: {bucket_id}")
        print(f"  Flow ID: {flow_id}")
        print(f"  Registry Client ID: {registry_client_id}")
        print(f"  Version: {deployment.version or 'latest'}")

        # Verify parent process group exists
        try:
            parent_pg = canvas.get_process_group(deployment.parent_process_group_id, identifier_type='id', greedy=False)
            if parent_pg is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Parent process group with ID {deployment.parent_process_group_id} not found",
                )
            if isinstance(parent_pg, list):
                parent_pg = parent_pg[0] if len(parent_pg) > 0 else None
                if parent_pg is None:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Parent process group with ID {deployment.parent_process_group_id} not found",
                    )

            parent_pg_name = parent_pg.component.name if hasattr(parent_pg, 'component') and hasattr(parent_pg.component, 'name') else 'Unknown'
            print(f"  Parent process group name: {parent_pg_name}")
        except HTTPException:
            raise
        except Exception as e:
            print(f"Error verifying parent process group: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Parent process group with ID {deployment.parent_process_group_id} not found: {str(e)}",
            )

        # Verify registry client exists
        try:
            registry_client = versioning.get_registry_client(registry_client_id)
            if registry_client:
                registry_name = registry_client.component.name if hasattr(registry_client, 'component') and hasattr(registry_client.component, 'name') else registry_client_id
                print(f"  Using registry client: {registry_name}")
        except Exception as e:
            print(f"Warning: Could not verify registry client: {str(e)}")

        # Deploy the flow using nipyapi's ProcessGroupsApi directly
        # This bypasses the buggy list_flow_versions() call in deploy_flow_version()
        location = (deployment.x_position, deployment.y_position)

        print(f"Deploying flow version from registry...")

        try:
            # Get registry client to verify it exists
            target_reg_client = versioning.get_registry_client(registry_client_id, 'id')
            print(f"Verified registry client: {target_reg_client.component.name if hasattr(target_reg_client, 'component') else registry_client_id}")

            # Get the bucket and flow to get the correct identifiers
            print(f"Getting bucket and flow identifiers...")
            try:
                bucket = versioning.get_registry_bucket(bucket_id, service='nifi')
                print(f"  Bucket: {bucket.name} ({bucket.identifier})")

                flow = versioning.get_flow_in_bucket(
                    bucket.identifier,
                    identifier=flow_id,
                    service='nifi'
                )
                print(f"  Flow: {flow.name} ({flow.identifier})")

                # Use the actual identifiers from the registry
                bucket_identifier = bucket.identifier
                flow_identifier = flow.identifier
            except Exception as lookup_error:
                print(f"  Could not lookup bucket/flow, using provided values: {lookup_error}")
                bucket_identifier = bucket_id
                flow_identifier = flow_id

            print(f"Deploying flow using nipyapi.versioning.deploy_flow_version:")
            print(f"  Parent PG: {deployment.parent_process_group_id}")
            print(f"  Registry ID: {target_reg_client.id}")
            print(f"  Bucket ID: {bucket_identifier}")
            print(f"  Flow ID: {flow_identifier}")
            print(f"  Version: {deployment.version if deployment.version else 'latest (None)'}")
            print(f"  Position: {location}")

            # Use nipyapi's deploy_flow_version function directly
            # This handles all the complexity of version resolution
            deployed_pg = versioning.deploy_flow_version(
                parent_id=deployment.parent_process_group_id,
                location=location,
                bucket_id=bucket_identifier,
                flow_id=flow_identifier,
                reg_client_id=target_reg_client.id,
                version=deployment.version  # None = latest version
            )

            print(f"✓ Successfully deployed process group: {deployed_pg.id}")

        except Exception as deploy_error:
            error_msg = str(deploy_error)
            print(f"✗ Deployment failed: {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to deploy flow: {error_msg}")

        # Old complex version fetching logic removed
        if False and flow_version is None:
                # Need to get the latest version from the registry
                print(f"  Fetching latest version from registry...")
                try:
                    # Use direct REST API call to avoid deserialization issues
                    import requests
                    versions_url = f"{nifi_base_url}/nifi-api/flow/registries/{registry_client_id}/buckets/{bucket_id}/flows/{flow_id}/versions"

                    # Use nipyapi's own API client to make the request
                    # This ensures we use the same authentication
                    from nipyapi.nifi import FlowApi
                    flow_api = FlowApi()

                    # Use nipyapi's built-in method but catch and parse the raw response
                    # to avoid deserialization issues
                    try:
                        # Get the raw response using nipyapi's rest client
                        api_client = config.nifi_config.api_client
                        response = api_client.rest_client.GET(
                            versions_url,
                            headers=api_client.default_headers if hasattr(api_client, 'default_headers') else {}
                        )

                        # Parse manually
                        import json
                        response_data = json.loads(response.data.decode('utf-8'))
                        versions_data = response_data
                        response_status = response.status

                        print(f"  Versions API response status: {response_status}")
                    except Exception as api_error:
                        print(f"  Error calling versions API: {api_error}")
                        # Fallback: try direct request with copied headers
                        session = requests.Session()
                        headers = {}

                        # Try to get auth headers from nipyapi
                        if hasattr(api_client, 'default_headers') and api_client.default_headers:
                            for key, value in api_client.default_headers.items():
                                if 'auth' in key.lower() or key == 'Authorization':
                                    headers[key] = value

                        # Add cookies if available
                        if hasattr(api_client, 'cookie') and api_client.cookie:
                            session.cookies.update(api_client.cookie)

                        response = session.get(versions_url, headers=headers, verify=instance.verify_ssl)
                        response_status = response.status_code
                        versions_data = response.json() if response.status_code == 200 else None

                    if response_status == 200 and versions_data:
                        print(f"  Response keys: {list(versions_data.keys())}")

                        # Try different response structures
                        # Structure 1: versionSet.versions
                        if 'versionSet' in versions_data and versions_data['versionSet']:
                            version_set = versions_data['versionSet']
                            print(f"  VersionSet keys: {list(version_set.keys())}")
                            if 'versions' in version_set and len(version_set['versions']) > 0:
                                latest = version_set['versions'][0]
                                print(f"  Latest version keys: {list(latest.keys()) if isinstance(latest, dict) else type(latest)}")
                                if isinstance(latest, dict):
                                    if 'versionedFlowSnapshotMetadata' in latest:
                                        metadata = latest['versionedFlowSnapshotMetadata']
                                        if 'version' in metadata:
                                            flow_version = str(metadata['version'])
                                            print(f"  Found latest version: {flow_version}")
                                    elif 'version' in latest:
                                        flow_version = str(latest['version'])
                                        print(f"  Found latest version (direct): {flow_version}")

                        # Structure 2: Direct versions array
                        elif 'versions' in versions_data and len(versions_data['versions']) > 0:
                            latest = versions_data['versions'][0]
                            if isinstance(latest, dict) and 'version' in latest:
                                flow_version = str(latest['version'])
                                print(f"  Found latest version (direct array): {flow_version}")

                        # Print full response if still not found
                        if flow_version is None:
                            import json
                            print(f"  Full response: {json.dumps(versions_data, indent=2)[:1000]}")

                    else:
                        print(f"  Failed to fetch versions: {response.status_code} - {response.text[:500]}")

                    if flow_version is None:
                        raise Exception("Could not determine latest version from registry")

                except Exception as version_error:
                    print(f"  Error fetching latest version: {version_error}")
                    raise Exception(f"Failed to get latest version: {version_error}")

            print(f"  Using version: {flow_version}")

            # Deploy using the ProcessGroupsApi
            # Create process group with version control information directly
            pg_api = ProcessGroupsApi()

            if False and use_import_flow:
                # Create empty process group first, then import from version control
                print(f"Creating empty process group...")
                pg_entity = ProcessGroupEntity(
                    revision=RevisionDTO(version=0),
                    component=ProcessGroupDTO(
                        name=template_name or 'Deployed Flow',
                        position=PositionDTO(
                            x=float(location[0]),
                            y=float(location[1])
                        )
                    )
                )

                with nipyapi.utils.rest_exceptions():
                    deployed_pg = pg_api.create_process_group(
                        id=deployment.parent_process_group_id,
                        body=pg_entity
                    )

                print(f"✓ Created empty process group: {deployed_pg.id}")
                print(f"Importing latest version from registry...")

                # Now import the flow from version control using VersionsApi
                from nipyapi.nifi import VersionsApi, StartVersionControlRequestEntity
                versions_api = VersionsApi()

                # Create the version control request
                start_vc_request = StartVersionControlRequestEntity(
                    process_group_revision=deployed_pg.revision,
                    versioned_flow=VciDTO(
                        bucket_id=bucket_id,
                        flow_id=flow_id,
                        registry_id=target_reg_client.id,
                        flow_name=template_name or 'Deployed Flow',
                        description='Deployed from datenschleuder'
                    )
                )

                with nipyapi.utils.rest_exceptions():
                    # This initiates version control and imports the flow
                    vci_result = versions_api.save_to_flow_registry(
                        id=deployed_pg.id,
                        body=start_vc_request
                    )

                print(f"✓ Imported flow from registry")

            else:
                # Create process group with version control information directly
                # Build VCI parameters
                vci_params = {
                    'bucket_id': bucket_id,
                    'flow_id': flow_id,
                    'registry_id': target_reg_client.id,
                }

                # Only add version if specified (omit for latest)
                if flow_version is not None:
                    vci_params['version'] = flow_version

                pg_entity = ProcessGroupEntity(
                    revision=RevisionDTO(version=0),
                    component=ProcessGroupDTO(
                        name=template_name or 'Deployed Flow',
                        position=PositionDTO(
                            x=float(location[0]),
                            y=float(location[1])
                        ),
                        version_control_information=VciDTO(**vci_params)
                    )
                )

                print(f"Deploying with VCI params: {vci_params}")

                with nipyapi.utils.rest_exceptions():
                    deployed_pg = pg_api.create_process_group(
                        id=deployment.parent_process_group_id,
                        body=pg_entity
                    )

                print(f"✓ Successfully deployed process group: {deployed_pg.id}")

        except Exception as deploy_error:
            error_msg = str(deploy_error)
            print(f"✗ Deployment failed: {error_msg}")
            import traceback
            traceback.print_exc()
            raise Exception(f"Failed to deploy flow: {error_msg}")

        # Extract process group information
        pg_id = deployed_pg.id if hasattr(deployed_pg, 'id') else None
        pg_name = None
        deployed_version = None

        if hasattr(deployed_pg, 'component'):
            pg_name = deployed_pg.component.name if hasattr(deployed_pg.component, 'name') else None

            # Get version info
            if hasattr(deployed_pg.component, 'version_control_information'):
                vci = deployed_pg.component.version_control_information
                if vci and hasattr(vci, 'version'):
                    deployed_version = vci.version

        success_message = f"Flow deployed successfully to {instance.hierarchy_attribute}={instance.hierarchy_value}"
        if template_name:
            success_message += f" using template '{template_name}'"

        print(f"✓ {success_message}")
        print(f"  Deployed process group: {pg_name} (ID: {pg_id})")
        print(f"  Version: {deployed_version}")

        return DeploymentResponse(
            status="success",
            message=success_message,
            process_group_id=pg_id,
            process_group_name=pg_name,
            instance_id=instance_id,
            bucket_id=bucket_id,
            flow_id=flow_id,
            version=deployed_version or deployment.version,
        )

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"✗ Deployment failed: {error_msg}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to deploy flow: {error_msg}",
        )


@router.get("/{instance_id}/process-group")
async def get_process_group(
    instance_id: int,
    id: str = None,
    name: str = None,
    greedy: bool = True,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get a process group by ID or name.

    Either 'id' or 'name' parameter must be provided.
    If 'id' is provided, searches by process group ID.
    If 'name' is provided, searches by process group name.

    Args:
        instance_id: ID of the NiFi instance
        id: Optional process group ID to search for
        name: Optional process group name to search for
        greedy: If True (default), allows partial matching. If False, requires exact match.

    Returns:
        Process group information (id, name, parent_group_id, etc.)
        If multiple matches found, returns a list of process groups.
    """
    # Validate that at least one search parameter is provided
    if not id and not name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'id' or 'name' parameter must be provided",
        )

    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Search for process group by ID or name
        process_group_result = None

        if id:
            print(f"Searching for process group with ID: {id} (greedy={greedy})")
            process_group_result = canvas.get_process_group(identifier=id, identifier_type='id', greedy=greedy)
        elif name:
            print(f"Searching for process group with name: {name} (greedy={greedy})")
            process_group_result = canvas.get_process_group(identifier=name, identifier_type='name', greedy=greedy)

        if process_group_result is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
            )

        # Helper function to extract process group info
        def extract_pg_info(pg):
            return {
                "id": pg.id if hasattr(pg, 'id') else None,
                "name": pg.component.name if hasattr(pg, 'component') and hasattr(pg.component, 'name') else None,
                "parent_group_id": pg.component.parent_group_id if hasattr(pg, 'component') and hasattr(pg.component, 'parent_group_id') else None,
                "comments": pg.component.comments if hasattr(pg, 'component') and hasattr(pg.component, 'comments') else None,
                "running_count": pg.running_count if hasattr(pg, 'running_count') else 0,
                "stopped_count": pg.stopped_count if hasattr(pg, 'stopped_count') else 0,
                "invalid_count": pg.invalid_count if hasattr(pg, 'invalid_count') else 0,
            }

        # Handle different return types
        if isinstance(process_group_result, list):
            if len(process_group_result) == 0:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group not found with {'ID' if id else 'name'}: {id or name}",
                )

            # Multiple matches - return as list
            pg_list = [extract_pg_info(pg) for pg in process_group_result]
            print(f"Found {len(pg_list)} process groups")

            return {
                "status": "success",
                "process_groups": pg_list,
                "count": len(pg_list),
            }
        else:
            # Single match
            pg_info = extract_pg_info(process_group_result)
            print(f"Found process group: {pg_info['name']} (ID: {pg_info['id']})")

            return {
                "status": "success",
                "process_group": pg_info,
            }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get process group: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group: {error_msg}",
        )


@router.get("/{instance_id}/process-groups")
async def search_process_groups(
    instance_id: int,
    name: str = None,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Search for process groups on a NiFi instance by name.

    If name is not provided, returns all process groups.
    If name is provided, searches for process groups matching that name.

    Args:
        instance_id: ID of the NiFi instance
        name: Optional name to search for (supports partial matching)

    Returns:
        List of process groups with id, name, and parent information
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        process_groups = []

        if name:
            # Search for process groups by name
            print(f"Searching for process groups with name: {name}")
            result = canvas.get_process_group(identifier=name, identifier_type='name', greedy=True)

            # Handle different return types
            if result is None:
                # No matches
                process_groups = []
            elif isinstance(result, list):
                # Multiple matches
                process_groups = result
            else:
                # Single match
                process_groups = [result]
        else:
            # List all process groups
            print("Listing all process groups")
            process_groups = canvas.list_all_process_groups()

        # Format the response
        pg_list = []
        for pg in process_groups:
            pg_info = {
                "id": pg.id if hasattr(pg, 'id') else None,
                "name": pg.component.name if hasattr(pg, 'component') and hasattr(pg.component, 'name') else None,
                "parent_group_id": pg.component.parent_group_id if hasattr(pg, 'component') and hasattr(pg.component, 'parent_group_id') else None,
                "comments": pg.component.comments if hasattr(pg, 'component') and hasattr(pg.component, 'comments') else None,
                "running_count": pg.running_count if hasattr(pg, 'running_count') else 0,
                "stopped_count": pg.stopped_count if hasattr(pg, 'stopped_count') else 0,
                "invalid_count": pg.invalid_count if hasattr(pg, 'invalid_count') else 0,
            }
            pg_list.append(pg_info)

        print(f"Found {len(pg_list)} process groups")

        return {
            "status": "success",
            "process_groups": pg_list,
            "count": len(pg_list),
            "search_name": name,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Failed to search process groups: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search process groups: {error_msg}",
        )


@router.get("/{instance_id}/get-path")
async def get_process_group_path(
    instance_id: int,
    process_group_id: str,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get the full path from a process group to the root.

    Returns a list of all parent process groups from the specified process group
    up to the root process group.

    Args:
        instance_id: ID of the NiFi instance
        process_group_id: ID of the process group to get path for

    Returns:
        List of process groups representing the path to root, with each entry
        containing id, name, and parent_group_id. The list starts with the
        specified process group and ends with the root.
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Get root process group ID for comparison
        root_pg_id = canvas.get_root_pg_id()
        print(f"Root process group ID: {root_pg_id}")

        # Build path from process_group_id to root
        path = []
        current_pg_id = process_group_id
        visited_ids = set()  # Prevent infinite loops

        print(f"Building path from process group ID: {process_group_id}")

        while current_pg_id:
            # Check for circular reference
            if current_pg_id in visited_ids:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail=f"Circular reference detected in process group hierarchy at ID: {current_pg_id}",
                )
            visited_ids.add(current_pg_id)

            # Get current process group
            try:
                current_pg = canvas.get_process_group(identifier=current_pg_id, identifier_type='id', greedy=False)
            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group with ID '{current_pg_id}' not found: {str(e)}",
                )

            if current_pg is None:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Process group with ID '{current_pg_id}' not found",
                )

            # Handle list return (shouldn't happen with ID search, but be safe)
            if isinstance(current_pg, list):
                if len(current_pg) == 0:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail=f"Process group with ID '{current_pg_id}' not found",
                    )
                current_pg = current_pg[0]

            # Extract process group info
            pg_info = {
                "id": current_pg.id if hasattr(current_pg, 'id') else None,
                "name": current_pg.component.name if hasattr(current_pg, 'component') and hasattr(current_pg.component, 'name') else None,
                "parent_group_id": current_pg.component.parent_group_id if hasattr(current_pg, 'component') and hasattr(current_pg.component, 'parent_group_id') else None,
            }

            path.append(pg_info)
            print(f"Added to path: {pg_info['name']} (ID: {pg_info['id']}, Parent: {pg_info['parent_group_id']})")

            # Check if we've reached the root
            if current_pg_id == root_pg_id:
                print("Reached root process group")
                break

            # Move to parent
            parent_id = pg_info['parent_group_id']
            if not parent_id:
                # No parent means we're at root
                print("No parent ID - reached root")
                break

            current_pg_id = parent_id

        print(f"Path built successfully with {len(path)} levels")

        return {
            "status": "success",
            "path": path,
            "depth": len(path),
            "root_id": root_pg_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get process group path: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get process group path: {error_msg}",
        )


@router.get("/{instance_id}/get-all-paths")
async def get_all_process_group_paths(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get all process group paths from the NiFi instance.

    Returns a list of all process groups with their full paths to the root.
    This endpoint recursively traverses the entire canvas starting from root.

    Args:
        instance_id: ID of the NiFi instance

    Returns:
        List of all process groups with their paths, where each entry contains:
        - id: Process group ID
        - name: Process group name
        - parent_group_id: Parent process group ID
        - path: List of parent process groups from this PG to root
        - depth: How deep in the hierarchy (0 = root)
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Get root process group ID
        root_pg_id = canvas.get_root_pg_id()
        print(f"Root process group ID: {root_pg_id}")

        # Get all process groups using nipyapi's recursive function
        print("Fetching all process groups...")
        all_process_groups = canvas.list_all_process_groups(pg_id=root_pg_id)
        print(f"Found {len(all_process_groups)} process groups")

        # Build a map of process groups for quick lookup
        pg_map = {}
        for pg in all_process_groups:
            pg_id = pg.id if hasattr(pg, 'id') else None
            if pg_id:
                pg_map[pg_id] = {
                    "id": pg_id,
                    "name": pg.component.name if hasattr(pg, 'component') and hasattr(pg.component, 'name') else None,
                    "parent_group_id": pg.component.parent_group_id if hasattr(pg, 'component') and hasattr(pg.component, 'parent_group_id') else None,
                    "comments": pg.component.comments if hasattr(pg, 'component') and hasattr(pg.component, 'comments') else None,
                }

        # Function to build path for a process group
        def build_path(pg_id):
            path = []
            current_id = pg_id
            visited = set()

            while current_id and current_id in pg_map:
                if current_id in visited:
                    # Circular reference
                    break
                visited.add(current_id)

                pg_info = pg_map[current_id]
                path.append({
                    "id": pg_info["id"],
                    "name": pg_info["name"],
                    "parent_group_id": pg_info["parent_group_id"],
                })

                # Check if we've reached root
                if current_id == root_pg_id or not pg_info["parent_group_id"]:
                    break

                current_id = pg_info["parent_group_id"]

            return path

        # Build result with paths for each process group
        result = []
        for pg_id, pg_info in pg_map.items():
            path = build_path(pg_id)

            result.append({
                "id": pg_info["id"],
                "name": pg_info["name"],
                "parent_group_id": pg_info["parent_group_id"],
                "comments": pg_info["comments"],
                "path": path,
                "depth": len(path) - 1,  # depth is path length minus 1 (root is depth 0)
            })

        # Sort by depth (root first, then children, etc.)
        result.sort(key=lambda x: x["depth"])

        print(f"Built paths for {len(result)} process groups")

        return {
            "status": "success",
            "process_groups": result,
            "count": len(result),
            "root_id": root_pg_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get all process group paths: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get all process group paths: {error_msg}",
        )


@router.get("/{instance_id}/get-root")
async def get_root_process_group(
    instance_id: int,
    token_data: dict = Depends(verify_token),
    db: Session = Depends(get_db),
):
    """
    Get the root process group ID for a NiFi instance.

    This is useful as the default parent_process_group_id for deployments.

    Args:
        instance_id: ID of the NiFi instance

    Returns:
        Root process group ID and name
    """
    instance = db.query(NiFiInstance).filter(NiFiInstance.id == instance_id).first()

    if not instance:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"NiFi instance with ID {instance_id} not found",
        )

    try:
        import nipyapi
        from nipyapi import config, security, canvas

        # Configure nipyapi
        nifi_url = instance.nifi_url.rstrip("/")
        config.nifi_config.host = nifi_url
        config.nifi_config.verify_ssl = instance.verify_ssl

        if not instance.verify_ssl:
            nipyapi.config.disable_insecure_request_warnings = True

        # Decrypt password if present
        password = None
        if instance.password_encrypted:
            password = encryption_service.decrypt_from_string(instance.password_encrypted)

        # Set credentials
        if instance.username and password:
            config.nifi_config.username = instance.username
            config.nifi_config.password = password
            security.service_login(service='nifi', username=instance.username, password=password)

        # Get root process group ID
        root_pg_id = canvas.get_root_pg_id()
        print(f"Root process group ID: {root_pg_id}")

        # Get root process group details
        root_pg = canvas.get_process_group(root_pg_id, identifier_type='id')

        root_pg_name = None
        if root_pg and hasattr(root_pg, 'component') and hasattr(root_pg.component, 'name'):
            root_pg_name = root_pg.component.name

        return {
            "status": "success",
            "root_process_group_id": root_pg_id,
            "name": root_pg_name,
        }

    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get root process group: {error_msg}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get root process group: {error_msg}",
        )
