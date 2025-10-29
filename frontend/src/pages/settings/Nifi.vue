<template>
  <div class="settings-page">
    <div v-if="instances.length > 0 || loading" class="page-header mb-4">
      <h2>NiFi Instances</h2>
      <p class="text-muted">
        Manage multiple NiFi instances, one for each top hierarchy value
      </p>
      <b-button variant="primary" @click="showAddModal">
        + Add NiFi Instance
      </b-button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <b-spinner></b-spinner>
      <p class="text-muted mt-2">Loading NiFi instances...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="instances.length === 0" class="empty-state">
      <i class="pe-7s-server" style="font-size: 4rem; color: #6c757d"></i>
      <h4 class="mt-3">No NiFi Instances</h4>
      <p class="text-muted">Add your first NiFi instance to get started</p>
      <b-button variant="primary" @click="showAddModal">
        + Add NiFi Instance
      </b-button>
    </div>

    <!-- Instance Cards -->
    <div v-else class="instances-grid">
      <div
        v-for="instance in instances"
        :key="instance.id"
        class="instance-card"
      >
        <div class="card-header-custom">
          <div class="instance-badge">
            {{ instance.hierarchy_attribute }}={{ instance.hierarchy_value }}
          </div>
          <div class="card-actions">
            <b-button
              variant="link"
              size="sm"
              @click="testConnection(instance.id)"
              title="Test Connection"
            >
              <i class="pe-7s-check"></i>
            </b-button>
            <b-button
              variant="link"
              size="sm"
              @click="editInstance(instance)"
              title="Edit"
            >
              <i class="pe-7s-pen"></i>
            </b-button>
            <b-button
              variant="link"
              size="sm"
              class="delete-btn"
              @click="deleteInstance(instance.id)"
              title="Delete"
            >
              <i class="pe-7s-trash"></i>
            </b-button>
          </div>
        </div>

        <div class="card-body-custom">
          <div class="instance-info">
            <div class="info-row">
              <span class="label">URL:</span>
              <span class="value">{{ instance.nifi_url }}</span>
            </div>
            <div class="info-row">
              <span class="label">Username:</span>
              <span class="value">{{ instance.username || "Not set" }}</span>
            </div>
            <div class="info-row">
              <span class="label">SSL:</span>
              <span class="value">
                <span v-if="instance.use_ssl" class="badge bg-success"
                  >Enabled</span
                >
                <span v-else class="badge bg-secondary">Disabled</span>
              </span>
            </div>
            <div class="info-row">
              <span class="label">Verify SSL:</span>
              <span class="value">
                <span v-if="instance.verify_ssl" class="badge bg-success"
                  >Yes</span
                >
                <span v-else class="badge bg-warning">No</span>
              </span>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Add/Edit Modal -->
    <b-modal
      v-model="showModal"
      :title="isEditMode ? 'Edit NiFi Instance' : 'Add NiFi Instance'"
      size="lg"
      @hidden="resetForm"
    >
      <form @submit.prevent="handleSave">
        <div class="row g-3">
          <div class="col-md-6">
            <label class="form-label">Hierarchy Attribute</label>
            <b-form-select
              v-model="form.hierarchy_attribute"
              :options="hierarchyOptions"
              :disabled="isEditMode"
              required
            />
          </div>

          <div class="col-md-6">
            <label class="form-label">Hierarchy Value</label>
            <b-form-select
              v-model="form.hierarchy_value"
              :options="hierarchyValueOptions"
              :disabled="isEditMode"
              required
            />
          </div>

          <div class="col-md-12">
            <label class="form-label">NiFi URL</label>
            <b-form-input
              v-model="form.nifi_url"
              placeholder="https://nifi.example.com:8443/nifi-api"
              required
            />
            <small class="form-text text-muted"
              >Full NiFi API endpoint URL (must end with /nifi-api)</small
            >
          </div>

          <div class="col-md-6">
            <label class="form-label">Username</label>
            <b-form-input v-model="form.username" placeholder="admin" />
          </div>

          <div class="col-md-6">
            <label class="form-label">Password</label>
            <b-form-input
              v-model="form.password"
              type="password"
              placeholder="••••••••"
            />
          </div>

          <div class="col-md-12">
            <b-form-checkbox v-model="form.useSSL">
              Use SSL/TLS
            </b-form-checkbox>
          </div>

          <div class="col-md-12">
            <b-form-checkbox v-model="form.verifySSL">
              Verify SSL Certificates
            </b-form-checkbox>
          </div>
        </div>
      </form>

      <template #footer>
        <b-button variant="secondary" @click="showModal = false">
          Cancel
        </b-button>
        <b-button
          variant="info"
          @click="testConnectionFromModal"
          :disabled="!form.nifi_url"
        >
          <i class="pe-7s-check"></i> Test Connection
        </b-button>
        <b-button variant="primary" @click="handleSave">
          {{ isEditMode ? "Update" : "Create" }} Instance
        </b-button>
      </template>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { apiRequest } from "@/utils/api";

interface NiFiInstance {
  id: number;
  hierarchy_attribute: string;
  hierarchy_value: string;
  nifi_url: string;
  username: string | null;
  use_ssl: boolean;
  verify_ssl: boolean;
}

interface HierarchyAttribute {
  name: string;
  label: string;
  values?: string[];
}

const loading = ref(true);
const instances = ref<NiFiInstance[]>([]);
const showModal = ref(false);
const isEditMode = ref(false);
const editingId = ref<number | null>(null);

const form = ref({
  hierarchy_attribute: "",
  hierarchy_value: "",
  nifi_url: "",
  username: "",
  password: "",
  useSSL: true,
  verifySSL: true,
});

// Load hierarchy configuration
const hierarchyConfig = ref<HierarchyAttribute[]>([]);

const hierarchyOptions = computed(() => {
  if (hierarchyConfig.value.length === 0) return [];
  // Only show the first (top) hierarchy attribute
  const topAttr = hierarchyConfig.value[0];
  return [{ value: topAttr.name, text: `${topAttr.name} (${topAttr.label})` }];
});

const hierarchyValueOptions = computed(() => {
  if (!form.value.hierarchy_attribute || hierarchyConfig.value.length === 0) {
    return [{ value: "", text: "Select hierarchy attribute first" }];
  }

  const attr = hierarchyConfig.value.find(
    (a) => a.name === form.value.hierarchy_attribute,
  );
  if (!attr || !attr.values || attr.values.length === 0) {
    return [{ value: "", text: "No values defined for this attribute" }];
  }

  return attr.values.map((v) => ({ value: v, text: v }));
});

const loadHierarchy = async () => {
  try {
    const data = await apiRequest("/api/settings/hierarchy");
    hierarchyConfig.value = data.hierarchy || [];

    // Load values for top hierarchy
    if (hierarchyConfig.value.length > 0) {
      const topAttr = hierarchyConfig.value[0];
      const valuesData = await apiRequest(
        `/api/settings/hierarchy/values/${encodeURIComponent(topAttr.name)}`,
      );
      topAttr.values = valuesData.values || [];
    }
  } catch (error) {
    console.error("Error loading hierarchy:", error);
  }
};

const loadInstances = async () => {
  loading.value = true;
  try {
    const data = await apiRequest("/api/nifi-instances/");
    instances.value = data;
  } catch (error) {
    console.error("Error loading instances:", error);
    alert("Failed to load NiFi instances");
  } finally {
    loading.value = false;
  }
};

const showAddModal = async () => {
  await loadHierarchy();

  // Set default hierarchy attribute to first one
  if (hierarchyConfig.value.length > 0) {
    form.value.hierarchy_attribute = hierarchyConfig.value[0].name;
  }

  isEditMode.value = false;
  showModal.value = true;
};

const editInstance = async (instance: NiFiInstance) => {
  await loadHierarchy();

  editingId.value = instance.id;
  form.value = {
    hierarchy_attribute: instance.hierarchy_attribute,
    hierarchy_value: instance.hierarchy_value,
    nifi_url: instance.nifi_url,
    username: instance.username || "",
    password: "",
    useSSL: instance.use_ssl,
    verifySSL: instance.verify_ssl,
  };
  isEditMode.value = true;
  showModal.value = true;
};

const handleSave = async (bvModalEvent: any) => {
  bvModalEvent.preventDefault();

  try {
    const payload = {
      hierarchy_attribute: form.value.hierarchy_attribute,
      hierarchy_value: form.value.hierarchy_value,
      nifi_url: form.value.nifi_url,
      username: form.value.username,
      password: form.value.password,
      use_ssl: form.value.useSSL,
      verify_ssl: form.value.verifySSL,
    };

    if (isEditMode.value && editingId.value) {
      await apiRequest(`/api/nifi-instances/${editingId.value}`, {
        method: "PUT",
        body: JSON.stringify(payload),
      });
      alert("NiFi instance updated successfully!");
    } else {
      await apiRequest("/api/nifi-instances/", {
        method: "POST",
        body: JSON.stringify(payload),
      });
      alert("NiFi instance created successfully!");
    }

    showModal.value = false;
    await loadInstances();
  } catch (error: any) {
    alert(error.message || "Failed to save NiFi instance");
  }
};

const testConnection = async (instanceId: number) => {
  try {
    const result = await apiRequest(
      `/api/nifi-instances/${instanceId}/test-connection`,
      {
        method: "POST",
      },
    );

    if (result.status === "success") {
      alert(
        `✓ Success\n\n${result.message}\n\nVersion: ${result.details.version}`,
      );
    } else {
      alert(`✗ Failed\n\n${result.message}`);
    }
  } catch (error: any) {
    alert(`✗ Failed\n\n${error.message}`);
  }
};

const testConnectionFromModal = async () => {
  try {
    const payload = {
      hierarchy_attribute: form.value.hierarchy_attribute || "test",
      hierarchy_value: form.value.hierarchy_value || "test",
      nifi_url: form.value.nifi_url,
      username: form.value.username || "",
      password: form.value.password || "",
      use_ssl: form.value.useSSL,
      verify_ssl: form.value.verifySSL,
    };

    const result = await apiRequest("/api/nifi-instances/test", {
      method: "POST",
      body: JSON.stringify(payload),
    });

    if (result.status === "success") {
      alert(
        `✓ Success\n\n${result.message}\n\nVersion: ${result.details.version}`,
      );
    } else {
      alert(`✗ Failed\n\n${result.message}`);
    }
  } catch (error: any) {
    const errorMsg = error.message || JSON.stringify(error);
    alert(`✗ Failed\n\n${errorMsg}`);
  }
};

const deleteInstance = async (instanceId: number) => {
  if (!confirm("Are you sure you want to delete this NiFi instance?")) {
    return;
  }

  try {
    await apiRequest(`/api/nifi-instances/${instanceId}`, {
      method: "DELETE",
    });
    alert("NiFi instance deleted successfully!");
    await loadInstances();
  } catch (error: any) {
    alert(error.message || "Failed to delete NiFi instance");
  }
};

const resetForm = () => {
  form.value = {
    hierarchy_attribute: "",
    hierarchy_value: "",
    nifi_url: "",
    username: "",
    password: "",
    useSSL: true,
    verifySSL: true,
  };
  editingId.value = null;
};

onMounted(() => {
  loadInstances();
});
</script>

<style scoped lang="scss">
@import "./settings-common.scss";

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;

  h2 {
    margin: 0;
  }

  p {
    margin: 0;
  }
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.instances-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 20px;
}

.instance-card {
  background: linear-gradient(135deg, #f5f7fa 0%, #e8eef5 100%);
  border: 1px solid #d0dae6;
  border-radius: 12px;
  overflow: hidden;
  transition: all 0.3s ease;
  box-shadow: 0 2px 8px rgba(100, 120, 150, 0.08);

  &:hover {
    box-shadow: 0 6px 20px rgba(100, 120, 150, 0.15);
    transform: translateY(-2px);
  }
}

.card-header-custom {
  background: linear-gradient(135deg, #6c8fb3 0%, #527ba0 100%);
  padding: 15px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.instance-badge {
  background: rgba(255, 255, 255, 0.95);
  color: #4a6380;
  padding: 6px 14px;
  border-radius: 20px;
  font-weight: 600;
  font-size: 13px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.card-actions {
  display: flex;
  gap: 8px;

  button {
    color: white;
    padding: 6px 10px;
    font-size: 16px;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    transition: all 0.2s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.2);
      color: white;
      transform: scale(1.1);
    }

    &.delete-btn {
      color: white;

      &:hover {
        background: rgba(220, 53, 69, 0.9);
        color: white;
      }
    }
  }
}

.card-body-custom {
  padding: 20px;
  background: white;
}

.instance-info {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.info-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 0;
  border-bottom: 1px solid #e8eef5;

  &:last-child {
    border-bottom: none;
  }

  .label {
    font-weight: 600;
    color: #5a6c7d;
    font-size: 13px;
  }

  .value {
    color: #2c3e50;
    font-size: 13px;
    text-align: right;
    word-break: break-all;
  }
}
</style>
