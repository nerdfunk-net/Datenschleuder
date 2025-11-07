import { apiRequest } from '@/utils/api'
import type { DeploymentConfig, DeploymentSettings } from '@/composables/useDeploymentWizard'

export interface DeploymentRequest {
  template_id: number | null
  parent_process_group_id: string
  process_group_name: string
  version: number | null
  x_position: number
  y_position: number
  stop_versioning_after_deploy: boolean
  disable_after_deploy: boolean
  start_after_deploy: boolean
  hierarchy_attribute?: string
}

export interface DeploymentResult {
  status: string
  message: string
  process_group_id?: string
  process_group_name?: string
}

export interface ConflictResolution {
  action: 'deploy_anyway' | 'delete_and_deploy' | 'update_version'
  deployment_request: DeploymentRequest
}

/**
 * Deploy a flow to a NiFi instance
 */
export async function deployFlow(
  instanceId: number,
  deploymentRequest: DeploymentRequest
): Promise<DeploymentResult> {
  return await apiRequest(`/api/deploy/${instanceId}/flow`, {
    method: 'POST',
    body: JSON.stringify(deploymentRequest)
  })
}

/**
 * Resolve a deployment conflict
 */
export async function resolveDeploymentConflict(
  instanceId: number,
  conflictId: string,
  resolution: ConflictResolution
): Promise<DeploymentResult> {
  return await apiRequest(`/api/deploy/${instanceId}/flow/resolve-conflict`, {
    method: 'POST',
    body: JSON.stringify({
      conflict_id: conflictId,
      ...resolution
    })
  })
}

/**
 * Load all process group paths for a NiFi instance
 */
export async function loadProcessGroupPaths(instanceId: number) {
  return await apiRequest(`/api/nifi-instances/${instanceId}/get-all-paths`)
}

/**
 * Load NiFi instances
 */
export async function loadNiFiInstances() {
  const response = await apiRequest('/api/nifi-instances')
  return response.instances || []
}

/**
 * Load registry flows (templates)
 */
export async function loadRegistryFlows() {
  const response = await apiRequest('/api/registry-flows')
  return response.flows || []
}

/**
 * Load flows for deployment
 */
export async function loadFlows() {
  const response = await apiRequest('/api/flows')
  return response.flows || []
}

/**
 * Load hierarchy configuration
 */
export async function loadHierarchyConfig() {
  const response = await apiRequest('/api/hierarchy-config')
  return response.hierarchy_config || []
}

/**
 * Load deployment settings
 */
export async function loadDeploymentSettings() {
  const response = await apiRequest('/api/deployment-settings')
  return response.settings || {
    global: {
      process_group_name_template: '{last_hierarchy_value}',
      disable_after_deploy: false,
      stop_versioning_after_deploy: false,
      start_after_deploy: false
    },
    paths: {}
  }
}

/**
 * Build deployment request from config and settings
 */
export function buildDeploymentRequest(
  config: DeploymentConfig,
  settings: DeploymentSettings,
  hierarchyAttribute?: string
): DeploymentRequest {
  const request: DeploymentRequest = {
    template_id: config.templateId,
    parent_process_group_id: config.selectedProcessGroupId,
    process_group_name: config.processGroupName,
    version: null, // Use latest version
    x_position: 0,
    y_position: 0,
    stop_versioning_after_deploy: settings.global.stop_versioning_after_deploy,
    disable_after_deploy: settings.global.disable_after_deploy,
    start_after_deploy: settings.global.start_after_deploy
  }

  if (hierarchyAttribute) {
    request.hierarchy_attribute = hierarchyAttribute
  }

  return request
}
