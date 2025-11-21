import type { Ref } from 'vue'
import * as deploymentService from '@/services/deploymentService'
import * as processGroupUtils from '@/utils/processGroupUtils'
import * as flowUtils from '@/utils/flowUtils'
import type {
  Flow,
  DeploymentConfig,
  HierarchyAttribute,
  DeploymentSettings,
  ProcessGroupPath,
  DeploymentResults,
  ConflictInfo,
} from './useDeploymentWizard'

/**
 * Composable for deployment operations (preparing configs, deploying flows)
 */
export function useDeploymentOperations(
  selectedFlows: Ref<number[]>,
  deploymentTargets: Ref<Record<number, 'source' | 'destination' | 'both'>>,
  hierarchyConfig: Ref<HierarchyAttribute[]>,
  nifiInstances: Ref<Array<Record<string, unknown>>>,
  registryFlows: Ref<Array<Record<string, unknown>>>,
  processGroupPaths: Ref<Record<string, ProcessGroupPath[]>>,
  deploymentSettings: Ref<DeploymentSettings>,
  deploymentConfigs: Ref<DeploymentConfig[]>,
  isLoadingPaths: Ref<boolean>,
  isDeploying: Ref<boolean>,
  conflictInfo: Ref<unknown>,
  currentConflictDeployment: Ref<unknown>,
  showConflictModal: Ref<boolean>,
  deploymentResults: Ref<DeploymentResults | null>,
  showResultsModal: Ref<boolean>,
  flows: Ref<Flow[]>
) {
  /**
   * Prepare deployment configurations for selected flows
   */
  const prepareDeploymentConfigs = async (flows: Flow[]) => {
    deploymentConfigs.value = []
    isLoadingPaths.value = true

    try {
      // Build deployment configs based on selected flows and targets
      for (const flowId of selectedFlows.value) {
        const flow = flows.find((f: Flow) => f.id === flowId)
        if (!flow) continue

        const target = deploymentTargets.value[flowId]
        const flowName = flowUtils.getFlowName(flow, hierarchyConfig.value)

        // Process source deployment
        if (target === 'source' || target === 'both') {
          await createDeploymentConfig(flow, flowName, 'source')
        }

        // Process destination deployment
        if (target === 'destination' || target === 'both') {
          await createDeploymentConfig(flow, flowName, 'destination')
        }
      }
    } catch (error) {
      console.error('Error preparing deployment configs:', error)
    } finally {
      isLoadingPaths.value = false
    }
  }

  /**
   * Create a single deployment configuration
   */
  const createDeploymentConfig = async (
    flow: Flow,
    flowName: string,
    target: 'source' | 'destination'
  ) => {
    const hierarchyValue = flowUtils.getTopHierarchyValue(
      flow,
      target,
      hierarchyConfig.value
    )

    const instanceId = await flowUtils.getInstanceIdForHierarchyValue(
      hierarchyValue,
      hierarchyConfig.value[0]?.name || 'DC',
      nifiInstances.value
    )

    const templateIdRaw = target === 'source' ? flow.src_template_id : flow.dest_template_id
    const templateId = typeof templateIdRaw === 'number' ? templateIdRaw : null
    const templateName = flowUtils.getTemplateName(templateId, registryFlows.value)
    const paramContextRaw = target === 'source' ? flow.src_connection_param : flow.dest_connection_param
    const parameterContextName = typeof paramContextRaw === 'string' ? paramContextRaw : null

    const config: DeploymentConfig = {
      key: `${flow.id}-${target}`,
      flowId: flow.id,
      flowName,
      target,
      hierarchyValue,
      instanceId,
      availablePaths: [],
      selectedProcessGroupId: '',
      suggestedPath: processGroupUtils.getSuggestedPath(flow, target, hierarchyConfig.value),
      templateId,
      templateName,
      processGroupName: processGroupUtils.generateProcessGroupName(
        flow,
        target,
        hierarchyConfig.value,
        deploymentSettings.value?.global?.process_group_name_template || '{last_hierarchy_value}'
      ),
      parameterContextName
    }

    // Load paths for this instance
    if (instanceId) {
      const cacheKey = hierarchyValue
      const rawPaths = await loadProcessGroupPaths(instanceId, cacheKey)
      config.availablePaths = rawPaths

      // Auto-select process group based on deployment settings
      const selectedPgId = processGroupUtils.autoSelectProcessGroup(
        flow,
        target,
        instanceId,
        processGroupPaths.value[cacheKey] || [],
        deploymentSettings.value,
        hierarchyConfig.value
      )
      if (selectedPgId) {
        config.selectedProcessGroupId = selectedPgId
      }
    }

    deploymentConfigs.value.push(config)
  }

  /**
   * Load process group paths with caching
   */
  const loadProcessGroupPaths = async (
    instanceId: number,
    cacheKey: string
  ): Promise<Array<{ id: string; pathDisplay: string }>> => {
    // Check cache first
    if (processGroupPaths.value[cacheKey]) {
      return processGroupUtils.formatPathsForDisplay(processGroupPaths.value[cacheKey])
    }

    try {
      const data = await deploymentService.loadProcessGroupPaths(instanceId) as { status: string; process_groups?: ProcessGroupPath[] }

      if (data.status === 'success' && data.process_groups) {
        processGroupPaths.value[cacheKey] = data.process_groups
        return processGroupUtils.formatPathsForDisplay(data.process_groups)
      }

      return []
    } catch (error) {
      console.error('Error loading process group paths:', error)
      return processGroupUtils.getMockPaths()
    }
  }

  /**
   * Deploy all configured flows
   * IMPORTANT: For flows with both source and destination, deploy destination first!
   */
  const deployFlows = async () => {
    isDeploying.value = true

    try {
      console.warn('Deploying flows with configs:', deploymentConfigs.value)

      const results = []
      let successCount = 0
      let failCount = 0

      // Track failed destination deployments to skip corresponding sources
      const failedDestinations = new Set<number>()

      // Sort deployments: destinations first, then sources
      // This ensures receiving end is ready before sending starts
      const sortedConfigs = [...deploymentConfigs.value].sort((a, b) => {
        // Group by flowId first to keep related deployments together
        if (a.flowId !== b.flowId) {
          return a.flowId - b.flowId
        }
        // Within same flow: destination (0) before source (1)
        const targetOrder: Record<'source' | 'destination', number> = { destination: 0, source: 1 }
        const aTarget = a.target as 'source' | 'destination'
        const bTarget = b.target as 'source' | 'destination'
        return targetOrder[aTarget] - targetOrder[bTarget]
      })

      console.warn('Deployment order (destination → source):',
        sortedConfigs.map(c => `${c.flowName} (${c.target})`).join(' → '))

      // Deploy each configuration in sorted order
      for (const config of sortedConfigs) {
        try {
          // Skip source deployment if corresponding destination failed
          if (config.target === 'source' && failedDestinations.has(config.flowId)) {
            console.warn(
              `⚠️  Skipping source deployment for ${config.flowName} because destination deployment failed`
            )
            failCount++
            results.push({
              success: false,
              message: 'Skipped: Destination deployment failed. Cannot deploy source without working destination.',
              config
            })
            continue
          }

          console.warn(
            `Deploying ${config.flowName} to ${config.target} (${config.hierarchyValue})...`
          )

          if (!config.instanceId) {
            throw new Error(`No NiFi instance found for ${config.hierarchyValue}`)
          }

          if (!config.selectedProcessGroupId) {
            throw new Error('No process group selected')
          }

          // Calculate hierarchy attribute
          const instanceKey = `${config.target}_${config.instanceId}`
          const hierarchyAttribute = processGroupUtils.getHierarchyAttributeForProcessGroup(
            config.selectedProcessGroupId,
            instanceKey,
            config.instanceId,
            config.target,
            processGroupPaths.value,
            deploymentSettings.value,
            hierarchyConfig.value
          )

          // Build deployment request
          const deploymentRequest = deploymentService.buildDeploymentRequest(
            config,
            deploymentSettings.value,
            hierarchyAttribute || undefined
          )

          console.warn('Deployment request:', deploymentRequest)

          // Call deployment API
          try {
            const result = await deploymentService.deployFlow(
              config.instanceId,
              deploymentRequest
            )

            console.warn('Deployment result:', result)

            if (result.status === 'success') {
              successCount++
              results.push({
                config,
                success: true,
                message: result.message,
                processGroupId: result.process_group_id,
                processGroupName: result.process_group_name
              })
              console.warn(`✅ Successfully deployed ${config.flowName} (${config.target})`)
            } else {
              failCount++
              results.push({
                config,
                success: false,
                message: result.message || 'Deployment failed'
              })
              // Track failed destination to skip source
              if (config.target === 'destination') {
                failedDestinations.add(config.flowId)
                console.error(`❌ Destination deployment failed for ${config.flowName} - will skip source deployment`)
              }
            }
          } catch (apiError: unknown) {
            // Check if it's a 409 Conflict (process group already exists)
            const error = apiError as { status?: number; detail?: unknown }
            if (error.status === 409 && error.detail) {
              console.warn('Conflict detected:', error.detail)

              // Store conflict info and current deployment config
              conflictInfo.value = error.detail as ConflictInfo
              const matchedFlow = flows.value.find((f: Flow) => f.id === config.flowId)
              const instanceId = config.instanceId
              
              if (matchedFlow && instanceId) {
                currentConflictDeployment.value = { 
                  flow: matchedFlow,
                  target: config.target,
                  instanceId: instanceId,
                  hierarchyValue: config.hierarchyValue,
                  processGroupName: config.processGroupName,
                  deploymentRequest,
                  config
                }
              }

              // Show conflict modal and wait for user decision
              showConflictModal.value = true
              isDeploying.value = false

              // Stop the deployment loop
              return
            }

            // For other errors, add to results
            throw apiError
          }
        } catch (error: unknown) {
          failCount++
          console.error(`Deployment failed for ${config.flowName}:`, error)

          const errorMessage = extractErrorMessage(error)

          results.push({
            config,
            success: false,
            message: errorMessage
          })

          // Track failed destination to skip source
          if (config.target === 'destination') {
            failedDestinations.add(config.flowId)
            console.error(`❌ Destination deployment failed for ${config.flowName} - will skip source deployment`)
          }
        }
      }

      // Update deployment results
      deploymentResults.value = {
        successCount,
        failCount,
        total: deploymentConfigs.value.length,
        successful: results.filter((r) => r.success),
        failed: results.filter((r) => !r.success)
      }

      // Show results modal
      showResultsModal.value = true
    } catch (error) {
      console.error('Deployment process failed:', error)
      window.alert('Deployment process failed. Check console for details.')
    } finally {
      isDeploying.value = false
    }
  }

  /**
   * Extract error message from various error structures
   */
  const extractErrorMessage = (error: unknown): string => {
    if (!error) return 'Unknown error'
    if (typeof error === 'string') return error

    // Cast to a generic error object type
    const err = error as Record<string, unknown>

    // Check common error message paths
    const detail = err.detail as Record<string, unknown> | undefined
    if (detail?.message && typeof detail.message === 'string') return detail.message
    if (detail?.error && typeof detail.error === 'string') return detail.error
    if (err.message && typeof err.message === 'string') return err.message
    if (err.error && typeof err.error === 'string') return err.error
    if (err.statusText && typeof err.statusText === 'string') return err.statusText

    // If detail is an object, try to stringify it nicely
    if (detail && typeof detail === 'object') {
      try {
        return JSON.stringify(detail, null, 2)
      } catch {
        return 'Complex error - see console'
      }
    }

    // Last resort
    try {
      return JSON.stringify(error, null, 2)
    } catch {
      return 'Error converting error to string'
    }
  }

  return {
    prepareDeploymentConfigs,
    deployFlows,
    loadProcessGroupPaths
  }
}
