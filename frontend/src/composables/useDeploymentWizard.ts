import { ref, computed } from 'vue'

export interface Flow {
  id: number
  [key: string]: any
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
}

export interface DeploymentSettings {
  global: {
    process_group_name_template: string
    disable_after_deploy: boolean
    stop_versioning_after_deploy: boolean
    start_after_deploy: boolean
  }
  paths: Record<string, any>
}

export interface DeploymentResults {
  successCount: number
  failCount: number
  total: number
  successful: any[]
  failed: any[]
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
  const nifiInstances = ref<any[]>([])
  const registryFlows = ref<any[]>([])

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
  const conflictInfo = ref<any>(null)
  const currentConflictDeployment = ref<any>(null)
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
