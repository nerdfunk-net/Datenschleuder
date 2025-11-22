<template>
  <div class="registry-flows">
    <div class="page-card">
      <!-- Header -->
      <div class="card-header">
        <h2 class="card-title">
          Registry Flows
        </h2>
        <div v-if="isAdmin" class="header-actions">
          <b-button variant="outline-secondary" @click="showImportModal = true">
            <i class="pe-7s-upload"></i> Import Flow
          </b-button>
          <b-button variant="light" @click="showAddFlowModal = true">
            <i class="pe-7s-plus"></i> Add Flow
          </b-button>
        </div>
      </div>

      <!-- Filter Section -->
      <div class="card-body border-bottom">
        <div class="row align-items-center">
          <div class="col-md-4">
            <label class="form-label small">Filter by NiFi Instance:</label>
            <b-form-select
              v-model="selectedFilterInstance"
              :options="filterInstanceOptions"
              @change="applyInstanceFilter"
            />
          </div>
          <div class="col-md-8 text-end">
            <small class="text-muted">
              Showing {{ registryFlows.length }} flows
              {{ selectedFilterInstance !== null ? `for selected instance` : `(all instances)` }}
            </small>
          </div>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-5">
        <b-spinner variant="primary" />
        <p class="mt-3 text-muted">
          Loading registry flows...
        </p>
      </div>

      <!-- Table -->
      <div v-else class="table-responsive">
        <table class="table flows-table">
          <thead>
            <tr>
              <th>Flow Name</th>
              <th>NiFi Instance</th>
              <th>Registry</th>
              <th>Bucket</th>
              <th>Description</th>
              <th class="text-end">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="flow in registryFlows" :key="flow.id">
              <td>
                <strong>{{ flow.flow_name }}</strong>
              </td>
              <td>{{ flow.nifi_instance_name }}</td>
              <td>{{ flow.registry_name }}</td>
              <td>{{ flow.bucket_name }}</td>
              <td class="text-muted small">
                {{ flow.flow_description || "No description" }}
              </td>
              <td class="text-end">
                <div v-if="isAdmin" class="btn-group" role="group">
                  <!-- Loading spinner while registry details are being fetched -->
                  <template v-if="!getRegistryDetails(flow)">
                    <b-button
                      size="sm"
                      variant="outline-secondary"
                      disabled
                      title="Loading registry details..."
                    >
                      <b-spinner small />
                    </b-button>
                  </template>

                  <!-- GitHub Link Button -->
                  <template v-else-if="isGitHubRegistry(flow)">
                    <a
                      :href="getGitHubUrl(flow) || undefined"
                      target="_blank"
                      class="btn btn-sm btn-outline-primary"
                      title="View on GitHub"
                    >
                      <i class="pe-7s-link"></i> GitHub
                    </a>
                  </template>

                  <!-- Export Dropdown (for non-GitHub registries) -->
                  <template v-else>
                    <b-dropdown
                      size="sm"
                      variant="outline-primary"
                      :disabled="exportingFlowIds.has(`${flow.registry_id}_${flow.bucket_id}_${flow.flow_id}`)"
                      title="Export Flow"
                      no-caret
                      split
                      @click="handleExport(flow, 'json')"
                    >
                      <template #button-content>
                        <b-spinner
                          v-if="exportingFlowIds.has(`${flow.registry_id}_${flow.bucket_id}_${flow.flow_id}`)"
                          small
                        />
                        <i v-else class="pe-7s-download"></i>
                      </template>
                      <b-dropdown-item @click="handleExport(flow, 'json')">
                        Export as JSON
                      </b-dropdown-item>
                      <b-dropdown-item @click="handleExport(flow, 'yaml')">
                        Export as YAML
                      </b-dropdown-item>
                    </b-dropdown>
                  </template>

                  <b-button
                    size="sm"
                    variant="outline-danger"
                    title="Remove"
                    @click="handleDelete(flow)"
                  >
                    <i class="pe-7s-trash"></i>
                  </b-button>
                </div>
                <div v-else class="text-muted small">
                  <i class="pe-7s-lock"></i> Admin only
                </div>
              </td>
            </tr>
            <tr v-if="registryFlows.length === 0">
              <td colspan="6" class="text-center py-4 text-muted">
                <i class="pe-7s-info display-4 d-block mb-2"></i>
                No registry flows configured. Click "Add Flow" to get started.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Add Flow Modal -->
    <b-modal
      v-model="showAddFlowModal"
      title="Add Registry Flows"
      size="xl"
      modal-class="add-flow-modal"
    >
      <div class="add-flow-content">
        <!-- Step 1: Select NiFi Instance -->
        <div class="selection-step">
          <h6 class="step-title">
            1. Select NiFi Instance
          </h6>
          <b-form-select
            v-model="selectedInstance"
            :options="instanceOptions"
            size="sm"
            @change="onInstanceChange"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select NiFi Instance --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 2: Select Bucket -->
        <div v-if="selectedInstance" class="selection-step">
          <h6 class="step-title">
            2. Select Bucket
          </h6>
          <div v-if="loadingBuckets" class="text-center py-3">
            <b-spinner small variant="primary" />
            <span class="ms-2">Loading buckets...</span>
          </div>
          <b-form-select
            v-else
            v-model="selectedBucket"
            :options="bucketOptions"
            size="sm"
            @change="onBucketChange"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select Bucket --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 3: Select Flows -->
        <div v-if="selectedBucket" class="selection-step">
          <h6 class="step-title">
            3. Select Flows
          </h6>
          <div v-if="loadingFlows" class="text-center py-3">
            <b-spinner small variant="primary" />
            <span class="ms-2">Loading flows...</span>
          </div>
          <div v-else class="flows-list">
            <div
              v-if="availableFlows.length === 0"
              class="text-muted text-center py-3"
            >
              No flows found in this bucket
            </div>
            <div
              v-for="flow in availableFlows"
              :key="flow.identifier"
              class="flow-item"
            >
              <b-form-checkbox v-model="selectedFlows" :value="flow">
                <div class="flow-info">
                  <div class="flow-name">
                    {{ flow.name }}
                  </div>
                  <div class="flow-desc">
                    {{ flow.description || "No description" }}
                  </div>
                </div>
              </b-form-checkbox>
            </div>
          </div>
        </div>
      </div>

      <template #footer>
        <b-button
          variant="secondary"
          size="sm"
          @click="closeModal"
        >
          Cancel
        </b-button>
        <b-button
          variant="primary"
          size="sm"
          :disabled="selectedFlows.length === 0 || isSaving"
          @click="saveFlows"
        >
          <b-spinner v-if="isSaving" small class="me-1" />
          {{ isSaving ? "Saving..." : `Save ${selectedFlows.length} Flow(s)` }}
        </b-button>
      </template>
    </b-modal>

    <!-- Import Flow Modal -->
    <b-modal
      v-model="showImportModal"
      title="Import Flow"
      size="lg"
      modal-class="import-flow-modal"
    >
      <div class="import-flow-content">
        <!-- Step 1: Select NiFi Instance -->
        <div class="selection-step">
          <h6 class="step-title">
            1. Select NiFi Instance
          </h6>
          <b-form-select
            v-model="importSelectedInstance"
            :options="instanceOptions"
            size="sm"
            @change="onImportInstanceChange"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select NiFi Instance --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 2: Select Registry -->
        <div v-if="importSelectedInstance" class="selection-step">
          <h6 class="step-title">
            2. Select Registry
          </h6>
          <div v-if="loadingImportRegistries" class="text-center py-3">
            <b-spinner small variant="primary" />
            <span class="ms-2">Loading registries...</span>
          </div>
          <b-form-select
            v-else
            v-model="importSelectedRegistry"
            :options="importRegistryOptions"
            size="sm"
            @change="onImportRegistryChange"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select Registry --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 3: Select Bucket -->
        <div v-if="importSelectedRegistry" class="selection-step">
          <h6 class="step-title">
            3. Select Bucket
          </h6>
          <div v-if="loadingImportBuckets" class="text-center py-3">
            <b-spinner small variant="primary" />
            <span class="ms-2">Loading buckets...</span>
          </div>
          <b-form-select
            v-else
            v-model="importSelectedBucket"
            :options="importBucketOptions"
            size="sm"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select Bucket --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 4: Import Mode -->
        <div v-if="importSelectedBucket" class="selection-step">
          <h6 class="step-title">
            4. Import Mode
          </h6>
          <b-form-radio-group v-model="importMode" :options="importModeOptions" />
        </div>

        <!-- Step 5: Flow Name (for new flow) -->
        <div v-if="importSelectedBucket && importMode === 'new'" class="selection-step">
          <h6 class="step-title">
            5. Flow Name
          </h6>
          <b-form-input
            v-model="importFlowName"
            placeholder="Enter flow name for new flow"
            size="sm"
          />
        </div>

        <!-- Step 5/6: Existing Flow (for existing flow) -->
        <div v-if="importSelectedBucket && importMode === 'existing'" class="selection-step">
          <h6 class="step-title">
            5. Select Existing Flow
          </h6>
          <div v-if="loadingImportFlows" class="text-center py-3">
            <b-spinner small variant="primary" />
            <span class="ms-2">Loading flows...</span>
          </div>
          <b-form-select
            v-else
            v-model="importSelectedFlow"
            :options="importFlowOptions"
            size="sm"
          >
            <template #first>
              <b-form-select-option
                :value="null"
                disabled
              >
                -- Select Flow --
              </b-form-select-option>
            </template>
          </b-form-select>
        </div>

        <!-- Step 6/7: File Upload -->
        <div v-if="importSelectedBucket && ((importMode === 'new' && importFlowName) || (importMode === 'existing' && importSelectedFlow))" class="selection-step">
          <h6 class="step-title">
            {{ importMode === 'new' ? '6' : '6' }}. Select File
          </h6>
          <b-form-file
            v-model="importFile"
            placeholder="Choose a JSON or YAML file..."
            accept=".json,.yaml,.yml"
            size="sm"
          />
        </div>
      </div>

      <template #footer>
        <b-button
          variant="secondary"
          size="sm"
          @click="closeImportModal"
        >
          Cancel
        </b-button>
        <b-button
          variant="primary"
          size="sm"
          :disabled="!canImport || isImporting"
          @click="importFlow"
        >
          <b-spinner v-if="isImporting" small class="me-1" />
          {{ isImporting ? "Importing..." : "Import Flow" }}
        </b-button>
      </template>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { apiRequest } from "@/utils/api";
import { useAuth } from "@/composables/useAuth";

const { isAdmin } = useAuth();

interface RegistryFlow {
  id: number;
  nifi_instance_id: number;
  nifi_instance_name: string;
  nifi_instance_url: string;
  registry_id: string;
  registry_name: string;
  bucket_id: string;
  bucket_name: string;
  flow_id: string;
  flow_name: string;
  flow_description: string | null;
  created_at: string;
  modified_at: string;
}

interface NiFiInstance {
  id: number;
  hierarchy_attribute: string;
  hierarchy_value: string;
  nifi_url: string;
  username: string | null;
  use_ssl: boolean;
  verify_ssl: boolean;
}

interface Bucket {
  identifier: string;
  name: string;
  description: string;
}

interface Flow {
  identifier: string;
  name: string;
  description: string;
  bucketIdentifier: string;
  bucketName: string;
}

interface Registry {
  id: string;
  name: string;
}

const isLoading = ref(false);
const registryFlows = ref<RegistryFlow[]>([]);
const selectedFilterInstance = ref<number | null>(null);

// Modal state
const showAddFlowModal = ref(false);
const selectedInstance = ref<NiFiInstance | null>(null);
const selectedRegistry = ref<Registry | null>(null);
const selectedBucket = ref<Bucket | null>(null);
const selectedFlows = ref<Flow[]>([]);
const isSaving = ref(false);

// Data loading
const nifiInstances = ref<NiFiInstance[]>([]);
const buckets = ref<Bucket[]>([]);
const availableFlows = ref<Flow[]>([]);

const loadingBuckets = ref(false);
const loadingFlows = ref(false);

// Import modal state
const showImportModal = ref(false);
const importSelectedInstance = ref<NiFiInstance | null>(null);
const importSelectedRegistry = ref<Registry | null>(null);
const importSelectedBucket = ref<Bucket | null>(null);
const importSelectedFlow = ref<Flow | null>(null);
const importFlowName = ref("");
const importFile = ref<File | null>(null);
const importMode = ref<"new" | "existing">("new");
const isImporting = ref(false);

// Import data loading
const importRegistries = ref<Registry[]>([]);
const importBuckets = ref<Bucket[]>([]);
const importFlows = ref<Flow[]>([]);
const loadingImportRegistries = ref(false);
const loadingImportBuckets = ref(false);
const loadingImportFlows = ref(false);

// Export state
const exportingFlowIds = ref<Set<string>>(new Set());

// Registry details cache (registry_id -> details)
const registryDetailsCache = ref<Map<string, any>>(new Map());

const instanceOptions = computed(() => {
  return nifiInstances.value.map((instance) => ({
    value: instance,
    text: `${instance.hierarchy_value} (${instance.nifi_url})`,
  }));
});

const filterInstanceOptions = computed(() => {
  return [
    { value: null, text: "All Instances" },
    ...nifiInstances.value.map((instance) => ({
      value: instance.id,
      text: `${instance.hierarchy_value} (${instance.nifi_url})`,
    }))
  ];
});

const bucketOptions = computed(() => {
  return buckets.value.map((bucket) => ({
    value: bucket,
    text: bucket.name,
  }));
});

// Import computed properties
const importRegistryOptions = computed(() => {
  return importRegistries.value.map((registry) => ({
    value: registry,
    text: registry.name,
  }));
});

const importBucketOptions = computed(() => {
  return importBuckets.value.map((bucket) => ({
    value: bucket,
    text: bucket.name,
  }));
});

const importFlowOptions = computed(() => {
  return importFlows.value.map((flow) => ({
    value: flow,
    text: flow.name,
  }));
});

const importModeOptions = computed(() => [
  { text: "Create new flow", value: "new" },
  { text: "Add version to existing flow", value: "existing" },
]);

const canImport = computed(() => {
  return (
    importSelectedBucket.value &&
    importFile.value &&
    ((importMode.value === "new" && importFlowName.value.trim()) ||
      (importMode.value === "existing" && importSelectedFlow.value))
  );
});

const loadRegistryFlows = async () => {
  isLoading.value = true;
  try {
    // Build API URL with optional nifi_instance filter
    let apiUrl = "/api/registry-flows/";
    if (selectedFilterInstance.value !== null) {
      apiUrl += `?nifi_instance=${selectedFilterInstance.value}`;
    }
    
    registryFlows.value = await apiRequest(apiUrl);

    // Load registry details for each unique registry
    const uniqueRegistries = new Set<string>();
    console.log('Building unique registries list from flows:', registryFlows.value.length);
    for (const flow of registryFlows.value) {
      const instanceId = getInstanceIdByUrl(flow.nifi_instance_url);
      const key = `${instanceId}_${flow.registry_id}`;
      console.log(`Flow ${flow.flow_name}: instanceId=${instanceId}, registryId=${flow.registry_id}, key=${key}`);
      if (!uniqueRegistries.has(key) && !registryDetailsCache.value.has(key)) {
        uniqueRegistries.add(key);
      }
    }
    console.log('Unique registries to fetch:', Array.from(uniqueRegistries));

    // Fetch details for each unique registry
    for (const key of uniqueRegistries) {
      const parts = key.split('_');
      const instanceIdStr = parts[0];
      const registryId = parts.slice(1).join('_'); // Handle registry IDs with underscores
      const instanceId = parseInt(instanceIdStr);

      if (instanceId > 0) {
        try {
          const details = await apiRequest(
            `/api/nifi-instances/${instanceId}/registry/${registryId}/details`
          );
          console.log(`Loaded registry details for ${key}:`, details);
          registryDetailsCache.value.set(key, details);
        } catch (error) {
          console.error(`Failed to load registry details for ${key}:`, error);
        }
      }
    }

    console.log('Registry details cache:', registryDetailsCache.value);
  } catch (error) {
    console.error("Error loading registry flows:", error);
    alert("Failed to load registry flows");
  } finally {
    isLoading.value = false;
  }
};

const applyInstanceFilter = async () => {
  // Reload data with the new filter
  await loadRegistryFlows();
};

const loadNiFiInstances = async () => {
  try {
    nifiInstances.value = await apiRequest("/api/nifi-instances/");
  } catch (error) {
    console.error("Error loading NiFi instances:", error);
  }
};

const onInstanceChange = async () => {
  if (!selectedInstance.value) return;

  // Reset downstream selections
  selectedBucket.value = null;
  selectedFlows.value = [];
  buckets.value = [];
  availableFlows.value = [];

  // Load registries and buckets for this instance
  loadingBuckets.value = true;
  try {
    // Get registry clients from this NiFi instance
    const response = await apiRequest(
      `/api/nifi/${selectedInstance.value.id}/get-registries`,
    ) as any;

    if (response.registry_clients && response.registry_clients.length > 0) {
      // Use the first registry (or we could let user select)
      const firstRegistry = response.registry_clients[0];
      selectedRegistry.value = {
        id: firstRegistry.id,
        name: firstRegistry.name,
      };

      // Load buckets from this registry
      const bucketsResponse = await apiRequest(
        `/api/nifi/${selectedInstance.value.id}/registry/${firstRegistry.id}/get-buckets`,
      ) as any;
      buckets.value = bucketsResponse.buckets || [];
    } else {
      alert("No registries found for this NiFi instance");
      buckets.value = [];
    }
  } catch (error) {
    console.error("Error loading buckets:", error);
    alert("Failed to load buckets");
  } finally {
    loadingBuckets.value = false;
  }
};

const onBucketChange = async () => {
  if (
    !selectedBucket.value ||
    !selectedInstance.value ||
    !selectedRegistry.value
  )
    return;

  // Reset flow selection
  selectedFlows.value = [];
  availableFlows.value = [];

  // Load flows for this bucket
  loadingFlows.value = true;
  try {
    const response = await apiRequest(
      `/api/nifi/${selectedInstance.value.id}/registry/${selectedRegistry.value.id}/${selectedBucket.value.identifier}/get-flows`,
    ) as any;
    availableFlows.value = response.flows || [];
  } catch (error) {
    console.error("Error loading flows:", error);
    alert("Failed to load flows");
  } finally {
    loadingFlows.value = false;
  }
};

const saveFlows = async () => {
  if (
    !selectedInstance.value ||
    !selectedRegistry.value ||
    !selectedBucket.value ||
    selectedFlows.value.length === 0
  ) {
    return;
  }

  isSaving.value = true;
  try {
    const flowsToSave = selectedFlows.value.map((flow) => ({
      nifi_instance_id: selectedInstance.value!.id,
      nifi_instance_name: selectedInstance.value!.hierarchy_value,
      nifi_instance_url: selectedInstance.value!.nifi_url,
      registry_id: selectedRegistry.value!.id,
      registry_name: selectedRegistry.value!.name,
      bucket_id: selectedBucket.value!.identifier,
      bucket_name: selectedBucket.value!.name,
      flow_id: flow.identifier,
      flow_name: flow.name,
      flow_description: flow.description || null,
    }));

    const result = await apiRequest("/api/registry-flows/", {
      method: "POST",
      body: JSON.stringify(flowsToSave),
    }) as any;

    alert(
      `Successfully saved ${result.created} flow(s)` +
        (result.skipped > 0 ? ` (${result.skipped} duplicate(s) skipped)` : ""),
    );
    closeModal();
    await loadRegistryFlows();
  } catch (error: any) {
    console.error("Error saving flows:", error);
    alert("Error: " + (error.message || "Failed to save flows"));
  } finally {
    isSaving.value = false;
  }
};

const handleDelete = async (flow: RegistryFlow) => {
  if (!confirm(`Are you sure you want to remove "${flow.flow_name}"?`)) {
    return;
  }

  try {
    await apiRequest(`/api/registry-flows/${flow.id}`, { method: "DELETE" });
    alert("Flow removed successfully!");
    await loadRegistryFlows();
  } catch (error: any) {
    console.error("Error deleting flow:", error);
    alert("Error: " + (error.message || "Failed to delete flow"));
  }
};

const closeModal = () => {
  showAddFlowModal.value = false;
  selectedInstance.value = null;
  selectedRegistry.value = null;
  selectedBucket.value = null;
  selectedFlows.value = [];
  buckets.value = [];
  availableFlows.value = [];
};

// Export flow function
const handleExport = async (flow: RegistryFlow, format: 'json' | 'yaml' = 'json') => {
  const flowKey = `${flow.registry_id}_${flow.bucket_id}_${flow.flow_id}`;
  
  if (exportingFlowIds.value.has(flowKey)) {
    return; // Already exporting this flow
  }

  exportingFlowIds.value.add(flowKey);
  
  try {
    const instanceId = getInstanceIdByUrl(flow.nifi_instance_url);
    const url = `/api/nifi-instances/${instanceId}/registry/${flow.registry_id}/${flow.bucket_id}/export-flow?flow_id=${flow.flow_id}&mode=${format}`;
    
    console.log('Export URL:', url);
    
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) {
      headers["Authorization"] = `Bearer ${token}`;
    }
    
    console.log('Headers:', headers);
    
    const response = await fetch(url, {
      method: 'GET',
      headers,
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("rememberMe");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: "Export failed" }));
      throw new Error(error.detail || `Export failed with status ${response.status}`);
    }

    // Get the blob from response
    const blob = await response.blob();
    
    // Create download link
    const downloadUrl = window.URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = downloadUrl;
    link.download = `${flow.flow_name}.${format}`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // Clean up the blob URL
    window.URL.revokeObjectURL(downloadUrl);
  } catch (error) {
    console.error("Error exporting flow:", error);
    alert(`Failed to export flow: ${error instanceof Error ? error.message : String(error)}`);
  } finally {
    exportingFlowIds.value.delete(flowKey);
  }
};

// Helper function to get instance ID by URL
const getInstanceIdByUrl = (url: string): number => {
  const instance = nifiInstances.value.find(inst => inst.nifi_url === url);
  return instance?.id || 0;
};

// Helper function to get registry details for a flow
const getRegistryDetails = (flow: RegistryFlow) => {
  const instanceId = getInstanceIdByUrl(flow.nifi_instance_url);
  const key = `${instanceId}_${flow.registry_id}`;
  return registryDetailsCache.value.get(key);
};

// Helper function to check if registry is GitHub
const isGitHubRegistry = (flow: RegistryFlow): boolean => {
  const details = getRegistryDetails(flow);
  console.log(`Checking if GitHub registry for flow ${flow.flow_name}:`, {
    hasDetails: !!details,
    isGithub: details?.is_github,
    type: details?.type
  });
  return details?.is_github === true;
};

// Helper function to get GitHub URL for a flow
const getGitHubUrl = (flow: RegistryFlow): string | null => {
  const details = getRegistryDetails(flow);
  if (!details?.github_url) return null;

  // Append bucket and flow path with .json extension
  let url = details.github_url;

  // Replace /tree/ with /blob/ for file viewing
  if (!url.includes('/tree/')) {
    url += '/blob/main';
  } else {
    url = url.replace('/tree/', '/blob/');
  }

  url += `/${flow.bucket_id}/${flow.flow_id}.json`;

  return url;
};

// Import modal functions
const closeImportModal = () => {
  showImportModal.value = false;
  resetImportForm();
};

const resetImportForm = () => {
  importSelectedInstance.value = null;
  importSelectedRegistry.value = null;
  importSelectedBucket.value = null;
  importSelectedFlow.value = null;
  importFlowName.value = "";
  importFile.value = null;
  importMode.value = "new";
  importRegistries.value = [];
  importBuckets.value = [];
  importFlows.value = [];
};

const onImportInstanceChange = async () => {
  if (!importSelectedInstance.value) return;

  // Reset downstream selections
  importSelectedRegistry.value = null;
  importSelectedBucket.value = null;
  importSelectedFlow.value = null;
  importRegistries.value = [];
  importBuckets.value = [];
  importFlows.value = [];

  // Load registries for this instance
  loadingImportRegistries.value = true;
  try {
    const response = await apiRequest(
      `/api/nifi/${importSelectedInstance.value.id}/get-registries`,
    ) as any;
    importRegistries.value = response.registries || [];
  } catch (error) {
    console.error("Error loading registries:", error);
    alert("Failed to load registries");
  } finally {
    loadingImportRegistries.value = false;
  }
};

const onImportRegistryChange = async () => {
  if (!importSelectedInstance.value || !importSelectedRegistry.value) return;

  // Reset downstream selections
  importSelectedBucket.value = null;
  importSelectedFlow.value = null;
  importBuckets.value = [];
  importFlows.value = [];

  // Load buckets for this registry
  loadingImportBuckets.value = true;
  try {
    const response = await apiRequest(
      `/api/nifi/${importSelectedInstance.value.id}/registry/${importSelectedRegistry.value.id}/get-buckets`,
    ) as any;
    importBuckets.value = response.buckets || [];
  } catch (error) {
    console.error("Error loading buckets:", error);
    alert("Failed to load buckets");
  } finally {
    loadingImportBuckets.value = false;
  }
};

const loadImportFlows = async () => {
  if (!importSelectedInstance.value || !importSelectedRegistry.value || !importSelectedBucket.value) return;

  loadingImportFlows.value = true;
  try {
    const response = await apiRequest(
      `/api/nifi/${importSelectedInstance.value.id}/registry/${importSelectedRegistry.value.id}/${importSelectedBucket.value.identifier}/get-flows`,
    ) as any;
    importFlows.value = response.flows || [];
  } catch (error) {
    console.error("Error loading flows:", error);
    alert("Failed to load flows");
  } finally {
    loadingImportFlows.value = false;
  }
};

const importFlow = async () => {
  if (!canImport.value) return;

  isImporting.value = true;
  try {
    const formData = new FormData();
    formData.append('file', importFile.value!);
    
    if (importMode.value === 'new') {
      formData.append('flow_name', importFlowName.value);
    } else {
      formData.append('flow_id', importSelectedFlow.value!.identifier);
    }

    const url = `/api/nifi-instances/${importSelectedInstance.value!.id}/registry/${importSelectedRegistry.value!.id}/${importSelectedBucket.value!.identifier}/import-flow`;
    
    const token = localStorage.getItem('token');
    const headers: Record<string, string> = {};
    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    const response = await fetch(url, {
      method: 'POST',
      body: formData,
      headers,
    });

    // Handle 401 Unauthorized
    if (response.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("rememberMe");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({ detail: 'Import failed' }));
      throw new Error(errorData.detail || `Import failed with status ${response.status}`);
    }

    const result = await response.json();
    alert(`Flow imported successfully: ${result.flow_name}`);
    closeImportModal();
    
    // Refresh the flows list
    await loadRegistryFlows();
  } catch (error) {
    console.error("Error importing flow:", error);
    alert(`Failed to import flow: ${error instanceof Error ? error.message : String(error)}`);
  } finally {
    isImporting.value = false;
  }
};

// Watch for bucket selection in import modal to load flows for existing mode
watch(
  [importSelectedBucket, importMode],
  () => {
    if (importMode.value === "existing" && importSelectedBucket.value) {
      loadImportFlows();
    }
  }
);

onMounted(async () => {
  await loadNiFiInstances();
  await loadRegistryFlows();
});
</script>

<style scoped lang="scss">
.registry-flows {
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

.header-actions {
  display: flex;
  gap: 10px;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: white;
  margin: 0;
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
    }

    tr {
      transition: background 0.2s;

      &:hover {
        background: #f8f9fa;
      }
    }
  }
}

.add-flow-content {
  padding: 10px 0;
}

.selection-step {
  margin-bottom: 24px;
  padding: 16px;
  background: #f8f9fa;
  border-radius: 6px;

  .step-title {
    font-weight: 600;
    color: #495057;
    margin-bottom: 12px;
    font-size: 0.95rem;
  }
}

.flows-list {
  max-height: 400px;
  overflow-y: auto;
  padding: 8px;
  background: white;
  border-radius: 4px;

  .flow-item {
    padding: 12px;
    margin-bottom: 8px;
    background: #f8f9fa;
    border-radius: 4px;
    transition: background 0.2s;

    &:hover {
      background: #e9ecef;
    }

    .flow-info {
      margin-left: 8px;

      .flow-name {
        font-weight: 600;
        color: #495057;
        font-size: 0.95rem;
      }

      .flow-desc {
        font-size: 0.85rem;
        color: #6c757d;
        margin-top: 4px;
      }
    }
  }
}
</style>

<style lang="scss">
// Global styles for modal (not scoped)
.add-flow-modal {
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
    padding: 20px;
  }

  .modal-footer {
    padding: 12px 20px;
    background: #f8f9fa;
    border-top: 2px solid #e9ecef;
  }
}
</style>
