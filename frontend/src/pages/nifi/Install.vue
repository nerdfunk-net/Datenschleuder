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
      <div class="card-header">
        <h5 class="mb-0">
          <i class="pe-7s-upload me-2"></i>Source Path
        </h5>
      </div>
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

          <b-button
            v-if="sourceMissingCount > 0"
            variant="primary"
            class="mt-3"
            @click="createSourceGroups"
            :disabled="creatingSource"
          >
            <b-spinner v-if="creatingSource" small class="me-2"></b-spinner>
            Create Missing Process Groups ({{ sourceMissingCount }})
          </b-button>
        </div>
      </div>
    </div>

    <!-- Destination Path Panel -->
    <div class="card">
      <div class="card-header">
        <h5 class="mb-0">
          <i class="pe-7s-download me-2"></i>Destination Path
        </h5>
      </div>
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

          <b-button
            v-if="destinationMissingCount > 0"
            variant="primary"
            class="mt-3"
            @click="createDestinationGroups"
            :disabled="creatingDestination"
          >
            <b-spinner v-if="creatingDestination" small class="me-2"></b-spinner>
            Create Missing Process Groups ({{ destinationMissingCount }})
          </b-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
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

const sourceInstance = ref<number | null>(null);
const destinationInstance = ref<number | null>(null);
const instances = ref<NiFiInstance[]>([]);
const sourceStatus = ref<PathStatus[] | null>(null);
const destinationStatus = ref<PathStatus[] | null>(null);
const creatingSource = ref(false);
const creatingDestination = ref(false);

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

const loadInstances = async () => {
  try {
    const data = await apiRequest("/api/nifi-instances/");
    instances.value = data;
  } catch (error) {
    console.error("Error loading instances:", error);
    alert("Failed to load NiFi instances");
  }
};

const checkSourcePath = async () => {
  if (!sourceInstance.value) return;

  try {
    const data = await apiRequest(
      `/api/nifi-install/check-path?instance_id=${sourceInstance.value}&path_type=source`,
    );
    sourceStatus.value = data.status;
  } catch (error: any) {
    console.error("Error checking source path:", error);
    alert(error.message || "Failed to check source path");
  }
};

const checkDestinationPath = async () => {
  if (!destinationInstance.value) return;

  try {
    const data = await apiRequest(
      `/api/nifi-install/check-path?instance_id=${destinationInstance.value}&path_type=destination`,
    );
    destinationStatus.value = data.status;
  } catch (error: any) {
    console.error("Error checking destination path:", error);
    alert(error.message || "Failed to check destination path");
  }
};

const createSourceGroups = async () => {
  if (!sourceInstance.value) return;

  creatingSource.value = true;
  try {
    await apiRequest(`/api/nifi-install/create-groups`, {
      method: "POST",
      body: JSON.stringify({
        instance_id: sourceInstance.value,
        path_type: "source",
      }),
    });
    alert("Source process groups created successfully!");
    await checkSourcePath();
  } catch (error: any) {
    console.error("Error creating source groups:", error);
    alert(error.message || "Failed to create source process groups");
  } finally {
    creatingSource.value = false;
  }
};

const createDestinationGroups = async () => {
  if (!destinationInstance.value) return;

  creatingDestination.value = true;
  try {
    await apiRequest(`/api/nifi-install/create-groups`, {
      method: "POST",
      body: JSON.stringify({
        instance_id: destinationInstance.value,
        path_type: "destination",
      }),
    });
    alert("Destination process groups created successfully!");
    await checkDestinationPath();
  } catch (error: any) {
    console.error("Error creating destination groups:", error);
    alert(error.message || "Failed to create destination process groups");
  } finally {
    creatingDestination.value = false;
  }
};

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
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid #e0e0e0;

  &:last-child {
    border-bottom: none;
  }

  i {
    font-size: 1.2rem;
  }

  span:first-of-type {
    flex: 1;
    font-family: monospace;
  }
}

.text-success {
  color: #28a745;
}

.text-danger {
  color: #dc3545;
}
</style>
