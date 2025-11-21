<template>
  <div class="flows-manage">
    <div class="page-card">
      <!-- Header with Controls -->
      <div class="card-header">
        <h2 class="card-title">
          Flow Management
        </h2>
        <div class="header-actions">
          <!-- Columns Dropdown -->
          <b-dropdown 
            variant="light"
            size="sm"
            class="me-2 columns-dropdown"
            menu-class="columns-dropdown-menu"
            no-caret
          >
            <template #button-content>
              <i class="pe-7s-config"></i> Columns <i class="pe-7s-angle-down"></i>
            </template>
            <b-dropdown-item-button @click="deselectAllColumns">
              <i class="pe-7s-close-circle"></i> Deselect All
            </b-dropdown-item-button>
            <b-dropdown-divider />
            <div class="column-dropdown-form" @click.stop>
              <b-form-checkbox
                v-for="col in allAvailableColumns"
                :key="col.key"
                v-model="visibleColumns[col.key]"
                class="column-checkbox-compact"
                @change="onColumnToggle"
              >
                {{ col.label }}
              </b-form-checkbox>
            </div>
          </b-dropdown>
          
          <!-- Views Dropdown -->
          <b-dropdown 
            variant="light"
            size="sm"
            class="me-2 views-dropdown"
          >
            <template #button-content>
              <i class="pe-7s-photo-gallery"></i> Views
            </template>
            <b-dropdown-item-button 
              :disabled="currentLoadedViewId === null"
              @click="handleSaveView(false)"
            >
              <i class="pe-7s-disk"></i> Save
            </b-dropdown-item-button>
            <b-dropdown-item-button @click="handleSaveView(true)">
              <i class="pe-7s-copy-file"></i> Save as New
            </b-dropdown-item-button>
            <b-dropdown-item-button 
              :disabled="currentLoadedViewId === null"
              @click="handleSetAsDefault"
            >
              <i class="pe-7s-star"></i> Set as Default
            </b-dropdown-item-button>
            <b-dropdown-divider v-if="savedViews.length > 0" />
            <b-dropdown-header v-if="savedViews.length > 0" class="views-header">
              Saved Views
            </b-dropdown-header>
            <div class="saved-views-list">
              <div
                v-for="view in savedViews"
                :key="view.id"
                class="view-item-custom"
                @click="loadView(view, true)"
              >
                <span class="view-name">
                  <i v-if="view.is_default" class="pe-7s-star"></i>
                  {{ view.name }}
                </span>
                <b-button
                  size="sm"
                  variant="link"
                  class="text-danger p-0 delete-btn"
                  title="Delete"
                  @click.stop="deleteView(view.id)"
                >
                  <i class="pe-7s-trash"></i>
                </b-button>
              </div>
            </div>
          </b-dropdown>
          
          <b-button
            variant="success"
            :disabled="!tableExists"
            @click="handleAddFlow"
          >
            <i class="pe-7s-plus"></i> Add Flow
          </b-button>
        </div>
      </div>

      <!-- Table Not Exists Warning -->
      <div v-if="!isLoading && !tableExists" class="alert alert-warning m-4">
        <i class="pe-7s-attention"></i>
        <strong>Table Not Created</strong>
        <p class="mb-0 mt-2">
          The NiFi flows table hasn't been created yet. Please configure your
          hierarchy in
          <router-link to="/settings/hierarchy">
            Settings → Hierarchy
          </router-link>
          first.
        </p>
      </div>

      <!-- Filters (Dynamic based on visible columns) -->
      <div
        v-if="tableExists && visibleColumnsList.length > 0"
        class="filters-section"
      >
        <div class="filter-header">
          <h6 class="mb-0">
            <i class="pe-7s-filter"></i> Filters
          </h6>
          <b-button
            size="sm"
            variant="link"
            @click="clearFilters"
          >
            Clear All
          </b-button>
        </div>
        <div class="row g-2">
          <div
            v-for="col in visibleColumnsList"
            :key="col.key"
            class="col-md-2"
          >
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
        <b-spinner variant="primary" />
        <p class="mt-3 text-muted">
          Loading flows...
        </p>
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
                class="draggable-header resizable-header"
                :class="{
                  dragging: draggingIndex === index,
                  resizing: resizingColumn === col.key,
                }"
                :style="{
                  width: columnWidths[col.key]
                    ? columnWidths[col.key] + 'px'
                    : 'auto',
                }"
                @dragstart="handleDragStart(index, $event)"
                @dragover="handleDragOver($event)"
                @drop="handleDrop(index)"
                @dragend="handleDragEnd"
              >
                <span class="drag-handle">⋮⋮</span>
                {{ col.label }}
                <span
                  class="resize-handle"
                  @mousedown.stop.prevent="startResize(col.key, $event)"
                ></span>
              </th>
              <th class="text-end">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="flow in paginatedFlows" :key="flow.id">
              <td>{{ flow.id }}</td>
              <td v-for="col in visibleColumnsList" :key="col.key">
                <span
                  v-if="col.key === 'active'"
                  class="status-badge"
                  :class="{ active: flow.active }"
                >
                  {{ flow.active ? "Active" : "Inactive" }}
                </span>
                <span
                  v-else-if="
                    col.key === 'src_template_id' ||
                      col.key === 'dest_template_id'
                  "
                >
                  {{ getTemplateName(flow[col.key]) }}
                </span>
                <span v-else>{{ flow[col.key] }}</span>
              </td>
              <td class="text-end">
                <div class="action-buttons">
                  <b-button
                    size="sm"
                    variant="outline-success"
                    title="Deploy to Source"
                    :disabled="deployingFlows[`${flow.id}-source`]"
                    @click="handleQuickDeploySource(flow)"
                  >
                    <b-spinner
                      v-if="deployingFlows[`${flow.id}-source`]"
                      small
                    />
                    <i v-else class="pe-7s-angle-right-circle"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-success"
                    title="Deploy to Destination"
                    :disabled="deployingFlows[`${flow.id}-dest`]"
                    @click="handleQuickDeployDest(flow)"
                  >
                    <b-spinner
                      v-if="deployingFlows[`${flow.id}-dest`]"
                      small
                    />
                    <i v-else class="pe-7s-angle-left-circle"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-primary"
                    title="Edit"
                    @click="handleEdit(flow)"
                  >
                    <i class="pe-7s-pen"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-info"
                    title="View"
                    @click="handleView(flow)"
                  >
                    <i class="pe-7s-look"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-secondary"
                    title="Copy"
                    @click="handleCopy(flow)"
                  >
                    <i class="pe-7s-copy-file"></i>
                  </b-button>
                  <b-button
                    size="sm"
                    variant="outline-danger"
                    title="Remove"
                    @click="handleRemove(flow)"
                  >
                    <i class="pe-7s-trash"></i>
                  </b-button>
                </div>
              </td>
            </tr>
            <tr v-if="filteredFlows.length === 0">
              <td
                :colspan="visibleColumnsList.length + 2"
                class="text-center py-4 text-muted"
              >
                <i class="pe-7s-info display-4 d-block mb-2"></i>
                No flows found
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination -->
      <div
        v-if="tableExists && filteredFlows.length > 0"
        class="pagination-section"
      >
        <div class="pagination-info">
          Showing {{ paginationStart }} to {{ paginationEnd }} of
          {{ filteredFlows.length }} flows
        </div>
        <div class="pagination-controls">
          <b-button
            size="sm"
            variant="outline-secondary"
            :disabled="currentPage === 1"
            @click="previousPage"
          >
            Previous
          </b-button>
          <span class="mx-3">Page {{ currentPage }} of {{ totalPages }}</span>
          <b-button
            size="sm"
            variant="outline-secondary"
            :disabled="currentPage === totalPages"
            @click="nextPage"
          >
            Next
          </b-button>
        </div>
      </div>
    </div>

    <!-- Edit/View Modal -->
    <b-modal
      v-model="showModal"
      :title="modalTitle"
      size="xl"
      modal-class="flow-modal"
    >
      <div v-if="selectedFlow" class="modal-compact">
        <div class="row g-3">
          <!-- Source Section -->
          <div class="col-md-12">
            <div class="section-frame source-frame">
              <div class="section-header">
                Source
              </div>
              <div class="row g-2">
                <!-- Dynamic hierarchy fields - Source -->
                <div
                  v-for="col in hierarchyColumns"
                  :key="'src_' + col.name"
                  class="col-md-3"
                >
                  <label class="form-label-compact">{{ col.name }}</label>
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
                          v-for="value in hierarchyValues[col.name]"
                          :key="value"
                          @click="selectedFlow[col.src_column] = value"
                        >
                          {{ value }}
                        </b-dropdown-item>
                        <b-dropdown-divider
                          v-if="hierarchyValues[col.name]?.length > 0"
                        />
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
                  <b-form-input
                    v-else
                    v-model="selectedFlow[col.src_column]"
                    disabled
                    size="sm"
                  />
                </div>

                <!-- Source Parameter Context and Template in one row -->
                <div class="col-md-6">
                  <label class="form-label-compact">Source Parameter Context</label>
                  <b-form-select
                    v-model="selectedFlow.src_connection_param"
                    :options="sourceParameterContextOptions"
                    :disabled="isViewMode || !sourceNiFiInstanceId"
                    size="sm"
                  />
                </div>
                <div class="col-md-6">
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
              <div class="section-header">
                Destination
              </div>
              <div class="row g-2">
                <!-- Dynamic hierarchy fields - Destination -->
                <div
                  v-for="col in hierarchyColumns"
                  :key="'dest_' + col.name"
                  class="col-md-3"
                >
                  <label class="form-label-compact">{{ col.name }}</label>
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
                          v-for="value in hierarchyValues[col.name]"
                          :key="value"
                          @click="selectedFlow[col.dest_column] = value"
                        >
                          {{ value }}
                        </b-dropdown-item>
                        <b-dropdown-divider
                          v-if="hierarchyValues[col.name]?.length > 0"
                        />
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
                  <b-form-input
                    v-else
                    v-model="selectedFlow[col.dest_column]"
                    disabled
                    size="sm"
                  />
                </div>

                <!-- Destination Parameter Context and Template -->
                <div class="col-md-6">
                  <label class="form-label-compact">Destination Parameter Context</label>
                  <b-form-select
                    v-model="selectedFlow.dest_connection_param"
                    :options="destParameterContextOptions"
                    :disabled="isViewMode || !destNiFiInstanceId"
                    size="sm"
                  />
                </div>
                <div class="col-md-6">
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
          <div class="col-md-6">
            <label class="form-label-compact">Name</label>
            <b-form-input
              v-model="selectedFlow.name"
              :disabled="isViewMode"
              size="sm"
              placeholder="Flow name"
            />
          </div>
          <div class="col-md-6">
            <label class="form-label-compact">Contact</label>
            <b-form-input
              v-model="selectedFlow.contact"
              :disabled="isViewMode"
              size="sm"
              placeholder="Contact information"
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
            <b-form-checkbox
              v-model="selectedFlow.active"
              :disabled="isViewMode"
            >
              Active
            </b-form-checkbox>
          </div>
        </div>
      </div>

      <template #footer>
        <b-button variant="secondary" size="sm" @click="showModal = false">
          {{ isViewMode ? "Close" : "Cancel" }}
        </b-button>
        <b-button
          v-if="!isViewMode"
          variant="primary"
          size="sm"
          @click="handleModalOk"
        >
          {{ selectedFlow?.id ? "Update" : "Create" }}
        </b-button>
      </template>
    </b-modal>

    <!-- Save View Modal -->
    <b-modal
      v-model="showSaveViewModal"
      :title="isSaveAsNew ? 'Save as New View' : 'Save View'"
      size="md"
    >
      <div v-if="isSaveAsNew" class="form-group mb-3">
        <label class="form-label">View Name</label>
        <b-form-input
          v-model="newViewName"
          placeholder="e.g., Source View, Destination View"
          :state="viewNameValidation"
        />
        <b-form-invalid-feedback :state="viewNameValidation">
          A view with this name already exists
        </b-form-invalid-feedback>
      </div>
      <div v-else class="form-group mb-3">
        <label class="form-label">View Name</label>
        <b-form-input v-model="newViewName" :disabled="true" />
        <small class="text-muted">You are updating the existing view</small>
      </div>
      <div class="form-group mb-3">
        <label class="form-label">Description (Optional)</label>
        <b-form-input
          v-model="newViewDescription"
          placeholder="Description of this view"
        />
      </div>
      <div class="form-group">
        <b-form-checkbox v-model="newViewIsDefault">
          Set as default view
        </b-form-checkbox>
      </div>

      <template #footer>
        <b-button
          variant="secondary"
          size="sm"
          @click="showSaveViewModal = false"
        >
          Cancel
        </b-button>
        <b-button
          variant="primary"
          size="sm"
          :disabled="!isValidViewName"
          @click="saveView"
        >
          {{ isSaveAsNew ? "Save as New" : "Update" }}
        </b-button>
      </template>
    </b-modal>

    <!-- Conflict Resolution Modal -->
    <b-modal
      v-model="showConflictModal"
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
                  ? "Yes"
                  : "No"
              }}
            </li>
          </ul>
        </div>

        <div class="conflict-message mb-4">
          <p>{{ conflictInfo.message }}</p>
          <p class="text-muted">
            What would you like to do?
          </p>
        </div>

        <div class="conflict-actions">
          <b-button
            variant="primary"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
            @click="handleConflictResolution('deploy_anyway')"
          >
            <b-spinner
              v-if="
                isResolvingConflict && conflictResolution === 'deploy_anyway'
              "
              small
              class="me-2"
            />
            <i v-else class="pe-7s-plus"></i>
            Deploy Anyway (Create Additional Process Group)
          </b-button>

          <b-button
            variant="danger"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
            @click="handleConflictResolution('delete_and_deploy')"
          >
            <b-spinner
              v-if="
                isResolvingConflict &&
                  conflictResolution === 'delete_and_deploy'
              "
              small
              class="me-2"
            />
            <i v-else class="pe-7s-trash"></i>
            Delete Existing and Deploy New
          </b-button>

          <b-button
            v-if="conflictInfo.existing_process_group.has_version_control"
            variant="info"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
            @click="handleConflictResolution('update_version')"
          >
            <b-spinner
              v-if="
                isResolvingConflict && conflictResolution === 'update_version'
              "
              small
              class="me-2"
            />
            <i v-else class="pe-7s-refresh-2"></i>
            Update to New Version
          </b-button>

          <b-button
            variant="outline-secondary"
            :disabled="isResolvingConflict"
            class="w-100"
            @click="showConflictModal = false"
          >
            Cancel
          </b-button>
        </div>
      </div>
    </b-modal>

    <!-- Deployment Result Modal -->
    <b-modal
      v-model="showResultModal"
      :title="
        deploymentResult.success ? 'Deployment Successful' : 'Deployment Failed'
      "
      size="lg"
      hide-footer
    >
      <div class="deployment-result">
        <div v-if="deploymentResult.success" class="result-success">
          <div class="result-icon success">
            <i class="pe-7s-check"></i>
          </div>
          <h5 class="mb-3">
            Flow Deployed Successfully!
          </h5>

          <div class="result-details">
            <div class="detail-row">
              <span class="label">Flow:</span>
              <strong>{{ deploymentResult.flowName }}</strong>
            </div>
            <div class="detail-row">
              <span class="label">Target:</span>
              <span
                class="badge"
                :class="
                  deploymentResult.target === 'source'
                    ? 'badge-primary'
                    : 'badge-success'
                "
              >
                {{ deploymentResult.target }}
              </span>
            </div>
            <div class="detail-row">
              <span class="label">Instance:</span>
              <span>{{ deploymentResult.instance }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Process Group:</span>
              <code>{{ deploymentResult.processGroupName }}</code>
            </div>
            <div v-if="deploymentResult.processGroupId" class="detail-row">
              <span class="label">Process Group ID:</span>
              <code class="small">{{ deploymentResult.processGroupId }}</code>
            </div>
          </div>
        </div>

        <div v-else class="result-failed">
          <div class="result-icon failed">
            <i class="pe-7s-close"></i>
          </div>
          <h5 class="mb-3">
            Deployment Failed
          </h5>

          <div class="result-details">
            <div class="detail-row">
              <span class="label">Flow:</span>
              <strong>{{ deploymentResult.flowName }}</strong>
            </div>
            <div class="detail-row">
              <span class="label">Target:</span>
              <span
                class="badge"
                :class="
                  deploymentResult.target === 'source'
                    ? 'badge-primary'
                    : 'badge-success'
                "
              >
                {{ deploymentResult.target }}
              </span>
            </div>
            <div class="detail-row">
              <span class="label">Instance:</span>
              <span>{{ deploymentResult.instance }}</span>
            </div>
            <div class="detail-row error">
              <span class="label">Error:</span>
              <span>{{ deploymentResult.error }}</span>
            </div>
          </div>
        </div>

        <div class="result-actions">
          <b-button
            variant="primary"
            class="w-100"
            @click="showResultModal = false"
          >
            <i class="pe-7s-check"></i>
            Close
          </b-button>
        </div>
      </div>
    </b-modal>

    <!-- Error Modal -->
    <b-modal
      v-model="showErrorModal"
      :title="errorTitle"
      size="md"
      hide-footer
    >
      <div class="error-modal-content">
        <div class="result-icon failed">
          <i class="pe-7s-close"></i>
        </div>
        <div class="error-message">
          {{ errorMessage }}
        </div>
        <div class="result-actions mt-3">
          <b-button
            variant="danger"
            class="w-100"
            @click="showErrorModal = false"
          >
            <i class="pe-7s-check"></i>
            Close
          </b-button>
        </div>
      </div>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { apiRequest } from "@/utils/api";

interface TableColumn {
  name: string;
  type: string;
  nullable: boolean;
  primary_key: boolean;
}

interface HierarchyColumn {
  name: string;
  src_column: string;
  dest_column: string;
}

interface TableInfo {
  exists: boolean;
  table_name?: string;
  columns?: TableColumn[];
  hierarchy_columns?: HierarchyColumn[];
  current_hierarchy?: any[];
}

interface ColumnDefinition {
  key: string;
  label: string;
}

interface FlowView {
  id: number;
  name: string;
  description: string | null;
  visible_columns: string[];
  column_widths: Record<string, number> | null;
  is_default: boolean;
  created_by: string | null;
  created_at: string;
  modified_at: string;
}

interface RegistryFlow {
  id: number;
  flow_name: string;
  nifi_instance_name: string;
  bucket_name: string;
}

interface HierarchyAttribute {
  name: string;
  label: string;
  order: number;
}

const isLoading = ref(false);
const tableExists = ref(false);
const hierarchyColumns = ref<HierarchyColumn[]>([]);
const allColumns = ref<TableColumn[]>([]);
const hierarchyValues = ref<Record<string, string[]>>({});
const hierarchyConfig = ref<HierarchyAttribute[]>([]);
const flows = ref<any[]>([]);
const filters = ref<Record<string, string>>({});
const registryFlows = ref<RegistryFlow[]>([]);

// Column visibility
const visibleColumns = ref<Record<string, boolean>>({});
const allAvailableColumns = ref<ColumnDefinition[]>([]);
const columnOrder = ref<string[]>([]); // Store the order of column keys

// Drag and drop state
const draggingIndex = ref<number | null>(null);

// Column resizing state
const columnWidths = ref<Record<string, number>>({});
const resizingColumn = ref<string | null>(null);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);
const isResizing = ref(false);

// View management
const savedViews = ref<FlowView[]>([]);
const showSaveViewModal = ref(false);
const newViewName = ref("");
const newViewDescription = ref("");
const newViewIsDefault = ref(false);
const currentLoadedViewId = ref<number | null>(null);
const isSaveAsNew = ref(false);


const currentPage = ref(1);
const itemsPerPage = ref(10);

const showModal = ref(false);
const selectedFlow = ref<any | null>(null);
const isViewMode = ref(false);

// Quick deploy state
const deployingFlows = ref<Record<string, boolean>>({});
const deploymentSettings = ref<any>(null);
const nifiInstances = ref<any[]>([]);
const processGroupPaths = ref<Record<string, any[]>>({});

// Parameter context management
const sourceNiFiInstanceId = ref<number | null>(null);
const destNiFiInstanceId = ref<number | null>(null);
const sourceParameterContextOptions = ref<Array<{ value: string; text: string }>>([]);
const destParameterContextOptions = ref<Array<{ value: string; text: string }>>([]);

// Conflict resolution
const showConflictModal = ref(false);
const conflictInfo = ref<any>(null);
const currentConflictDeployment = ref<any>(null);
const isResolvingConflict = ref(false);
const conflictResolution = ref<string>("");

// Deployment result
const showResultModal = ref(false);
const deploymentResult = ref({
  success: false,
  flowName: "",
  target: "",
  instance: "",
  processGroupName: "",
  processGroupId: "",
  error: "",
});

// Error modal
const showErrorModal = ref(false);
const errorMessage = ref("");
const errorTitle = ref("");

const modalTitle = computed(() => {
  if (!selectedFlow.value) return "";
  if (isViewMode.value) return "View Flow";
  return selectedFlow.value.id ? "Edit Flow" : "Add New Flow";
});

const templateOptions = computed(() => {
  return [
    { value: null, text: "-- Select Template --" },
    ...registryFlows.value.map((flow) => ({
      value: flow.id,
      text: `${flow.flow_name} (${flow.nifi_instance_name} / ${flow.bucket_name})`,
    })),
  ];
});

const visibleColumnsList = computed(() => {
  const visibleCols = allAvailableColumns.value.filter(
    (col) => visibleColumns.value[col.key],
  );

  // Sort by columnOrder if it exists
  if (columnOrder.value.length > 0) {
    return visibleCols.sort((a, b) => {
      const indexA = columnOrder.value.indexOf(a.key);
      const indexB = columnOrder.value.indexOf(b.key);

      // If not in order array, put at end
      if (indexA === -1) return 1;
      if (indexB === -1) return -1;

      return indexA - indexB;
    });
  }

  return visibleCols;
});

const filteredFlows = computed(() => {
  return flows.value.filter((flow) => {
    // Filter by visible columns only
    for (const col of visibleColumnsList.value) {
      const filterValue = filters.value[col.key];
      if (
        filterValue &&
        !flow[col.key]
          ?.toString()
          .toLowerCase()
          .includes(filterValue.toLowerCase())
      ) {
        return false;
      }
    }
    return true;
  });
});

const totalPages = computed(() => {
  return Math.ceil(filteredFlows.value.length / itemsPerPage.value);
});

const paginationStart = computed(() => {
  return (currentPage.value - 1) * itemsPerPage.value + 1;
});

const paginationEnd = computed(() => {
  return Math.min(
    currentPage.value * itemsPerPage.value,
    filteredFlows.value.length,
  );
});

const paginatedFlows = computed(() => {
  const start = (currentPage.value - 1) * itemsPerPage.value;
  const end = start + itemsPerPage.value;
  return filteredFlows.value.slice(start, end);
});

const viewNameValidation = computed(() => {
  if (!isSaveAsNew.value || !newViewName.value.trim()) {
    return null;
  }
  
  const isDuplicate = savedViews.value.some(
    (view) => view.name.toLowerCase() === newViewName.value.trim().toLowerCase()
  );
  
  return !isDuplicate;
});

const isValidViewName = computed(() => {
  if (!isSaveAsNew.value) {
    // For updates, always valid as we don't change the name
    return true;
  }
  
  // For new views, check if name is not empty and not a duplicate
  return newViewName.value.trim() !== '' && viewNameValidation.value !== false;
});

const loadTableInfo = async () => {
  try {
    const data: TableInfo = await apiRequest("/api/nifi-flows/table-info");
    tableExists.value = data.exists;

    if (data.exists && data.hierarchy_columns) {
      hierarchyColumns.value = data.hierarchy_columns;
      allColumns.value = data.columns || [];

      // Build all available columns
      const cols: ColumnDefinition[] = [];

      // Add hierarchy columns (src and dest)
      for (const col of data.hierarchy_columns) {
        cols.push({ key: col.src_column, label: `Src ${col.name}` });
        cols.push({ key: col.dest_column, label: `Dest ${col.name}` });
      }

      // Add standard columns
      cols.push({ key: "name", label: "Name" });
      cols.push({ key: "contact", label: "Contact" });
      cols.push({ key: "src_connection_param", label: "Src Connection Param" });
      cols.push({ key: "src_template_id", label: "Src Template" });
      cols.push({
        key: "dest_connection_param",
        label: "Dest Connection Param",
      });
      cols.push({ key: "dest_template_id", label: "Dest Template" });
      cols.push({ key: "active", label: "Active" });
      cols.push({ key: "description", label: "Description" });

      allAvailableColumns.value = cols;
      console.log('[INIT] Total columns:', cols.length);

      // Initialize all columns as hidden and filters as empty
      for (const col of cols) {
        visibleColumns.value[col.key] = false;
        filters.value[col.key] = "";
      }
      console.log('[INIT] All columns set to hidden');

      // Load hierarchy values for each attribute
      await loadHierarchyValues();

      // Load registry flows for templates
      await loadRegistryFlows();

      // Load saved views
      await loadViews();
      console.log('[INIT] Loaded views:', savedViews.value.length);
      console.log('[INIT] All views:', savedViews.value.map(v => ({ name: v.name, id: v.id, is_default: v.is_default })));

      // Load default view if exists, otherwise show all columns
      const defaultView = savedViews.value.find((v) => v.is_default);
      
      if (defaultView) {
        loadView(defaultView, false);
      } else {
        // No default view - show all columns
        for (const col of cols) {
          visibleColumns.value[col.key] = true;
        }
      }
    }
  } catch (error) {
    console.error("Error loading table info:", error);
    tableExists.value = false;
  }
};

const loadHierarchyValues = async () => {
  try {
    for (const col of hierarchyColumns.value) {
      const data = await apiRequest(
        `/api/settings/hierarchy/values/${encodeURIComponent(col.name)}`,
      );
      hierarchyValues.value[col.name] = data.values || [];
    }
  } catch (error) {
    console.error("Error loading hierarchy values:", error);
  }
};

const loadHierarchyConfig = async () => {
  try {
    const data = await apiRequest("/api/settings/hierarchy");
    if (data.hierarchy) {
      hierarchyConfig.value = data.hierarchy.sort(
        (a: HierarchyAttribute, b: HierarchyAttribute) => a.order - b.order,
      );
    }
  } catch (error) {
    console.error("Error loading hierarchy config:", error);
  }
};

const loadRegistryFlows = async () => {
  try {
    const flows = await apiRequest("/api/registry-flows/");
    registryFlows.value = flows;
  } catch (error) {
    console.error("Error loading registry flows:", error);
  }
};

const getTemplateName = (templateId: number | null) => {
  if (!templateId) return "None";
  const template = registryFlows.value.find((f) => f.id === templateId);
  return template
    ? `${template.flow_name} (${template.nifi_instance_name})`
    : "Unknown";
};

const loadFlows = async () => {
  if (!tableExists.value) return;

  isLoading.value = true;
  try {
    const data = await apiRequest("/api/nifi-flows/");
    flows.value = data.flows || [];
  } catch (error) {
    console.error("Error loading flows:", error);
    flows.value = [];
  } finally {
    isLoading.value = false;
  }
};

const loadViews = async () => {
  try {
    savedViews.value = await apiRequest("/api/flow-views/");
  } catch (error) {
    console.error("Error loading views:", error);
    savedViews.value = [];
  }
};

const handleSaveView = (saveAsNew: boolean) => {
  isSaveAsNew.value = saveAsNew;

  if (saveAsNew) {
    // Save as new - clear the form
    newViewName.value = "";
    newViewDescription.value = "";
    newViewIsDefault.value = false;
  } else {
    // Save (overwrite) - load current view data
    const currentView = savedViews.value.find(
      (v) => v.id === currentLoadedViewId.value,
    );
    if (currentView) {
      newViewName.value = currentView.name;
      newViewDescription.value = currentView.description || "";
      newViewIsDefault.value = currentView.is_default;
    }
  }

  showSaveViewModal.value = true;
};

const saveView = async () => {
  if (isSaveAsNew.value && !newViewName.value.trim()) {
    alert("Please enter a view name");
    return;
  }

  try {
    // Get visible columns in their current order
    let visibleCols: string[];
    if (columnOrder.value.length > 0) {
      // Start with ordered columns that are visible
      visibleCols = columnOrder.value.filter(
        (key) => visibleColumns.value[key],
      );
      
      // Add any newly checked columns that aren't in columnOrder yet
      const orderedSet = new Set(columnOrder.value);
      const newlyVisible = allAvailableColumns.value
        .filter((col) => visibleColumns.value[col.key] && !orderedSet.has(col.key))
        .map((col) => col.key);
      
      visibleCols = [...visibleCols, ...newlyVisible];
    } else {
      // Fallback to unordered list
      visibleCols = allAvailableColumns.value
        .filter((col) => visibleColumns.value[col.key])
        .map((col) => col.key);
    }

    if (isSaveAsNew.value) {
      // Create new view
      await apiRequest("/api/flow-views/", {
        method: "POST",
        body: JSON.stringify({
          name: newViewName.value.trim(),
          description: newViewDescription.value.trim() || null,
          visible_columns: visibleCols,
          column_widths: columnWidths.value,
          is_default: newViewIsDefault.value,
        }),
      });
      alert("New view saved successfully!");
    } else {
      // Update existing view
      if (currentLoadedViewId.value === null) {
        alert("No view is currently loaded");
        return;
      }

      await apiRequest(`/api/flow-views/${currentLoadedViewId.value}`, {
        method: "PUT",
        body: JSON.stringify({
          name: newViewName.value.trim(),
          description: newViewDescription.value.trim() || null,
          visible_columns: visibleCols,
          column_widths: columnWidths.value,
          is_default: newViewIsDefault.value,
        }),
      });
      alert("View updated successfully!");
    }

    showSaveViewModal.value = false;
    await loadViews();
  } catch (error: any) {
    console.error("Error saving view:", error);
    alert("Error: " + (error.message || "Failed to save view"));
  }
};

const loadView = (view: FlowView, showMessage: boolean = true) => {
  // Get all valid column keys
  const validKeys = new Set(allAvailableColumns.value.map(col => col.key));
  
  // Check for invalid columns in the view
  const invalidColumns = view.visible_columns.filter(key => !validKeys.has(key));
  if (invalidColumns.length > 0) {
    console.warn('Warning: View contains invalid column keys:', invalidColumns);
    console.warn('This view may have been created with old column definitions. Consider recreating the view.');
  }
  
  // Reset all columns to hidden
  for (const col of allAvailableColumns.value) {
    visibleColumns.value[col.key] = false;
  }

  // Show only columns in the view that are valid
  for (const colKey of view.visible_columns) {
    if (validKeys.has(colKey)) {
      visibleColumns.value[colKey] = true;
    }
  }

  // Set the column order from the view (the order in visible_columns array defines the order)
  columnOrder.value = [...view.visible_columns];

  // Load column widths
  if (view.column_widths) {
    columnWidths.value = { ...view.column_widths };
  } else {
    columnWidths.value = {};
  }

  // Set the current loaded view ID
  currentLoadedViewId.value = view.id;

  if (showMessage) {
    alert(`Loaded view: ${view.name}`);
  }
};

const setDefaultView = async (viewId: number) => {
  try {
    await apiRequest(`/api/flow-views/${viewId}/set-default`, {
      method: "POST",
    });
    alert("Default view updated!");
    await loadViews();
  } catch (error: any) {
    console.error("Error setting default view:", error);
    alert("Error: " + (error.message || "Failed to set default view"));
  }
};

const deleteView = async (viewId: number) => {
  if (!confirm("Are you sure you want to delete this view?")) {
    return;
  }

  try {
    await apiRequest(`/api/flow-views/${viewId}`, { method: "DELETE" });
    alert("View deleted successfully!");
    await loadViews();
  } catch (error: any) {
    console.error("Error deleting view:", error);
    alert("Error: " + (error.message || "Failed to delete view"));
  }
};

const handleSetAsDefault = async () => {
  if (currentLoadedViewId.value === null) {
    alert("No view is currently loaded");
    return;
  }
  await setDefaultView(currentLoadedViewId.value);
};

const deselectAllColumns = () => {
  for (const col of allAvailableColumns.value) {
    visibleColumns.value[col.key] = false;
  }
  onColumnToggle();
};

const onColumnToggle = () => {
  // Reset filters for hidden columns
  for (const col of allAvailableColumns.value) {
    if (!visibleColumns.value[col.key]) {
      filters.value[col.key] = "";
    }
  }
};

const clearFilters = () => {
  for (const col of visibleColumnsList.value) {
    filters.value[col.key] = "";
  }
};

// Drag and drop handlers
const handleDragStart = (index: number, event: DragEvent) => {
  draggingIndex.value = index;
  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
  }
};

const handleDragOver = (event: DragEvent) => {
  event.preventDefault();
  if (event.dataTransfer) {
    event.dataTransfer.dropEffect = "move";
  }
};

const handleDrop = (dropIndex: number) => {
  if (draggingIndex.value === null || draggingIndex.value === dropIndex) {
    return;
  }

  // Reorder the columns
  const newOrder = [...visibleColumnsList.value.map((col) => col.key)];
  const [draggedItem] = newOrder.splice(draggingIndex.value, 1);
  newOrder.splice(dropIndex, 0, draggedItem);

  // Update columnOrder with the new order
  columnOrder.value = newOrder;
};

const handleDragEnd = () => {
  draggingIndex.value = null;
};

// Column resizing handlers
const startResize = (columnKey: string, event: MouseEvent) => {
  isResizing.value = true;
  resizingColumn.value = columnKey;
  resizeStartX.value = event.pageX;

  // Get current width or default
  const th = (event.target as HTMLElement)
    .parentElement as HTMLTableCellElement;
  resizeStartWidth.value = th.offsetWidth;

  // Add event listeners for mouse move and mouse up
  document.addEventListener("mousemove", handleResize);
  document.addEventListener("mouseup", stopResize);

  // Prevent text selection during resize
  document.body.style.userSelect = "none";
  document.body.style.cursor = "col-resize";
};

const handleResize = (event: MouseEvent) => {
  if (resizingColumn.value === null) return;

  event.preventDefault();

  const diff = event.pageX - resizeStartX.value;
  const newWidth = Math.max(50, resizeStartWidth.value + diff); // Min width of 50px

  columnWidths.value[resizingColumn.value] = newWidth;
};

const stopResize = () => {
  isResizing.value = false;
  resizingColumn.value = null;
  document.removeEventListener("mousemove", handleResize);
  document.removeEventListener("mouseup", stopResize);
  document.body.style.userSelect = "";
  document.body.style.cursor = "";
};

const handleAddFlow = () => {
  const newFlow: any = {
    id: 0,
    name: "",
    contact: "",
    src_connection_param: "",
    dest_connection_param: "",
    src_template_id: null,
    dest_template_id: null,
    active: true,
    description: "",
    creator_name: "",
  };

  // Add hierarchy fields (src and dest for each)
  for (const col of hierarchyColumns.value) {
    newFlow[col.src_column] = "";
    newFlow[col.dest_column] = "";
  }

  selectedFlow.value = newFlow;
  isViewMode.value = false;
  showModal.value = true;
};

const handleEdit = async (flow: any) => {
  selectedFlow.value = { ...flow };
  isViewMode.value = false;
  showModal.value = true;

  // Load parameter contexts after setting the flow
  await updateSourceParameterContexts();
  await updateDestParameterContexts();
};

const handleView = async (flow: any) => {
  selectedFlow.value = { ...flow };
  isViewMode.value = true;
  showModal.value = true;

  // Load parameter contexts after setting the flow
  await updateSourceParameterContexts();
  await updateDestParameterContexts();
};

const handleRemove = async (flow: any) => {
  const identifier = hierarchyColumns.value
    .map((col) => `${flow[col.src_column]} → ${flow[col.dest_column]}`)
    .join(" / ");
  if (confirm(`Are you sure you want to remove flow "${identifier}"?`)) {
    try {
      await apiRequest(`/api/nifi-flows/${flow.id}`, { method: "DELETE" });
      alert("Flow deleted successfully!");
      await loadFlows();
    } catch (error: any) {
      console.error("Error removing flow:", error);
      alert("Error: " + (error.message || "Failed to remove flow"));
    }
  }
};

const handleCopy = async (flow: any) => {
  try {
    // Create a copy of the flow with active set to false
    const copiedFlow = { ...flow };
    delete copiedFlow.id;
    delete copiedFlow.created_at;
    delete copiedFlow.modified_at;
    copiedFlow.active = false;

    // Open the edit modal with the copied flow data
    selectedFlow.value = copiedFlow;
    isViewMode.value = false;
    showModal.value = true;
  } catch (error: any) {
    console.error("Error copying flow:", error);
    alert("Error: " + (error.message || "Failed to copy flow"));
  }
};

// Parameter context functions
const findNiFiInstanceByHierarchyValue = (hierarchyValue: string, hierarchyAttr: string): number | null => {
  if (!hierarchyValue || !hierarchyAttr || !nifiInstances.value || nifiInstances.value.length === 0) {
    return null;
  }

  // Find the instance that matches BOTH the hierarchy attribute and value
  const instance = nifiInstances.value.find(
    (inst) =>
      inst.hierarchy_attribute === hierarchyAttr &&
      inst.hierarchy_value === hierarchyValue
  );

  return instance ? instance.id : null;
};

const loadParameterContexts = async (instanceId: number, isSource: boolean) => {
  if (!instanceId) {
    if (isSource) {
      sourceParameterContextOptions.value = [{ value: "", text: "Select a parameter context..." }];
    } else {
      destParameterContextOptions.value = [{ value: "", text: "Select a parameter context..." }];
    }
    return;
  }

  try {
    const data = await apiRequest(`/api/nifi-instances/${instanceId}/get-parameters`);

    const options = [
      { value: "", text: "Select a parameter context..." },
      { value: "None", text: "None (no parameter context)" },
      ...data.parameter_contexts.map((pc: any) => ({
        value: pc.name,
        text: pc.name,
      })),
    ];

    if (isSource) {
      sourceParameterContextOptions.value = options;
    } else {
      destParameterContextOptions.value = options;
    }
  } catch (error) {
    console.error(`Error loading parameter contexts for instance ${instanceId}:`, error);
    const fallbackOptions = [
      { value: "", text: "Error loading parameter contexts" },
      { value: "None", text: "None (no parameter context)" }
    ];
    if (isSource) {
      sourceParameterContextOptions.value = fallbackOptions;
    } else {
      destParameterContextOptions.value = fallbackOptions;
    }
  }
};

const updateSourceParameterContexts = async () => {
  if (!selectedFlow.value || !hierarchyColumns.value.length) return;

  // Get the top hierarchy attribute (first in the list)
  const topHierarchyColumn = hierarchyColumns.value[0];
  const sourceHierarchyValue = selectedFlow.value[topHierarchyColumn.src_column];

  if (!sourceHierarchyValue) {
    sourceNiFiInstanceId.value = null;
    sourceParameterContextOptions.value = [{ value: "", text: "Select source hierarchy value first" }];
    return;
  }

  // Load NiFi instances if not already loaded
  if (nifiInstances.value.length === 0) {
    try {
      const data = await apiRequest("/api/nifi-instances/");
      nifiInstances.value = data;
    } catch (error) {
      console.error("Error loading NiFi instances:", error);
      sourceParameterContextOptions.value = [{ value: "", text: "Error loading NiFi instances" }];
      return;
    }
  }

  const instanceId = findNiFiInstanceByHierarchyValue(sourceHierarchyValue, topHierarchyColumn.name);
  sourceNiFiInstanceId.value = instanceId;

  if (instanceId) {
    await loadParameterContexts(instanceId, true);
  } else {
    sourceParameterContextOptions.value = [{ value: "", text: `No NiFi instance found for ${topHierarchyColumn.name}=${sourceHierarchyValue}` }];
  }
};

const updateDestParameterContexts = async () => {
  if (!selectedFlow.value || !hierarchyColumns.value.length) return;

  // Get the top hierarchy attribute (first in the list)
  const topHierarchyColumn = hierarchyColumns.value[0];
  const destHierarchyValue = selectedFlow.value[topHierarchyColumn.dest_column];

  if (!destHierarchyValue) {
    destNiFiInstanceId.value = null;
    destParameterContextOptions.value = [{ value: "", text: "Select destination hierarchy value first" }];
    return;
  }

  // Load NiFi instances if not already loaded
  if (nifiInstances.value.length === 0) {
    try {
      const data = await apiRequest("/api/nifi-instances/");
      nifiInstances.value = data;
    } catch (error) {
      console.error("Error loading NiFi instances:", error);
      destParameterContextOptions.value = [{ value: "", text: "Error loading NiFi instances" }];
      return;
    }
  }

  const instanceId = findNiFiInstanceByHierarchyValue(destHierarchyValue, topHierarchyColumn.name);
  destNiFiInstanceId.value = instanceId;

  if (instanceId) {
    await loadParameterContexts(instanceId, false);
  } else {
    destParameterContextOptions.value = [{ value: "", text: `No NiFi instance found for ${topHierarchyColumn.name}=${destHierarchyValue}` }];
  }
};

// Quick deploy functions
const handleQuickDeploySource = async (flow: any) => {
  await quickDeploy(flow, "source");
};

const handleQuickDeployDest = async (flow: any) => {
  await quickDeploy(flow, "destination");
};

const quickDeploy = async (flow: any, target: "source" | "destination") => {
  const deployKey = `${flow.id}-${target === "source" ? "source" : "dest"}`;
  deployingFlows.value[deployKey] = true;

  try {
    // Get hierarchy value for top level (instance identifier)
    const topHierarchy = hierarchyColumns.value[0];
    const prefix = target === "source" ? "src_" : "dest_";
    const hierarchyValue = flow[`${prefix}${topHierarchy.name.toLowerCase()}`];

    // Get instance ID
    const instanceId = await getInstanceIdForHierarchyValue(
      hierarchyValue,
      topHierarchy.name,
    );
    if (!instanceId) {
      throw new Error(
        `No NiFi instance found for ${topHierarchy.name}=${hierarchyValue}`,
      );
    }

    // Get process group path using auto-selection logic
    const processGroupPath = await autoSelectProcessGroupForFlow(
      flow,
      target,
      instanceId,
      hierarchyValue,
    );
    if (!processGroupPath) {
      throw new Error(
        "Could not auto-select process group. Please use the full deployment wizard.",
      );
    }

    // Generate process group name
    const processGroupName = generateProcessGroupNameForFlow(flow, target);

    // Get template ID
    const templateId =
      target === "source" ? flow.src_template_id : flow.dest_template_id;
    if (!templateId) {
      throw new Error("No template configured for this flow");
    }

    // Get last hierarchy attribute for RouteOnAttribute processor
    const lastHierarchyAttr = hierarchyConfig.value.length > 0 
      ? hierarchyConfig.value[hierarchyConfig.value.length - 1].name 
      : null;

    // Get parameter context name for this deployment
    const parameterContextName = target === "source" ? flow.src_connection_param : flow.dest_connection_param;

    // Deploy using parent_process_group_path (will auto-create missing groups)
    // Use all deployment settings from database defaults
    const deploymentRequest: any = {
      template_id: templateId,
      parent_process_group_path: processGroupPath,
      process_group_name: processGroupName,
      version: null,
      x_position: 0,
      y_position: 0,
      stop_versioning_after_deploy: deploymentSettings.value?.global?.stop_versioning_after_deploy || false,
      disable_after_deploy: deploymentSettings.value?.global?.disable_after_deploy || false,
      start_after_deploy: deploymentSettings.value?.global?.start_after_deploy || false,
      parameter_context_name: parameterContextName,
    };

    // Add hierarchy attribute if available
    if (lastHierarchyAttr) {
      deploymentRequest.hierarchy_attribute = lastHierarchyAttr;
    }

    try {
      const result = await apiRequest(`/api/deploy/${instanceId}/flow`, {
        method: "POST",
        body: JSON.stringify(deploymentRequest),
      });

      if (result.status === "success") {
        // Show success modal
        deploymentResult.value = {
          success: true,
          flowName: getFlowIdentifier(flow),
          target,
          instance: hierarchyValue,
          processGroupName: result.process_group_name,
          processGroupId: result.process_group_id || "",
          error: "",
        };
        showResultModal.value = true;
      } else {
        throw new Error(result.message || "Deployment failed");
      }
    } catch (apiError: any) {
      // Check if it's a 409 Conflict (process group already exists)
      if (apiError.status === 409 && apiError.detail) {
        // Store conflict info and show modal
        conflictInfo.value = apiError.detail;
        currentConflictDeployment.value = {
          flow,
          target,
          instanceId,
          hierarchyValue,
          processGroupName,
          deploymentRequest,
        };
        showConflictModal.value = true;
      } else {
        throw apiError;
      }
    }
  } catch (error: any) {
    console.error(`Error deploying to ${target}:`, error);

    // Get flow identifier
    const flowIdentifier = hierarchyColumns.value
      .map(
        (col) =>
          `${flow[`src_${col.name.toLowerCase()}`]} → ${flow[`dest_${col.name.toLowerCase()}`]}`,
      )
      .join(" / ");

    // Show error modal
    deploymentResult.value = {
      success: false,
      flowName: flowIdentifier,
      target,
      instance:
        flow[
          `${target === "source" ? "src_" : "dest_"}${hierarchyColumns.value[0]?.name.toLowerCase()}`
        ] || "",
      processGroupName: "",
      processGroupId: "",
      error: error.message || "Unknown error",
    };
    showResultModal.value = true;
  } finally {
    deployingFlows.value[deployKey] = false;
  }
};

const getFlowIdentifier = (flow: any) => {
  // Build source path
  const sourceParts = hierarchyColumns.value
    .map((col) => {
      const value = flow[`src_${col.name.toLowerCase()}`];
      return `${col.name} → ${value}`;
    })
    .join(" / ");

  // Build destination path
  const destParts = hierarchyColumns.value
    .map((col) => {
      const value = flow[`dest_${col.name.toLowerCase()}`];
      return `${col.name} → ${value}`;
    })
    .join(" / ");

  return `Source: ${sourceParts} | Destination: ${destParts}`;
};

const handleConflictResolution = async (resolution: string) => {
  conflictResolution.value = resolution;
  isResolvingConflict.value = true;

  try {
    const {
      flow,
      target,
      instanceId,
      hierarchyValue,
      processGroupName,
      deploymentRequest,
    } = currentConflictDeployment.value;
    const existingPgId = conflictInfo.value.existing_process_group.id;

    if (resolution === "deploy_anyway") {
      // Deploy anyway - clear the process_group_name to let NiFi use default name
      const modifiedRequest = {
        ...deploymentRequest,
        process_group_name: null,
      };

      const result = await apiRequest(`/api/deploy/${instanceId}/flow`, {
        method: "POST",
        body: JSON.stringify(modifiedRequest),
      });

      if (result.status === "success") {
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;

        // Show success modal
        deploymentResult.value = {
          success: true,
          flowName: getFlowIdentifier(flow),
          target,
          instance: hierarchyValue,
          processGroupName: result.process_group_name,
          processGroupId: result.process_group_id || "",
          error: "",
        };
        showResultModal.value = true;
      }
    } else if (resolution === "delete_and_deploy") {
      // Delete existing process group first
      await apiRequest(
        `/api/nifi-instances/${instanceId}/process-group/${existingPgId}`,
        {
          method: "DELETE",
        },
      );

      // Then deploy new one
      const result = await apiRequest(`/api/deploy/${instanceId}/flow`, {
        method: "POST",
        body: JSON.stringify(deploymentRequest),
      });

      if (result.status === "success") {
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;

        // Show success modal
        deploymentResult.value = {
          success: true,
          flowName: getFlowIdentifier(flow),
          target,
          instance: hierarchyValue,
          processGroupName: result.process_group_name,
          processGroupId: result.process_group_id || "",
          error: "",
        };
        showResultModal.value = true;
      }
    } else if (resolution === "update_version") {
      // Update existing process group to new version
      const updateRequest = {
        version: deploymentRequest.version,
      };

      const result = await apiRequest(
        `/api/nifi-instances/${instanceId}/process-group/${existingPgId}/update-version`,
        {
          method: "POST",
          body: JSON.stringify(updateRequest),
        },
      );

      if (result.status === "success") {
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;

        // Show success modal
        deploymentResult.value = {
          success: true,
          flowName: getFlowIdentifier(flow),
          target,
          instance: hierarchyValue,
          processGroupName: processGroupName,
          processGroupId: existingPgId,
          error: "",
        };
        showResultModal.value = true;
      }
    }
  } catch (error: any) {
    console.error("Conflict resolution failed:", error);

    // Show error modal
    const { flow, target, hierarchyValue } = currentConflictDeployment.value;
    deploymentResult.value = {
      success: false,
      flowName: getFlowIdentifier(flow),
      target,
      instance: hierarchyValue,
      processGroupName: "",
      processGroupId: "",
      error: error.message || error.detail || "Unknown error",
    };
    showConflictModal.value = false;
    showResultModal.value = true;
  } finally {
    isResolvingConflict.value = false;
    conflictResolution.value = "";

    // Clear deploying flag
    if (currentConflictDeployment.value) {
      const { flow, target } = currentConflictDeployment.value;
      const deployKey = `${flow.id}-${target === "source" ? "source" : "dest"}`;
      deployingFlows.value[deployKey] = false;
    }
  }
};

const getInstanceIdForHierarchyValue = async (
  hierarchyValue: string,
  hierarchyAttr: string,
): Promise<number | null> => {
  try {
    if (nifiInstances.value.length === 0) {
      const data = await apiRequest("/api/nifi-instances/");
      nifiInstances.value = data;
    }

    const instance = nifiInstances.value.find(
      (inst) =>
        inst.hierarchy_attribute === hierarchyAttr &&
        inst.hierarchy_value === hierarchyValue,
    );

    return instance ? instance.id : null;
  } catch (error) {
    console.error("Error getting instance ID:", error);
    return null;
  }
};

const autoSelectProcessGroupForFlow = async (
  flow: any,
  target: "source" | "destination",
  instanceId: number,
  cacheKey: string,
): Promise<string | null> => {
  try {
    // Load deployment settings if not already loaded
    if (!deploymentSettings.value) {
      const data = await apiRequest("/api/settings/deploy");
      const paths: {
        [key: number]: { source_path?: string; dest_path?: string };
      } = {};
      if (data.paths) {
        Object.keys(data.paths).forEach((key) => {
          const numKey = parseInt(key, 10);
          paths[numKey] = data.paths[key];
        });
      }
      deploymentSettings.value = {
        global: data.global,
        paths: paths,
      };
    }

    // Get configured base path from settings
    if (
      !deploymentSettings.value.paths ||
      !deploymentSettings.value.paths[instanceId]
    ) {
      console.error("No deployment paths configured for this instance");
      return null;
    }

    const pathConfig =
      target === "source"
        ? deploymentSettings.value.paths[instanceId].source_path
        : deploymentSettings.value.paths[instanceId].dest_path;

    if (!pathConfig) {
      console.error(`No ${target} path configured for instance ${instanceId}`);
      return null;
    }

    // Extract base path string from config
    // Support both new format (object with path property) and legacy format (string ID)
    let basePathString: string;
    if (typeof pathConfig === "object" && pathConfig.path) {
      basePathString = pathConfig.path;
    } else {
      console.error("Invalid path configuration format");
      return null;
    }

    // Build full path: base_path + hierarchy_attributes (middle levels only)
    const pathParts = basePathString.split("/").filter((s) => s.trim());

    // Get hierarchy attributes (skip first and last)
    // First level is already in base path, last level is the flow name itself
    const prefix = target === "source" ? "src_" : "dest_";

    for (let i = 1; i < hierarchyColumns.value.length - 1; i++) {
      const attrName = hierarchyColumns.value[i].name.toLowerCase();
      const value = flow[`${prefix}${attrName}`];
      if (value) {
        pathParts.push(value);
      }
    }

    // Return the full path string
    const fullPath = pathParts.join("/");
    console.log(
      `Built deployment path for ${target}: ${fullPath}`,
    );

    return fullPath;
  } catch (error) {
    console.error("Error in autoSelectProcessGroupForFlow:", error);
    return null;
  }
};

const generateProcessGroupNameForFlow = (
  flow: any,
  target: "source" | "destination",
): string => {
  const template =
    deploymentSettings.value?.global?.process_group_name_template ||
    "{last_hierarchy_value}";
  const prefix = target === "source" ? "src_" : "dest_";
  const hierarchyValues: string[] = [];

  for (let i = 0; i < hierarchyColumns.value.length; i++) {
    const attrName = hierarchyColumns.value[i].name.toLowerCase();
    const value = flow[`${prefix}${attrName}`] || "";
    hierarchyValues.push(value);
  }

  let result = template;

  if (hierarchyValues.length > 0) {
    result = result.replace(/{first_hierarchy_value}/g, hierarchyValues[0]);
  }

  if (hierarchyValues.length > 0) {
    result = result.replace(
      /{last_hierarchy_value}/g,
      hierarchyValues[hierarchyValues.length - 1],
    );
  }

  for (let i = 0; i < hierarchyValues.length; i++) {
    const placeholder = `{${i + 1}_hierarchy_value}`;
    result = result.replace(
      new RegExp(placeholder.replace(/[{}]/g, "\\$&"), "g"),
      hierarchyValues[i],
    );
  }

  return result;
};

const handleModalOk = async () => {
  if (!selectedFlow.value) return;

  try {
    // Build hierarchy values with source and destination for each attribute
    const hierarchyValues: Record<
      string,
      { source: string; destination: string }
    > = {};
    for (const col of hierarchyColumns.value) {
      hierarchyValues[col.name] = {
        source: selectedFlow.value[col.src_column] || "",
        destination: selectedFlow.value[col.dest_column] || "",
      };
    }

    const payload = {
      hierarchy_values: hierarchyValues,
      name: selectedFlow.value.name,
      contact: selectedFlow.value.contact,
      src_connection_param: selectedFlow.value.src_connection_param,
      dest_connection_param: selectedFlow.value.dest_connection_param,
      src_template_id: selectedFlow.value.src_template_id,
      dest_template_id: selectedFlow.value.dest_template_id,
      active: selectedFlow.value.active,
      description: selectedFlow.value.description,
      creator_name: selectedFlow.value.creator_name || "admin",
    };

    if (selectedFlow.value.id) {
      // Update existing flow
      await apiRequest(`/api/nifi-flows/${selectedFlow.value.id}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      showModal.value = false;
      await loadFlows();
    } else {
      // Create new flow
      await apiRequest("/api/nifi-flows/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      showModal.value = false;
      await loadFlows();
    }
  } catch (error: any) {
    console.error("Error saving flow:", error);
    errorTitle.value = "Failed to Save Flow";
    errorMessage.value = error.message || "An unknown error occurred while saving the flow. Please try again.";
    showErrorModal.value = true;
  }
};

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--;
  }
};

const nextPage = () => {
  if (currentPage.value < totalPages.value) {
    currentPage.value++;
  }
};

// Watch for changes in top hierarchy values to update parameter contexts
watch(() => {
  if (!selectedFlow.value || !hierarchyColumns.value.length) return null;
  const topHierarchyColumn = hierarchyColumns.value[0];
  return selectedFlow.value[topHierarchyColumn.src_column];
}, async (newValue) => {
  if (newValue) {
    await updateSourceParameterContexts();
  }
});

watch(() => {
  if (!selectedFlow.value || !hierarchyColumns.value.length) return null;
  const topHierarchyColumn = hierarchyColumns.value[0];
  return selectedFlow.value[topHierarchyColumn.dest_column];
}, async (newValue) => {
  if (newValue) {
    await updateDestParameterContexts();
  }
});

onMounted(async () => {
  await loadTableInfo();
  await loadFlows();
  await loadHierarchyConfig();
});
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
        transition:
          background 0.2s,
          transform 0.2s;

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
            content: "";
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

// Conflict Modal (reuse from Deploy.vue)
.conflict-modal {
  .conflict-details {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 8px;
    margin-bottom: 20px;

    h6 {
      margin-bottom: 10px;
      font-weight: 600;
    }

    ul {
      margin: 0;
      padding-left: 20px;

      li {
        margin-bottom: 8px;
      }
    }

    code {
      background: #e9ecef;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.875rem;
    }
  }

  .conflict-actions {
    .btn {
      text-align: left;
      display: flex;
      align-items: center;
      gap: 8px;

      i {
        font-size: 1.2rem;
      }
    }
  }
}

// Deployment Result Modal
.deployment-result {
  text-align: center;

  .result-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    margin: 0 auto 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;

    &.success {
      background: #d4edda;
      color: #28a745;
    }

    &.failed {
      background: #f8d7da;
      color: #dc3545;
    }
  }

  .result-details {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    text-align: left;

    .detail-row {
      display: flex;
      gap: 10px;
      margin-bottom: 12px;
      font-size: 14px;

      &:last-child {
        margin-bottom: 0;
      }

      .label {
        font-weight: 600;
        color: #6c757d;
        min-width: 140px;
      }

      &.error {
        color: #dc3545;

        .label {
          color: #dc3545;
        }
      }

      code {
        background: #e9ecef;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 13px;
        color: #007bff;

        &.small {
          font-size: 11px;
        }
      }

      .badge {
        padding: 4px 10px;
        font-size: 12px;
        border-radius: 4px;

        &.badge-primary {
          background: #007bff;
          color: white;
        }

        &.badge-success {
          background: #28a745;
          color: white;
        }
      }
    }
  }

  .result-actions {
    margin-top: 20px;
  }
}

// Error Modal
.error-modal-content {
  text-align: center;

  .result-icon {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    margin: 0 auto 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 40px;

    &.failed {
      background: #f8d7da;
      color: #dc3545;
    }
  }

  .error-message {
    background: #f8f9fa;
    border-radius: 8px;
    padding: 20px;
    margin: 20px 0;
    text-align: left;
    color: #dc3545;
    font-size: 14px;
    line-height: 1.6;
  }
}

// Dropdown Styles
.columns-dropdown-menu {
  min-width: 500px !important;
  width: 500px !important;
}

.columns-dropdown {
  :deep(.dropdown-menu) {
    min-width: 500px !important;
    width: 500px !important;
  }
}

.column-dropdown-form {
  padding: 0.5rem 1rem;
  max-height: 400px;
  overflow-y: auto;
  width: 100%;
  min-width: 500px;
}

.column-checkbox-compact {
  margin-bottom: 0.25rem;
  font-size: 0.875rem;
  
  &:last-child {
    margin-bottom: 0;
  }

  :deep(.form-check-input) {
    margin-top: 0.15em;
  }

  :deep(.form-check-label) {
    padding-left: 0.25rem;
  }
}

.column-checkbox-item {
  padding: 0 !important;

  label {
    margin: 0;
    padding: 0.5rem 1rem;
    display: block;
    width: 100%;
    cursor: pointer;
  }
}

.saved-views-list {
  padding: 0;
  margin: 0;
}

.view-item-custom {
  padding: 0.35rem 1rem;
  font-size: 0.875rem;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: space-between;
  transition: background-color 0.15s;

  &:hover {
    background-color: rgba(0, 0, 0, 0.05);
  }

  .view-name {
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    flex: 1;
    text-align: left;
  }

  .delete-btn {
    opacity: 0;
    transition: opacity 0.2s;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  &:hover .delete-btn {
    opacity: 1;
  }
}

.view-item {
  padding: 0.15rem 1rem;
  font-size: 0.875rem;
  text-align: left;

  .view-item-content {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
  }

  .view-name {
    font-size: 0.875rem;
    display: flex;
    align-items: center;
    gap: 0.25rem;
    flex: 1;
    text-align: left;
  }

  .delete-btn {
    opacity: 0;
    transition: opacity 0.2s;
    font-size: 0.875rem;
    flex-shrink: 0;
  }

  &:hover .delete-btn {
    opacity: 1;
  }
}

.views-header {
  font-size: 0.75rem;
  font-weight: 600;
  color: #6c757d;
  padding: 0.5rem 1rem 0.25rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0;
}
</style>

<style lang="scss">
// Global styles for dropdown menu (unscoped to avoid specificity issues)
.columns-dropdown-menu {
  min-width: 300px !important;
  width: 300px !important;
}

.views-dropdown {
  .dropdown-header {
    border-bottom: none !important;
  }

  .dropdown-menu {
    .dropdown-item {
      border: none !important;
      border-top: none !important;
      border-bottom: none !important;
    }
  }

  .dropdown-item.view-item {
    padding: 0.15rem 1rem !important;
    text-align: left !important;
    display: block !important;
    border: none !important;
    margin: 0 !important;
  }

  .dropdown-item.view-item::before,
  .dropdown-item.view-item::after {
    display: none !important;
  }

  .dropdown-item + .dropdown-item {
    border-top: none !important;
    margin-top: 0 !important;
  }
}
</style>
