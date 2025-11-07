<template>
  <b-modal
    v-model="isVisible"
    title="Process Group Already Exists"
    size="lg"
    hide-footer
  >
    <div v-if="conflictInfo" class="conflict-modal">
      <div class="alert alert-warning">
        <i class="pe-7s-attention"></i>
        <strong>A process group with this name already exists</strong>
      </div>

      <div class="conflict-details">
        <h6>Existing Process Group:</h6>
        <ul>
          <li>
            <strong>Name:</strong>
            {{ conflictInfo.existing_process_group.name }}
          </li>
          <li>
            <strong>ID:</strong>
            <code>{{ conflictInfo.existing_process_group.id }}</code>
          </li>
          <li>
            <strong>Status:</strong>
            {{ conflictInfo.existing_process_group.running_count }} running,
            {{ conflictInfo.existing_process_group.stopped_count }} stopped
          </li>
          <li>
            <strong>Version Control:</strong>
            {{
              conflictInfo.existing_process_group.has_version_control
                ? 'Yes'
                : 'No'
            }}
          </li>
        </ul>
      </div>

      <div class="conflict-message mb-4">
        <p>{{ conflictInfo.message }}</p>
        <p class="text-muted">What would you like to do?</p>
      </div>

      <div class="conflict-actions">
        <b-button
          variant="primary"
          @click="handleResolution('deploy_anyway')"
          :disabled="isResolving"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'deploy_anyway'"
            small
            class="me-2"
          ></b-spinner>
          <i v-else class="pe-7s-plus"></i>
          Deploy Anyway (Create Additional Process Group)
        </b-button>

        <b-button
          variant="danger"
          @click="handleResolution('delete_and_deploy')"
          :disabled="isResolving"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'delete_and_deploy'"
            small
            class="me-2"
          ></b-spinner>
          <i v-else class="pe-7s-trash"></i>
          Delete Existing and Deploy New
        </b-button>

        <b-button
          v-if="conflictInfo.existing_process_group.has_version_control"
          variant="info"
          @click="handleResolution('update_version')"
          :disabled="isResolving"
          class="mb-2 w-100"
        >
          <b-spinner
            v-if="isResolving && selectedResolution === 'update_version'"
            small
            class="me-2"
          ></b-spinner>
          <i v-else class="pe-7s-refresh-2"></i>
          Update to New Version
        </b-button>

        <b-button
          variant="outline-secondary"
          @click="handleCancel"
          :disabled="isResolving"
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

interface Props {
  show: boolean
  conflictInfo: ConflictInfo | null
  isResolving?: boolean
}

interface Emits {
  (e: 'update:show', value: boolean): void
  (e: 'resolve', action: 'deploy_anyway' | 'delete_and_deploy' | 'update_version'): void
  (e: 'cancel'): void
}

const props = withDefaults(defineProps<Props>(), {
  isResolving: false
})

const emit = defineEmits<Emits>()

const selectedResolution = ref<string>('')

const isVisible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

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
  .conflict-details {
    margin-bottom: 20px;

    h6 {
      font-weight: 600;
      margin-bottom: 10px;
    }

    ul {
      list-style: none;
      padding-left: 0;

      li {
        margin-bottom: 8px;
        padding: 8px;
        background: #f8f9fa;
        border-radius: 4px;

        code {
          background: #e9ecef;
          padding: 2px 6px;
          border-radius: 3px;
          font-size: 0.875rem;
        }
      }
    }
  }

  .conflict-message {
    padding: 15px;
    background: #fff3cd;
    border-left: 4px solid #ffc107;
    border-radius: 4px;

    p:last-child {
      margin-bottom: 0;
    }
  }

  .conflict-actions {
    display: flex;
    flex-direction: column;
    gap: 0;
  }
}
</style>
