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
  parameter_context_name?: string | null
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

export interface FlowsResponse {
  flows: unknown[]
}

export interface HierarchyAttribute {
  name: string
  label: string
  order: number
  [key: string]: unknown
}

export interface HierarchyResponse {
  hierarchy?: HierarchyAttribute[]
}

export interface DeploymentSettingsResponse {
  global?: {
    process_group_name_template?: string
    disable_after_deploy?: boolean
    stop_versioning_after_deploy?: boolean
    start_after_deploy?: boolean
  }
  paths?: Record<string, { source_path?: string; dest_path?: string }>
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
  const instances = await apiRequest('/api/nifi-instances/')
  if (instances && Array.isArray(instances)) {
    console.log(`Loaded ${instances.length} NiFi instances`)
    return instances
  }
  return []
}

/**
 * Load registry flows (templates)
 */
export async function loadRegistryFlows() {
  const flows = await apiRequest('/api/registry-flows/')
  if (flows && Array.isArray(flows)) {
    console.log(`Loaded ${flows.length} registry flows`)
    return flows
  }
  return []
}

/**
 * Load flows for deployment
 */
export async function loadFlows() {
  const data = await apiRequest('/api/nifi-flows/') as FlowsResponse
  return data.flows || []
}

/**
 * Load hierarchy configuration
 */
export async function loadHierarchyConfig() {
  const data = await apiRequest('/api/settings/hierarchy') as HierarchyResponse
  if (data.hierarchy) {
    return data.hierarchy.sort((a: HierarchyAttribute, b: HierarchyAttribute) => a.order - b.order)
  }
  return []
}

/**
 * Load deployment settings
 */
export async function loadDeploymentSettings() {
  const data = await apiRequest('/api/settings/deploy') as DeploymentSettingsResponse

  // Convert string keys to numbers since JSON serialization converts numeric keys to strings
  const paths: { [key: number]: { source_path?: string; dest_path?: string } } = {}
  if (data.paths) {
    Object.keys(data.paths).forEach((key) => {
      const numKey = parseInt(key, 10)
      if (data.paths) {
        paths[numKey] = data.paths[key]
      }
    })
  }

  return {
    global: {
      process_group_name_template:
        data.global?.process_group_name_template || '{last_hierarchy_value}',
      disable_after_deploy: data.global?.disable_after_deploy || false,
      stop_versioning_after_deploy: data.global?.stop_versioning_after_deploy || false,
      start_after_deploy: data.global?.start_after_deploy || false
    },
    paths: paths
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
    version: config.selectedVersion, // Use selected version or null for latest
    x_position: 0,
    y_position: 0,
    stop_versioning_after_deploy: settings.global.stop_versioning_after_deploy,
    disable_after_deploy: settings.global.disable_after_deploy,
    start_after_deploy: settings.global.start_after_deploy,
    parameter_context_name: config.parameterContextName
  }

  if (hierarchyAttribute) {
    request.hierarchy_attribute = hierarchyAttribute
  }

  return request
}
