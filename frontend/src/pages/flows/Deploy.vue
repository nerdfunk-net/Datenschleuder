<template>
  <div class="flows-deploy">
    <div class="page-card">
      <!-- Header -->
      <div class="card-header">
        <h2 class="card-title">Deploy Flows</h2>
        <b-button variant="primary" @click="handleDeployAll" :disabled="isDeploying || selectedFlows.length === 0">
          <i class="pe-7s-cloud-upload"></i>
          Deploy Selected ({{ selectedFlows.length }})
        </b-button>
      </div>

      <!-- Deployment Status -->
      <div v-if="deploymentStatus" class="alert-section">
        <b-alert :variant="deploymentStatus.type" show dismissible @dismissed="deploymentStatus = null">
          <i :class="deploymentStatus.icon"></i>
          {{ deploymentStatus.message }}
        </b-alert>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-5">
        <b-spinner variant="primary"></b-spinner>
        <p class="mt-3 text-muted">Loading flows...</p>
      </div>

      <!-- Flows List -->
      <div v-else class="flows-list">
        <div v-if="activeFlows.length === 0" class="empty-state">
          <i class="pe-7s-info display-1 text-muted"></i>
          <h4 class="mt-3 text-muted">No Active Flows</h4>
          <p class="text-muted">There are no active flows available for deployment.</p>
          <router-link to="/flows/manage" class="btn btn-primary mt-3">
            <i class="pe-7s-plus"></i>
            Manage Flows
          </router-link>
        </div>

        <div v-else class="flow-cards">
          <div v-for="flow in activeFlows" :key="flow.id" class="flow-card" :class="{ selected: isSelected(flow.id), deploying: isFlowDeploying(flow.id) }">
            <div class="flow-card-header">
              <b-form-checkbox
                :model-value="isSelected(flow.id)"
                @update:model-value="toggleFlow(flow.id)"
                :disabled="isDeploying"
              >
                <span class="flow-name">{{ flow.cn }}</span>
              </b-form-checkbox>
              <span class="flow-type-badge" :class="getTypeBadgeClass(flow.type)">
                {{ flow.type }}
              </span>
            </div>

            <div class="flow-card-body">
              <div class="flow-info-row">
                <div class="flow-info-item">
                  <span class="label">OU:</span>
                  <span class="value">{{ flow.ou }}</span>
                </div>
                <div class="flow-info-item">
                  <span class="label">DC:</span>
                  <span class="value">{{ flow.dc }}</span>
                </div>
              </div>

              <div class="flow-path">
                <div class="path-item">
                  <i class="pe-7s-angle-right-circle text-primary"></i>
                  <span class="path-label">Source:</span>
                  <span class="path-value">{{ flow.src }}</span>
                </div>
                <div class="path-arrow">
                  <i class="pe-7s-angle-right"></i>
                </div>
                <div class="path-item">
                  <i class="pe-7s-angle-left-circle text-success"></i>
                  <span class="path-label">Destination:</span>
                  <span class="path-value">{{ flow.dest }}</span>
                </div>
              </div>
            </div>

            <div v-if="isFlowDeploying(flow.id)" class="flow-card-footer deploying">
              <b-spinner small class="me-2"></b-spinner>
              Deploying...
            </div>

            <div v-else-if="deploymentResults[flow.id]" class="flow-card-footer" :class="deploymentResults[flow.id].success ? 'success' : 'error'">
              <i :class="deploymentResults[flow.id].success ? 'pe-7s-check text-success' : 'pe-7s-close text-danger'"></i>
              {{ deploymentResults[flow.id].message }}
            </div>
          </div>
        </div>
      </div>

      <!-- Deployment History -->
      <div v-if="!isLoading && deploymentHistory.length > 0" class="deployment-history">
        <h4 class="history-title">Recent Deployments</h4>
        <div class="history-list">
          <div v-for="(entry, index) in deploymentHistory" :key="index" class="history-item">
            <div class="history-icon" :class="entry.success ? 'success' : 'error'">
              <i :class="entry.success ? 'pe-7s-check' : 'pe-7s-close'"></i>
            </div>
            <div class="history-content">
              <div class="history-header">
                <span class="history-flow-name">{{ entry.flowName }}</span>
                <span class="history-time">{{ formatTime(entry.timestamp) }}</span>
              </div>
              <div class="history-message">{{ entry.message }}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'

interface Flow {
  id: number
  cn: string
  ou: string
  dc: string
  type: string
  src: string
  dest: string
  active: boolean
}

interface DeploymentResult {
  success: boolean
  message: string
}

interface DeploymentHistory {
  flowName: string
  timestamp: Date
  success: boolean
  message: string
}

const isLoading = ref(false)
const isDeploying = ref(false)
const flows = ref<Flow[]>([])
const selectedFlows = ref<number[]>([])
const deployingFlows = ref<number[]>([])
const deploymentResults = ref<Record<number, DeploymentResult>>({})
const deploymentHistory = ref<DeploymentHistory[]>([])
const deploymentStatus = ref<{ type: string; icon: string; message: string } | null>(null)

const activeFlows = computed(() => {
  return flows.value.filter((flow) => flow.active)
})

const isSelected = (flowId: number) => {
  return selectedFlows.value.includes(flowId)
}

const isFlowDeploying = (flowId: number) => {
  return deployingFlows.value.includes(flowId)
}

const toggleFlow = (flowId: number) => {
  const index = selectedFlows.value.indexOf(flowId)
  if (index === -1) {
    selectedFlows.value.push(flowId)
  } else {
    selectedFlows.value.splice(index, 1)
  }
}

const getTypeBadgeClass = (type: string) => {
  const classes: Record<string, string> = {
    http: 'bg-primary',
    kafka: 'bg-success',
    file: 'bg-warning',
    database: 'bg-info'
  }
  return classes[type] || 'bg-secondary'
}

const loadFlows = async () => {
  isLoading.value = true
  try {
    // TODO: Replace with actual API call
    const response = await fetch('/api/proxy/flows')
    if (response.ok) {
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        flows.value = await response.json()
      } else {
        // Not JSON, use mock data
        useMockData()
      }
    } else {
      // Backend not available, use mock data
      useMockData()
    }
  } catch (error) {
    console.log('Backend not available, using mock data for development')
    // Use mock data on error
    useMockData()
  } finally {
    isLoading.value = false
  }
}

const useMockData = () => {
  flows.value = [
    { id: 1, cn: 'flow1', ou: 'engineering', dc: 'us-east', type: 'http', src: 'api.source.com', dest: 'api.dest.com', active: true },
    { id: 2, cn: 'flow2', ou: 'marketing', dc: 'us-west', type: 'kafka', src: 'topic-a', dest: 'topic-b', active: false },
    { id: 3, cn: 'flow3', ou: 'sales', dc: 'eu-central', type: 'file', src: '/data/input', dest: '/data/output', active: true },
    { id: 4, cn: 'flow4', ou: 'engineering', dc: 'us-east', type: 'database', src: 'postgres://source', dest: 'postgres://dest', active: true },
    { id: 5, cn: 'flow5', ou: 'operations', dc: 'ap-south', type: 'http', src: 'webhook.example.com', dest: 'processor.example.com', active: true }
  ]
}

const deployFlow = async (flowId: number): Promise<DeploymentResult> => {
  // Simulate deployment
  await new Promise((resolve) => setTimeout(resolve, 2000))

  // TODO: Replace with actual API call
  const success = Math.random() > 0.2 // 80% success rate for demo
  return {
    success,
    message: success ? 'Deployed successfully' : 'Deployment failed'
  }
}

const handleDeployAll = async () => {
  if (selectedFlows.value.length === 0) return

  isDeploying.value = true
  deploymentResults.value = {}
  deploymentStatus.value = {
    type: 'info',
    icon: 'pe-7s-cloud-upload',
    message: `Deploying ${selectedFlows.value.length} flow(s)...`
  }

  const deployPromises = selectedFlows.value.map(async (flowId) => {
    deployingFlows.value.push(flowId)
    const result = await deployFlow(flowId)
    deploymentResults.value[flowId] = result

    // Add to history
    const flow = flows.value.find((f) => f.id === flowId)
    if (flow) {
      deploymentHistory.value.unshift({
        flowName: flow.cn,
        timestamp: new Date(),
        success: result.success,
        message: result.message
      })
    }

    deployingFlows.value = deployingFlows.value.filter((id) => id !== flowId)
  })

  await Promise.all(deployPromises)

  const successCount = Object.values(deploymentResults.value).filter((r) => r.success).length
  const failCount = selectedFlows.value.length - successCount

  if (failCount === 0) {
    deploymentStatus.value = {
      type: 'success',
      icon: 'pe-7s-check',
      message: `Successfully deployed all ${successCount} flow(s)`
    }
  } else {
    deploymentStatus.value = {
      type: 'warning',
      icon: 'pe-7s-attention',
      message: `Deployed ${successCount} flow(s) successfully, ${failCount} failed`
    }
  }

  isDeploying.value = false
  selectedFlows.value = []

  // Keep history limited to 10 items
  if (deploymentHistory.value.length > 10) {
    deploymentHistory.value = deploymentHistory.value.slice(0, 10)
  }
}

const formatTime = (date: Date) => {
  const now = new Date()
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000)

  if (diffInSeconds < 60) return 'Just now'
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)} minutes ago`
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)} hours ago`
  return date.toLocaleDateString()
}

onMounted(() => {
  loadFlows()
})
</script>

<style scoped lang="scss">
.flows-deploy {
  max-width: 1200px;
}

.page-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-bottom: 1px solid #e9ecef;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #2c3e50;
  margin: 0;
}

.alert-section {
  padding: 20px 30px;
  padding-bottom: 0;

  i {
    margin-right: 8px;
  }
}

.flows-list {
  padding: 30px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
}

.flow-cards {
  display: grid;
  gap: 20px;
}

.flow-card {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  overflow: hidden;
  transition: all 0.3s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  &.selected {
    border-color: #4a90e2;
    background: #f0f7ff;
  }

  &.deploying {
    opacity: 0.7;
  }
}

.flow-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 15px 20px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;

  .flow-name {
    font-weight: 600;
    font-size: 1rem;
    color: #2c3e50;
  }
}

.flow-type-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: white;
}

.flow-card-body {
  padding: 20px;
}

.flow-info-row {
  display: flex;
  gap: 30px;
  margin-bottom: 15px;
}

.flow-info-item {
  display: flex;
  gap: 8px;

  .label {
    font-weight: 600;
    color: #6c757d;
  }

  .value {
    color: #495057;
  }
}

.flow-path {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.path-item {
  display: flex;
  align-items: center;
  gap: 8px;
  flex: 1;

  i {
    font-size: 1.5rem;
  }

  .path-label {
    font-weight: 600;
    color: #6c757d;
    font-size: 0.875rem;
  }

  .path-value {
    color: #495057;
    font-size: 0.875rem;
    word-break: break-all;
  }
}

.path-arrow {
  color: #6c757d;
  font-size: 1.5rem;
}

.flow-card-footer {
  padding: 12px 20px;
  border-top: 1px solid #e9ecef;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  font-weight: 500;

  &.deploying {
    background: #e7f3ff;
    color: #0066cc;
  }

  &.success {
    background: #d4edda;
    color: #155724;
  }

  &.error {
    background: #f8d7da;
    color: #721c24;
  }
}

.deployment-history {
  padding: 30px;
  border-top: 2px solid #e9ecef;
  background: #f8f9fa;
}

.history-title {
  font-size: 1rem;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 20px;
}

.history-list {
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.history-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  background: white;
  border-radius: 6px;
  border: 1px solid #e9ecef;
}

.history-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  &.success {
    background: #d4edda;
    color: #155724;
  }

  &.error {
    background: #f8d7da;
    color: #721c24;
  }

  i {
    font-size: 1.25rem;
  }
}

.history-content {
  flex: 1;
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 5px;
}

.history-flow-name {
  font-weight: 600;
  color: #2c3e50;
}

.history-time {
  font-size: 0.75rem;
  color: #6c757d;
}

.history-message {
  font-size: 0.875rem;
  color: #6c757d;
}
</style>
