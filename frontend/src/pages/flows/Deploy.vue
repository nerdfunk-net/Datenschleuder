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
            :class="{
              active: currentStep === index,
              completed: currentStep > index,
            }"
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
                  {{ flow[col.key] || "-" }}
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
          <b-button
            variant="outline-secondary"
            @click="$router.push('/flows/manage')"
          >
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
          <div
            v-for="flow in selectedFlowObjects"
            :key="flow.id"
            class="target-card"
          >
            <div class="target-header">
              <h5>{{ getFlowName(flow) }}</h5>
              <span class="text-muted"
                >{{ flow.source }} → {{ flow.destination }}</span
              >
            </div>

            <div class="target-body">
              <div class="hierarchy-info">
                <div class="hierarchy-item">
                  <span class="label"
                    >Top Hierarchy ({{ topHierarchyName }}):</span
                  >
                  <span class="value-badge source"
                    >Source: {{ getTopHierarchyValue(flow, "source") }}</span
                  >
                  <span class="value-badge dest"
                    >Dest: {{ getTopHierarchyValue(flow, "destination") }}</span
                  >
                </div>
              </div>

              <div class="deployment-options">
                <label class="option-label">Deploy to:</label>
                <div class="option-buttons">
                  <b-button
                    :variant="
                      getDeploymentTarget(flow.id) === 'source'
                        ? 'primary'
                        : 'outline-primary'
                    "
                    @click="setDeploymentTarget(flow.id, 'source')"
                    class="target-btn"
                  >
                    <i class="pe-7s-angle-right-circle"></i>
                    Source ({{ getTopHierarchyValue(flow, "source") }})
                  </b-button>
                  <b-button
                    :variant="
                      getDeploymentTarget(flow.id) === 'destination'
                        ? 'primary'
                        : 'outline-primary'
                    "
                    @click="setDeploymentTarget(flow.id, 'destination')"
                    class="target-btn"
                  >
                    <i class="pe-7s-angle-left-circle"></i>
                    Destination ({{
                      getTopHierarchyValue(flow, "destination")
                    }})
                  </b-button>
                  <b-button
                    :variant="
                      getDeploymentTarget(flow.id) === 'both'
                        ? 'primary'
                        : 'outline-primary'
                    "
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
          <p class="text-muted">
            Select the target process group for each deployment
          </p>
        </div>

        <div v-if="isLoadingPaths" class="text-center py-5">
          <b-spinner variant="primary"></b-spinner>
          <p class="mt-3 text-muted">Loading process groups...</p>
        </div>

        <div v-else class="process-group-selection">
          <div
            v-for="deployment in deploymentConfigs"
            :key="deployment.key"
            class="pg-card"
          >
            <div class="pg-header">
              <h5>{{ deployment.flowName }}</h5>
              <span class="text-muted">
                <i
                  :class="
                    deployment.target === 'source'
                      ? 'pe-7s-angle-right-circle'
                      : 'pe-7s-angle-left-circle'
                  "
                ></i>
                {{ deployment.target === "source" ? "Source" : "Destination" }}
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

              <div
                v-if="deployment.selectedProcessGroupId"
                class="selected-info"
              >
                <i class="pe-7s-check text-success"></i>
                <span
                  >Selected:
                  <strong>{{
                    getSelectedPathDisplay(deployment)
                  }}</strong></span
                >
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
            Next: Settings
            <i class="pe-7s-angle-right"></i>
          </b-button>
        </div>
      </div>

      <!-- Step 4: Settings -->
      <div v-if="currentStep === 3" class="wizard-content">
        <div class="step-header">
          <h3>Step 4: Deployment Settings</h3>
          <p class="text-muted">
            Configure deployment parameters (leave as default or override)
          </p>
        </div>

        <div class="settings-form">
          <!-- Process Group Name Template -->
          <div class="form-group">
            <label class="form-label">Process Group Name Template</label>
            <b-form-input
              v-model="deploymentSettings.global.process_group_name_template"
              placeholder="{last_hierarchy_value}"
            />
            <small class="form-text text-muted">
              Default: {last_hierarchy_value} - Use the value of the last
              hierarchy attribute (e.g., CN value)
            </small>
          </div>

          <!-- Disable After Deploy -->
          <div class="form-group">
            <b-form-checkbox v-model="deploymentSettings.global.disable_after_deploy">
              Disable flow after deployment
            </b-form-checkbox>
            <small class="form-text text-muted d-block">
              If enabled, the deployed process group will be DISABLED (locked) after deployment.
              Note: NiFi deploys flows in STOPPED state by default. This setting goes further
              to DISABLE them, preventing accidental starting.
            </small>
          </div>

          <!-- Stop Versioning After Deploy -->
          <div class="form-group">
            <b-form-checkbox v-model="deploymentSettings.global.stop_versioning_after_deploy">
              Stop versioning after deployment
            </b-form-checkbox>
            <small class="form-text text-muted d-block">
              If enabled, version control will be stopped for the deployed process group
            </small>
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
          >
            Next: Review & Deploy
            <i class="pe-7s-angle-right"></i>
          </b-button>
        </div>
      </div>

      <!-- Step 5: Review & Deploy -->
      <div v-if="currentStep === 4" class="wizard-content">
        <div class="step-header">
          <h3>Step 5: Review & Deploy</h3>
          <p class="text-muted">
            Review your deployment configuration before proceeding
          </p>
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
            <h5>Deployment Settings</h5>
            <div class="review-card settings-card">
              <div class="review-card-body">
                <div class="review-row">
                  <span class="review-label">Process Group Name Template:</span>
                  <span class="final-pg-name">{{ deploymentSettings.global.process_group_name_template }}</span>
                </div>
                <div class="review-row">
                  <span class="review-label">Disable After Deploy:</span>
                  <span>
                    <i :class="deploymentSettings.global.disable_after_deploy ? 'pe-7s-check text-success' : 'pe-7s-close text-muted'"></i>
                    {{ deploymentSettings.global.disable_after_deploy ? "Yes" : "No" }}
                  </span>
                </div>
                <div class="review-row">
                  <span class="review-label">Stop Versioning After Deploy:</span>
                  <span>
                    <i :class="deploymentSettings.global.stop_versioning_after_deploy ? 'pe-7s-check text-success' : 'pe-7s-close text-muted'"></i>
                    {{ deploymentSettings.global.stop_versioning_after_deploy ? "Yes" : "No" }}
                  </span>
                </div>
              </div>
            </div>

            <h5 class="mt-4">Deployment Details</h5>
            <div
              v-for="deployment in deploymentConfigs"
              :key="deployment.key"
              class="review-card"
            >
              <div class="review-card-header">
                <strong>{{ deployment.flowName }}</strong>
                <span
                  class="badge"
                  :class="
                    deployment.target === 'source'
                      ? 'badge-primary'
                      : 'badge-success'
                  "
                >
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
                  <span class="final-pg-name">{{
                    deployment.processGroupName
                  }}</span>
                </div>
                <div class="review-row">
                  <span class="review-label">Template:</span>
                  <span>{{ deployment.templateName || "No Template" }}</span>
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
          <p class="text-muted">What would you like to do?</p>
        </div>

        <div class="conflict-actions">
          <b-button
            variant="primary"
            @click="handleConflictResolution('deploy_anyway')"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
          >
            <b-spinner
              v-if="
                isResolvingConflict && conflictResolution === 'deploy_anyway'
              "
              small
              class="me-2"
            ></b-spinner>
            <i v-else class="pe-7s-plus"></i>
            Deploy Anyway (Create Additional Process Group)
          </b-button>

          <b-button
            variant="danger"
            @click="handleConflictResolution('delete_and_deploy')"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
          >
            <b-spinner
              v-if="
                isResolvingConflict &&
                conflictResolution === 'delete_and_deploy'
              "
              small
              class="me-2"
            ></b-spinner>
            <i v-else class="pe-7s-trash"></i>
            Delete Existing and Deploy New
          </b-button>

          <b-button
            v-if="conflictInfo.existing_process_group.has_version_control"
            variant="info"
            @click="handleConflictResolution('update_version')"
            :disabled="isResolvingConflict"
            class="mb-2 w-100"
          >
            <b-spinner
              v-if="
                isResolvingConflict && conflictResolution === 'update_version'
              "
              small
              class="me-2"
            ></b-spinner>
            <i v-else class="pe-7s-refresh-2"></i>
            Update to New Version
          </b-button>

          <b-button
            variant="outline-secondary"
            @click="showConflictModal = false"
            :disabled="isResolvingConflict"
            class="w-100"
          >
            Cancel
          </b-button>
        </div>
      </div>
    </b-modal>

    <!-- Deployment Results Modal -->
    <b-modal
      v-model="showResultsModal"
      title="Deployment Results"
      size="lg"
      hide-footer
    >
      <div class="deployment-results">
        <!-- Summary Stats -->
        <div class="results-summary">
          <div class="stat-card success">
            <div class="stat-icon">
              <i class="pe-7s-check"></i>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ deploymentResults.successCount }}</div>
              <div class="stat-label">Successful</div>
            </div>
          </div>
          <div class="stat-card failed">
            <div class="stat-icon">
              <i class="pe-7s-close"></i>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ deploymentResults.failCount }}</div>
              <div class="stat-label">Failed</div>
            </div>
          </div>
          <div class="stat-card total">
            <div class="stat-icon">
              <i class="pe-7s-network"></i>
            </div>
            <div class="stat-content">
              <div class="stat-value">{{ deploymentResults.total }}</div>
              <div class="stat-label">Total</div>
            </div>
          </div>
        </div>

        <!-- Successful Deployments -->
        <div
          v-if="deploymentResults.successful.length > 0"
          class="results-section success-section"
        >
          <h6 class="section-title">
            <i class="pe-7s-check"></i>
            Successful Deployments
          </h6>
          <div class="result-list">
            <div
              v-for="(result, index) in deploymentResults.successful"
              :key="index"
              class="result-item success"
            >
              <div class="result-header">
                <i class="pe-7s-check-circle"></i>
                <strong>{{ result.config.flowName }}</strong>
                <span
                  class="badge"
                  :class="
                    result.config.target === 'source'
                      ? 'badge-primary'
                      : 'badge-success'
                  "
                >
                  {{ result.config.target }}
                </span>
              </div>
              <div class="result-details">
                <div class="detail-row">
                  <span class="label">Instance:</span>
                  <span>{{ result.config.hierarchyValue }}</span>
                </div>
                <div class="detail-row">
                  <span class="label">Process Group:</span>
                  <code>{{ result.processGroupName }}</code>
                </div>
                <div v-if="result.processGroupId" class="detail-row">
                  <span class="label">ID:</span>
                  <code class="small">{{ result.processGroupId }}</code>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Failed Deployments -->
        <div
          v-if="deploymentResults.failed.length > 0"
          class="results-section failed-section"
        >
          <h6 class="section-title">
            <i class="pe-7s-close"></i>
            Failed Deployments
          </h6>
          <div class="result-list">
            <div
              v-for="(result, index) in deploymentResults.failed"
              :key="index"
              class="result-item failed"
            >
              <div class="result-header">
                <i class="pe-7s-close-circle"></i>
                <strong>{{ result.config.flowName }}</strong>
                <span
                  class="badge"
                  :class="
                    result.config.target === 'source'
                      ? 'badge-primary'
                      : 'badge-success'
                  "
                >
                  {{ result.config.target }}
                </span>
              </div>
              <div class="result-details">
                <div class="detail-row">
                  <span class="label">Instance:</span>
                  <span>{{ result.config.hierarchyValue }}</span>
                </div>
                <div class="detail-row error">
                  <span class="label">Error:</span>
                  <span>{{ result.message }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Actions -->
        <div class="results-actions">
          <b-button
            v-if="deploymentResults.failCount === 0"
            variant="success"
            @click="closeResultsAndReset"
            class="w-100"
          >
            <i class="pe-7s-check"></i>
            Done - Start New Deployment
          </b-button>
          <b-button
            v-else
            variant="primary"
            @click="showResultsModal = false"
            class="w-100"
          >
            <i class="pe-7s-angle-left"></i>
            Review and Fix Issues
          </b-button>
        </div>
      </div>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiRequest } from "@/utils/api";

interface Flow {
  id: number;
  [key: string]: any;
  source: string;
  destination: string;
}

interface HierarchyAttribute {
  name: string;
  label: string;
  order: number;
}

interface ProcessGroupPath {
  id: string;
  name: string;
  parent_group_id: string | null;
  depth: number;
  path: Array<{ id: string; name: string; parent_group_id: string | null }>;
}

interface DeploymentConfig {
  key: string;
  flowId: number;
  flowName: string;
  target: "source" | "destination";
  hierarchyValue: string;
  instanceId: number | null;
  availablePaths: Array<{ id: string; pathDisplay: string }>;
  selectedProcessGroupId: string;
  suggestedPath: string | null;
  templateId: number | null;
  templateName: string | null;
  processGroupName: string;
}

const steps = [
  "Select Flows",
  "Choose Targets",
  "Choose Process Groups",
  "Settings",
  "Review & Deploy",
];
const currentStep = ref(0);
const isLoading = ref(false);
const isLoadingPaths = ref(false);
const isDeploying = ref(false);

// Conflict resolution
const showConflictModal = ref(false);
const conflictInfo = ref<any>(null);
const currentConflictDeployment = ref<any>(null);
const isResolvingConflict = ref(false);
const conflictResolution = ref<string>("");

// Deployment results
const showResultsModal = ref(false);
const deploymentResults = ref({
  successCount: 0,
  failCount: 0,
  total: 0,
  successful: [] as any[],
  failed: [] as any[],
});

// Flow data
const flows = ref<Flow[]>([]);
const selectedFlows = ref<number[]>([]);
const hierarchyConfig = ref<HierarchyAttribute[]>([]);
const visibleColumns = ref<Array<{ key: string; label: string }>>([]);
const nifiInstances = ref<any[]>([]);
const registryFlows = ref<any[]>([]);

// Deployment configuration
const deploymentTargets = ref<
  Record<number, "source" | "destination" | "both">
>({});
const deploymentConfigs = ref<DeploymentConfig[]>([]);
const processGroupPaths = ref<Record<string, ProcessGroupPath[]>>({});
const deploymentSettings = ref<any>({
  global: {
    process_group_name_template: "{last_hierarchy_value}",
    disable_after_deploy: false,
    stop_versioning_after_deploy: false,
  },
  paths: {},
});

// Computed
const allSelected = computed(() => {
  return (
    flows.value.length > 0 && selectedFlows.value.length === flows.value.length
  );
});

const selectedFlowObjects = computed(() => {
  return flows.value.filter((f) => selectedFlows.value.includes(f.id));
});

const topHierarchyName = computed(() => {
  return hierarchyConfig.value.length > 0
    ? hierarchyConfig.value[0].name
    : "DC";
});

const secondHierarchyName = computed(() => {
  return hierarchyConfig.value.length > 1
    ? hierarchyConfig.value[1].name
    : "OU";
});

const allTargetsSelected = computed(() => {
  return selectedFlows.value.every((flowId) => deploymentTargets.value[flowId]);
});

const allProcessGroupsSelected = computed(() => {
  return deploymentConfigs.value.every(
    (config) => config.selectedProcessGroupId,
  );
});

const uniqueInstancesCount = computed(() => {
  const instances = new Set(
    deploymentConfigs.value.map((c) => c.hierarchyValue),
  );
  return instances.size;
});

// Methods
const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedFlows.value = [];
  } else {
    selectedFlows.value = flows.value.map((f) => f.id);
  }
};

const toggleFlow = (flowId: number) => {
  const index = selectedFlows.value.indexOf(flowId);
  if (index === -1) {
    selectedFlows.value.push(flowId);
  } else {
    selectedFlows.value.splice(index, 1);
  }
};

const getFlowName = (flow: Flow) => {
  // Try to get the first hierarchy attribute value as the name
  if (hierarchyConfig.value.length > 0) {
    const firstAttr = hierarchyConfig.value[0].name.toLowerCase();
    return flow[`src_${firstAttr}`] || flow[firstAttr] || `Flow ${flow.id}`;
  }
  return `Flow ${flow.id}`;
};

const getTopHierarchyValue = (flow: Flow, side: "source" | "destination") => {
  if (hierarchyConfig.value.length === 0) return "N/A";

  const topAttr = hierarchyConfig.value[0].name.toLowerCase();
  const prefix = side === "source" ? "src_" : "dest_";
  return flow[`${prefix}${topAttr}`] || "N/A";
};

const getDeploymentTarget = (flowId: number) => {
  return deploymentTargets.value[flowId];
};

const setDeploymentTarget = (
  flowId: number,
  target: "source" | "destination" | "both",
) => {
  deploymentTargets.value[flowId] = target;
};

const goToNextStep = async () => {
  if (currentStep.value === 1) {
    // Moving to step 3: prepare deployment configs and load process groups
    await prepareDeploymentConfigs();
  }
  currentStep.value++;
};

const goToPreviousStep = () => {
  currentStep.value--;
};

const prepareDeploymentConfigs = async () => {
  deploymentConfigs.value = [];
  isLoadingPaths.value = true;

  try {
    // Build deployment configs based on selected flows and targets
    for (const flowId of selectedFlows.value) {
      const flow = flows.value.find((f) => f.id === flowId);
      if (!flow) continue;

      const target = deploymentTargets.value[flowId];
      const flowName = getFlowName(flow);

      if (target === "source" || target === "both") {
        const hierarchyValue = getTopHierarchyValue(flow, "source");
        const instanceId = await getInstanceIdForHierarchyValue(hierarchyValue);
        const templateId = flow.src_template_id || null;
        const templateName = getTemplateName(templateId);

        const config: DeploymentConfig = {
          key: `${flowId}-source`,
          flowId,
          flowName,
          target: "source",
          hierarchyValue,
          instanceId,
          availablePaths: [],
          selectedProcessGroupId: "",
          suggestedPath: getSuggestedPath(flow, "source"),
          templateId,
          templateName,
          processGroupName: generateProcessGroupName(flow, "source"),
        };

        // Load paths for this instance
        if (instanceId) {
          const rawPaths = await loadProcessGroupPaths(
            instanceId,
            hierarchyValue,
          );
          config.availablePaths = rawPaths;

          // Auto-select process group based on deployment settings
          const selectedPgId = autoSelectProcessGroup(
            flow,
            "source",
            instanceId,
            processGroupPaths.value[hierarchyValue] || [],
          );
          if (selectedPgId) {
            config.selectedProcessGroupId = selectedPgId;
          }
        }

        deploymentConfigs.value.push(config);
      }

      if (target === "destination" || target === "both") {
        const hierarchyValue = getTopHierarchyValue(flow, "destination");
        const instanceId = await getInstanceIdForHierarchyValue(hierarchyValue);
        const templateId = flow.dest_template_id || null;
        const templateName = getTemplateName(templateId);

        const config: DeploymentConfig = {
          key: `${flowId}-destination`,
          flowId,
          flowName,
          target: "destination",
          hierarchyValue,
          instanceId,
          availablePaths: [],
          selectedProcessGroupId: "",
          suggestedPath: getSuggestedPath(flow, "destination"),
          templateId,
          templateName,
          processGroupName: generateProcessGroupName(flow, "destination"),
        };

        // Load paths for this instance
        if (instanceId) {
          const rawPaths = await loadProcessGroupPaths(
            instanceId,
            hierarchyValue,
          );
          config.availablePaths = rawPaths;

          // Auto-select process group based on deployment settings
          const selectedPgId = autoSelectProcessGroup(
            flow,
            "destination",
            instanceId,
            processGroupPaths.value[hierarchyValue] || [],
          );
          if (selectedPgId) {
            config.selectedProcessGroupId = selectedPgId;
          }
        }

        deploymentConfigs.value.push(config);
      }
    }
  } catch (error) {
    console.error("Error preparing deployment configs:", error);
  } finally {
    isLoadingPaths.value = false;
  }
};

const getSuggestedPath = (flow: Flow, side: "source" | "destination") => {
  // Get the penultimate hierarchy value (e.g., OU)
  if (hierarchyConfig.value.length < 2) return null;

  const secondAttr = hierarchyConfig.value[1].name.toLowerCase();
  const prefix = side === "source" ? "src_" : "dest_";
  const value = flow[`${prefix}${secondAttr}`];

  return value ? `Contains "${value}"` : null;
};

const getTemplateName = (templateId: number | null): string | null => {
  if (!templateId) return null;

  const template = registryFlows.value.find((rf) => rf.id === templateId);
  return template ? template.flow_name : `Template ID ${templateId}`;
};

const getInstanceIdForHierarchyValue = async (
  hierarchyValue: string,
): Promise<number | null> => {
  try {
    // Ensure we have loaded NiFi instances
    if (nifiInstances.value.length === 0) {
      await loadNiFiInstances();
    }

    // Get the top hierarchy attribute name (e.g., "DC")
    const topHierarchyAttr = topHierarchyName.value;

    // Find the instance that matches the hierarchy attribute and value
    const instance = nifiInstances.value.find(
      (inst) =>
        inst.hierarchy_attribute === topHierarchyAttr &&
        inst.hierarchy_value === hierarchyValue,
    );

    if (instance) {
      console.log(
        `Found NiFi instance ${instance.id} for ${topHierarchyAttr}=${hierarchyValue}`,
      );
      return instance.id;
    }

    console.warn(
      `No NiFi instance found for ${topHierarchyAttr}=${hierarchyValue}`,
    );
    return null;
  } catch (error) {
    console.error("Error getting instance ID:", error);
    return null;
  }
};

const loadProcessGroupPaths = async (
  instanceId: number,
  cacheKey: string,
): Promise<Array<{ id: string; pathDisplay: string }>> => {
  // Check cache first
  if (processGroupPaths.value[cacheKey]) {
    return formatPathsForDisplay(processGroupPaths.value[cacheKey]);
  }

  try {
    const data = await apiRequest(`/api/nifi-instances/${instanceId}/get-all-paths`);

    if (data.status === "success" && data.process_groups) {
      processGroupPaths.value[cacheKey] = data.process_groups;
      return formatPathsForDisplay(data.process_groups);
    }

    return [];
  } catch (error) {
    console.error("Error loading process group paths:", error);
    // Return mock data for development when backend is not available
    return getMockPaths();
  }
};

const formatPathsForDisplay = (
  paths: ProcessGroupPath[],
): Array<{ id: string; pathDisplay: string }> => {
  return paths.map((pg) => {
    // Reverse the path array so root is first and deepest is last
    const pathNames = pg.path
      .slice()
      .reverse()
      .map((p) => p.name)
      .join(" → ");
    return {
      id: pg.id,
      pathDisplay: pathNames,
    };
  });
};

const getMockPaths = (): Array<{ id: string; pathDisplay: string }> => {
  return [
    { id: "root", pathDisplay: "NiFi Flow" },
    { id: "pg1", pathDisplay: "NiFi Flow → Engineering" },
    { id: "pg2", pathDisplay: "NiFi Flow → Engineering → DataPipeline" },
    { id: "pg3", pathDisplay: "NiFi Flow → Marketing" },
    { id: "pg4", pathDisplay: "NiFi Flow → Marketing → Analytics" },
  ];
};

const updateProcessGroupSelection = (deployment: DeploymentConfig) => {
  // Selection is already updated via v-model
  console.log(
    `Selected process group ${deployment.selectedProcessGroupId} for ${deployment.key}`,
  );
};

const getSelectedPathDisplay = (deployment: DeploymentConfig) => {
  const selected = deployment.availablePaths.find(
    (p) => p.id === deployment.selectedProcessGroupId,
  );
  return selected?.pathDisplay || "Not selected";
};

const generateProcessGroupName = (
  flow: Flow,
  target: "source" | "destination",
): string => {
  // Get the template from deployment settings
  const template =
    deploymentSettings.value?.global?.process_group_name_template ||
    "{last_hierarchy_value}";

  // Get hierarchy values for this flow
  const prefix = target === "source" ? "src_" : "dest_";
  const hierarchyValues: string[] = [];

  for (let i = 0; i < hierarchyConfig.value.length; i++) {
    const attrName = hierarchyConfig.value[i].name.toLowerCase();
    const value = flow[`${prefix}${attrName}`] || "";
    hierarchyValues.push(value);
  }

  // Replace placeholders in template
  let result = template;

  // Replace {first_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(/{first_hierarchy_value}/g, hierarchyValues[0]);
  }

  // Replace {last_hierarchy_value}
  if (hierarchyValues.length > 0) {
    result = result.replace(
      /{last_hierarchy_value}/g,
      hierarchyValues[hierarchyValues.length - 1],
    );
  }

  // Replace {N_hierarchy_value} where N is 1, 2, 3, etc.
  for (let i = 0; i < hierarchyValues.length; i++) {
    const placeholder = `{${i + 1}_hierarchy_value}`;
    result = result.replace(
      new RegExp(placeholder.replace(/[{}]/g, "\\$&"), "g"),
      hierarchyValues[i],
    );
  }

  return result;
};

const autoSelectProcessGroup = (
  flow: Flow,
  target: "source" | "destination",
  instanceId: number,
  availablePaths: ProcessGroupPath[],
): string | null => {
  try {
    // Get the search path from deployment settings
    if (
      !deploymentSettings.value ||
      !deploymentSettings.value.paths ||
      !deploymentSettings.value.paths[instanceId]
    ) {
      return null;
    }

    const searchPathId =
      target === "source"
        ? deploymentSettings.value.paths[instanceId].source_path
        : deploymentSettings.value.paths[instanceId].dest_path;

    if (!searchPathId) {
      return null;
    }

    // Find the search path in available paths
    const searchPath = availablePaths.find((p) => p.id === searchPathId);
    if (!searchPath) {
      return null;
    }

    // Get the search path as an array of names (reversed, since path is stored root-first)
    const searchPathNames = searchPath.path
      .slice()
      .reverse()
      .map((p) => p.name);

    // Get hierarchy attributes for this flow, skipping:
    // - Top hierarchy (index 0) - represents the NiFi instance
    // - Last hierarchy (index length-1) - the final process group that will be created during deployment
    // So we use attributes from index 1 to length-2
    const hierarchyAttributes: string[] = [];
    const prefix = target === "source" ? "src_" : "dest_";

    for (let i = 1; i < hierarchyConfig.value.length - 1; i++) {
      const attrName = hierarchyConfig.value[i].name.toLowerCase();
      const value = flow[`${prefix}${attrName}`];
      if (value) {
        hierarchyAttributes.push(value);
      }
    }

    // Now find a path that:
    // 1. Starts with all elements from searchPathNames
    // 2. Contains all hierarchyAttributes in order
    for (const pg of availablePaths) {
      const pgPathNames = pg.path
        .slice()
        .reverse()
        .map((p) => p.name);

      // Check if path starts with search path
      let startsWithSearchPath = true;
      for (let i = 0; i < searchPathNames.length; i++) {
        if (pgPathNames[i] !== searchPathNames[i]) {
          startsWithSearchPath = false;
          break;
        }
      }

      if (!startsWithSearchPath) {
        continue;
      }

      // Check if path contains all hierarchy attributes in order
      let matchesHierarchy = true;
      let searchIndex = searchPathNames.length; // Start searching after the search path prefix

      for (const attr of hierarchyAttributes) {
        let found = false;
        for (let i = searchIndex; i < pgPathNames.length; i++) {
          if (pgPathNames[i] === attr) {
            found = true;
            searchIndex = i + 1;
            break;
          }
        }
        if (!found) {
          matchesHierarchy = false;
          break;
        }
      }

      if (matchesHierarchy) {
        return pg.id;
      }
    }

    return null;
  } catch (error) {
    console.error("Error in autoSelectProcessGroup:", error);
    return null;
  }
};

/**
 * Get the hierarchy attribute name for a given process group.
 * 
 * The backend builds paths as: configured_path + hierarchy_values
 * We need to determine which hierarchy level the selected PG represents
 * by comparing its path against the configured deployment path.
 * 
 * For example:
 * - Configured path: "NiFi Flow/To net1"
 * - Selected PG path: "NiFi Flow/To net1/o1/ou1"
 * - Hierarchy offset: 2 (ou1 is the 2nd level after configured path)
 * - Returns: hierarchy[2] = "datenschleuder_ou"
 * 
 * @param processGroupId - The ID of the selected process group
 * @param instanceKey - The key to lookup process group paths (e.g., "source_123")
 * @param instanceId - The NiFi instance ID to get configured path
 * @param target - "source" or "destination" to determine which configured path to use
 * @returns The hierarchy attribute name (e.g., "datenschleuder_ou") or null if not found
 */
const getHierarchyAttributeForProcessGroup = (
  processGroupId: string,
  instanceKey: string,
  instanceId: number,
  target: "source" | "destination",
): string | null => {
  if (!hierarchyConfig.value.length || !deploymentSettings.value) return null;
  
  // Find the process group in the paths
  const paths = processGroupPaths.value[instanceKey] || [];
  const selectedPg = paths.find((pg) => pg.id === processGroupId);
  
  if (!selectedPg || !selectedPg.path || selectedPg.path.length === 0) return null;
  
  // Get configured path for this instance
  const instanceSettings = deploymentSettings.value.paths?.[instanceId];
  if (!instanceSettings) return null;
  
  // Get the PathConfig object (contains id and path properties)
  const pathConfig = target === "source" 
    ? instanceSettings.source_path 
    : instanceSettings.dest_path;
  
  if (!pathConfig || !pathConfig.path) return null;
  
  // Extract the path string from the PathConfig object
  const configuredPath = pathConfig.path;
  
  // Build PG path string from the path array (excluding root)
  const pgPathSegments = selectedPg.path
    .filter((p: any) => p.name !== "NiFi Flow") // Exclude root
    .map((p: any) => p.name);
  
  // Count configured path segments
  const configuredSegments = configuredPath.split('/').filter((p: string) => p.length > 0);
  
  // Calculate hierarchy offset: PG segments - configured segments
  // This tells us how many hierarchy levels deep we are after the configured path
  const hierarchyOffset = pgPathSegments.length - configuredSegments.length;
  
  // Map to hierarchy index (accounting for skipped first level)
  // hierarchy[0] = top level (DC) - in configured path
  // hierarchy[1] = second level (O) - first deployed level
  // hierarchy[2] = third level (OU) - second deployed level
  const hierarchyIndex = hierarchyOffset;
  
  if (hierarchyIndex > 0 && hierarchyIndex < hierarchyConfig.value.length) {
    return hierarchyConfig.value[hierarchyIndex].name;
  }
  
  return null;
};

const deployFlows = async () => {
  isDeploying.value = true;

  try {
    console.log("Deploying flows with configs:", deploymentConfigs.value);

    const results = [];
    let successCount = 0;
    let failCount = 0;

    // Deploy each configuration
    for (const config of deploymentConfigs.value) {
      try {
        console.log(
          `Deploying ${config.flowName} to ${config.target} (${config.hierarchyValue})...`,
        );

        if (!config.instanceId) {
          throw new Error(
            `No NiFi instance found for ${config.hierarchyValue}`,
          );
        }

        if (!config.selectedProcessGroupId) {
          throw new Error("No process group selected");
        }

        // Calculate hierarchy attribute based on selected process group path
        // accounting for configured deployment paths
        const instanceKey = `${config.target}_${config.instanceId}`;
        const hierarchyAttribute = getHierarchyAttributeForProcessGroup(
          config.selectedProcessGroupId,
          instanceKey,
          config.instanceId,
          config.target,
        );

        // Prepare deployment request using the settings from step 4
        const deploymentRequest: any = {
          template_id: config.templateId,
          parent_process_group_id: config.selectedProcessGroupId,
          process_group_name: config.processGroupName,
          version: null, // Use latest version
          x_position: 0,
          y_position: 0,
          stop_versioning_after_deploy: deploymentSettings.value.global.stop_versioning_after_deploy,
          disable_after_deploy: deploymentSettings.value.global.disable_after_deploy,
        };

        // Add hierarchy attribute if calculated
        if (hierarchyAttribute) {
          deploymentRequest.hierarchy_attribute = hierarchyAttribute;
        }

        console.log("Deployment request:", deploymentRequest);

        // Call deployment API
        try {
          const result = await apiRequest(
            `/api/deploy/${config.instanceId}/flow`,
            {
              method: "POST",
              body: JSON.stringify(deploymentRequest),
            },
          );

          console.log("Deployment result:", result);

          if (result.status === "success") {
            successCount++;
            results.push({
              config,
              success: true,
              message: result.message,
              processGroupId: result.process_group_id,
              processGroupName: result.process_group_name,
            });
          } else {
            failCount++;
            results.push({
              config,
              success: false,
              message: result.message || "Deployment failed",
            });
          }
        } catch (apiError: any) {
          // Check if it's a 409 Conflict (process group already exists)
          if (apiError.status === 409 && apiError.detail) {
            console.log("Conflict detected:", apiError.detail);

            // Store conflict info and current deployment config
            conflictInfo.value = apiError.detail;
            currentConflictDeployment.value = { config, deploymentRequest };

            // Show conflict modal and wait for user decision
            showConflictModal.value = true;
            isDeploying.value = false;

            // Stop the deployment loop - user needs to make a decision
            // Don't show summary - modal is shown instead
            return;
          }

          // For other errors, add to results
          throw apiError;
        }
      } catch (error: any) {
        failCount++;
        console.error(`Deployment failed for ${config.flowName}:`, error);
        console.log("DEBUG - Error object:", JSON.parse(JSON.stringify(error)));

        // Extract error message properly - handle all possible error structures
        let errorMessage = "Deployment failed";

        // Try different paths to get the error message
        const extractMessage = (obj: any): string => {
          if (!obj) return "Unknown error";
          if (typeof obj === "string") return obj;

          // Check common error message paths
          if (obj.detail?.message) return obj.detail.message;
          if (obj.detail?.error) return obj.detail.error;
          if (obj.message) return obj.message;
          if (obj.error) return obj.error;
          if (obj.statusText) return obj.statusText;

          // If detail is an object, try to stringify it nicely
          if (obj.detail && typeof obj.detail === "object") {
            try {
              return JSON.stringify(obj.detail, null, 2);
            } catch {
              return "Complex error - see console";
            }
          }

          // Last resort - stringify the whole thing
          try {
            return JSON.stringify(obj, null, 2);
          } catch {
            return "Error details unavailable";
          }
        };

        errorMessage = extractMessage(error);

        console.log("DEBUG - Extracted message:", errorMessage);

        results.push({
          config,
          success: false,
          message: errorMessage,
        });
      }
    }

    // Show results only if we completed the loop (no conflict modal shown)
    if (!showConflictModal.value) {
      console.log("Deployment results:", results);

      // Populate results modal data
      deploymentResults.value = {
        successCount,
        failCount,
        total: successCount + failCount,
        successful: results.filter((r) => r.success),
        failed: results.filter((r) => !r.success),
      };

      // Show results modal
      showResultsModal.value = true;
    }
  } catch (error: any) {
    console.error("Deployment error:", error);
    alert("Deployment failed: " + (error.message || error));
  } finally {
    isDeploying.value = false;
  }
};

const handleConflictResolution = async (resolution: string) => {
  conflictResolution.value = resolution;
  isResolvingConflict.value = true;

  try {
    const { config, deploymentRequest } = currentConflictDeployment.value;
    const existingPgId = conflictInfo.value.existing_process_group.id;

    if (resolution === "deploy_anyway") {
      // Deploy anyway - just clear the process_group_name to let NiFi use default name
      const modifiedRequest = {
        ...deploymentRequest,
        process_group_name: null,
      };

      const result = await apiRequest(`/api/deploy/${config.instanceId}/flow`, {
        method: "POST",
        body: JSON.stringify(modifiedRequest),
      });

      if (result.status === "success") {
        alert(
          `✓ Successfully deployed!\nProcess Group: ${result.process_group_name}`,
        );
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;
      }
    } else if (resolution === "delete_and_deploy") {
      // Delete existing process group first
      await apiRequest(
        `/api/nifi-instances/${config.instanceId}/process-group/${existingPgId}`,
        {
          method: "DELETE",
        },
      );

      // Then deploy new one
      const result = await apiRequest(`/api/deploy/${config.instanceId}/flow`, {
        method: "POST",
        body: JSON.stringify(deploymentRequest),
      });

      if (result.status === "success") {
        alert(
          `✓ Successfully deployed after deleting old process group!\nProcess Group: ${result.process_group_name}`,
        );
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;
      }
    } else if (resolution === "update_version") {
      // Update existing process group to new version
      const updateRequest = {
        version: deploymentRequest.version,
      };

      const result = await apiRequest(
        `/api/nifi-instances/${config.instanceId}/process-group/${existingPgId}/update-version`,
        {
          method: "POST",
          body: JSON.stringify(updateRequest),
        },
      );

      if (result.status === "success") {
        alert(`✓ Successfully updated process group to new version!`);
        showConflictModal.value = false;
        conflictInfo.value = null;
        currentConflictDeployment.value = null;
      }
    }
  } catch (error: any) {
    console.error("Conflict resolution failed:", error);
    alert(
      `✗ Failed to ${resolution.replace("_", " ")}: ${error.message || error.detail || "Unknown error"}`,
    );
  } finally {
    isResolvingConflict.value = false;
    conflictResolution.value = "";
  }
};

const closeResultsAndReset = () => {
  showResultsModal.value = false;

  // Reset wizard to start
  currentStep.value = 0;
  selectedFlows.value = [];
  deploymentTargets.value = {};
  deploymentConfigs.value = [];

  // Clear results
  deploymentResults.value = {
    successCount: 0,
    failCount: 0,
    total: 0,
    successful: [],
    failed: [],
  };
};

const loadFlows = async () => {
  isLoading.value = true;
  try {
    const data = await apiRequest("/api/nifi-flows/");
    if (data.flows) {
      flows.value = data.flows;
    }
  } catch (error) {
    console.error("Error loading flows:", error);
  } finally {
    isLoading.value = false;
  }
};

const loadHierarchyConfig = async () => {
  try {
    const data = await apiRequest("/api/settings/hierarchy");
    if (data.hierarchy) {
      hierarchyConfig.value = data.hierarchy.sort(
        (a: HierarchyAttribute, b: HierarchyAttribute) => a.order - b.order,
      );

      // Build visible columns from hierarchy
      visibleColumns.value = hierarchyConfig.value.map((attr) => ({
        key: `src_${attr.name.toLowerCase()}`,
        label: `Src ${attr.name}`,
      }));
    }
  } catch (error) {
    console.error("Error loading hierarchy config:", error);
  }
};

const loadNiFiInstances = async () => {
  try {
    const instances = await apiRequest("/api/nifi-instances/");
    if (instances && Array.isArray(instances)) {
      nifiInstances.value = instances;
      console.log(`Loaded ${instances.length} NiFi instances`);
    }
  } catch (error) {
    console.error("Error loading NiFi instances:", error);
  }
};

const loadRegistryFlows = async () => {
  try {
    const flows = await apiRequest("/api/registry-flows/");
    if (flows && Array.isArray(flows)) {
      registryFlows.value = flows;
      console.log(`Loaded ${flows.length} registry flows`);
    }
  } catch (error) {
    console.error("Error loading registry flows:", error);
  }
};

const loadDeploymentSettings = async () => {
  try {
    const data = await apiRequest("/api/settings/deploy");

    // Convert string keys to numbers since JSON serialization converts numeric keys to strings
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
      global: {
        process_group_name_template: data.global?.process_group_name_template || "{last_hierarchy_value}",
        disable_after_deploy: data.global?.disable_after_deploy || false,
        stop_versioning_after_deploy: data.global?.stop_versioning_after_deploy || false,
      },
      paths: paths,
    };
  } catch (error) {
    console.error("Error loading deployment settings:", error);
  }
};

onMounted(async () => {
  await loadHierarchyConfig();
  await loadNiFiInstances();
  await loadRegistryFlows();
  await loadDeploymentSettings();
  await loadFlows();
});
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

// Conflict Modal
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

// Deployment Results Modal
.deployment-results {
  .results-summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
    margin-bottom: 30px;

    .stat-card {
      background: #f8f9fa;
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 15px;
      border: 2px solid transparent;

      &.success {
        border-color: #28a745;
        background: #d4edda;
      }

      &.failed {
        border-color: #dc3545;
        background: #f8d7da;
      }

      &.total {
        border-color: #007bff;
        background: #d1ecf1;
      }

      .stat-icon {
        width: 50px;
        height: 50px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 24px;
        flex-shrink: 0;

        .success & {
          background: #28a745;
          color: white;
        }

        .failed & {
          background: #dc3545;
          color: white;
        }

        .total & {
          background: #007bff;
          color: white;
        }
      }

      .stat-content {
        .stat-value {
          font-size: 32px;
          font-weight: 700;
          line-height: 1;
          margin-bottom: 5px;
        }

        .stat-label {
          font-size: 14px;
          color: #6c757d;
          font-weight: 500;
        }
      }
    }
  }

  .results-section {
    margin-bottom: 25px;

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 15px;
      font-size: 16px;
      font-weight: 600;

      i {
        font-size: 20px;
      }
    }

    &.success-section .section-title {
      color: #28a745;
    }

    &.failed-section .section-title {
      color: #dc3545;
    }

    .result-list {
      display: flex;
      flex-direction: column;
      gap: 12px;
    }

    .result-item {
      border: 2px solid #e9ecef;
      border-radius: 8px;
      padding: 15px;
      background: white;

      &.success {
        border-color: #28a745;
        background: #f8fff9;
      }

      &.failed {
        border-color: #dc3545;
        background: #fff8f8;
      }

      .result-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 10px;

        i {
          font-size: 20px;

          .success & {
            color: #28a745;
          }

          .failed & {
            color: #dc3545;
          }
        }

        strong {
          flex: 1;
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

      .result-details {
        padding-left: 30px;

        .detail-row {
          display: flex;
          gap: 10px;
          margin-bottom: 8px;
          font-size: 14px;

          &:last-child {
            margin-bottom: 0;
          }

          .label {
            font-weight: 600;
            color: #6c757d;
            min-width: 120px;
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
        }
      }
    }
  }

  .results-actions {
    margin-top: 25px;
    padding-top: 20px;
    border-top: 2px solid #e9ecef;
  }
}

// Settings Form
.settings-form {
  max-width: 800px;
  margin-bottom: 30px;

  .form-group {
    margin-bottom: 24px;

    .form-label {
      display: block;
      font-weight: 600;
      margin-bottom: 8px;
      color: #495057;
      font-size: 0.95rem;
    }

    .form-text {
      display: block;
      margin-top: 6px;
      font-size: 0.875rem;
      line-height: 1.4;
    }
  }

  .form-control,
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
}

// Settings Card in Review Section
.settings-card {
  background: #f8f9fa;
  border: 2px solid #007bff !important;

  .review-row {
    display: flex;
    align-items: center;
    gap: 8px;

    i {
      font-size: 1.2rem;
    }
  }
}
</style>
