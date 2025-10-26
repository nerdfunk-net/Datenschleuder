<template>
  <div class="flows-manage">
    <div class="page-card">
      <!-- Header with Controls -->
      <div class="card-header">
        <h2 class="card-title">Flow Management</h2>
        <div class="header-actions">
          <b-button variant="outline-light" size="sm" @click="showColumnToggle = !showColumnToggle" class="me-2">
            <i class="pe-7s-config"></i> Columns
          </b-button>
          <b-button variant="outline-light" size="sm" @click="showViewManager = !showViewManager" class="me-2">
            <i class="pe-7s-photo-gallery"></i> Views
          </b-button>
          <b-button variant="light" @click="handleAddFlow" :disabled="!tableExists">
            <i class="pe-7s-plus"></i> Add Flow
          </b-button>
        </div>
      </div>

      <!-- Table Not Exists Warning -->
      <div v-if="!isLoading && !tableExists" class="alert alert-warning m-4">
        <i class="pe-7s-attention"></i>
        <strong>Table Not Created</strong>
        <p class="mb-0 mt-2">
          The NiFi flows table hasn't been created yet. Please configure your hierarchy in
          <router-link to="/settings/hierarchy">Settings → Hierarchy</router-link> first.
        </p>
      </div>

      <!-- Column Toggle Panel -->
      <div v-if="showColumnToggle && tableExists" class="column-toggle-panel">
        <div class="panel-header">
          <h6 class="mb-0">Show/Hide Columns</h6>
          <b-button size="sm" variant="link" @click="showColumnToggle = false">
            <i class="pe-7s-close"></i>
          </b-button>
        </div>
        <div class="panel-body">
          <div class="row g-2">
            <div class="col-md-3" v-for="col in allAvailableColumns" :key="col.key">
              <b-form-checkbox v-model="visibleColumns[col.key]" @change="onColumnToggle">
                {{ col.label }}
              </b-form-checkbox>
            </div>
          </div>
        </div>
      </div>

      <!-- View Manager Panel -->
      <div v-if="showViewManager && tableExists" class="view-manager-panel">
        <div class="panel-header">
          <h6 class="mb-0">Manage Views</h6>
          <b-button size="sm" variant="link" @click="showViewManager = false">
            <i class="pe-7s-close"></i>
          </b-button>
        </div>
        <div class="panel-body">
          <div class="view-actions mb-3">
            <b-button
              size="sm"
              variant="primary"
              @click="handleSaveView(false)"
              :disabled="currentLoadedViewId === null"
              title="Overwrite the currently loaded view"
            >
              <i class="pe-7s-diskette"></i> Save
            </b-button>
            <b-button
              size="sm"
              variant="success"
              @click="handleSaveView(true)"
              class="ms-2"
            >
              <i class="pe-7s-plus"></i> Save as New
            </b-button>
          </div>
          <div class="view-list">
            <div v-if="savedViews.length === 0" class="text-muted text-center py-3">
              No saved views yet
            </div>
            <div v-for="view in savedViews" :key="view.id" class="view-item">
              <div class="view-info">
                <div class="view-name">
                  {{ view.name }}
                  <span v-if="view.is_default" class="badge bg-primary ms-2">Default</span>
                </div>
                <div class="view-description">{{ view.description || 'No description' }}</div>
                <div class="view-columns-count">{{ view.visible_columns.length }} columns</div>
              </div>
              <div class="view-actions-btn">
                <b-button size="sm" variant="outline-primary" @click="loadView(view)" title="Load View">
                  <i class="pe-7s-look"></i>
                </b-button>
                <b-button size="sm" variant="outline-info" @click="setDefaultView(view.id)" title="Set as Default" :disabled="view.is_default">
                  <i class="pe-7s-star"></i>
                </b-button>
                <b-button size="sm" variant="outline-danger" @click="deleteView(view.id)" title="Delete">
                  <i class="pe-7s-trash"></i>
                </b-button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Filters (Dynamic based on visible columns) -->
      <div v-if="tableExists && visibleColumnsList.length > 0" class="filters-section">
        <div class="filter-header">
          <h6 class="mb-0">
            <i class="pe-7s-filter"></i> Filters
          </h6>
          <b-button size="sm" variant="link" @click="clearFilters">Clear All</b-button>
        </div>
        <div class="row g-2">
          <div v-for="col in visibleColumnsList" :key="col.key" class="col-md-2">
            <label class="filter-label">{{ col.label }}</label>
            <b-form-input
              v-model="filters[col.key]"
              :placeholder="`Filter ${col.label}`"
              size="sm"
            />
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
              <th
                v-for="(col, index) in visibleColumnsList"
                :key="col.key"
                :draggable="!isResizing"
                @dragstart="handleDragStart(index, $event)"
                @dragover="handleDragOver($event)"
                @drop="handleDrop(index)"
                @dragend="handleDragEnd"
                class="draggable-header resizable-header"
                :class="{ 'dragging': draggingIndex === index, 'resizing': resizingColumn === col.key }"
                :style="{ width: columnWidths[col.key] ? columnWidths[col.key] + 'px' : 'auto' }"
              >
                <span class="drag-handle">⋮⋮</span>
                {{ col.label }}
                <span
                  class="resize-handle"
                  @mousedown.stop.prevent="startResize(col.key, $event)"
                ></span>
              </th>
              <th class="text-end">Actions</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="flow in paginatedFlows" :key="flow.id">
              <td>{{ flow.id }}</td>
              <td v-for="col in visibleColumnsList" :key="col.key">
                <code v-if="col.key === 'source' || col.key === 'destination'" :class="col.key === 'source' ? 'text-primary' : 'text-success'">
                  {{ flow[col.key] }}
                </code>
                <span v-else-if="col.key === 'active'" class="status-badge" :class="{ active: flow.active }">
                  {{ flow.active ? 'Active' : 'Inactive' }}
                </span>
                <span v-else-if="col.key === 'src_template_id' || col.key === 'dest_template_id'">
                  {{ getTemplateName(flow[col.key]) }}
                </span>
                <span v-else>{{ flow[col.key] }}</span>
              </td>
              <td class="text-end">
                <div class="action-buttons">
                  <b-button size="sm" variant="outline-primary" @click="handleEdit(flow)" title="Edit">
                    <i class="pe-7s-pen"></i>
                  </b-button>
                  <b-button size="sm" variant="outline-info" @click="handleView(flow)" title="View">
                    <i class="pe-7s-look"></i>
                  </b-button>
                  <b-button size="sm" variant="outline-danger" @click="handleRemove(flow)" title="Remove">
                    <i class="pe-7s-trash"></i>
                  </b-button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredFlows.length === 0">
              <td :colspan="visibleColumnsList.length + 2" class="text-center py-4 text-muted">
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
          <b-button size="sm" variant="outline-secondary" @click="previousPage" :disabled="currentPage === 1">
            Previous
          </b-button>
          <span class="mx-3">Page {{ currentPage }} of {{ totalPages }}</span>
          <b-button size="sm" variant="outline-secondary" @click="nextPage" :disabled="currentPage === totalPages">
            Next
          </b-button>
        </div>
      </div>
    </div>

    <!-- Edit/View Modal -->
    <b-modal v-model="showModal" :title="modalTitle" size="xl" modal-class="flow-modal">
      <div v-if="selectedFlow" class="modal-compact">
        <div class="row g-3">
          <!-- Source Section -->
          <div class="col-md-12">
            <div class="section-frame source-frame">
              <div class="section-header">Source</div>
              <div class="row g-2">
                <!-- Dynamic hierarchy fields - Source -->
                <div v-for="col in hierarchyColumns" :key="'src_' + col.name" class="col-md-3">
                  <label class="form-label-compact">{{ col.name }}</label>
                  <div v-if="!isViewMode" class="hierarchy-combo-wrapper">
                    <div class="input-with-dropdown">
                      <b-dropdown size="sm" variant="link" no-caret boundary="viewport" class="hierarchy-dropdown-btn">
                        <template #button-content>
                          <i class="pe-7s-angle-down"></i>
                        </template>
                        <b-dropdown-item
                          v-for="value in hierarchyValues[col.name]"
                          :key="value"
                          @click="selectedFlow[col.src_column] = value"
                        >
                          {{ value }}
                        </b-dropdown-item>
                        <b-dropdown-divider v-if="hierarchyValues[col.name]?.length > 0" />
                        <b-dropdown-item disabled class="text-muted small">
                          Or type custom value above
                        </b-dropdown-item>
                      </b-dropdown>
                      <b-form-input
                        v-model="selectedFlow[col.src_column]"
                        :placeholder="`Select or type ${col.name}`"
                        size="sm"
                        class="hierarchy-input"
                      />
                    </div>
                  </div>
                  <b-form-input v-else v-model="selectedFlow[col.src_column]" disabled size="sm" />
                </div>

                <!-- Source URL, Connection Parameter, and Template in one row -->
                <div class="col-md-4">
                  <label class="form-label-compact">Source URL</label>
                  <b-form-input v-model="selectedFlow.source" :disabled="isViewMode" size="sm" />
                </div>
                <div class="col-md-4">
                  <label class="form-label-compact">Connection Parameter</label>
                  <b-form-input v-model="selectedFlow.src_connection_param" :disabled="isViewMode" size="sm" />
                </div>
                <div class="col-md-4">
                  <label class="form-label-compact">Template</label>
                  <b-form-select
                    v-model="selectedFlow.src_template_id"
                    :options="templateOptions"
                    :disabled="isViewMode"
                    size="sm"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Destination Section -->
          <div class="col-md-12">
            <div class="section-frame destination-frame">
              <div class="section-header">Destination</div>
              <div class="row g-2">
                <!-- Dynamic hierarchy fields - Destination -->
                <div v-for="col in hierarchyColumns" :key="'dest_' + col.name" class="col-md-3">
                  <label class="form-label-compact">{{ col.name }}</label>
                  <div v-if="!isViewMode" class="hierarchy-combo-wrapper">
                    <div class="input-with-dropdown">
                      <b-dropdown size="sm" variant="link" no-caret boundary="viewport" class="hierarchy-dropdown-btn">
                        <template #button-content>
                          <i class="pe-7s-angle-down"></i>
                        </template>
                        <b-dropdown-item
                          v-for="value in hierarchyValues[col.name]"
                          :key="value"
                          @click="selectedFlow[col.dest_column] = value"
                        >
                          {{ value }}
                        </b-dropdown-item>
                        <b-dropdown-divider v-if="hierarchyValues[col.name]?.length > 0" />
                        <b-dropdown-item disabled class="text-muted small">
                          Or type custom value above
                        </b-dropdown-item>
                      </b-dropdown>
                      <b-form-input
                        v-model="selectedFlow[col.dest_column]"
                        :placeholder="`Select or type ${col.name}`"
                        size="sm"
                        class="hierarchy-input"
                      />
                    </div>
                  </div>
                  <b-form-input v-else v-model="selectedFlow[col.dest_column]" disabled size="sm" />
                </div>

                <!-- Destination field -->
                <div class="col-md-4">
                  <label class="form-label-compact">Destination URL</label>
                  <b-form-input v-model="selectedFlow.destination" :disabled="isViewMode" size="sm" />
                </div>
                <div class="col-md-4">
                  <label class="form-label-compact">Connection Parameter</label>
                  <b-form-input v-model="selectedFlow.dest_connection_param" :disabled="isViewMode" size="sm" />
                </div>
                <div class="col-md-4">
                  <label class="form-label-compact">Template</label>
                  <b-form-select
                    v-model="selectedFlow.dest_template_id"
                    :options="templateOptions"
                    :disabled="isViewMode"
                    size="sm"
                  />
                </div>
              </div>
            </div>
          </div>

          <!-- Other fields -->
          <div class="col-md-12">
            <label class="form-label-compact">Description</label>
            <b-form-textarea v-model="selectedFlow.description" :disabled="isViewMode" rows="2" size="sm" />
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

    <!-- Save View Modal -->
    <b-modal v-model="showSaveViewModal" :title="isSaveAsNew ? 'Save as New View' : 'Save View'" size="md">
      <div class="form-group mb-3" v-if="isSaveAsNew">
        <label class="form-label">View Name</label>
        <b-form-input v-model="newViewName" placeholder="e.g., Source View, Destination View" />
      </div>
      <div class="form-group mb-3" v-else>
        <label class="form-label">View Name</label>
        <b-form-input v-model="newViewName" :disabled="true" />
        <small class="text-muted">You are updating the existing view</small>
      </div>
      <div class="form-group mb-3">
        <label class="form-label">Description (Optional)</label>
        <b-form-input v-model="newViewDescription" placeholder="Description of this view" />
      </div>
      <div class="form-group">
        <b-form-checkbox v-model="newViewIsDefault">
          Set as default view
        </b-form-checkbox>
      </div>

      <template #footer>
        <b-button variant="secondary" @click="showSaveViewModal = false" size="sm">Cancel</b-button>
        <b-button variant="primary" @click="saveView" size="sm" :disabled="isSaveAsNew && !newViewName.trim()">
          {{ isSaveAsNew ? 'Save as New' : 'Update' }}
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

interface HierarchyColumn {
  name: string
  src_column: string
  dest_column: string
}

interface TableInfo {
  exists: boolean
  table_name?: string
  columns?: TableColumn[]
  hierarchy_columns?: HierarchyColumn[]
  current_hierarchy?: any[]
}

interface ColumnDefinition {
  key: string
  label: string
}

interface FlowView {
  id: number
  name: string
  description: string | null
  visible_columns: string[]
  column_widths: Record<string, number> | null
  is_default: boolean
  created_by: string | null
  created_at: string
  modified_at: string
}

interface RegistryFlow {
  id: number
  flow_name: string
  nifi_instance_name: string
  bucket_name: string
}

const isLoading = ref(false)
const tableExists = ref(false)
const hierarchyColumns = ref<HierarchyColumn[]>([])
const allColumns = ref<TableColumn[]>([])
const hierarchyValues = ref<Record<string, string[]>>({})
const flows = ref<any[]>([])
const filters = ref<Record<string, string>>({})
const registryFlows = ref<RegistryFlow[]>([])

// Column visibility
const visibleColumns = ref<Record<string, boolean>>({})
const allAvailableColumns = ref<ColumnDefinition[]>([])
const showColumnToggle = ref(false)
const columnOrder = ref<string[]>([]) // Store the order of column keys

// Drag and drop state
const draggingIndex = ref<number | null>(null)

// Column resizing state
const columnWidths = ref<Record<string, number>>({})
const resizingColumn = ref<string | null>(null)
const resizeStartX = ref(0)
const resizeStartWidth = ref(0)
const isResizing = ref(false)

// View management
const showViewManager = ref(false)
const savedViews = ref<FlowView[]>([])
const showSaveViewModal = ref(false)
const newViewName = ref('')
const newViewDescription = ref('')
const newViewIsDefault = ref(false)
const currentLoadedViewId = ref<number | null>(null)
const isSaveAsNew = ref(false)

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

const templateOptions = computed(() => {
  return [
    { value: null, text: '-- Select Template --' },
    ...registryFlows.value.map(flow => ({
      value: flow.id,
      text: `${flow.flow_name} (${flow.nifi_instance_name} / ${flow.bucket_name})`
    }))
  ]
})

const visibleColumnsList = computed(() => {
  const visibleCols = allAvailableColumns.value.filter(col => visibleColumns.value[col.key])

  // Sort by columnOrder if it exists
  if (columnOrder.value.length > 0) {
    return visibleCols.sort((a, b) => {
      const indexA = columnOrder.value.indexOf(a.key)
      const indexB = columnOrder.value.indexOf(b.key)

      // If not in order array, put at end
      if (indexA === -1) return 1
      if (indexB === -1) return -1

      return indexA - indexB
    })
  }

  return visibleCols
})

const filteredFlows = computed(() => {
  return flows.value.filter((flow) => {
    // Filter by visible columns only
    for (const col of visibleColumnsList.value) {
      const filterValue = filters.value[col.key]
      if (filterValue && !flow[col.key]?.toString().toLowerCase().includes(filterValue.toLowerCase())) {
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

      // Build all available columns
      const cols: ColumnDefinition[] = []

      // Add hierarchy columns (src and dest)
      for (const col of data.hierarchy_columns) {
        cols.push({ key: col.src_column, label: `Src ${col.name}` })
        cols.push({ key: col.dest_column, label: `Dest ${col.name}` })
      }

      // Add standard columns
      cols.push({ key: 'source', label: 'Source' })
      cols.push({ key: 'src_connection_param', label: 'Src Connection Param' })
      cols.push({ key: 'src_template_id', label: 'Src Template' })
      cols.push({ key: 'destination', label: 'Destination' })
      cols.push({ key: 'dest_connection_param', label: 'Dest Connection Param' })
      cols.push({ key: 'dest_template_id', label: 'Dest Template' })
      cols.push({ key: 'active', label: 'Active' })
      cols.push({ key: 'description', label: 'Description' })

      allAvailableColumns.value = cols

      // Initialize all as visible by default
      for (const col of cols) {
        visibleColumns.value[col.key] = true
        filters.value[col.key] = ''
      }

      // Load hierarchy values for each attribute
      await loadHierarchyValues()

      // Load registry flows for templates
      await loadRegistryFlows()

      // Load saved views
      await loadViews()

      // Load default view if exists
      const defaultView = savedViews.value.find(v => v.is_default)
      if (defaultView) {
        loadView(defaultView, false)
      }
    }
  } catch (error) {
    console.error('Error loading table info:', error)
    tableExists.value = false
  }
}

const loadHierarchyValues = async () => {
  try {
    for (const col of hierarchyColumns.value) {
      const data = await apiRequest(`/api/settings/hierarchy/values/${encodeURIComponent(col.name)}`)
      hierarchyValues.value[col.name] = data.values || []
    }
  } catch (error) {
    console.error('Error loading hierarchy values:', error)
  }
}

const loadRegistryFlows = async () => {
  try {
    const flows = await apiRequest('/api/registry-flows/')
    registryFlows.value = flows
  } catch (error) {
    console.error('Error loading registry flows:', error)
  }
}

const getTemplateName = (templateId: number | null) => {
  if (!templateId) return 'None'
  const template = registryFlows.value.find(f => f.id === templateId)
  return template ? `${template.flow_name} (${template.nifi_instance_name})` : 'Unknown'
}

const loadFlows = async () => {
  if (!tableExists.value) return

  isLoading.value = true
  try {
    const data = await apiRequest('/api/nifi-flows/')
    flows.value = data.flows || []
  } catch (error) {
    console.error('Error loading flows:', error)
    flows.value = []
  } finally {
    isLoading.value = false
  }
}

const loadViews = async () => {
  try {
    savedViews.value = await apiRequest('/api/flow-views/')
  } catch (error) {
    console.error('Error loading views:', error)
    savedViews.value = []
  }
}

const handleSaveView = (saveAsNew: boolean) => {
  isSaveAsNew.value = saveAsNew

  if (saveAsNew) {
    // Save as new - clear the form
    newViewName.value = ''
    newViewDescription.value = ''
    newViewIsDefault.value = false
  } else {
    // Save (overwrite) - load current view data
    const currentView = savedViews.value.find(v => v.id === currentLoadedViewId.value)
    if (currentView) {
      newViewName.value = currentView.name
      newViewDescription.value = currentView.description || ''
      newViewIsDefault.value = currentView.is_default
    }
  }

  showSaveViewModal.value = true
}

const saveView = async () => {
  if (isSaveAsNew.value && !newViewName.value.trim()) {
    alert('Please enter a view name')
    return
  }

  try {
    // Get visible columns in their current order
    let visibleCols: string[]
    if (columnOrder.value.length > 0) {
      // Use the ordered list
      visibleCols = columnOrder.value.filter(key => visibleColumns.value[key])
    } else {
      // Fallback to unordered list
      visibleCols = allAvailableColumns.value
        .filter(col => visibleColumns.value[col.key])
        .map(col => col.key)
    }

    if (isSaveAsNew.value) {
      // Create new view
      await apiRequest('/api/flow-views/', {
        method: 'POST',
        body: JSON.stringify({
          name: newViewName.value.trim(),
          description: newViewDescription.value.trim() || null,
          visible_columns: visibleCols,
          column_widths: columnWidths.value,
          is_default: newViewIsDefault.value
        })
      })
      alert('New view saved successfully!')
    } else {
      // Update existing view
      if (currentLoadedViewId.value === null) {
        alert('No view is currently loaded')
        return
      }

      await apiRequest(`/api/flow-views/${currentLoadedViewId.value}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: newViewName.value.trim(),
          description: newViewDescription.value.trim() || null,
          visible_columns: visibleCols,
          column_widths: columnWidths.value,
          is_default: newViewIsDefault.value
        })
      })
      alert('View updated successfully!')
    }

    showSaveViewModal.value = false
    await loadViews()
  } catch (error: any) {
    console.error('Error saving view:', error)
    alert('Error: ' + (error.message || 'Failed to save view'))
  }
}

const loadView = (view: FlowView, showMessage: boolean = true) => {
  // Reset all columns to hidden
  for (const col of allAvailableColumns.value) {
    visibleColumns.value[col.key] = false
  }

  // Show only columns in the view
  for (const colKey of view.visible_columns) {
    visibleColumns.value[colKey] = true
  }

  // Set the column order from the view (the order in visible_columns array defines the order)
  columnOrder.value = [...view.visible_columns]

  // Load column widths
  if (view.column_widths) {
    columnWidths.value = { ...view.column_widths }
  } else {
    columnWidths.value = {}
  }

  // Set the current loaded view ID
  currentLoadedViewId.value = view.id

  if (showMessage) {
    alert(`Loaded view: ${view.name}`)
  }
}

const setDefaultView = async (viewId: number) => {
  try {
    await apiRequest(`/api/flow-views/${viewId}/set-default`, { method: 'POST' })
    alert('Default view updated!')
    await loadViews()
  } catch (error: any) {
    console.error('Error setting default view:', error)
    alert('Error: ' + (error.message || 'Failed to set default view'))
  }
}

const deleteView = async (viewId: number) => {
  if (!confirm('Are you sure you want to delete this view?')) {
    return
  }

  try {
    await apiRequest(`/api/flow-views/${viewId}`, { method: 'DELETE' })
    alert('View deleted successfully!')
    await loadViews()
  } catch (error: any) {
    console.error('Error deleting view:', error)
    alert('Error: ' + (error.message || 'Failed to delete view'))
  }
}

const onColumnToggle = () => {
  // Reset filters for hidden columns
  for (const col of allAvailableColumns.value) {
    if (!visibleColumns.value[col.key]) {
      filters.value[col.key] = ''
    }
  }
}

const clearFilters = () => {
  for (const col of visibleColumnsList.value) {
    filters.value[col.key] = ''
  }
}

// Drag and drop handlers
const handleDragStart = (index: number, event: DragEvent) => {
  draggingIndex.value = index
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = 'move'
  }
}

const handleDragOver = (event: DragEvent) => {
  event.preventDefault()
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = 'move'
  }
}

const handleDrop = (dropIndex: number) => {
  if (draggingIndex.value === null || draggingIndex.value === dropIndex) {
    return
  }

  // Reorder the columns
  const newOrder = [...visibleColumnsList.value.map(col => col.key)]
  const [draggedItem] = newOrder.splice(draggingIndex.value, 1)
  newOrder.splice(dropIndex, 0, draggedItem)

  // Update columnOrder with the new order
  columnOrder.value = newOrder
}

const handleDragEnd = () => {
  draggingIndex.value = null
}

// Column resizing handlers
const startResize = (columnKey: string, event: MouseEvent) => {
  isResizing.value = true
  resizingColumn.value = columnKey
  resizeStartX.value = event.pageX

  // Get current width or default
  const th = (event.target as HTMLElement).parentElement as HTMLTableCellElement
  resizeStartWidth.value = th.offsetWidth

  // Add event listeners for mouse move and mouse up
  document.addEventListener('mousemove', handleResize)
  document.addEventListener('mouseup', stopResize)

  // Prevent text selection during resize
  document.body.style.userSelect = 'none'
  document.body.style.cursor = 'col-resize'
}

const handleResize = (event: MouseEvent) => {
  if (resizingColumn.value === null) return

  event.preventDefault()

  const diff = event.pageX - resizeStartX.value
  const newWidth = Math.max(50, resizeStartWidth.value + diff) // Min width of 50px

  columnWidths.value[resizingColumn.value] = newWidth
}

const stopResize = () => {
  isResizing.value = false
  resizingColumn.value = null
  document.removeEventListener('mousemove', handleResize)
  document.removeEventListener('mouseup', stopResize)
  document.body.style.userSelect = ''
  document.body.style.cursor = ''
}

const handleAddFlow = () => {
  const newFlow: any = {
    id: 0,
    source: '',
    destination: '',
    src_connection_param: '',
    dest_connection_param: '',
    src_template_id: null,
    dest_template_id: null,
    active: true,
    description: '',
    creator_name: ''
  }

  // Add hierarchy fields (src and dest for each)
  for (const col of hierarchyColumns.value) {
    newFlow[col.src_column] = ''
    newFlow[col.dest_column] = ''
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
  const identifier = hierarchyColumns.value
    .map(col => `${flow[col.src_column]} → ${flow[col.dest_column]}`)
    .join(' / ')
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
    // Build hierarchy values with source and destination for each attribute
    const hierarchyValues: Record<string, { source: string; destination: string }> = {}
    for (const col of hierarchyColumns.value) {
      hierarchyValues[col.name] = {
        source: selectedFlow.value[col.src_column] || '',
        destination: selectedFlow.value[col.dest_column] || ''
      }
    }

    const payload = {
      hierarchy_values: hierarchyValues,
      source: selectedFlow.value.source,
      destination: selectedFlow.value.destination,
      src_connection_param: selectedFlow.value.src_connection_param,
      dest_connection_param: selectedFlow.value.dest_connection_param,
      src_template_id: selectedFlow.value.src_template_id,
      dest_template_id: selectedFlow.value.dest_template_id,
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
  max-width: 1600px;
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

.header-actions {
  display: flex;
  gap: 8px;
}

.column-toggle-panel,
.view-manager-panel {
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 30px;
  border-bottom: 1px solid #dee2e6;
  background: white;

  h6 {
    font-weight: 600;
    color: #495057;
  }
}

.panel-body {
  padding: 20px 30px;
}

.view-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-height: 400px;
  overflow-y: auto;
}

.view-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background: white;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
}

.view-info {
  flex: 1;

  .view-name {
    font-weight: 600;
    color: #495057;
    font-size: 0.95rem;
  }

  .view-description {
    font-size: 0.85rem;
    color: #6c757d;
    margin-top: 4px;
  }

  .view-columns-count {
    font-size: 0.75rem;
    color: #adb5bd;
    margin-top: 4px;
  }
}

.view-actions-btn {
  display: flex;
  gap: 6px;
}

.filters-section {
  padding: 20px 30px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;

  .filter-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h6 {
      font-weight: 600;
      color: #495057;
    }
  }

  .filter-label {
    font-size: 0.75rem;
    font-weight: 600;
    color: #6c757d;
    margin-bottom: 4px;
    display: block;
  }
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
      white-space: nowrap;

      &.draggable-header {
        cursor: move;
        user-select: none;
        transition: background 0.2s, transform 0.2s;

        &:hover:not(.resizing) {
          background: #e9ecef;
        }

        &.dragging {
          opacity: 0.5;
          transform: scale(0.98);
        }

        &.resizing {
          background: #e3f2fd;
          cursor: col-resize !important;
        }

        .drag-handle {
          display: inline-block;
          margin-right: 8px;
          color: #adb5bd;
          font-size: 0.9rem;
          vertical-align: middle;
        }
      }

      &.resizable-header {
        position: relative;

        .resize-handle {
          position: absolute;
          right: 0;
          top: 0;
          bottom: 0;
          width: 8px;
          cursor: col-resize;
          background: transparent;
          z-index: 10;

          &:hover {
            background: rgba(0, 123, 255, 0.3);
          }

          &::after {
            content: '';
            position: absolute;
            right: 3px;
            top: 50%;
            transform: translateY(-50%);
            height: 60%;
            width: 2px;
            background: #dee2e6;
          }
        }
      }
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

.section-frame {
  background: #e9ecef;
  padding: 8px 10px;
  border-radius: 4px;
  margin-bottom: 6px;

  .section-header {
    font-size: 0.8rem;
    font-weight: 700;
    color: #495057;
    margin-bottom: 6px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
}

.source-frame {
  background: #e3f2fd;

  .section-header {
    color: #1976d2;
  }
}

.destination-frame {
  background: #e8f5e9;

  .section-header {
    color: #388e3c;
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
