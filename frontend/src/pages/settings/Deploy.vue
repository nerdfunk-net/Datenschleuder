<template>
  <div class="settings-page">
    <div class="page-card">
      <div class="card-header">
        <h2 class="card-title">
          Deployment Settings
        </h2>
        <p class="text-muted mb-0">
          Configure deployment parameters for flow deployment
        </p>
      </div>

      <div class="card-body">
        <form @submit.prevent="handleSave">
          <!-- Global Deployment Settings -->
          <div class="section-header">
            <h4>Global Settings</h4>
          </div>

          <div class="row g-4 mb-4">
            <!-- Process Group Name Template -->
            <div class="col-md-12">
              <label class="form-label">Process Group Name Template</label>
              <b-form-input
                v-model="settings.global.process_group_name_template"
                placeholder="{last_hierarchy_value}"
                :disabled="!isAdmin"
              />
              <small class="form-text text-muted">
                Default: {last_hierarchy_value} - Use the value of the last
                hierarchy attribute (e.g., CN value)
              </small>
            </div>

            <!-- Disable After Deploy -->
            <div class="col-md-12">
              <b-form-checkbox v-model="settings.global.disable_after_deploy" :disabled="!isAdmin">
                Disable flow after deployment
              </b-form-checkbox>
              <small class="form-text text-muted d-block">
                If enabled, the deployed process group will be DISABLED (locked) after deployment.
                Note: NiFi deploys flows in STOPPED state by default. This setting goes further
                to DISABLE them, preventing accidental starting.
              </small>
            </div>

            <!-- Start After Deploy -->
            <div class="col-md-12">
              <b-form-checkbox v-model="settings.global.start_after_deploy" :disabled="!isAdmin">
                Start flow after deployment
              </b-form-checkbox>
              <small class="form-text text-muted d-block">
                If enabled, the deployed process group will be STARTED after deployment.
                This allows the flow to begin processing data immediately.
              </small>
            </div>

            <!-- Stop Versioning After Deploy -->
            <div class="col-md-12">
              <b-form-checkbox v-model="settings.global.stop_versioning_after_deploy" :disabled="!isAdmin">
                Stop versioning after deployment
              </b-form-checkbox>
              <small class="form-text text-muted d-block">
                If enabled, version control will be stopped for the deployed process group
              </small>
            </div>
          </div>

          <!-- Per-Instance Path Settings -->
          <div class="section-header mt-4">
            <h4>Instance Path Configuration</h4>
            <p class="text-muted mb-0">
              Configure source and destination paths for each NiFi instance
            </p>
          </div>

          <!-- Loading State -->
          <div v-if="loadingInstances" class="text-center py-3">
            <b-spinner small />
            <span class="ms-2">Loading instances...</span>
          </div>

          <!-- Instance Path Settings -->
          <div v-else-if="instances.length > 0" class="instance-paths mt-3">
            <div
              v-for="instance in instances"
              :key="instance.id"
              class="instance-path-item"
            >
              <div class="instance-label">
                <strong>{{ instance.hierarchy_attribute }}={{
                  instance.hierarchy_value
                }}</strong>
                <small class="text-muted d-block">{{
                  instance.nifi_url
                }}</small>
              </div>

              <div class="row g-3">
                <div class="col-md-6">
                  <label class="form-label">Source Path ({{ topHierarchyName }})</label>
                  <div class="path-select-wrapper">
                    <b-form-select
                      :model-value="getSourcePath(instance.id)"
                      :options="getPathOptionsForInstance(instance.id)"
                      :disabled="loadingPaths[instance.id] || !isAdmin"
                      @update:model-value="
                        updateSourcePath(instance.id, $event)
                      "
                    />
                    <b-button
                      v-if="isAdmin"
                      variant="outline-primary"
                      size="sm"
                      :disabled="loadingPaths[instance.id]"
                      @click="loadPathsForInstance(instance.id)"
                    >
                      <b-spinner
                        v-if="loadingPaths[instance.id]"
                        small
                      />
                      <i v-else class="pe-7s-refresh"></i>
                    </b-button>
                  </div>
                  <small class="form-text text-muted">
                    Search path for the source element in the top hierarchy
                  </small>
                </div>

                <div class="col-md-6">
                  <label class="form-label">Destination Path ({{ topHierarchyName }})</label>
                  <div class="path-select-wrapper">
                    <b-form-select
                      :model-value="getDestPath(instance.id)"
                      :options="getPathOptionsForInstance(instance.id)"
                      :disabled="loadingPaths[instance.id] || !isAdmin"
                      @update:model-value="updateDestPath(instance.id, $event)"
                    />
                    <b-button
                      v-if="isAdmin"
                      variant="outline-primary"
                      size="sm"
                      :disabled="loadingPaths[instance.id]"
                      @click="loadPathsForInstance(instance.id)"
                    >
                      <b-spinner
                        v-if="loadingPaths[instance.id]"
                        small
                      />
                      <i v-else class="pe-7s-refresh"></i>
                    </b-button>
                  </div>
                  <small class="form-text text-muted">
                    Search path for the destination element in the top hierarchy
                  </small>
                </div>
              </div>
            </div>
          </div>

          <div v-else class="alert alert-info mt-3">
            No NiFi instances configured. Please add instances in
            <router-link to="/settings/nifi">
              Settings / NiFi
            </router-link>.
          </div>

          <div class="card-footer">
            <b-button
              v-if="isAdmin"
              type="button"
              variant="outline-secondary"
              @click="handleReset"
            >
              Reset
            </b-button>
            <b-button
              v-if="isAdmin"
              type="submit"
              variant="primary"
              class="ms-2"
              :disabled="isSaving"
            >
              <b-spinner v-if="isSaving" small class="me-2" />
              Save Settings
            </b-button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed, reactive } from "vue";
import { apiRequest } from "@/utils/api";
import { useAuth } from "@/composables/useAuth";

const { isAdmin } = useAuth();

interface NiFiInstance {
  id: number;
  hierarchy_attribute: string;
  hierarchy_value: string;
  nifi_url: string;
}

interface ProcessGroupPath {
  id: string;
  name: string;
  path: Array<{ id: string; name: string; parent_group_id: string }>;
}

interface PathConfig {
  id: string; // UUID of the process group
  path: string; // Human-readable path like "Nifi Flow/From DC1"
}

interface DeploymentSettings {
  global: {
    process_group_name_template: string;
    disable_after_deploy: boolean;
    start_after_deploy: boolean;
    stop_versioning_after_deploy: boolean;
  };
  paths: {
    [instanceId: number]: {
      source_path?: PathConfig;
      dest_path?: PathConfig;
    };
  };
}

const isSaving = ref(false);
const loadingInstances = ref(true);
const instances = ref<NiFiInstance[]>([]);
const instancePaths = reactive<{ [instanceId: number]: ProcessGroupPath[] }>(
  {},
);
const loadingPaths = reactive<{ [instanceId: number]: boolean }>({});
const topHierarchyName = ref("");

const settings = ref<DeploymentSettings>({
  global: {
    process_group_name_template: "{last_hierarchy_value}",
    disable_after_deploy: false,
    start_after_deploy: true,
    stop_versioning_after_deploy: false,
  },
  paths: {},
});

const loadHierarchy = async () => {
  try {
    const data = await apiRequest("/api/settings/hierarchy");
    if (data.hierarchy && data.hierarchy.length > 0) {
      // Get the top hierarchy attribute name
      topHierarchyName.value = data.hierarchy[0].name;
    }
  } catch (error) {
    console.error("Error loading hierarchy:", error);
  }
};

const loadInstances = async () => {
  loadingInstances.value = true;
  try {
    const data = await apiRequest("/api/nifi-instances/");
    instances.value = data;

    // Initialize path settings for each instance if not already set
    instances.value.forEach((instance) => {
      if (!settings.value.paths[instance.id]) {
        settings.value.paths[instance.id] = {
          source_path: undefined,
          dest_path: undefined,
        };
      }
    });
  } catch (error) {
    console.error("Error loading instances:", error);
  } finally {
    loadingInstances.value = false;
  }
};

const loadPathsForInstance = async (instanceId: number) => {
  loadingPaths[instanceId] = true;
  try {
    const data = await apiRequest(`/api/nifi-instances/${instanceId}/get-all-paths`);
    if (data.process_groups) {
      instancePaths[instanceId] = data.process_groups;
    }
  } catch (error: any) {
    console.error(`Error loading paths for instance ${instanceId}:`, error);
    alert(`Failed to load paths: ${error.message || "Unknown error"}`);
  } finally {
    loadingPaths[instanceId] = false;
  }
};

const getPathOptionsForInstance = (instanceId: number) => {
  const paths = instancePaths[instanceId] || [];

  if (loadingPaths[instanceId]) {
    return [{ value: "", text: "Loading paths..." }];
  }

  if (paths.length === 0) {
    return [{ value: "", text: "Click refresh to load paths" }];
  }

  // Create options from paths - show full path string reversed
  // Convert "OU1 / O1 / From DC1 / Nifi Flow" to "Nifi Flow / From DC1 / O1 / OU1"
  const options = paths.map((pg) => {
    const pathString = pg.path
      .map((p) => p.name)
      .reverse()
      .join(" / ");
    return {
      value: pg.id,
      text: pathString || pg.name,
    };
  });

  return [{ value: "", text: "Select a path..." }, ...options];
};

const getSourcePath = (instanceId: number) => {
  return settings.value.paths[instanceId]?.source_path?.id || "";
};

const getDestPath = (instanceId: number) => {
  return settings.value.paths[instanceId]?.dest_path?.id || "";
};

const updateSourcePath = (instanceId: number, pgId: string) => {
  if (!settings.value.paths[instanceId]) {
    settings.value.paths[instanceId] = {};
  }

  if (!pgId) {
    settings.value.paths[instanceId].source_path = undefined;
    return;
  }

  // Find the process group to get its path
  const pg = instancePaths[instanceId]?.find((p) => p.id === pgId);
  if (pg) {
    const pathString = pg.path.map((p) => p.name).reverse().join("/");
    settings.value.paths[instanceId].source_path = {
      id: pgId,
      path: pathString,
    };
  }
};

const updateDestPath = (instanceId: number, pgId: string) => {
  if (!settings.value.paths[instanceId]) {
    settings.value.paths[instanceId] = {};
  }

  if (!pgId) {
    settings.value.paths[instanceId].dest_path = undefined;
    return;
  }

  // Find the process group to get its path
  const pg = instancePaths[instanceId]?.find((p) => p.id === pgId);
  if (pg) {
    const pathString = pg.path.map((p) => p.name).reverse().join("/");
    settings.value.paths[instanceId].dest_path = {
      id: pgId,
      path: pathString,
    };
  }
};

const loadSettings = async () => {
  try {
    const data = await apiRequest("/api/settings/deploy");

    // Convert string keys to numbers since JSON serialization converts numeric keys to strings
    const paths: {
      [key: number]: { source_path?: PathConfig; dest_path?: PathConfig };
    } = {};
    if (data.paths) {
      Object.keys(data.paths).forEach((key) => {
        const numKey = parseInt(key, 10);
        paths[numKey] = data.paths[key];
      });
    }

    settings.value = {
      global: data.global || settings.value.global,
      paths: paths,
    };

    // Ensure all instances have path entries
    instances.value.forEach((instance) => {
      if (!settings.value.paths[instance.id]) {
        settings.value.paths[instance.id] = {
          source_path: undefined,
          dest_path: undefined,
        };
      }
    });
  } catch (error) {
    console.error("Error loading settings:", error);
  }
};

const handleSave = async () => {
  isSaving.value = true;
  try {
    await apiRequest("/api/settings/deploy", {
      method: "POST",
      body: JSON.stringify(settings.value),
    });

    alert("✓ Deployment settings saved successfully!");
  } catch (error: any) {
    console.error("Error saving settings:", error);
    alert("✗ Error: " + (error.message || "Error saving settings"));
  } finally {
    isSaving.value = false;
  }
};

const handleReset = () => {
  loadSettings();
};

onMounted(async () => {
  await loadHierarchy();
  await loadInstances();
  await loadSettings();

  // Auto-load paths for all instances so saved values display properly
  instances.value.forEach((instance) => {
    loadPathsForInstance(instance.id);
  });
});
</script>

<style scoped lang="scss">
@import "./settings-common.scss";

.section-header {
  padding-bottom: 12px;
  margin-bottom: 16px;
  border-bottom: 2px solid #e9ecef;

  h4 {
    margin: 0;
    color: #495057;
    font-size: 1.1rem;
    font-weight: 600;
  }
}

.instance-paths {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.instance-path-item {
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
  border: 1px solid #dee2e6;
}

.instance-label {
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid #dee2e6;

  strong {
    color: #007bff;
    font-size: 1rem;
  }
}

.path-select-wrapper {
  display: flex;
  gap: 8px;
  align-items: center;

  .form-select {
    flex: 1;
  }

  button {
    flex-shrink: 0;
    padding: 6px 12px;
  }
}
</style>
