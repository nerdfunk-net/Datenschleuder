<template>
  <div class="flows-deploy">
    <div class="page-card">
      <!-- Wizard Header -->
      <div class="card-header">
        <h2 class="card-title">Deploy Flows</h2>
        <div class="wizard-steps">
          <div
            v-for="(step, index) in steps"
            :key="index"
            class="wizard-step"
            :class="{ active: currentStep === index, completed: currentStep > index }"
          >
            <div class="step-number">{{ index + 1 }}</div>
            <div class="step-label">{{ step }}</div>
          </div>
        </div>
      </div>

      <!-- Step 1: Select Flows -->
      <div v-if="currentStep === 0" class="wizard-content">
        <div class="step-header">
          <h3>Step 1: Select Flows to Deploy</h3>
          <p class="text-muted">Choose one or more flows from the list below</p>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="text-center py-5">
          <b-spinner variant="primary"></b-spinner>
          <p class="mt-3 text-muted">Loading flows...</p>
        </div>

        <!-- Flows Table -->
        <div v-else-if="flows.length > 0" class="flows-table-container">
          <table class="flows-table">
            <thead>
              <tr>
                <th>
                  <b-form-checkbox
                    :model-value="allSelected"
                    @update:model-value="toggleSelectAll"
                  />
                </th>
                <th v-for="col in visibleColumns" :key="col.key">
                  {{ col.label }}
                </th>
                <th>Source</th>
                <th>Destination</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="flow in flows"
                :key="flow.id"
                :class="{ selected: selectedFlows.includes(flow.id) }"
                @click="toggleFlow(flow.id)"
              >
                <td @click.stop>
                  <b-form-checkbox
                    :model-value="selectedFlows.includes(flow.id)"
                    @update:model-value="toggleFlow(flow.id)"
                  />
                </td>
                <td v-for="col in visibleColumns" :key="col.key">
                  {{ flow[col.key] || '-' }}
                </td>
                <td>{{ flow.source }}</td>
                <td>{{ flow.destination }}</td>
              </tr>
            </tbody>
          </table>
        </div>

        <!-- Empty State -->
        <div v-else class="empty-state">
          <i class="pe-7s-info display-1 text-muted"></i>
          <h4 class="mt-3 text-muted">No Flows Available</h4>
          <p class="text-muted">There are no flows available for deployment.</p>
          <router-link to="/flows/manage" class="btn btn-primary mt-3">
            <i class="pe-7s-plus"></i>
            Manage Flows
          </router-link>
        </div>

        <div class="wizard-actions">
          <b-button variant="outline-secondary" @click="$router.push('/flows/manage')">
            Cancel
          </b-button>
          <b-button
            variant="primary"
            @click="goToNextStep"
            :disabled="selectedFlows.length === 0"
          >
            Next: Choose Deployment Targets
            <i class="pe-7s-angle-right"></i>
          </b-button>
        </div>
      </div>

      <!-- Step 2: Choose Deployment Target -->
      <div v-if="currentStep === 1" class="wizard-content">
        <div class="step-header">
          <h3>Step 2: Choose Deployment Targets</h3>
          <p class="text-muted">Select where each flow should be deployed</p>
        </div>

        <div class="deployment-targets">
          <div v-for="flow in selectedFlowObjects" :key="flow.id" class="target-card">
            <div class="target-header">
              <h5>{{ getFlowName(flow) }}</h5>
              <span class="text-muted">{{ flow.source }} → {{ flow.destination }}</span>
            </div>

            <div class="target-body">
              <div class="hierarchy-info">
                <div class="hierarchy-item">
                  <span class="label">Top Hierarchy ({{ topHierarchyName }}):</span>
                  <span class="value-badge source">Source: {{ getTopHierarchyValue(flow, 'source') }}</span>
                  <span class="value-badge dest">Dest: {{ getTopHierarchyValue(flow, 'destination') }}</span>
                </div>
              </div>

              <div class="deployment-options">
                <label class="option-label">Deploy to:</label>
                <div class="option-buttons">
                  <b-button
                    :variant="getDeploymentTarget(flow.id) === 'source' ? 'primary' : 'outline-primary'"
                    @click="setDeploymentTarget(flow.id, 'source')"
                    class="target-btn"
                  >
                    <i class="pe-7s-angle-right-circle"></i>
                    Source ({{ getTopHierarchyValue(flow, 'source') }})
                  </b-button>
                  <b-button
                    :variant="getDeploymentTarget(flow.id) === 'destination' ? 'primary' : 'outline-primary'"
                    @click="setDeploymentTarget(flow.id, 'destination')"
                    class="target-btn"
                  >
                    <i class="pe-7s-angle-left-circle"></i>
                    Destination ({{ getTopHierarchyValue(flow, 'destination') }})
                  </b-button>
                  <b-button
                    :variant="getDeploymentTarget(flow.id) === 'both' ? 'primary' : 'outline-primary'"
                    @click="setDeploymentTarget(flow.id, 'both')"
                    class="target-btn"
                  >
                    <i class="pe-7s-refresh-2"></i>
                    Both
                  </b-button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="wizard-actions">
          <b-button variant="outline-secondary" @click="goToPreviousStep">
            <i class="pe-7s-angle-left"></i>
            Back
          </b-button>
          <b-button
            variant="primary"
            @click="goToNextStep"
            :disabled="!allTargetsSelected"
          >
            Next: Choose Process Groups
            <i class="pe-7s-angle-right"></i>
          </b-button>
        </div>
      </div>

      <!-- Step 3: Choose Process Groups -->
      <div v-if="currentStep === 2" class="wizard-content">
        <div class="step-header">
          <h3>Step 3: Choose Process Groups</h3>
          <p class="text-muted">Select the target process group for each deployment</p>
        </div>

        <div v-if="isLoadingPaths" class="text-center py-5">
          <b-spinner variant="primary"></b-spinner>
          <p class="mt-3 text-muted">Loading process groups...</p>
        </div>

        <div v-else class="process-group-selection">
          <div v-for="deployment in deploymentConfigs" :key="deployment.key" class="pg-card">
            <div class="pg-header">
              <h5>{{ deployment.flowName }}</h5>
              <span class="text-muted">
                <i :class="deployment.target === 'source' ? 'pe-7s-angle-right-circle' : 'pe-7s-angle-left-circle'"></i>
                {{ deployment.target === 'source' ? 'Source' : 'Destination' }}
                ({{ deployment.hierarchyValue }})
              </span>
            </div>

            <div class="pg-body">
              <div class="form-group">
                <label>Select Process Group:</label>
                <select
                  class="form-select"
                  v-model="deployment.selectedProcessGroupId"
                  @change="updateProcessGroupSelection(deployment)"
                >
                  <option value="">-- Select a process group --</option>
                  <option
                    v-for="pg in deployment.availablePaths"
                    :key="pg.id"
                    :value="pg.id"
                  >
                    {{ pg.pathDisplay }}
                  </option>
                </select>
              </div>

              <div v-if="deployment.selectedProcessGroupId" class="selected-info">
                <i class="pe-7s-check text-success"></i>
                <span>Selected: <strong>{{ getSelectedPathDisplay(deployment) }}</strong></span>
              </div>
            </div>
          </div>
        </div>

        <div class="wizard-actions">
          <b-button variant="outline-secondary" @click="goToPreviousStep">
            <i class="pe-7s-angle-left"></i>
            Back
          </b-button>
          <b-button
            variant="primary"
            @click="goToNextStep"
            :disabled="!allProcessGroupsSelected"
          >
            Next: Review & Deploy
            <i class="pe-7s-angle-right"></i>
          </b-button>
        </div>
      </div>

      <!-- Step 4: Review & Deploy -->
      <div v-if="currentStep === 3" class="wizard-content">
        <div class="step-header">
          <h3>Step 4: Review & Deploy</h3>
          <p class="text-muted">Review your deployment configuration before proceeding</p>
        </div>

        <div class="review-section">
          <div class="review-summary">
            <div class="summary-item">
              <i class="pe-7s-network"></i>
              <div>
                <div class="summary-label">Total Flows</div>
                <div class="summary-value">{{ selectedFlows.length }}</div>
              </div>
            </div>
            <div class="summary-item">
              <i class="pe-7s-server"></i>
              <div>
                <div class="summary-label">Total Deployments</div>
                <div class="summary-value">{{ deploymentConfigs.length }}</div>
              </div>
            </div>
            <div class="summary-item">
              <i class="pe-7s-config"></i>
              <div>
                <div class="summary-label">Instances Affected</div>
                <div class="summary-value">{{ uniqueInstancesCount }}</div>
              </div>
            </div>
          </div>

          <div class="review-details">
            <h5>Deployment Details</h5>
            <div v-for="deployment in deploymentConfigs" :key="deployment.key" class="review-card">
              <div class="review-card-header">
                <strong>{{ deployment.flowName }}</strong>
                <span class="badge" :class="deployment.target === 'source' ? 'badge-primary' : 'badge-success'">
                  {{ deployment.target }}
                </span>
              </div>
              <div class="review-card-body">
                <div class="review-row">
                  <span class="review-label">Instance:</span>
                  <span>{{ deployment.hierarchyValue }}</span>
                </div>
                <div class="review-row">
                  <span class="review-label">Parent Process Group:</span>
                  <span>{{ getSelectedPathDisplay(deployment) }}</span>
                </div>
                <div class="review-row">
                  <span class="review-label">Final Process Group Name:</span>
                  <span class="final-pg-name">{{ deployment.processGroupName }}</span>
                </div>
                <div class="review-row">
                  <span class="review-label">Template:</span>
                  <span>{{ deployment.templateName || 'No Template' }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="wizard-actions">
          <b-button variant="outline-secondary" @click="goToPreviousStep">
            <i class="pe-7s-angle-left"></i>
            Back
          </b-button>
          <b-button
            variant="success"
            @click="deployFlows"
            :disabled="isDeploying"
          >
            <b-spinner v-if="isDeploying" small class="me-2"></b-spinner>
            <i v-else class="pe-7s-cloud-upload"></i>
            Deploy Now
          </b-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiRequest } from '@/utils/api'

interface Flow {
  id: number
  [key: string]: any
  source: string
  destination: string
}

interface HierarchyAttribute {
  name: string
  label: string
  order: number
}

interface ProcessGroupPath {
  id: string
  name: string
  parent_group_id: string | null
  depth: number
  path: Array<{ id: string; name: string; parent_group_id: string | null }>
}

interface DeploymentConfig {
  key: string
  flowId: number
  flowName: string
  target: 'source' | 'destination'
  hierarchyValue: string
  instanceId: number | null
  availablePaths: Array<{ id: string; pathDisplay: string }>
  selectedProcessGroupId: string
  suggestedPath: string | null
  templateId: number | null
  templateName: string | null
  processGroupName: string
}

const steps = ['Select Flows', 'Choose Targets', 'Choose Process Groups', 'Review & Deploy']
const currentStep = ref(0)
const isLoading = ref(false)
const isLoadingPaths = ref(false)
const isDeploying = ref(false)

// Flow data
const flows = ref<Flow[]>([])
const selectedFlows = ref<number[]>([])
const hierarchyConfig = ref<HierarchyAttribute[]>([])
const visibleColumns = ref<Array<{ key: string; label: string }>>([])
const nifiInstances = ref<any[]>([])
const registryFlows = ref<any[]>([])

// Deployment configuration
const deploymentTargets = ref<Record<number, 'source' | 'destination' | 'both'>>({})
const deploymentConfigs = ref<DeploymentConfig[]>([])
const processGroupPaths = ref<Record<string, ProcessGroupPath[]>>({})
const deploymentSettings = ref<any>(null)

// Computed
const allSelected = computed(() => {
  return flows.value.length > 0 && selectedFlows.value.length === flows.value.length
})

const selectedFlowObjects = computed(() => {
  return flows.value.filter(f => selectedFlows.value.includes(f.id))
})

const topHierarchyName = computed(() => {
  return hierarchyConfig.value.length > 0 ? hierarchyConfig.value[0].name : 'DC'
})

const secondHierarchyName = computed(() => {
  return hierarchyConfig.value.length > 1 ? hierarchyConfig.value[1].name : 'OU'
})

const allTargetsSelected = computed(() => {
  return selectedFlows.value.every(flowId => deploymentTargets.value[flowId])
})

const allProcessGroupsSelected = computed(() => {
  return deploymentConfigs.value.every(config => config.selectedProcessGroupId)
})

const uniqueInstancesCount = computed(() => {
  const instances = new Set(deploymentConfigs.value.map(c => c.hierarchyValue))
  return instances.size
})

// Methods
const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedFlows.value = []
  } else {
    selectedFlows.value = flows.value.map(f => f.id)
  }
}

const toggleFlow = (flowId: number) => {
  const index = selectedFlows.value.indexOf(flowId)
  if (index === -1) {
    selectedFlows.value.push(flowId)
  } else {
    selectedFlows.value.splice(index, 1)
  }
}

const getFlowName = (flow: Flow) => {
  // Try to get the first hierarchy attribute value as the name
  if (hierarchyConfig.value.length > 0) {
    const firstAttr = hierarchyConfig.value[0].name.toLowerCase()
    return flow[`src_${firstAttr}`] || flow[firstAttr] || `Flow ${flow.id}`
  }
  return `Flow ${flow.id}`
}

const getTopHierarchyValue = (flow: Flow, side: 'source' | 'destination') => {
  if (hierarchyConfig.value.length === 0) return 'N/A'

  const topAttr = hierarchyConfig.value[0].name.toLowerCase()
  const prefix = side === 'source' ? 'src_' : 'dest_'
  return flow[`${prefix}${topAttr}`] || 'N/A'
}

const getDeploymentTarget = (flowId: number) => {
  return deploymentTargets.value[flowId]
}

const setDeploymentTarget = (flowId: number, target: 'source' | 'destination' | 'both') => {
  deploymentTargets.value[flowId] = target
}

const goToNextStep = async () => {
  if (currentStep.value === 1) {
    // Moving to step 3: prepare deployment configs and load process groups
    await prepareDeploymentConfigs()
  }
  currentStep.value++
}

const goToPreviousStep = () => {
  currentStep.value--
}

const prepareDeploymentConfigs = async () => {
  deploymentConfigs.value = []
  isLoadingPaths.value = true

  try {
    // Build deployment configs based on selected flows and targets
    for (const flowId of selectedFlows.value) {
      const flow = flows.value.find(f => f.id === flowId)
      if (!flow) continue

      const target = deploymentTargets.value[flowId]
      const flowName = getFlowName(flow)

      if (target === 'source' || target === 'both') {
        const hierarchyValue = getTopHierarchyValue(flow, 'source')
        const instanceId = await getInstanceIdForHierarchyValue(hierarchyValue)
        const templateId = flow.src_template_id || null
        const templateName = getTemplateName(templateId)

        const config: DeploymentConfig = {
          key: `${flowId}-source`,
          flowId,
          flowName,
          target: 'source',
          hierarchyValue,
          instanceId,
          availablePaths: [],
          selectedProcessGroupId: '',
          suggestedPath: getSuggestedPath(flow, 'source'),
          templateId,
          templateName,
          processGroupName: generateProcessGroupName(flow, 'source'),
        }

        // Load paths for this instance
        if (instanceId) {
          const rawPaths = await loadProcessGroupPaths(instanceId, hierarchyValue)
          config.availablePaths = rawPaths

          // Auto-select process group based on deployment settings
          const selectedPgId = autoSelectProcessGroup(flow, 'source', instanceId, processGroupPaths.value[hierarchyValue] || [])
          if (selectedPgId) {
            config.selectedProcessGroupId = selectedPgId
          }
        }

        deploymentConfigs.value.push(config)
      }

      if (target === 'destination' || target === 'both') {
        const hierarchyValue = getTopHierarchyValue(flow, 'destination')
        const instanceId = await getInstanceIdForHierarchyValue(hierarchyValue)
        const templateId = flow.dest_template_id || null
        const templateName = getTemplateName(templateId)

        const config: DeploymentConfig = {
          key: `${flowId}-destination`,
          flowId,
          flowName,
          target: 'destination',
          hierarchyValue,
          instanceId,
          availablePaths: [],
          selectedProcessGroupId: '',
          suggestedPath: getSuggestedPath(flow, 'destination'),
          templateId,
          templateName,
          processGroupName: generateProcessGroupName(flow, 'destination'),
        }

        // Load paths for this instance
        if (instanceId) {
          const rawPaths = await loadProcessGroupPaths(instanceId, hierarchyValue)
          config.availablePaths = rawPaths

          // Auto-select process group based on deployment settings
          const selectedPgId = autoSelectProcessGroup(flow, 'destination', instanceId, processGroupPaths.value[hierarchyValue] || [])
          if (selectedPgId) {
            config.selectedProcessGroupId = selectedPgId
          }
        }

        deploymentConfigs.value.push(config)
      }
    }
  } catch (error) {
    console.error('Error preparing deployment configs:', error)
  } finally {
    isLoadingPaths.value = false
  }
}

const getSuggestedPath = (flow: Flow, side: 'source' | 'destination') => {
  // Get the penultimate hierarchy value (e.g., OU)
  if (hierarchyConfig.value.length < 2) return null

  const secondAttr = hierarchyConfig.value[1].name.toLowerCase()
  const prefix = side === 'source' ? 'src_' : 'dest_'
  const value = flow[`${prefix}${secondAttr}`]

  return value ? `Contains "${value}"` : null
}

const getTemplateName = (templateId: number | null): string | null => {
  if (!templateId) return null

  const template = registryFlows.value.find(rf => rf.id === templateId)
  return template ? template.flow_name : `Template ID ${templateId}`
}

const getInstanceIdForHierarchyValue = async (hierarchyValue: string): Promise<number | null> => {
  try {
    // Ensure we have loaded NiFi instances
    if (nifiInstances.value.length === 0) {
      await loadNiFiInstances()
    }

    // Get the top hierarchy attribute name (e.g., "DC")
    const topHierarchyAttr = topHierarchyName.value

    // Find the instance that matches the hierarchy attribute and value
    const instance = nifiInstances.value.find(
      inst => inst.hierarchy_attribute === topHierarchyAttr && inst.hierarchy_value === hierarchyValue
    )

    if (instance) {
      console.log(`Found NiFi instance ${instance.id} for ${topHierarchyAttr}=${hierarchyValue}`)
      return instance.id
    }

    console.warn(`No NiFi instance found for ${topHierarchyAttr}=${hierarchyValue}`)
    return null
  } catch (error) {
    console.error('Error getting instance ID:', error)
    return null
  }
}

const loadProcessGroupPaths = async (instanceId: number, cacheKey: string): Promise<Array<{ id: string; pathDisplay: string }>> => {
  // Check cache first
  if (processGroupPaths.value[cacheKey]) {
    return formatPathsForDisplay(processGroupPaths.value[cacheKey])
  }

  try {
    const data = await apiRequest(`/api/deploy/${instanceId}/get-all-paths`)

    if (data.status === 'success' && data.process_groups) {
      processGroupPaths.value[cacheKey] = data.process_groups
      return formatPathsForDisplay(data.process_groups)
    }

    return []
  } catch (error) {
    console.error('Error loading process group paths:', error)
    // Return mock data for development when backend is not available
    return getMockPaths()
  }
}

const formatPathsForDisplay = (paths: ProcessGroupPath[]): Array<{ id: string; pathDisplay: string }> => {
  return paths.map(pg => {
    // Reverse the path array so root is first and deepest is last
    const pathNames = pg.path.slice().reverse().map(p => p.name).join(' → ')
    return {
      id: pg.id,
      pathDisplay: pathNames,
    }
  })
}

const getMockPaths = (): Array<{ id: string; pathDisplay: string }> => {
  return [
    { id: 'root', pathDisplay: 'NiFi Flow' },
    { id: 'pg1', pathDisplay: 'NiFi Flow → Engineering' },
    { id: 'pg2', pathDisplay: 'NiFi Flow → Engineering → DataPipeline' },
    { id: 'pg3', pathDisplay: 'NiFi Flow → Marketing' },
    { id: 'pg4', pathDisplay: 'NiFi Flow → Marketing → Analytics' },
  ]
}

const updateProcessGroupSelection = (deployment: DeploymentConfig) => {
  // Selection is already updated via v-model
  console.log(`Selected process group ${deployment.selectedProcessGroupId} for ${deployment.key}`)
}

const getSelectedPathDisplay = (deployment: DeploymentConfig) => {
  const selected = deployment.availablePaths.find(p => p.id === deployment.selectedProcessGroupId)
  return selected?.pathDisplay || 'Not selected'
}

const generateProcessGroupName = (flow: Flow, target: 'source' | 'destination'): string => {
  // Get the template from deployment settings
  const template = deploymentSettings.value?.global?.process_group_name_template || '{last_hierarchy_value}'

  // Get hierarchy values for this flow
  const prefix = target === 'source' ? 'src_' : 'dest_'
  const hierarchyValues: string[] = []

  for (let i = 0; i < hierarchyConfig.value.length; i++) {
    const attrName = hierarchyConfig.value[i].name.toLowerCase()
    const value = flow[`${prefix}${attrName}`] || ''
    hierarchyValues.push(value)
  }

  // Replace placeholders in template
  let result = template

  // Replace {first_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(/{first_hierarchy_value}/g, hierarchyValues[0])
  }

  // Replace {last_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(/{last_hierarchy_value}/g, hierarchyValues[hierarchyValues.length - 1])
  }

  // Replace {N_hierarchy_value} where N is 1, 2, 3, etc.
  for (let i = 0; i < hierarchyValues.length; i++) {
    const placeholder = `{${i + 1}_hierarchy_value}`
    result = result.replace(new RegExp(placeholder.replace(/[{}]/g, '\\$&'), 'g'), hierarchyValues[i])
  }

  return result
}

const autoSelectProcessGroup = (
  flow: Flow,
  target: 'source' | 'destination',
  instanceId: number,
  availablePaths: ProcessGroupPath[]
): string | null => {
  try {
    // Get the search path from deployment settings
    if (!deploymentSettings.value || !deploymentSettings.value.paths || !deploymentSettings.value.paths[instanceId]) {
      return null
    }

    const searchPathId = target === 'source'
      ? deploymentSettings.value.paths[instanceId].source_path
      : deploymentSettings.value.paths[instanceId].dest_path

    if (!searchPathId) {
      return null
    }

    // Find the search path in available paths
    const searchPath = availablePaths.find(p => p.id === searchPathId)
    if (!searchPath) {
      return null
    }

    // Get the search path as an array of names (reversed, since path is stored root-first)
    const searchPathNames = searchPath.path.slice().reverse().map(p => p.name)

    // Get hierarchy attributes for this flow, skipping:
    // - Top hierarchy (index 0) - represents the NiFi instance
    // - Last hierarchy (index length-1) - the final process group that will be created during deployment
    // So we use attributes from index 1 to length-2
    const hierarchyAttributes: string[] = []
    const prefix = target === 'source' ? 'src_' : 'dest_'

    for (let i = 1; i < hierarchyConfig.value.length - 1; i++) {
      const attrName = hierarchyConfig.value[i].name.toLowerCase()
      const value = flow[`${prefix}${attrName}`]
      if (value) {
        hierarchyAttributes.push(value)
      }
    }

    // Now find a path that:
    // 1. Starts with all elements from searchPathNames
    // 2. Contains all hierarchyAttributes in order
    for (const pg of availablePaths) {
      const pgPathNames = pg.path.slice().reverse().map(p => p.name)

      // Check if path starts with search path
      let startsWithSearchPath = true
      for (let i = 0; i < searchPathNames.length; i++) {
        if (pgPathNames[i] !== searchPathNames[i]) {
          startsWithSearchPath = false
          break
        }
      }

      if (!startsWithSearchPath) {
        continue
      }

      // Check if path contains all hierarchy attributes in order
      let matchesHierarchy = true
      let searchIndex = searchPathNames.length // Start searching after the search path prefix

      for (const attr of hierarchyAttributes) {
        let found = false
        for (let i = searchIndex; i < pgPathNames.length; i++) {
          if (pgPathNames[i] === attr) {
            found = true
            searchIndex = i + 1
            break
          }
        }
        if (!found) {
          matchesHierarchy = false
          break
        }
      }

      if (matchesHierarchy) {
        return pg.id
      }
    }

    return null
  } catch (error) {
    console.error('Error in autoSelectProcessGroup:', error)
    return null
  }
}

const deployFlows = async () => {
  isDeploying.value = true

  try {
    console.log('Deploying flows with configs:', deploymentConfigs.value)

    const results = []
    let successCount = 0
    let failCount = 0

    // Deploy each configuration
    for (const config of deploymentConfigs.value) {
      try {
        console.log(`Deploying ${config.flowName} to ${config.target} (${config.hierarchyValue})...`)

        if (!config.instanceId) {
          throw new Error(`No NiFi instance found for ${config.hierarchyValue}`)
        }

        if (!config.selectedProcessGroupId) {
          throw new Error('No process group selected')
        }

        // Prepare deployment request
        const deploymentRequest = {
          template_id: config.templateId,
          parent_process_group_id: config.selectedProcessGroupId,
          process_group_name: config.processGroupName,
          version: null, // Use latest version
          x_position: 0,
          y_position: 0,
        }

        console.log('Deployment request:', deploymentRequest)

        // Call deployment API
        const result = await apiRequest(`/api/deploy/${config.instanceId}/flow`, {
          method: 'POST',
          body: JSON.stringify(deploymentRequest),
        })

        console.log('Deployment result:', result)

        if (result.status === 'success') {
          successCount++
          results.push({
            config,
            success: true,
            message: result.message,
            processGroupId: result.process_group_id,
            processGroupName: result.process_group_name,
          })
        } else {
          failCount++
          results.push({
            config,
            success: false,
            message: result.message || 'Deployment failed',
          })
        }
      } catch (error: any) {
        failCount++
        console.error(`Deployment failed for ${config.flowName}:`, error)
        results.push({
          config,
          success: false,
          message: error.message || error.detail || 'Deployment failed',
        })
      }
    }

    // Show results
    console.log('Deployment results:', results)

    let message = `Deployment completed!\n\n`
    message += `✓ Successful: ${successCount}\n`
    if (failCount > 0) {
      message += `✗ Failed: ${failCount}\n\n`

      // Show failed deployments
      const failures = results.filter(r => !r.success)
      if (failures.length > 0) {
        message += `Failed deployments:\n`
        failures.forEach(f => {
          message += `- ${f.config.flowName} (${f.config.target}): ${f.message}\n`
        })
      }
    }

    alert(message)

    // Reset wizard on success
    if (failCount === 0) {
      currentStep.value = 0
      selectedFlows.value = []
      deploymentTargets.value = {}
      deploymentConfigs.value = []
    }

  } catch (error: any) {
    console.error('Deployment error:', error)
    alert('Deployment failed: ' + (error.message || error))
  } finally {
    isDeploying.value = false
  }
}

const loadFlows = async () => {
  isLoading.value = true
  try {
    const data = await apiRequest('/api/nifi-flows/')
    if (data.flows) {
      flows.value = data.flows
    }
  } catch (error) {
    console.error('Error loading flows:', error)
  } finally {
    isLoading.value = false
  }
}

const loadHierarchyConfig = async () => {
  try {
    const data = await apiRequest('/api/settings/hierarchy')
    if (data.hierarchy) {
      hierarchyConfig.value = data.hierarchy.sort((a: HierarchyAttribute, b: HierarchyAttribute) => a.order - b.order)

      // Build visible columns from hierarchy
      visibleColumns.value = hierarchyConfig.value.map(attr => ({
        key: `src_${attr.name.toLowerCase()}`,
        label: `Src ${attr.name}`,
      }))
    }
  } catch (error) {
    console.error('Error loading hierarchy config:', error)
  }
}

const loadNiFiInstances = async () => {
  try {
    const instances = await apiRequest('/api/nifi-instances/')
    if (instances && Array.isArray(instances)) {
      nifiInstances.value = instances
      console.log(`Loaded ${instances.length} NiFi instances`)
    }
  } catch (error) {
    console.error('Error loading NiFi instances:', error)
  }
}

const loadRegistryFlows = async () => {
  try {
    const flows = await apiRequest('/api/registry-flows/')
    if (flows && Array.isArray(flows)) {
      registryFlows.value = flows
      console.log(`Loaded ${flows.length} registry flows`)
    }
  } catch (error) {
    console.error('Error loading registry flows:', error)
  }
}

const loadDeploymentSettings = async () => {
  try {
    const data = await apiRequest('/api/settings/deploy')

    // Convert string keys to numbers since JSON serialization converts numeric keys to strings
    const paths: { [key: number]: { source_path?: string; dest_path?: string } } = {}
    if (data.paths) {
      Object.keys(data.paths).forEach(key => {
        const numKey = parseInt(key, 10)
        paths[numKey] = data.paths[key]
      })
    }

    deploymentSettings.value = {
      global: data.global,
      paths: paths
    }
  } catch (error) {
    console.error('Error loading deployment settings:', error)
  }
}

onMounted(async () => {
  await loadHierarchyConfig()
  await loadNiFiInstances()
  await loadRegistryFlows()
  await loadDeploymentSettings()
  await loadFlows()
})
</script>

<style scoped lang="scss">
.flows-deploy {
  max-width: 1400px;
  margin: 0 auto;
}

.page-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  padding: 20px 30px;
  border-bottom: 1px solid #e9ecef;
}

.card-title {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0 0 20px 0;
}

// Wizard Steps
.wizard-steps {
  display: flex;
  justify-content: space-between;
  gap: 20px;
}

.wizard-step {
  flex: 1;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px;
  border-radius: 6px;
  background: #f8f9fa;
  transition: all 0.3s;

  &.active {
    background: #e3f2fd;
    border: 2px solid #2196f3;

    .step-number {
      background: #2196f3;
      color: white;
    }
  }

  &.completed {
    background: #e8f5e9;

    .step-number {
      background: #4caf50;
      color: white;
    }
  }
}

.step-number {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #dee2e6;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  flex-shrink: 0;
}

.step-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: #495057;
}

// Wizard Content
.wizard-content {
  padding: 30px;
  min-height: 500px;
}

.step-header {
  margin-bottom: 30px;

  h3 {
    font-size: 1.25rem;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 8px;
  }
}

// Flows Table
.flows-table-container {
  overflow-x: auto;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  margin-bottom: 30px;
}

.flows-table {
  width: 100%;
  border-collapse: collapse;

  thead {
    background: #f8f9fa;

    th {
      padding: 12px 15px;
      text-align: left;
      font-weight: 600;
      color: #495057;
      border-bottom: 2px solid #dee2e6;
      font-size: 0.875rem;
    }
  }

  tbody {
    tr {
      cursor: pointer;
      transition: background 0.2s;

      &:hover {
        background: #f8f9fa;
      }

      &.selected {
        background: #e3f2fd;
      }

      td {
        padding: 12px 15px;
        border-bottom: 1px solid #dee2e6;
        font-size: 0.875rem;
      }
    }
  }
}

// Deployment Targets
.deployment-targets {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 30px;
}

.target-card {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.target-header {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;

  h5 {
    margin: 0 0 5px 0;
    font-size: 1rem;
    font-weight: 600;
  }
}

.target-body {
  padding: 20px;
}

.hierarchy-info {
  margin-bottom: 20px;
}

.hierarchy-item {
  display: flex;
  align-items: center;
  gap: 15px;

  .label {
    font-weight: 600;
    color: #495057;
  }
}

.value-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.875rem;
  font-weight: 500;

  &.source {
    background: #e3f2fd;
    color: #1976d2;
  }

  &.dest {
    background: #e8f5e9;
    color: #388e3c;
  }
}

.deployment-options {
  .option-label {
    display: block;
    font-weight: 600;
    margin-bottom: 10px;
    color: #495057;
  }
}

.option-buttons {
  display: flex;
  gap: 10px;
}

.target-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;

  i {
    font-size: 1.25rem;
  }
}

// Process Group Selection
.process-group-selection {
  display: flex;
  flex-direction: column;
  gap: 20px;
  margin-bottom: 30px;
}

.pg-card {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
}

.pg-header {
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;

  h5 {
    margin: 0 0 5px 0;
    font-size: 1rem;
    font-weight: 600;
  }
}

.pg-body {
  padding: 20px;
}

.default-suggestion {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 15px;
  background: #fff3cd;
  border: 1px solid #ffc107;
  border-radius: 6px;
  margin-bottom: 20px;
  font-size: 0.875rem;

  i {
    font-size: 1.25rem;
    color: #ff9800;
  }
}

.form-group {
  margin-bottom: 15px;

  label {
    display: block;
    font-weight: 600;
    margin-bottom: 8px;
    color: #495057;
  }
}

.form-select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid #ced4da;
  border-radius: 4px;
  font-size: 0.875rem;

  &:focus {
    border-color: #2196f3;
    outline: none;
    box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
  }
}

.selected-info {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 15px;
  background: #e8f5e9;
  border-radius: 6px;
  font-size: 0.875rem;

  i {
    font-size: 1.25rem;
  }
}

// Review Section
.review-section {
  margin-bottom: 30px;
}

.review-summary {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 30px;
}

.summary-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 2px solid #e9ecef;

  i {
    font-size: 2rem;
    color: #2196f3;
  }
}

.summary-label {
  font-size: 0.875rem;
  color: #6c757d;
  margin-bottom: 4px;
}

.summary-value {
  font-size: 1.5rem;
  font-weight: 600;
  color: #2c3e50;
}

.review-details {
  h5 {
    font-size: 1rem;
    font-weight: 600;
    margin-bottom: 15px;
    color: #2c3e50;
  }
}

.review-card {
  border: 1px solid #e9ecef;
  border-radius: 6px;
  margin-bottom: 15px;
  overflow: hidden;
}

.review-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 15px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;

  &.badge-primary {
    background: #e3f2fd;
    color: #1976d2;
  }

  &.badge-success {
    background: #e8f5e9;
    color: #388e3c;
  }
}

.review-card-body {
  padding: 15px;
}

.review-row {
  display: flex;
  margin-bottom: 8px;
  font-size: 0.875rem;

  &:last-child {
    margin-bottom: 0;
  }
}

.review-label {
  font-weight: 600;
  color: #6c757d;
  min-width: 180px;
}

.final-pg-name {
  font-weight: 600;
  color: #007bff;
  font-family: monospace;
}

// Wizard Actions
.wizard-actions {
  display: flex;
  justify-content: space-between;
  padding-top: 20px;
  border-top: 1px solid #e9ecef;
}

// Empty State
.empty-state {
  text-align: center;
  padding: 60px 20px;

  i {
    font-size: 4rem;
  }
}
</style>
