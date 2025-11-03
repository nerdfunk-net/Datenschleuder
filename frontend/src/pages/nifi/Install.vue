<template>
  <div class="install-page">
    <div class="page-header mb-4">
      <h2>NiFi Installation</h2>
      <p class="text-muted">
        Check and create process groups for flow hierarchy paths
      </p>
    </div>

    <!-- Source Path Panel -->
    <div class="card mb-4">
      <div 
        class="card-header d-flex justify-content-between align-items-center"
        @click="sourceCollapsed = !sourceCollapsed"
        style="cursor: pointer;"
      >
        <h5 class="mb-0">
          <i :class="sourceCollapsed ? 'pe-7s-angle-right' : 'pe-7s-angle-down'" class="me-2"></i>
          <i class="pe-7s-upload me-2"></i>Source Path
        </h5>
        <div class="d-flex gap-2" @click.stop>
          <b-button
            variant="light"
            size="sm"
            @click="checkSourcePath"
            :disabled="!sourceInstance || loadingSourcePath"
            title="Reload and re-check source path status"
          >
            <b-spinner v-if="loadingSourcePath" small></b-spinner>
            <i v-else class="pe-7s-refresh-2"></i>
            Reload paths
          </b-button>
        </div>
      </div>
      <b-collapse v-model="sourceCollapsed" id="source-collapse">
        <div class="card-body">
          <p class="text-muted">
            Check if source process groups exist for the flow hierarchy. The last
            hierarchy item will not be checked.
          </p>

          <div class="mb-3">
            <label class="form-label">Select NiFi Instance</label>
            <b-form-select
              v-model="sourceInstance"
              :options="instanceOptions"
              @change="checkSourcePath"
            />
          </div>

        <div v-if="sourceStatus" class="status-section">
          <h6>Status:</h6>
          <div
            v-for="(status, index) in sourceStatus"
            :key="index"
            class="status-item"
          >
            <div class="d-flex align-items-center justify-content-between">
              <div class="status-info">
                <i
                  :class="
                    status.exists ? 'pe-7s-check text-success' : 'pe-7s-close-circle text-danger'
                  "
                ></i>
                <span>{{ status.path }}</span>
                <span v-if="status.exists" class="badge bg-success ms-2"
                  >Exists</span
                >
                <span v-else class="badge bg-danger ms-2">Missing</span>
              </div>
              
              <!-- Individual deployment controls for missing paths -->
              <div v-if="!status.exists" class="deploy-controls d-flex align-items-center gap-2">
                <b-form-select
                  v-model="selectedSourceParameters[status.path]"
                  :options="sourceParameterOptions"
                  size="sm"
                  style="min-width: 140px; max-width: 140px;"
                  :disabled="!sourceParameterContexts.length"
                  title="Select parameter context (optional)"
                />
                <b-form-select
                  v-model="selectedSourceFlows[status.path]"
                  :options="sourceFlowOptions"
                  size="sm"
                  style="min-width: 250px; max-width: 250px;"
                  :disabled="!sourceRegistryFlows.length"
                  title="Select flow to deploy"
                />
                <b-button
                  variant="success"
                  size="sm"
                  class="deploy-btn"
                  @click="deployFlow(status.path, sourceInstance!, 'source')"
                  :disabled="!selectedSourceFlows[status.path] || deployingPaths.has(status.path)"
                  title="Deploy flow to this path"
                >
                  <b-spinner v-if="deployingPaths.has(status.path)" small></b-spinner>
                  <i v-else class="pe-7s-plus"></i>
                </b-button>
              </div>
            </div>
          </div>

          <div v-if="!sourceRegistryFlows.length && sourceMissingCount > 0" class="alert alert-info mt-3">
            <i class="pe-7s-info me-2"></i>
            No registry flows found for this instance. Please add some flows in the Registry section first.
          </div>
        </div>
      </div>
      </b-collapse>
    </div>

    <!-- Destination Path Panel -->
    <div class="card">
      <div 
        class="card-header d-flex justify-content-between align-items-center"
        @click="destinationCollapsed = !destinationCollapsed"
        style="cursor: pointer;"
      >
        <h5 class="mb-0">
          <i :class="destinationCollapsed ? 'pe-7s-angle-right' : 'pe-7s-angle-down'" class="me-2"></i>
          <i class="pe-7s-download me-2"></i>Destination Path
        </h5>
        <div class="d-flex gap-2" @click.stop>
          <b-button
            variant="light"
            size="sm"
            @click="checkDestinationPath"
            :disabled="!destinationInstance || loadingDestinationPath"
            title="Reload and re-check destination path status"
          >
            <b-spinner v-if="loadingDestinationPath" small></b-spinner>
            <i v-else class="pe-7s-refresh-2"></i>
            Reload paths
          </b-button>
        </div>
      </div>
      <b-collapse v-model="destinationCollapsed" id="destination-collapse">
        <div class="card-body">
          <p class="text-muted">
            Check if destination process groups exist for the flow hierarchy. The
            last hierarchy item will not be checked.
          </p>

          <div class="mb-3">
            <label class="form-label">Select NiFi Instance</label>
            <b-form-select
              v-model="destinationInstance"
              :options="instanceOptions"
              @change="checkDestinationPath"
            />
          </div>

          <div v-if="destinationStatus" class="status-section">
            <h6>Status:</h6>
            <div
              v-for="(status, index) in destinationStatus"
              :key="index"
              class="status-item"
            >
            <div class="d-flex align-items-center justify-content-between">
              <div class="status-info">
                <i
                  :class="
                    status.exists ? 'pe-7s-check text-success' : 'pe-7s-close-circle text-danger'
                  "
                ></i>
                <span>{{ status.path }}</span>
                <span v-if="status.exists" class="badge bg-success ms-2"
                  >Exists</span
                >
                <span v-else class="badge bg-danger ms-2">Missing</span>
              </div>
              
              <!-- Individual deployment controls for missing paths -->
              <div v-if="!status.exists" class="deploy-controls d-flex align-items-center gap-2">
                <b-form-select
                  v-model="selectedDestinationParameters[status.path]"
                  :options="destinationParameterOptions"
                  size="sm"
                  style="min-width: 140px; max-width: 140px;"
                  :disabled="!destinationParameterContexts.length"
                  title="Select parameter context (optional)"
                />
                <b-form-select
                  v-model="selectedDestinationFlows[status.path]"
                  :options="destinationFlowOptions"
                  size="sm"
                  style="min-width: 250px; max-width: 250px;"
                  :disabled="!destinationRegistryFlows.length"
                  title="Select flow to deploy"
                />
                <b-button
                  variant="success"
                  size="sm"
                  class="deploy-btn"
                  @click="deployFlow(status.path, destinationInstance!, 'destination')"
                  :disabled="!selectedDestinationFlows[status.path] || deployingPaths.has(status.path)"
                  title="Deploy flow to this path"
                >
                  <b-spinner v-if="deployingPaths.has(status.path)" small></b-spinner>
                  <i v-else class="pe-7s-plus"></i>
                </b-button>
              </div>
            </div>
          </div>

          <div v-if="!destinationRegistryFlows.length && destinationMissingCount > 0" class="alert alert-info mt-3">
            <i class="pe-7s-info me-2"></i>
            No registry flows found for this instance. Please add some flows in the Registry section first.
          </div>
        </div>
      </div>
      </b-collapse>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { apiRequest } from "@/utils/api";

interface NiFiInstance {
  id: number;
  hierarchy_value: string;
  nifi_url: string;
}

interface PathStatus {
  path: string;
  exists: boolean;
}

interface RegistryFlow {
  id: number;
  nifi_instance_id: number;
  flow_name: string;
  registry_name: string;
  bucket_name: string;
  flow_id: string;
  bucket_id: string;
  registry_id: string;
}

interface ParameterContext {
  id: string;
  name: string;
}

const sourceInstance = ref<number | null>(null);
const destinationInstance = ref<number | null>(null);
const instances = ref<NiFiInstance[]>([]);
const sourceStatus = ref<PathStatus[] | null>(null);
const destinationStatus = ref<PathStatus[] | null>(null);
const loadingSourcePath = ref(false);
const loadingDestinationPath = ref(false);
const sourceCollapsed = ref(true);
const destinationCollapsed = ref(true);

// Registry flows for deployment
const sourceRegistryFlows = ref<RegistryFlow[]>([]);
const destinationRegistryFlows = ref<RegistryFlow[]>([]);
const selectedSourceFlows = ref<{ [path: string]: number | null }>({});
const selectedDestinationFlows = ref<{ [path: string]: number | null }>({});
const deployingPaths = ref<Set<string>>(new Set());

// Parameter contexts for deployment
const sourceParameterContexts = ref<ParameterContext[]>([]);
const destinationParameterContexts = ref<ParameterContext[]>([]);
const selectedSourceParameters = ref<{ [path: string]: string | null }>({});
const selectedDestinationParameters = ref<{ [path: string]: string | null }>({});

const instanceOptions = computed(() => {
  return [
    { value: null, text: "Select an instance..." },
    ...instances.value.map((inst) => ({
      value: inst.id,
      text: `${inst.hierarchy_value} - ${inst.nifi_url}`,
    })),
  ];
});

const sourceMissingCount = computed(() => {
  if (!sourceStatus.value) return 0;
  return sourceStatus.value.filter((s) => !s.exists).length;
});

const destinationMissingCount = computed(() => {
  if (!destinationStatus.value) return 0;
  return destinationStatus.value.filter((s) => !s.exists).length;
});

const sourceFlowOptions = computed(() => {
  return [
    { value: null, text: "Select a flow..." },
    ...sourceRegistryFlows.value.map((flow) => ({
      value: flow.id,
      text: `${flow.flow_name} (${flow.registry_name}/${flow.bucket_name})`,
    }))
  ];
});

const destinationFlowOptions = computed(() => {
  return [
    { value: null, text: "Select a flow..." },
    ...destinationRegistryFlows.value.map((flow) => ({
      value: flow.id,
      text: `${flow.flow_name} (${flow.registry_name}/${flow.bucket_name})`,
    }))
  ];
});

const sourceParameterOptions = computed(() => {
  return [
    { value: null, text: "None" },
    ...sourceParameterContexts.value.map((param) => ({
      value: param.id,
      text: param.name,
    }))
  ];
});

const destinationParameterOptions = computed(() => {
  return [
    { value: null, text: "None" },
    ...destinationParameterContexts.value.map((param) => ({
      value: param.id,
      text: param.name,
    }))
  ];
});

const loadInstances = async () => {
  try {
    const data = await apiRequest("/api/nifi-instances/");
    instances.value = data;
  } catch (error) {
    console.error("Error loading instances:", error);
    alert("Failed to load NiFi instances");
  }
};

const loadRegistryFlows = async (instanceId: number, type: 'source' | 'destination') => {
  try {
    const flows = await apiRequest(`/api/registry-flows/?nifi_instance=${instanceId}`);
    if (type === 'source') {
      sourceRegistryFlows.value = flows;
    } else {
      destinationRegistryFlows.value = flows;
    }
  } catch (error) {
    console.error(`Error loading ${type} registry flows:`, error);
  }
};

const loadParameterContexts = async (instanceId: number, type: 'source' | 'destination') => {
  try {
    const response = await apiRequest(`/api/nifi-instances/${instanceId}/get-parameters`);
    // Extract parameter_contexts array from response
    const parameters = response.parameter_contexts || [];
    if (type === 'source') {
      sourceParameterContexts.value = parameters;
    } else {
      destinationParameterContexts.value = parameters;
    }
  } catch (error) {
    console.error(`Error loading ${type} parameter contexts:`, error);
    // Set empty array on error
    if (type === 'source') {
      sourceParameterContexts.value = [];
    } else {
      destinationParameterContexts.value = [];
    }
  }
};

const checkSourcePath = async () => {
  if (!sourceInstance.value) return;

  loadingSourcePath.value = true;
  try {
    const data = await apiRequest(
      `/api/nifi-install/check-path?instance_id=${sourceInstance.value}&path_type=source`,
    );
    sourceStatus.value = data.status;
  } catch (error: any) {
    console.error("Error checking source path:", error);
    alert(error.message || "Failed to check source path");
  } finally {
    loadingSourcePath.value = false;
  }
};

const checkDestinationPath = async () => {
  if (!destinationInstance.value) return;

  loadingDestinationPath.value = true;
  try {
    const data = await apiRequest(
      `/api/nifi-install/check-path?instance_id=${destinationInstance.value}&path_type=destination`,
    );
    destinationStatus.value = data.status;
  } catch (error: any) {
    console.error("Error checking destination path:", error);
    alert(error.message || "Failed to check destination path");
  } finally {
    loadingDestinationPath.value = false;
  }
};

const deployFlow = async (missingPath: string, instanceId: number, type: 'source' | 'destination') => {
  const selectedFlowId = type === 'source' 
    ? selectedSourceFlows.value[missingPath]
    : selectedDestinationFlows.value[missingPath];
  
  if (!selectedFlowId) {
    alert("Please select a flow to deploy");
    return;
  }

  // Get selected parameter context (if any)
  const selectedParameterContextId = type === 'source'
    ? selectedSourceParameters.value[missingPath]
    : selectedDestinationParameters.value[missingPath];

  const pathArray = missingPath.split('/').filter(p => p.length > 0);
  const targetProcessGroupName = pathArray[pathArray.length - 1];
  const parentPath = pathArray.slice(0, -1).join('/');

  deployingPaths.value.add(missingPath);

  try {
    const requestBody: any = {
      template_id: selectedFlowId,
      parent_process_group_path: parentPath || "/",
      process_group_name: targetProcessGroupName
    };

    // Add parameter context if selected (and not "None")
    if (selectedParameterContextId) {
      requestBody.parameter_context_id = selectedParameterContextId;
    }

    await apiRequest(`/api/deploy/${instanceId}/flow`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(requestBody),
    });

    alert(`Successfully deployed flow to ${missingPath}`);
    
    // Reload the paths to reflect the changes
    if (type === 'source') {
      await checkSourcePath();
    } else {
      await checkDestinationPath();
    }
  } catch (error) {
    console.error("Error deploying flow:", error);
    alert("Failed to deploy flow");
  } finally {
    deployingPaths.value.delete(missingPath);
  }
};

// Watch for instance changes to load registry flows and parameter contexts
watch(sourceInstance, (newInstanceId: number | null) => {
  if (newInstanceId) {
    loadRegistryFlows(newInstanceId, 'source');
    loadParameterContexts(newInstanceId, 'source');
  } else {
    sourceRegistryFlows.value = [];
    sourceParameterContexts.value = [];
  }
});

watch(destinationInstance, (newInstanceId: number | null) => {
  if (newInstanceId) {
    loadRegistryFlows(newInstanceId, 'destination');
    loadParameterContexts(newInstanceId, 'destination');
  } else {
    destinationRegistryFlows.value = [];
    destinationParameterContexts.value = [];
  }
});

onMounted(() => {
  loadInstances();
});
</script>

<style scoped lang="scss">
.install-page {
  padding: 20px;
}

.card {
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-header {
  background: linear-gradient(135deg, #6c8fb3 0%, #527ba0 100%);
  color: white;
  padding: 15px 20px;
  border-radius: 8px 8px 0 0;

  h5 {
    margin: 0;
    font-weight: 600;
  }
}

.status-section {
  margin-top: 20px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
}

.status-item {
  padding: 12px 0;
  border-bottom: 1px solid #e0e0e0;

  &:last-child {
    border-bottom: none;
  }

  .status-info {
    display: flex;
    align-items: center;
    gap: 10px;

    i {
      font-size: 1.2rem;
    }

    span:first-of-type {
      font-family: monospace;
      font-weight: 500;
    }
  }

  .deploy-controls {
    flex-shrink: 0;
    
    .deploy-btn {
      min-width: 32px;
      width: 32px;
      height: 32px;
      padding: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      
      i {
        font-size: 1rem;
        margin: 0;
      }
    }
  }
}

.text-success {
  color: #28a745;
}

.text-danger {
  color: #dc3545;
}
</style>
