import { ref, computed } from 'vue'

export interface Flow {
  id: number
  [key: string]: unknown
  source: string
  destination: string
}

export interface HierarchyAttribute {
  name: string
  label: string
  order: number
}

export interface ProcessGroupPath {
  id: string
  name: string
  parent_group_id: string | null
  depth: number
  path: Array<{ id: string; name: string; parent_group_id: string | null }>
}

export interface NiFiInstance {
  id: number
  hierarchy_attribute?: string
  hierarchy_value?: string
  nifi_url?: string
  [key: string]: unknown
}

export interface RegistryFlow {
  id: number
  flow_name: string
  nifi_instance_name?: string
  [key: string]: unknown
}

export interface ConflictInfo {
  message: string
  existing_process_group: {
    id: string
    name: string
    running_count: number
    stopped_count: number
    has_version_control: boolean
    [key: string]: unknown
  }
  [key: string]: unknown
}

export interface ConflictDeployment {
  flow: Flow
  target: 'source' | 'destination'
  instanceId: number
  hierarchyValue: string
  processGroupName: string
  deploymentRequest: Record<string, unknown>
  config: DeploymentConfig
}

export interface DeploymentConfig {
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
  parameterContextName: string | null
}

export interface DeploymentSettings {
  global: {
    process_group_name_template: string
    disable_after_deploy: boolean
    stop_versioning_after_deploy: boolean
    start_after_deploy: boolean
  }
  paths: Record<string, unknown>
}

export interface DeploymentResult {
  success: boolean
  message: string
  config: DeploymentConfig
  processGroupName?: string
  processGroupId?: string
  flowName?: string
  target?: string
  instance?: string
  error?: string
  [key: string]: unknown
}

export interface DeploymentResults {
  successCount: number
  failCount: number
  total: number
  successful: DeploymentResult[]
  failed: DeploymentResult[]
}

export function useDeploymentWizard() {
  // Wizard state
  const steps = [
    'Select Flows',
    'Choose Targets',
    'Choose Process Groups',
    'Settings',
    'Review & Deploy'
  ]
  const currentStep = ref(0)
  const isLoading = ref(false)
  const isLoadingPaths = ref(false)
  const isDeploying = ref(false)

  // Flow data
  const flows = ref<Flow[]>([])
  const selectedFlows = ref<number[]>([])
  const hierarchyConfig = ref<HierarchyAttribute[]>([])
  const visibleColumns = ref<Array<{ key: string; label: string }>>([])
  const nifiInstances = ref<NiFiInstance[]>([])
  const registryFlows = ref<RegistryFlow[]>([])

  // Deployment configuration
  const deploymentTargets = ref<Record<number, 'source' | 'destination' | 'both'>>({})
  const deploymentConfigs = ref<DeploymentConfig[]>([])
  const processGroupPaths = ref<Record<string, ProcessGroupPath[]>>({})
  const deploymentSettings = ref<DeploymentSettings>({
    global: {
      process_group_name_template: '{last_hierarchy_value}',
      disable_after_deploy: false,
      stop_versioning_after_deploy: false,
      start_after_deploy: false
    },
    paths: {}
  })

  // Conflict resolution
  const showConflictModal = ref(false)
  const conflictInfo = ref<ConflictInfo | null>(null)
  const currentConflictDeployment = ref<ConflictDeployment | null>(null)
  const isResolvingConflict = ref(false)
  const conflictResolution = ref<string>('')

  // Deployment results
  const showResultsModal = ref(false)
  const deploymentResults = ref<DeploymentResults>({
    successCount: 0,
    failCount: 0,
    total: 0,
    successful: [],
    failed: []
  })

  // Computed properties
  const allSelected = computed(() => {
    return flows.value.length > 0 && selectedFlows.value.length === flows.value.length
  })

  const selectedFlowObjects = computed(() => {
    return flows.value.filter((f) => selectedFlows.value.includes(f.id))
  })

  const topHierarchyName = computed(() => {
    return hierarchyConfig.value.length > 0 ? hierarchyConfig.value[0].name : 'DC'
  })

  const secondHierarchyName = computed(() => {
    return hierarchyConfig.value.length > 1 ? hierarchyConfig.value[1].name : 'OU'
  })

  const allTargetsSelected = computed(() => {
    return selectedFlows.value.every((flowId) => deploymentTargets.value[flowId])
  })

  const allProcessGroupsSelected = computed(() => {
    return deploymentConfigs.value.every((config) => config.selectedProcessGroupId)
  })

  const uniqueInstancesCount = computed(() => {
    const instances = new Set(deploymentConfigs.value.map((c) => c.hierarchyValue))
    return instances.size
  })

  // Navigation methods
  const goToNextStep = () => {
    currentStep.value++
  }

  const goToPreviousStep = () => {
    currentStep.value--
  }

  // Flow selection methods
  const toggleSelectAll = () => {
    if (allSelected.value) {
      selectedFlows.value = []
    } else {
      selectedFlows.value = flows.value.map((f) => f.id)
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

  // Deployment target methods
  const getDeploymentTarget = (flowId: number) => {
    return deploymentTargets.value[flowId]
  }

  const setDeploymentTarget = (flowId: number, target: 'source' | 'destination' | 'both') => {
    deploymentTargets.value[flowId] = target
  }

  return {
    // State
    steps,
    currentStep,
    isLoading,
    isLoadingPaths,
    isDeploying,
    flows,
    selectedFlows,
    hierarchyConfig,
    visibleColumns,
    nifiInstances,
    registryFlows,
    deploymentTargets,
    deploymentConfigs,
    processGroupPaths,
    deploymentSettings,
    showConflictModal,
    conflictInfo,
    currentConflictDeployment,
    isResolvingConflict,
    conflictResolution,
    showResultsModal,
    deploymentResults,

    // Computed
    allSelected,
    selectedFlowObjects,
    topHierarchyName,
    secondHierarchyName,
    allTargetsSelected,
    allProcessGroupsSelected,
    uniqueInstancesCount,

    // Methods
    goToNextStep,
    goToPreviousStep,
    toggleSelectAll,
    toggleFlow,
    getDeploymentTarget,
    setDeploymentTarget
  }
}
