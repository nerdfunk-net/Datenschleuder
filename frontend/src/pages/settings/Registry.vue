<template>
  <div class="registry-flows">
    <div class="page-card">
      <!-- Header -->
      <div class="card-header">
        <h2 class="card-title">Registry Flows</h2>
        <b-button variant="light" @click="showAddFlowModal = true">
          <i class="pe-7s-plus"></i> Add Flow
        </b-button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-5">
        <b-spinner variant="primary"></b-spinner>
        <p class="mt-3 text-muted">Loading registry flows...</p>
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
              <th class="text-end">Actions</th>
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
                <b-button
                  size="sm"
                  variant="outline-danger"
                  @click="handleDelete(flow)"
                  title="Remove"
                >
                  <i class="pe-7s-trash"></i>
                </b-button>
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
          <h6 class="step-title">1. Select NiFi Instance</h6>
          <b-form-select
            v-model="selectedInstance"
            :options="instanceOptions"
            size="sm"
            @change="onInstanceChange"
          >
            <template #first>
              <b-form-select-option :value="null" disabled
                >-- Select NiFi Instance --</b-form-select-option
              >
            </template>
          </b-form-select>
        </div>

        <!-- Step 2: Select Bucket -->
        <div v-if="selectedInstance" class="selection-step">
          <h6 class="step-title">2. Select Bucket</h6>
          <div v-if="loadingBuckets" class="text-center py-3">
            <b-spinner small variant="primary"></b-spinner>
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
              <b-form-select-option :value="null" disabled
                >-- Select Bucket --</b-form-select-option
              >
            </template>
          </b-form-select>
        </div>

        <!-- Step 3: Select Flows -->
        <div v-if="selectedBucket" class="selection-step">
          <h6 class="step-title">3. Select Flows</h6>
          <div v-if="loadingFlows" class="text-center py-3">
            <b-spinner small variant="primary"></b-spinner>
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
                  <div class="flow-name">{{ flow.name }}</div>
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
        <b-button variant="secondary" @click="closeModal" size="sm"
          >Cancel</b-button
        >
        <b-button
          variant="primary"
          @click="saveFlows"
          size="sm"
          :disabled="selectedFlows.length === 0 || isSaving"
        >
          <b-spinner v-if="isSaving" small class="me-1"></b-spinner>
          {{ isSaving ? "Saving..." : `Save ${selectedFlows.length} Flow(s)` }}
        </b-button>
      </template>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { apiRequest } from "@/utils/api";

interface RegistryFlow {
  id: number;
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

// Modal state
const showAddFlowModal = ref(false);
const selectedInstance = ref<NiFiInstance | null>(null);
const selectedRegistry = ref<Registry | null>(null);
const selectedBucket = ref<Bucket | null>(null);
const selectedFlows = ref<Flow[]>([]);
const isSaving = ref(false);

// Data loading
const nifiInstances = ref<NiFiInstance[]>([]);
const registries = ref<Registry[]>([]);
const buckets = ref<Bucket[]>([]);
const availableFlows = ref<Flow[]>([]);

const loadingBuckets = ref(false);
const loadingFlows = ref(false);

const instanceOptions = computed(() => {
  return nifiInstances.value.map((instance) => ({
    value: instance,
    text: `${instance.hierarchy_value} (${instance.nifi_url})`,
  }));
});

const bucketOptions = computed(() => {
  return buckets.value.map((bucket) => ({
    value: bucket,
    text: bucket.name,
  }));
});

const loadRegistryFlows = async () => {
  isLoading.value = true;
  try {
    registryFlows.value = await apiRequest("/api/registry-flows/");
  } catch (error) {
    console.error("Error loading registry flows:", error);
    alert("Failed to load registry flows");
  } finally {
    isLoading.value = false;
  }
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
      `/api/nifi-instances/${selectedInstance.value.id}/get-registries`,
    );

    if (response.registry_clients && response.registry_clients.length > 0) {
      // Use the first registry (or we could let user select)
      const firstRegistry = response.registry_clients[0];
      selectedRegistry.value = {
        id: firstRegistry.id,
        name: firstRegistry.name,
      };

      // Load buckets from this registry
      const bucketsResponse = await apiRequest(
        `/api/nifi-instances/${selectedInstance.value.id}/registry/${firstRegistry.id}/get-buckets`,
      );
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
      `/api/nifi-instances/${selectedInstance.value.id}/registry/${selectedRegistry.value.id}/${selectedBucket.value.identifier}/get-flows`,
    );
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
    });

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

onMounted(async () => {
  await loadRegistryFlows();
  await loadNiFiInstances();
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
