<template>
  <div class="flows-manage">
    <div class="page-card">
      <!-- Header with Add Button -->
      <div class="card-header">
        <h2 class="card-title">Flow Management</h2>
        <b-button variant="primary" @click="handleAddFlow" :disabled="!tableExists">
          <i class="pe-7s-plus"></i>
          Add New Flow
        </b-button>
      </div>

      <!-- Table Not Exists Warning -->
      <div v-if="!isLoading && !tableExists" class="alert alert-warning m-4">
        <i class="pe-7s-attention"></i>
        <strong>Table Not Created</strong>
        <p class="mb-0 mt-2">
          The NiFi flows table hasn't been created yet. Please configure your data format hierarchy in
          <router-link to="/settings/data-format">Settings → Data Format</router-link> first.
        </p>
      </div>

      <!-- Filters -->
      <div v-if="tableExists && hierarchyColumns.length > 0" class="filters-section">
        <div class="row g-3">
          <div v-for="col in hierarchyColumns" :key="col" class="col-md-3">
            <b-form-input
              v-model="filters[col.toLowerCase()]"
              :placeholder="`Filter by ${col}`"
              size="sm"
            />
          </div>
          <div class="col-md-3">
            <b-form-input v-model="filters.template" placeholder="Filter by Template" size="sm" />
          </div>
          <div class="col-md-3">
            <b-form-select v-model="filters.active" :options="activeOptions" size="sm" />
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-5">
        <b-spinner variant="primary"></b-spinner>
        <p class="mt-3 text-muted">Loading flows...</p>
      </div>

      <!-- Table -->
      <div v-else-if="tableExists" class="table-responsive">
        <table class="table flows-table">
          <thead>
            <tr>
              <th>ID</th>
              <th v-for="col in hierarchyColumns" :key="col">{{ col }}</th>
              <th>Source</th>
              <th>Destination</th>
              <th>Template</th>
              <th>Active</th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="flow in paginatedFlows" :key="flow.id">
              <td>{{ flow.id }}</td>
              <td v-for="col in hierarchyColumns" :key="col">
                {{ flow[col.toLowerCase()] }}
              </td>
              <td><code class="text-primary">{{ flow.source }}</code></td>
              <td><code class="text-success">{{ flow.destination }}</code></td>
              <td>{{ flow.template }}</td>
              <td>
                <span class="status-badge" :class="{ active: flow.active }">
                  {{ flow.active ? 'Active' : 'Inactive' }}
                </span>
              </td>
              <td class="text-end">
                <div class="action-buttons">
                  <b-button
                    size="sm"
                    variant="outline-primary"
                    @click="handleEdit(flow)"
                    title="Edit"
                  >
                    <i class="pe-7s-pen"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-info"
                    @click="handleView(flow)"
                    title="View"
                  >
                    <i class="pe-7s-look"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-danger"
                    @click="handleRemove(flow)"
                    title="Remove"
                  >
                    <i class="pe-7s-trash"></i>
                  </b-button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredFlows.length === 0">
              <td :colspan="hierarchyColumns.length + 7" class="text-center py-4 text-muted">
                <i class="pe-7s-info display-4 d-block mb-2"></i>
                No flows found
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div v-if="tableExists && filteredFlows.length > 0" class="pagination-section">
        <div class="pagination-info">
          Showing {{ paginationStart }} to {{ paginationEnd }} of {{ filteredFlows.length }} flows
        </div>
        <div class="pagination-controls">
          <b-button
            size="sm"
            variant="outline-secondary"
            @click="previousPage"
            :disabled="currentPage === 1"
          >
            Previous
          </b-button>
          <span class="mx-3">Page {{ currentPage }} of {{ totalPages }}</span>
          <b-button
            size="sm"
            variant="outline-secondary"
            @click="nextPage"
            :disabled="currentPage === totalPages"
          >
            Next
          </b-button>
        </div>
      </div>
    </div>

    <!-- Edit/View Modal -->
    <b-modal v-model="showModal" :title="modalTitle" size="xl" modal-class="flow-modal">
      <div v-if="selectedFlow" class="modal-compact">
        <div class="row g-2">
          <!-- Dynamic hierarchy fields with combo input -->
          <div v-for="col in hierarchyColumns" :key="col" class="col-md-3">
            <label class="form-label-compact">{{ col }}</label>
            <div v-if="!isViewMode" class="hierarchy-combo-wrapper">
              <div class="input-with-dropdown">
                <b-dropdown
                  size="sm"
                  variant="link"
                  no-caret
                  boundary="viewport"
                  class="hierarchy-dropdown-btn"
                >
                  <template #button-content>
                    <i class="pe-7s-angle-down"></i>
                  </template>
                  <b-dropdown-item
                    v-for="value in hierarchyValues[col]"
                    :key="value"
                    @click="selectedFlow[col.toLowerCase()] = value"
                  >
                    {{ value }}
                  </b-dropdown-item>
                  <b-dropdown-divider v-if="hierarchyValues[col]?.length > 0" />
                  <b-dropdown-item disabled class="text-muted small">
                    Or type custom value above
                  </b-dropdown-item>
                </b-dropdown>
                <b-form-input
                  v-model="selectedFlow[col.toLowerCase()]"
                  :placeholder="`Select or type ${col}`"
                  size="sm"
                  class="hierarchy-input"
                />
              </div>
            </div>
            <b-form-input
              v-else
              v-model="selectedFlow[col.toLowerCase()]"
              disabled
              size="sm"
            />
          </div>

          <!-- Standard fields -->
          <div class="col-md-6">
            <label class="form-label-compact">Source</label>
            <b-form-input v-model="selectedFlow.source" :disabled="isViewMode" size="sm" />
          </div>
          <div class="col-md-6">
            <label class="form-label-compact">Destination</label>
            <b-form-input v-model="selectedFlow.destination" :disabled="isViewMode" size="sm" />
          </div>
          <div class="col-md-6">
            <label class="form-label-compact">Connection Parameter</label>
            <b-form-input v-model="selectedFlow.connection_param" :disabled="isViewMode" size="sm" />
          </div>
          <div class="col-md-6">
            <label class="form-label-compact">Template</label>
            <b-form-input
              v-model="selectedFlow.template"
              :disabled="isViewMode"
              size="sm"
              placeholder="Enter template name"
            />
          </div>
          <div class="col-md-12">
            <label class="form-label-compact">Description</label>
            <b-form-textarea
              v-model="selectedFlow.description"
              :disabled="isViewMode"
              rows="2"
              size="sm"
            />
          </div>
          <div class="col-md-12">
            <b-form-checkbox v-model="selectedFlow.active" :disabled="isViewMode">
              Active
            </b-form-checkbox>
          </div>
        </div>
      </div>

      <template #footer>
        <b-button variant="secondary" @click="showModal = false" size="sm">
          {{ isViewMode ? 'Close' : 'Cancel' }}
        </b-button>
        <b-button v-if="!isViewMode" variant="primary" @click="handleModalOk" size="sm">
          {{ selectedFlow?.id ? 'Update' : 'Create' }}
        </b-button>
      </template>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { apiRequest } from '@/utils/api'

interface TableColumn {
  name: string
  type: string
  nullable: boolean
  primary_key: boolean
}

interface TableInfo {
  exists: boolean
  table_name?: string
  columns?: TableColumn[]
  hierarchy_columns?: string[]
  current_hierarchy?: any[]
}

const isLoading = ref(false)
const tableExists = ref(false)
const hierarchyColumns = ref<string[]>([])
const allColumns = ref<TableColumn[]>([])
const hierarchyValues = ref<Record<string, string[]>>({})
const flows = ref<any[]>([])
const filters = ref<Record<string, string>>({
  template: '',
  active: ''
})

const activeOptions = [
  { value: '', text: 'All Status' },
  { value: 'true', text: 'Active' },
  { value: 'false', text: 'Inactive' }
]

const currentPage = ref(1)
const itemsPerPage = ref(10)

const showModal = ref(false)
const selectedFlow = ref<any | null>(null)
const isViewMode = ref(false)

const modalTitle = computed(() => {
  if (!selectedFlow.value) return ''
  if (isViewMode.value) return 'View Flow'
  return selectedFlow.value.id ? 'Edit Flow' : 'Add New Flow'
})

const filteredFlows = computed(() => {
  return flows.value.filter((flow) => {
    // Filter by hierarchy columns
    for (const col of hierarchyColumns.value) {
      const filterValue = filters.value[col.toLowerCase()]
      if (filterValue && !flow[col.toLowerCase()]?.toLowerCase().includes(filterValue.toLowerCase())) {
        return false
      }
    }

    // Filter by template
    if (filters.value.template && !flow.template?.toLowerCase().includes(filters.value.template.toLowerCase())) {
      return false
    }

    // Filter by active status
    if (filters.value.active !== '') {
      const isActive = filters.value.active === 'true'
      if (flow.active !== isActive) {
        return false
      }
    }

    return true
  })
})

const totalPages = computed(() => {
  return Math.ceil(filteredFlows.value.length / itemsPerPage.value)
})

const paginationStart = computed(() => {
  return (currentPage.value - 1) * itemsPerPage.value + 1
})

const paginationEnd = computed(() => {
  return Math.min(currentPage.value * itemsPerPage.value, filteredFlows.value.length)
})

const paginatedFlows = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value
  const end = start + itemsPerPage.value
  return filteredFlows.value.slice(start, end)
})

const loadTableInfo = async () => {
  try {
    const data: TableInfo = await apiRequest('/api/nifi-flows/table-info')
    tableExists.value = data.exists

    if (data.exists && data.hierarchy_columns) {
      hierarchyColumns.value = data.hierarchy_columns
      allColumns.value = data.columns || []

      // Initialize filters for hierarchy columns
      for (const col of data.hierarchy_columns) {
        filters.value[col.toLowerCase()] = ''
      }

      // Load hierarchy values for each attribute
      await loadHierarchyValues()
    }
  } catch (error) {
    console.error('Error loading table info:', error)
    tableExists.value = false
  }
}

const loadHierarchyValues = async () => {
  try {
    for (const col of hierarchyColumns.value) {
      const data = await apiRequest(`/api/settings/data-format/values/${encodeURIComponent(col)}`)
      hierarchyValues.value[col] = data.values || []
    }
  } catch (error) {
    console.error('Error loading hierarchy values:', error)
  }
}

const getHierarchyOptions = (columnName: string) => {
  const values = hierarchyValues.value[columnName] || []
  const options = [
    { value: '', text: `-- Select ${columnName} --` },
    ...values.map(v => ({ value: v, text: v }))
  ]
  return options
}

const loadFlows = async () => {
  if (!tableExists.value) return

  isLoading.value = true
  try {
    const data = await apiRequest('/api/nifi-flows/')
    flows.value = data.flows || []
    console.log('Loaded flows:', flows.value)
    if (flows.value.length > 0) {
      console.log('First flow:', flows.value[0])
    }
  } catch (error) {
    console.error('Error loading flows:', error)
    flows.value = []
  } finally {
    isLoading.value = false
  }
}

const formatDate = (dateString: string) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  return date.toLocaleDateString() + ' ' + date.toLocaleTimeString()
}

const handleAddFlow = () => {
  const newFlow: any = {
    id: 0,
    source: '',
    destination: '',
    connection_param: '',
    template: '',
    active: true,
    description: '',
    creator_name: ''
  }

  // Add hierarchy fields
  for (const col of hierarchyColumns.value) {
    newFlow[col.toLowerCase()] = ''
  }

  selectedFlow.value = newFlow
  isViewMode.value = false
  showModal.value = true
}

const handleEdit = (flow: any) => {
  selectedFlow.value = { ...flow }
  isViewMode.value = false
  showModal.value = true
}

const handleView = (flow: any) => {
  selectedFlow.value = { ...flow }
  isViewMode.value = true
  showModal.value = true
}

const handleRemove = async (flow: any) => {
  const identifier = hierarchyColumns.value.map(col => flow[col.toLowerCase()]).join('/')
  if (confirm(`Are you sure you want to remove flow "${identifier}"?`)) {
    try {
      await apiRequest(`/api/nifi-flows/${flow.id}`, { method: 'DELETE' })
      alert('Flow deleted successfully!')
      await loadFlows()
    } catch (error: any) {
      console.error('Error removing flow:', error)
      alert('Error: ' + (error.message || 'Failed to remove flow'))
    }
  }
}

const handleModalOk = async () => {
  if (!selectedFlow.value) return

  try {
    // Build hierarchy values
    const hierarchyValues: Record<string, string> = {}
    for (const col of hierarchyColumns.value) {
      hierarchyValues[col] = selectedFlow.value[col.toLowerCase()]
    }

    const payload = {
      hierarchy_values: hierarchyValues,
      source: selectedFlow.value.source,
      destination: selectedFlow.value.destination,
      connection_param: selectedFlow.value.connection_param,
      template: selectedFlow.value.template,
      active: selectedFlow.value.active,
      description: selectedFlow.value.description,
      creator_name: selectedFlow.value.creator_name || 'admin'
    }

    if (selectedFlow.value.id) {
      // Update existing flow
      await apiRequest(`/api/nifi-flows/${selectedFlow.value.id}`, {
        method: 'PUT',
        body: JSON.stringify(payload)
      })
      alert('Flow updated successfully!')
      showModal.value = false
      await loadFlows()
    } else {
      // Create new flow
      await apiRequest('/api/nifi-flows/', {
        method: 'POST',
        body: JSON.stringify(payload)
      })
      alert('Flow created successfully!')
      showModal.value = false
      await loadFlows()
    }
  } catch (error: any) {
    console.error('Error saving flow:', error)
    alert('Error: ' + (error.message || 'Failed to save flow'))
  }
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
  }
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++
  }
}

onMounted(async () => {
  await loadTableInfo()
  await loadFlows()
})
</script>

<style scoped lang="scss">
.flows-manage {
  max-width: 1400px;
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
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  color: white;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: white;
  margin: 0;
}

.filters-section {
  padding: 20px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;
}

.flows-table {
  margin: 0;

  thead {
    background: #f8f9fa;

    th {
      font-weight: 600;
      color: #5a6c7d;
      border-bottom: 2px solid #dee2e6;
      padding: 12px 15px;
      font-size: 0.875rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }

  tbody {
    td {
      padding: 12px 15px;
      vertical-align: middle;
      color: #495057;

      code {
        font-size: 0.85rem;
        padding: 2px 6px;
        border-radius: 3px;
        background: #f8f9fa;
      }
    }

    tr {
      transition: background 0.2s;

      &:hover {
        background: #f8f9fa;
      }
    }
  }
}

.badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  text-transform: uppercase;
  color: white;
}

.status-badge {
  display: inline-block;
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 500;
  background: #dc3545;
  color: white;

  &.active {
    background: #28a745;
  }
}

.action-buttons {
  display: flex;
  gap: 8px;
  justify-content: flex-end;

  button {
    padding: 4px 8px;

    i {
      font-size: 1rem;
    }
  }
}

.pagination-section {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 20px 30px;
  border-top: 1px solid #e9ecef;
}

.pagination-info {
  color: #6c757d;
  font-size: 0.875rem;
}

.pagination-controls {
  display: flex;
  align-items: center;
}

.alert {
  border-radius: 6px;

  i {
    margin-right: 8px;
  }

  a {
    font-weight: 600;
  }
}

.modal-compact {
  .row {
    margin-left: -4px;
    margin-right: -4px;
  }

  .col-md-3,
  .col-md-4,
  .col-md-6,
  .col-md-12 {
    padding-left: 4px;
    padding-right: 4px;
  }
}

.form-label-compact {
  font-size: 0.8rem;
  font-weight: 600;
  color: #4a5568;
  margin-bottom: 4px;
  display: block;
}

.hierarchy-combo-wrapper {
  position: relative;
}

.input-with-dropdown {
  display: flex;
  align-items: stretch;
  gap: 2px;
}

.hierarchy-dropdown-btn {
  flex-shrink: 0;

  ::v-deep .btn {
    padding: 0 8px;
    height: 100%;
    border: 1px solid #ced4da;
    border-radius: 0.2rem 0 0 0.2rem;
    background: #f8f9fa;
    color: #6c757d;
    display: flex;
    align-items: center;

    &:hover {
      color: #495057;
      background: #e9ecef;
    }

    &:focus {
      box-shadow: none;
      border-color: #80bdff;
    }

    i {
      font-size: 1rem;
    }
  }

  ::v-deep .dropdown-menu {
    min-width: 200px;
    max-height: 200px;
    overflow-y: auto;
  }
}

.hierarchy-input {
  flex: 1;
  border-radius: 0 0.2rem 0.2rem 0 !important;
}
</style>

<style lang="scss">
// Global styles for modal (not scoped)
.flow-modal {
  .modal-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-bottom: none;

    .modal-title {
      font-weight: 600;
      font-size: 1.1rem;
      color: white;
    }

    .btn-close {
      filter: brightness(0) invert(1);
      opacity: 0.8;

      &:hover {
        opacity: 1;
      }
    }
  }

  .modal-body {
    padding: 16px 20px;
    max-height: 70vh;
    overflow-y: auto;
  }

  .modal-footer {
    padding: 12px 20px;
    background: #f8f9fa;
    border-top: 2px solid #e9ecef;
  }
}
</style>
