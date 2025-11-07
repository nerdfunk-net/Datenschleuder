import { apiRequest } from '@/utils/api'

/**
 * Handle conflict resolution for deployment conflicts
 */
export async function handleConflictResolution(
  resolution: 'deploy_anyway' | 'delete_and_deploy' | 'update_version',
  config: any,
  deploymentRequest: any,
  conflictInfo: any
) {
  const existingPgId = conflictInfo.existing_process_group.id

  if (resolution === 'deploy_anyway') {
    // Deploy anyway - clear process_group_name to let NiFi use default name
    const modifiedRequest = {
      ...deploymentRequest,
      process_group_name: null
    }

    const result = await apiRequest(`/api/deploy/${config.instanceId}/flow`, {
      method: 'POST',
      body: JSON.stringify(modifiedRequest)
    })

    if (result.status === 'success') {
      return {
        success: true,
        message: `Successfully deployed!\nProcess Group: ${result.process_group_name}`
      }
    }
    return { success: false, message: 'Deployment failed' }
  } else if (resolution === 'delete_and_deploy') {
    // Delete existing process group first
    await apiRequest(
      `/api/nifi-instances/${config.instanceId}/process-group/${existingPgId}`,
      {
        method: 'DELETE'
      }
    )

    // Then deploy
    const result = await apiRequest(`/api/deploy/${config.instanceId}/flow`, {
      method: 'POST',
      body: JSON.stringify(deploymentRequest)
    })

    if (result.status === 'success') {
      return {
        success: true,
        message: `Successfully deleted and redeployed!\nProcess Group: ${result.process_group_name}`
      }
    }
    return { success: false, message: 'Redeployment failed' }
  } else if (resolution === 'update_version') {
    // Update existing process group to new version
    const updateRequest = {
      version: deploymentRequest.version
    }

    const result = await apiRequest(
      `/api/nifi-instances/${config.instanceId}/process-group/${existingPgId}/update-version`,
      {
        method: 'POST',
        body: JSON.stringify(updateRequest)
      }
    )

    if (result.status === 'success') {
      return {
        success: true,
        message: 'Successfully updated process group to new version!'
      }
    }
    return { success: false, message: 'Version update failed' }
  }

  return { success: false, message: 'Unknown resolution type' }
}
