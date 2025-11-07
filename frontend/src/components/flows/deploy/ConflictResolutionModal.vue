<template>
  <b-modal
    v-model="isVisible"
    title="Process Group Already Exists"
    size="md"
    hide-footer
  >
    <div v-if="conflictInfo" class="conflict-modal">
      <!-- Deployment Info -->
      <div v-if="deploymentConfig" class="deployment-info mb-3">
        <div class="d-flex align-items-center gap-2">
          <i class="pe-7s-upload" style="font-size: 1.5rem;"></i>
          <div>
            <div class="fw-bold text-white">{{ deploymentConfig.flowName }}</div>
            <div class="small text-white-75">
              <span
                class="badge"
                :class="deploymentConfig.target === 'source' ? 'badge-light' : 'badge-success'"
              >
                {{ deploymentConfig.target.toUpperCase() }}
              </span>
              <span class="ms-2">{{ deploymentConfig.hierarchyValue }}</span>
            </div>
          </div>
        </div>
      </div>

      <!-- Existing Process Group - Compact -->
      <div class="existing-pg-card mb-3">
        <div class="card-header-sm bg-warning bg-opacity-10 border-warning">
          <i class="pe-7s-attention text-warning me-2"></i>
          <strong>Existing Process Group</strong>
        </div>
        <div class="card-body-sm">
          <div class="info-row">
            <span class="label">Name:</span>
            <span class="value fw-bold">{{ conflictInfo.existing_process_group.name }}</span>
          </div>
          <div class="info-row" v-if="deploymentConfig">
            <span class="label">Path:</span>
            <span class="value font-monospace small">{{ getSelectedPath() }}</span>
          </div>
          <div class="info-row">
            <span class="label">Status:</span>
            <span class="value">
              <i class="pe-7s-check text-success me-1"></i>{{ conflictInfo.existing_process_group.running_count }} running
              <i class="pe-7s-close text-muted ms-2 me-1"></i>{{ conflictInfo.existing_process_group.stopped_count }} stopped
            </span>
          </div>
          <div class="info-row" v-if="conflictInfo.existing_process_group.has_version_control">
            <span class="label">Version Control:</span>
            <span class="value">
              <i class="pe-7s-check text-info me-1"></i>Yes
            </span>
          </div>
        </div>
      </div>

      <!-- Actions Message -->
      <div class="text-center text-muted mb-3 small">
        What would you like to do?
      </div>

      <div class="conflict-actions">
        <b-button
          variant="primary"
          @click="handleResolution('deploy_anyway')"
          :disabled="isResolving"
          size="sm"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'deploy_anyway'"
            small
            class="me-1"
          ></b-spinner>
          <i v-else class="pe-7s-plus me-1"></i>
          Deploy Anyway
        </b-button>

        <b-button
          variant="danger"
          @click="handleResolution('delete_and_deploy')"
          :disabled="isResolving"
          size="sm"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'delete_and_deploy'"
            small
            class="me-1"
          ></b-spinner>
          <i v-else class="pe-7s-trash me-1"></i>
          Delete & Redeploy
        </b-button>

        <b-button
          v-if="conflictInfo.existing_process_group.has_version_control"
          variant="info"
          @click="handleResolution('update_version')"
          :disabled="isResolving"
          size="sm"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'update_version'"
            small
            class="me-1"
          ></b-spinner>
          <i v-else class="pe-7s-refresh-2 me-1"></i>
          Update Version
        </b-button>

        <b-button
          variant="outline-secondary"
          @click="handleCancel"
          :disabled="isResolving"
          size="sm"
          class="w-100"
        >
          Cancel
        </b-button>
      </div>
    </div>
  </b-modal>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

interface ConflictInfo {
  message: string
  existing_process_group: {
    id: string
    name: string
    running_count: number
    stopped_count: number
    has_version_control: boolean
  }
}

interface DeploymentConfig {
  flowName: string
  target: 'source' | 'destination'
  hierarchyValue: string
  availablePaths?: Array<{ id: string; pathDisplay: string }>
  selectedProcessGroupId?: string
}

interface Props {
  show: boolean
  conflictInfo: ConflictInfo | null
  deploymentConfig?: DeploymentConfig | null
  isResolving?: boolean
}

interface Emits {
  (e: 'update:show', value: boolean): void
  (e: 'resolve', action: 'deploy_anyway' | 'delete_and_deploy' | 'update_version'): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  isResolving: false,
  deploymentConfig: null
})

const emit = defineEmits<Emits>()

const selectedResolution = ref<string>('')

const isVisible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

const getSelectedPath = () => {
  if (!props.deploymentConfig?.availablePaths || !props.deploymentConfig?.selectedProcessGroupId) {
    return 'N/A'
  }

  const selected = props.deploymentConfig.availablePaths.find(
    p => p.id === props.deploymentConfig?.selectedProcessGroupId
  )
  return selected?.pathDisplay || 'N/A'
}

const handleResolution = (action: 'deploy_anyway' | 'delete_and_deploy' | 'update_version') => {
  selectedResolution.value = action
  emit('resolve', action)
}

const handleCancel = () => {
  emit('cancel')
  emit('update:show', false)
}
</script>

<style scoped lang="scss">
.conflict-modal {
  .deployment-info {
    padding: 12px 15px;
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border-radius: 6px;
    box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);

    i {
      color: white;
    }

    .text-white-75 {
      color: rgba(255, 255, 255, 0.85);
    }

    .badge {
      font-size: 0.7rem;
      padding: 3px 10px;
      font-weight: 600;

      &.badge-light {
        background: rgba(255, 255, 255, 0.9);
        color: #667eea;
      }

      &.badge-success {
        background: #28a745;
        color: white;
      }
    }
  }

  .existing-pg-card {
    border: 1px solid #ffc107;
    border-radius: 6px;
    overflow: hidden;

    .card-header-sm {
      padding: 8px 12px;
      border-bottom: 1px solid #ffc107;
      font-size: 0.9rem;
    }

    .card-body-sm {
      padding: 10px 12px;
      background: white;

      .info-row {
        display: flex;
        padding: 4px 0;
        font-size: 0.875rem;
        border-bottom: 1px solid #f0f0f0;

        &:last-child {
          border-bottom: none;
        }

        .label {
          font-weight: 600;
          color: #6c757d;
          min-width: 110px;
          flex-shrink: 0;
        }

        .value {
          flex: 1;
          color: #495057;

          i {
            font-size: 0.9rem;
          }
        }
      }
    }
  }

  .conflict-actions {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
}
</style>
