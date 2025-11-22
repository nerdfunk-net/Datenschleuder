<template>
  <div class="flows-deploy">
    <div class="page-card">
      <!-- Wizard Header -->
      <div class="card-header">
        <h2 class="card-title">
          Deploy Flows
        </h2>
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
            <div class="step-number">
              {{ index + 1 }}
            </div>
            <div class="step-label">
              {{ step }}
            </div>
          </div>
        </div>
      </div>

      <!-- Step 1: Select Flows -->
      <div v-if="currentStep === 0" class="wizard-content">
        <div class="step-header">
          <h3>Step 1: Select Flows to Deploy</h3>
          <p class="text-muted">
            Choose one or more flows from the list below
          </p>
        </div>

        <!-- Loading State -->
        <div v-if="isLoading" class="text-center py-5">
          <b-spinner variant="primary" />
          <p class="mt-3 text-muted">
            Loading flows...
          </p>
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
          <h4 class="mt-3 text-muted">
            No Flows Available
          </h4>
          <p class="text-muted">
            There are no flows available for deployment.
          </p>
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
            :disabled="selectedFlows.length === 0"
            @click="goToNextStep"
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
          <p class="text-muted">
            Select where each flow should be deployed
          </p>
        </div>

        <div class="deployment-targets">
          <div
            v-for="flow in selectedFlowObjects"
            :key="flow.id"
            class="target-card"
          >
            <div class="target-header">
              <h5>{{ getFlowName(flow) }}</h5>
              <span class="text-muted">{{ flow.source }} → {{ flow.destination }}</span>
            </div>

            <div class="target-body">
              <div class="hierarchy-info">
                <div class="hierarchy-item">
                  <span class="label">Top Hierarchy ({{ topHierarchyName }}):</span>
                  <span class="value-badge source">Source: {{ getTopHierarchyValue(flow, "source") }}</span>
                  <span class="value-badge dest">Dest: {{ getTopHierarchyValue(flow, "destination") }}</span>
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
                    class="target-btn"
                    @click="setDeploymentTarget(flow.id, 'source')"
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
                    class="target-btn"
                    @click="setDeploymentTarget(flow.id, 'destination')"
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
                    class="target-btn"
                    @click="setDeploymentTarget(flow.id, 'both')"
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
            :disabled="!allTargetsSelected"
            @click="goToNextStep"
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
          <b-spinner variant="primary" />
          <p class="mt-3 text-muted">
            Loading process groups...
          </p>
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
                  v-model="deployment.selectedProcessGroupId"
                  class="form-select"
                  @change="updateProcessGroupSelection(deployment)"
                >
                  <option value="">
                    -- Select a process group --
                  </option>
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
                <span>Selected:
                  <strong>{{
                    getSelectedPathDisplay(deployment)
                  }}</strong></span>
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
            :disabled="!allProcessGroupsSelected"
            @click="goToNextStep"
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
          <!-- Version Selection Section -->
          <div class="version-selection-section">
            <h5 class="section-title">
              <i class="pe-7s-album"></i>
              Flow Version Selection
            </h5>
            <p class="text-muted mb-3">
              Select which version to deploy for each target. Leave empty to deploy the latest version.
            </p>

            <div
              v-for="deployment in deploymentConfigs"
              :key="deployment.key"
              class="version-card"
            >
              <div class="version-card-header">
                <div>
                  <strong>{{ deployment.flowName }}</strong>
                  <span class="text-muted ms-2">
                    →
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
                    {{ deployment.hierarchyValue }}
                  </span>
                </div>
              </div>

              <div class="version-card-body">
                <div v-if="loadingVersionsForDeployment[deployment.key]" class="text-center py-3">
                  <b-spinner small variant="primary" />
                  <span class="ms-2 text-muted">Loading versions...</span>
                </div>

                <div v-else-if="deployment.availableVersions && deployment.availableVersions.length > 0">
                  <label class="form-label">Select Version:</label>
                  <select
                    v-model="deployment.selectedVersion"
                    class="form-select"
                  >
                    <option :value="null">
                      Latest version (automatic)
                    </option>
                    <option
                      v-for="ver in deployment.availableVersions"
                      :key="ver.version"
                      :value="ver.version"
                    >
                      v{{ ver.version }} - {{ ver.comments || 'No description' }}
                    </option>
                  </select>
                  <small class="form-text text-muted d-block mt-1">
                    {{ deployment.availableVersions.length }} version(s) available
                  </small>
                </div>

                <div v-else class="alert alert-warning mb-0">
                  <i class="pe-7s-info-circle"></i>
                  No versions available for this flow
                </div>
              </div>
            </div>
          </div>

          <!-- Divider -->
          <hr class="my-4">

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

          <!-- Start After Deploy -->
          <div class="form-group">
            <b-form-checkbox v-model="deploymentSettings.global.start_after_deploy">
              Start flow after deployment
            </b-form-checkbox>
            <small class="form-text text-muted d-block">
              If enabled, the deployed process group will be STARTED after deployment.
              Note: By default, NiFi deploys flows in STOPPED state.
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
                <div class="summary-label">
                  Total Flows
                </div>
                <div class="summary-value">
                  {{ selectedFlows.length }}
                </div>
              </div>
            </div>
            <div class="summary-item">
              <i class="pe-7s-server"></i>
              <div>
                <div class="summary-label">
                  Total Deployments
                </div>
                <div class="summary-value">
                  {{ deploymentConfigs.length }}
                </div>
              </div>
            </div>
            <div class="summary-item">
              <i class="pe-7s-config"></i>
              <div>
                <div class="summary-label">
                  Instances Affected
                </div>
                <div class="summary-value">
                  {{ uniqueInstancesCount }}
                </div>
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
                <div class="review-row">
                  <span class="review-label">Start After Deploy:</span>
                  <span>
                    <i :class="deploymentSettings.global.start_after_deploy ? 'pe-7s-check text-success' : 'pe-7s-close text-muted'"></i>
                    {{ deploymentSettings.global.start_after_deploy ? "Yes" : "No" }}
                  </span>
                </div>
              </div>
            </div>

            <h5 class="mt-4">
              Deployment Details
            </h5>
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
                <div class="review-row">
                  <span class="review-label">Version:</span>
                  <span>
                    <span v-if="deployment.selectedVersion === null" class="version-badge latest-version">
                      Latest (automatic)
                    </span>
                    <span v-else class="version-badge specific-version">
                      v{{ deployment.selectedVersion }}
                    </span>
                  </span>
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
            :disabled="isDeploying"
            @click="deployFlows"
          >
            <b-spinner v-if="isDeploying" small class="me-2" />
            <i v-else class="pe-7s-cloud-upload"></i>
            Deploy Now
          </b-button>
        </div>
      </div>
    </div>

    <!-- Conflict Resolution Modal -->
    <ConflictResolutionModal
      v-model:show="showConflictModal"
      :conflict-info="(conflictInfo as ConflictInfo)"
      :deployment-config="(currentConflictDeployment as ConflictDeployment | null)?.config"
      :is-resolving="isResolvingConflict"
      @resolve="handleConflictResolution"
      @cancel="showConflictModal = false"
    />

    <!-- Deployment Results Modal -->
    <DeploymentResultsModal
      v-model:show="showResultsModal"
      :results="deploymentResults"
      @done="closeResultsAndReset"
      @review="showResultsModal = false"
    />
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref, reactive } from "vue";
import { useDeploymentWizard } from "@/composables/useDeploymentWizard";
import { useDeploymentOperations } from "@/composables/useDeploymentOperations";
import * as deploymentService from "@/services/deploymentService";
import * as processGroupUtils from "@/utils/processGroupUtils";
import * as flowUtils from "@/utils/flowUtils";
import { apiRequest } from "@/utils/api";
import ConflictResolutionModal from "@/components/flows/deploy/ConflictResolutionModal.vue";
import DeploymentResultsModal from "@/components/flows/deploy/DeploymentResultsModal.vue";
import type { Flow, DeploymentConfig, ConflictDeployment, ConflictInfo } from "@/composables/useDeploymentWizard";

// Use the deployment wizard composable for state management
const {
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
  allSelected,
  selectedFlowObjects,
  topHierarchyName,
  allTargetsSelected,
  allProcessGroupsSelected,
  uniqueInstancesCount,
  goToNextStep: wizardGoToNextStep,
  goToPreviousStep,
  toggleSelectAll,
  toggleFlow,
  getDeploymentTarget,
  setDeploymentTarget,
} = useDeploymentWizard();

// Use deployment operations composable
const { prepareDeploymentConfigs, deployFlows } =
  useDeploymentOperations(
    selectedFlows,
    deploymentTargets,
    hierarchyConfig,
    nifiInstances,
    registryFlows,
    processGroupPaths,
    deploymentSettings,
    deploymentConfigs,
    isLoadingPaths,
    isDeploying,
    conflictInfo,
    currentConflictDeployment,
    showConflictModal,
    deploymentResults,
    showResultsModal,
    flows
  );

// Version loading state
const loadingVersionsForDeployment = reactive<Record<string, boolean>>({});

// Load versions for all deployment configs
const loadVersionsForDeployments = async () => {
  for (const deployment of deploymentConfigs.value) {
    loadingVersionsForDeployment[deployment.key] = true;

    try {
      // Find the registry flow to get registry/bucket/flow IDs
      const registryFlow = registryFlows.value.find(rf => rf.id === deployment.templateId);

      if (registryFlow && deployment.instanceId) {
        const response = await apiRequest(
          `/api/nifi/${deployment.instanceId}/registry/${registryFlow.registry_id}/${registryFlow.bucket_id}/${registryFlow.flow_id}/get-versions`
        ) as any;

        if (response.status === "success" && response.versions) {
          deployment.availableVersions = response.versions;
          deployment.registryId = registryFlow.registry_id as string;
          deployment.bucketId = registryFlow.bucket_id as string;
          deployment.flowIdRegistry = registryFlow.flow_id as string;
          // Default to null (latest version)
          deployment.selectedVersion = null;
        } else {
          deployment.availableVersions = [];
        }
      } else {
        deployment.availableVersions = [];
      }
    } catch (error) {
      console.error(`Error loading versions for ${deployment.key}:`, error);
      deployment.availableVersions = [];
    } finally {
      loadingVersionsForDeployment[deployment.key] = false;
    }
  }
};

// Wrapper methods that use utilities
const getFlowName = (flow: Flow) => {
  return flowUtils.getFlowName(flow, hierarchyConfig.value);
};

const getTopHierarchyValue = (flow: Flow, side: "source" | "destination") => {
  return flowUtils.getTopHierarchyValue(flow, side, hierarchyConfig.value);
};

const goToNextStep = async () => {
  if (currentStep.value === 1) {
    // Moving to step 3: prepare deployment configs and load process groups
    await prepareDeploymentConfigs(flows.value);
  } else if (currentStep.value === 2) {
    // Moving to step 4 (Settings): load versions for all deployments
    await loadVersionsForDeployments();
  }
  wizardGoToNextStep();
};

const updateProcessGroupSelection = (deployment: DeploymentConfig) => {
  // Selection is already updated via v-model
  console.log(
    `Selected process group ${deployment.selectedProcessGroupId} for ${deployment.key}`,
  );
};

const getSelectedPathDisplay = (deployment: DeploymentConfig) => {
  return processGroupUtils.getSelectedPathDisplay(deployment);
};

// Conflict resolution handler (uses the composable)
const handleConflictResolution = async (resolution: 'deploy_anyway' | 'delete_and_deploy' | 'update_version') => {
  conflictResolution.value = resolution;
  isResolvingConflict.value = true;

  try {
    const { handleConflictResolution: resolveConflict } = await import('@/composables/useConflictResolution');
    const deployment = currentConflictDeployment.value as ConflictDeployment;

    const result = await resolveConflict(
      resolution,
      deployment.config,
      deployment.deploymentRequest,
      conflictInfo.value as ConflictInfo
    );

    if (result.success) {
      alert(`✓ ${result.message}`);
      showConflictModal.value = false;
      conflictInfo.value = null;
      currentConflictDeployment.value = null;
    } else {
      alert(`✗ ${result.message}`);
    }
  } catch (error: any) {
    console.error('Conflict resolution failed:', error);
    alert(
      `✗ Failed to ${resolution.replace('_', ' ')}: ${error.message || error.detail || 'Unknown error'}`
    );
  } finally {
    isResolvingConflict.value = false;
    conflictResolution.value = '';
  }
};

// Note: deployFlows is provided by useDeploymentOperations composable

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
    const flows_data = await deploymentService.loadFlows();
    if (flows_data) {
      flows.value = flows_data as Flow[];
    }
  } catch (error) {
    console.error("Error loading flows:", error);
  } finally {
    isLoading.value = false;
  }
};

const loadHierarchyConfig = async () => {
  try {
    const hierarchy = await deploymentService.loadHierarchyConfig();
    if (hierarchy) {
      hierarchyConfig.value = hierarchy;

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
    const instances = await deploymentService.loadNiFiInstances();
    nifiInstances.value = instances;
  } catch (error) {
    console.error("Error loading NiFi instances:", error);
  }
};

const loadRegistryFlows = async () => {
  try {
    const registry_flows = await deploymentService.loadRegistryFlows();
    registryFlows.value = registry_flows;
  } catch (error) {
    console.error("Error loading registry flows:", error);
  }
};

const loadDeploymentSettings = async () => {
  try {
    const settings = await deploymentService.loadDeploymentSettings();
    deploymentSettings.value = settings;
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
  max-width: 1000px;
  margin-bottom: 30px;

  .section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 10px;

    i {
      font-size: 1.3rem;
      color: #2196f3;
    }
  }

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

// Version Selection
.version-selection-section {
  margin-bottom: 30px;
}

.version-card {
  border: 2px solid #e9ecef;
  border-radius: 8px;
  margin-bottom: 16px;
  overflow: hidden;
  transition: border-color 0.2s;

  &:hover {
    border-color: #2196f3;
  }
}

.version-card-header {
  padding: 12px 16px;
  background: #f8f9fa;
  border-bottom: 1px solid #e9ecef;

  strong {
    font-size: 0.95rem;
    color: #2c3e50;
  }

  .badge {
    font-size: 0.75rem;
    padding: 3px 8px;
    border-radius: 10px;
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
}

.version-card-body {
  padding: 16px;

  .alert {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 0.875rem;

    i {
      font-size: 1.2rem;
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

// Version badges in review
.version-badge {
  padding: 4px 12px;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  display: inline-block;

  &.latest-version {
    background: #28a745;
    color: white;
  }

  &.specific-version {
    background: #007bff;
    color: white;
  }
}
</style>
