<template>
  <div class="settings-page">
    <div class="page-header mb-4">
      <h2>Parameter Contexts</h2>
      <b-button variant="primary" @click="showCreateModal" class="new-context-btn">
        <i class="pe-7s-plus"></i> New Parameter Context
      </b-button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <b-spinner></b-spinner>
      <p class="text-muted mt-2">Loading parameter contexts...</p>
    </div>

    <!-- Parameter Contexts by Instance -->
    <div v-else>
      <div v-for="instance in instances" :key="instance.id" class="mb-5">
        <h4 class="mb-3">
          <span class="badge bg-primary">{{ instance.hierarchy_attribute }}={{ instance.hierarchy_value }}</span>
          <span class="text-muted ms-2">{{ instance.nifi_url }}</span>
        </h4>

        <!-- Loading state for instance -->
        <div v-if="instanceLoading[instance.id]" class="text-center py-3">
          <b-spinner small></b-spinner>
          <span class="text-muted ms-2">Loading...</span>
        </div>

        <!-- Parameter Contexts Table -->
        <b-table
          v-else-if="parameterContextsByInstance[instance.id]?.length > 0"
          :items="parameterContextsByInstance[instance.id]"
          :fields="tableFields"
          striped
          hover
          responsive
        >
          <template #cell(name)="data">
            <strong>{{ data.value }}</strong>
          </template>

          <template #cell(description)="data">
            <span class="text-muted">{{ data.value || 'No description' }}</span>
          </template>

          <template #cell(parameter_count)="data">
            <span class="param-count">{{ data.item.parameters?.length || 0 }} parameters</span>
          </template>

          <template #cell(actions)="data">
            <div class="action-buttons">
              <b-button
                variant="outline-primary"
                size="sm"
                @click="editParameterContext(instance.id, data.item)"
                title="Edit"
              >
                <i class="pe-7s-pen"></i>
              </b-button>
              <b-button
                variant="outline-info"
                size="sm"
                @click="viewParameterContext(instance.id, data.item)"
                title="View"
              >
                <i class="pe-7s-look"></i>
              </b-button>
              <b-button
                variant="outline-danger"
                size="sm"
                @click="deleteParameterContext(instance.id, data.item)"
                title="Remove"
              >
                <i class="pe-7s-trash"></i>
              </b-button>
            </div>
          </template>
        </b-table>

        <!-- Empty state for instance -->
        <div v-else class="alert alert-info">
          <i class="pe-7s-info"></i> No parameter contexts found for this instance.
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="instances.length === 0" class="alert alert-warning">
        <i class="pe-7s-attention"></i> No NiFi instances configured. Please configure a NiFi instance first.
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <b-modal
      v-model="showModal"
      :title="modalMode === 'create' ? 'Create Parameter Context' : modalMode === 'edit' ? 'Edit Parameter Context' : 'View Parameter Context'"
      size="xl"
      @hidden="resetForm"
      ok-title="Save"
      cancel-title="Cancel"
      @ok="handleSave"
      :ok-disabled="saving"
      modal-class="parameter-modal"
    >

      <form @submit.prevent="handleSave">
        <!-- NiFi Instance Selection (only for create) -->
        <div v-if="modalMode === 'create'" class="mb-3">
          <label class="form-label">NiFi Instance</label>
          <b-form-select
            v-model="form.instance_id"
            :options="instanceOptions"
            required
            :disabled="modalMode !== 'create'"
          ></b-form-select>
        </div>

        <!-- Name -->
        <div class="mb-3">
          <label class="form-label">Name <span class="text-danger">*</span></label>
          <b-form-input
            v-model="form.name"
            required
            :disabled="modalMode === 'view'"
            placeholder="Enter parameter context name"
          ></b-form-input>
        </div>

        <!-- Description -->
        <div class="mb-3">
          <label class="form-label">Description</label>
          <b-form-textarea
            v-model="form.description"
            :disabled="modalMode === 'view'"
            rows="2"
            placeholder="Enter description (optional)"
          ></b-form-textarea>
        </div>

        <!-- Parameters Table -->
        <div class="mb-3">
          <label class="form-label">Parameters</label>
          <b-table
            :items="form.parameters"
            :fields="parameterFields"
            small
            bordered
          >
            <template #cell(name)="data">
              <b-form-input
                v-model="data.item.name"
                size="sm"
                :disabled="modalMode === 'view' || data.item.isExisting"
                placeholder="Parameter name"
              ></b-form-input>
            </template>

            <template #cell(value)="data">
              <b-form-input
                v-if="!data.item.sensitive"
                v-model="data.item.value"
                size="sm"
                :disabled="modalMode === 'view'"
                placeholder="Parameter value"
              ></b-form-input>
              <b-form-input
                v-else
                v-model="data.item.value"
                type="password"
                size="sm"
                :disabled="modalMode === 'view'"
                placeholder="Sensitive value"
              ></b-form-input>
            </template>

            <template #cell(description)="data">
              <b-form-input
                v-model="data.item.description"
                size="sm"
                :disabled="modalMode === 'view'"
                placeholder="Description (optional)"
              ></b-form-input>
            </template>

            <template #cell(sensitive)="data">
              <b-form-checkbox
                v-model="data.item.sensitive"
                :disabled="modalMode === 'view'"
                switch
              ></b-form-checkbox>
            </template>

            <template #cell(actions)="data">
              <b-button
                v-if="modalMode !== 'view'"
                variant="link"
                size="sm"
                class="text-danger"
                @click="removeParameter(data.index)"
              >
                <i class="pe-7s-trash"></i>
              </b-button>
            </template>
          </b-table>

          <b-button
            v-if="modalMode !== 'view'"
            variant="outline-primary"
            size="sm"
            @click="addParameter"
          >
            <i class="pe-7s-plus"></i> Add Parameter
          </b-button>
        </div>
      </form>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import api from '@/utils/api'

// Simple notification helper
const showError = (message: string) => alert('Error: ' + message)
const showSuccess = (message: string) => alert('Success: ' + message)

// State
const loading = ref(false)
const instances = ref<any[]>([])
const parameterContextsByInstance = ref<Record<number, any[]>>({})
const instanceLoading = ref<Record<number, boolean>>({})
const showModal = ref(false)
const modalMode = ref<'create' | 'edit' | 'view'>('create')
const saving = ref(false)

// Form
const form = ref({
  instance_id: null as number | null,
  context_id: null as string | null,
  name: '',
  description: '',
  parameters: [] as any[],
})

// Table fields
const tableFields = [
  { key: 'name', label: 'Name', sortable: true },
  { key: 'description', label: 'Description', sortable: true },
  { key: 'parameter_count', label: 'Parameters', sortable: true },
  { key: 'actions', label: 'Actions', class: 'text-end' },
]

const parameterFields = [
  { key: 'name', label: 'Name' },
  { key: 'value', label: 'Value' },
  { key: 'description', label: 'Description' },
  { key: 'sensitive', label: 'Sensitive' },
  { key: 'actions', label: '', class: 'text-end' },
]

// Computed
const instanceOptions = computed(() => {
  return instances.value.map(instance => ({
    value: instance.id,
    text: `${instance.hierarchy_attribute}=${instance.hierarchy_value} (${instance.nifi_url})`
  }))
})

// Methods
async function loadInstances() {
  try {
    loading.value = true
    const response = await api.get('/api/nifi-instances/')
    instances.value = response

    // Load parameter contexts for each instance
    for (const instance of instances.value) {
      await loadParameterContexts(instance.id)
    }
  } catch (error: any) {
    showError(error.message || 'Failed to load NiFi instances')
  } finally {
    loading.value = false
  }
}

async function loadParameterContexts(instanceId: number) {
  try {
    instanceLoading.value[instanceId] = true
    const response = await api.get(`/api/nifi-instances/${instanceId}/get-parameters`)

    console.log(`Loaded parameter contexts for instance ${instanceId}:`, response)

    if (response.status === 'success') {
      // Force reactive update by creating a new object
      parameterContextsByInstance.value = {
        ...parameterContextsByInstance.value,
        [instanceId]: response.parameter_contexts
      }
      console.log(`Updated parameterContextsByInstance[${instanceId}] with ${response.parameter_contexts.length} contexts`)
    } else {
      parameterContextsByInstance.value = {
        ...parameterContextsByInstance.value,
        [instanceId]: []
      }
      if (response.message) {
        console.warn(`Failed to load parameters for instance ${instanceId}:`, response.message)
      }
    }
  } catch (error: any) {
    console.error(`Error loading parameters for instance ${instanceId}:`, error)
    parameterContextsByInstance.value = {
      ...parameterContextsByInstance.value,
      [instanceId]: []
    }
  } finally {
    instanceLoading.value[instanceId] = false
  }
}

function showCreateModal() {
  modalMode.value = 'create'
  resetForm()
  showModal.value = true
}

function viewParameterContext(instanceId: number, context: any) {
  modalMode.value = 'view'
  form.value = {
    instance_id: instanceId,
    context_id: context.id,
    name: context.name,
    description: context.description || '',
    parameters: context.parameters.map((p: any) => ({
      name: p.name,
      value: p.value || '',
      description: p.description || '',
      sensitive: p.sensitive || false,
      isExisting: true,
    })),
  }
  showModal.value = true
}

function editParameterContext(instanceId: number, context: any) {
  modalMode.value = 'edit'
  form.value = {
    instance_id: instanceId,
    context_id: context.id,
    name: context.name,
    description: context.description || '',
    parameters: context.parameters.map((p: any) => ({
      name: p.name,
      value: p.value || '',
      description: p.description || '',
      sensitive: p.sensitive || false,
      isExisting: true, // Mark as existing parameter
    })),
  }
  showModal.value = true
}

async function deleteParameterContext(instanceId: number, context: any) {
  if (!confirm(`Are you sure you want to delete parameter context "${context.name}"?`)) {
    return
  }

  try {
    await api.delete(`/api/nifi-instances/${instanceId}/parameter-contexts/${context.id}`)
    showSuccess('Parameter context deleted successfully')
    await loadParameterContexts(instanceId)
  } catch (error: any) {
    showError(error.message || 'Failed to delete parameter context')
  }
}

function addParameter() {
  form.value.parameters.push({
    name: '',
    value: '',
    description: '',
    sensitive: false,
    isExisting: false, // Mark as new parameter
  })
}

function removeParameter(index: number) {
  form.value.parameters.splice(index, 1)
}

async function handleSave(bvModalEvent?: any) {
  // Prevent modal from closing automatically
  if (bvModalEvent) {
    bvModalEvent.preventDefault()
  }

  console.log('handleSave called', { modalMode: modalMode.value, form: form.value })

  if (!form.value.name) {
    showError('Please enter a name for the parameter context')
    return
  }

  if (modalMode.value === 'create' && !form.value.instance_id) {
    showError('Please select a NiFi instance')
    return
  }

  if (modalMode.value === 'edit' && !form.value.instance_id) {
    showError('Instance ID is missing')
    return
  }

  if (modalMode.value === 'edit' && !form.value.context_id) {
    showError('Context ID is missing')
    return
  }

  try {
    saving.value = true

    const payload = {
      name: form.value.name,
      description: form.value.description || undefined,
      parameters: form.value.parameters
        .filter(p => p.name) // Only include parameters with names
        .map(p => ({
          name: p.name,
          description: p.description || undefined,
          sensitive: p.sensitive || false,
          value: p.value || undefined,
        })),
    }

    console.log('Sending request:', {
      mode: modalMode.value,
      instanceId: form.value.instance_id,
      contextId: form.value.context_id,
      payload,
      originalParameters: form.value.parameters,
    })

    if (modalMode.value === 'create') {
      const result = await api.post(`/api/nifi-instances/${form.value.instance_id}/parameter-contexts`, payload)
      console.log('Create result:', result)
      showSuccess('Parameter context created successfully')
      await loadParameterContexts(form.value.instance_id!)
    } else if (modalMode.value === 'edit') {
      const result = await api.put(`/api/nifi-instances/${form.value.instance_id}/parameter-contexts/${form.value.context_id}`, payload)
      console.log('Update result:', result)
      showSuccess('Parameter context updated successfully')
      await loadParameterContexts(form.value.instance_id!)
    }

    showModal.value = false
  } catch (error: any) {
    console.error('Save error:', error)
    showError(error.message || `Failed to ${modalMode.value} parameter context`)
  } finally {
    saving.value = false
  }
}

function resetForm() {
  form.value = {
    instance_id: instances.value.length > 0 ? instances.value[0].id : null,
    context_id: null,
    name: '',
    description: '',
    parameters: [],
  }
}

onMounted(() => {
  loadInstances()
})
</script>

<style scoped>
.settings-page {
  padding: 0;
}

.page-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  color: white;
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.new-context-btn {
  background: white !important;
  color: #667eea !important;
  border: none !important;
  font-weight: 600 !important;
  padding: 0.5rem 1.25rem !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.new-context-btn:hover {
  background: #f8f9fa !important;
  color: #764ba2 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
}

.new-context-btn i {
  margin-right: 0.5rem;
}

h4 .badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
}

h4 .text-muted {
  color: #6c757d !important;
  font-size: 0.9rem;
  font-weight: normal;
}

/* Table styling */
:deep(.table) {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e9ecef;
}

:deep(.table thead th) {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.875rem 1rem;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.75rem;
  letter-spacing: 0.5px;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.table thead th:last-child) {
  border-right: none;
}

:deep(.table tbody tr) {
  border-bottom: 1px solid #e9ecef;
  transition: background-color 0.2s ease;
}

:deep(.table tbody tr:hover) {
  background-color: #f8f9fa;
}

:deep(.table tbody tr:last-child) {
  border-bottom: none;
}

:deep(.table tbody td) {
  padding: 0.875rem 1rem;
  vertical-align: middle;
  color: #2c3e50;
  border-right: 1px solid #f1f3f5;
}

:deep(.table tbody td:last-child) {
  border-right: none;
}

:deep(.table tbody td strong) {
  color: #1a202c;
  font-weight: 600;
}

:deep(.table tbody td .text-muted) {
  color: #6c757d !important;
}

:deep(.table tbody td .param-count) {
  color: #2c3e50;
  font-weight: 500;
  font-size: 0.95rem;
}

:deep(.table .badge) {
  background: #667eea;
  color: white;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.8rem;
}

/* Action buttons */
.action-buttons {
  display: flex;
  gap: 0.5rem;
  justify-content: flex-end;
}

:deep(.action-buttons .btn) {
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: all 0.2s ease;
}

:deep(.action-buttons .btn:focus,
       .action-buttons .btn:active) {
  box-shadow: none !important;
  outline: none !important;
}

:deep(.action-buttons .btn i) {
  font-size: 1rem;
}

:deep(.action-buttons .btn-outline-primary) {
  color: #667eea;
  border-color: #667eea;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-primary:hover) {
  background-color: #667eea;
  border-color: #667eea;
  color: white;
}

:deep(.action-buttons .btn-outline-primary:focus,
       .action-buttons .btn-outline-primary:active) {
  color: #667eea !important;
  border-color: #667eea !important;
  background-color: transparent !important;
}

:deep(.action-buttons .btn-outline-info) {
  color: #17a2b8;
  border-color: #17a2b8;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-info:hover) {
  background-color: #17a2b8;
  border-color: #17a2b8;
  color: white;
}

:deep(.action-buttons .btn-outline-info:focus,
       .action-buttons .btn-outline-info:active) {
  color: #17a2b8 !important;
  border-color: #17a2b8 !important;
  background-color: transparent !important;
}

:deep(.action-buttons .btn-outline-danger) {
  color: #dc3545;
  border-color: #dc3545;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-danger:hover) {
  background-color: #dc3545;
  border-color: #dc3545;
  color: white;
}

:deep(.action-buttons .btn-outline-danger:focus,
       .action-buttons .btn-outline-danger:active) {
  color: #dc3545 !important;
  border-color: #dc3545 !important;
  background-color: transparent !important;
}

/* Alert styling */
.alert {
  border-radius: 8px;
  border: none;
  padding: 1rem 1.5rem;
}

.alert-info {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%);
  color: #667eea;
  border-left: 4px solid #667eea;
}

.alert-warning {
  background: linear-gradient(135deg, rgba(255, 193, 7, 0.1) 0%, rgba(255, 152, 0, 0.1) 100%);
  color: #ff9800;
  border-left: 4px solid #ff9800;
}

/* Loading spinner */
.text-center {
  padding: 3rem;
}

:deep(.spinner-border) {
  color: #667eea;
}
</style>

<style lang="scss">
/* Modal styling - copied from flow-modal */
.parameter-modal {
  .modal-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-bottom: none;

    .modal-title {
      color: white;
      font-weight: 600;
    }

    .btn-close {
      filter: brightness(0) invert(1);
      opacity: 0.8;

      &:hover {
        opacity: 1;
      }
    }
  }
}
</style>
