<template>
  <div class="settings-page">
    <div class="page-card">
      <div class="card-header">
        <h2 class="card-title">Hierarchy Settings</h2>
        <p class="text-muted mb-0">
          Configure the hierarchy of attributes (e.g.,
          CN=test,O=myOrg,OU=myOrgUnit,DC=myNet)
        </p>
      </div>

      <div class="card-body">
        <form @submit.prevent="handleSave">
          <!-- Hierarchy Configuration -->
          <div class="row g-4">
            <div class="col-md-12">
              <label class="form-label">Attribute Hierarchy</label>
              <small class="form-text text-muted d-block mb-3">
                Define the order of attributes from top (first) to bottom
                (last). Each attribute name must be unique.
              </small>

              <!-- Hierarchy List -->
              <div class="hierarchy-list">
                <div
                  v-for="(attr, index) in settings.hierarchy"
                  :key="index"
                  class="hierarchy-item"
                >
                  <div class="hierarchy-order">{{ index + 1 }}</div>

                  <div class="hierarchy-fields">
                    <div class="row g-2">
                      <div class="col-md-4">
                        <b-form-input
                          v-model="attr.name"
                          placeholder="Name (e.g., CN)"
                          @input="validateUniqueName(index)"
                          :class="{ 'is-invalid': attr.nameError }"
                          :disabled="!isAdmin"
                        />
                        <div
                          v-if="attr.nameError"
                          class="invalid-feedback d-block"
                        >
                          {{ attr.nameError }}
                        </div>
                      </div>
                      <div class="col-md-6">
                        <b-form-input
                          v-model="attr.label"
                          placeholder="Label (e.g., Common Name)"
                          :disabled="!isAdmin"
                        />
                      </div>
                      <div class="col-md-2 d-flex gap-1">
                        <b-button
                          variant="outline-info"
                          size="sm"
                          @click="viewAttribute(index)"
                          title="View values"
                        >
                          <i class="pe-7s-look"></i>
                        </b-button>
                        <b-button
                          v-if="isAdmin"
                          variant="outline-primary"
                          size="sm"
                          @click="editAttribute(index)"
                          title="Edit values"
                        >
                          <i class="pe-7s-pen"></i>
                        </b-button>
                        <b-button
                          v-if="isAdmin"
                          variant="outline-danger"
                          size="sm"
                          @click="removeAttribute(index)"
                          :disabled="settings.hierarchy.length === 1"
                          title="Remove attribute"
                        >
                          <i class="pe-7s-trash"></i>
                        </b-button>
                      </div>
                    </div>
                  </div>

                  <div class="hierarchy-actions">
                    <b-button
                      v-if="isAdmin"
                      variant="link"
                      size="sm"
                      @click="moveUp(index)"
                      :disabled="index === 0"
                      class="p-0"
                    >
                      ▲
                    </b-button>
                    <b-button
                      v-if="isAdmin"
                      variant="link"
                      size="sm"
                      @click="moveDown(index)"
                      :disabled="index === settings.hierarchy.length - 1"
                      class="p-0"
                    >
                      ▼
                    </b-button>
                  </div>
                </div>
              </div>

              <!-- Add Attribute Button -->
              <b-button
                v-if="isAdmin"
                variant="outline-primary"
                size="sm"
                class="mt-3"
                @click="addAttribute"
              >
                + Add Attribute
              </b-button>
            </div>

            <!-- Preview -->
            <div class="col-md-12">
              <label class="form-label">Preview</label>
              <div class="preview-box">
                {{ generatePreview() }}
              </div>
              <small class="form-text text-muted">
                Example output with sample values
              </small>
            </div>
          </div>

          <div class="card-footer">
            <b-button
              v-if="isAdmin"
              type="button"
              variant="outline-secondary"
              @click="handleReset"
              >Reset</b-button
            >
            <b-button
              v-if="isAdmin"
              type="submit"
              variant="primary"
              class="ms-2"
              :disabled="isSaving || hasErrors"
            >
              <b-spinner v-if="isSaving" small class="me-2"></b-spinner>
              Save Settings
            </b-button>
          </div>
        </form>
      </div>
    </div>

    <!-- Values Modal -->
    <b-modal
      v-model="showModal"
      :title="modalTitle"
      size="lg"
      :ok-title="isViewMode ? 'Close' : 'Save Values'"
      :cancel-title="isViewMode ? '' : 'Cancel'"
      :ok-only="isViewMode"
      @ok="handleModalOk"
      @cancel="closeModal"
      @hidden="closeModal"
    >
      <div v-if="editingAttribute">
        <p class="text-muted">
          Manage values for <strong>{{ editingAttribute.name }}</strong> ({{
            editingAttribute.label
          }})
        </p>

        <!-- Values List -->
        <div class="values-list mb-3">
          <div
            v-for="(value, idx) in editingAttribute.values || []"
            :key="idx"
            class="value-item"
          >
            <b-form-input
              v-if="editingAttribute.values"
              v-model="editingAttribute.values[idx]"
              :readonly="isViewMode"
              placeholder="Enter value"
              class="flex-grow-1"
            />
            <b-button
              v-if="!isViewMode"
              variant="outline-danger"
              size="sm"
              @click="removeValue(idx)"
            >
              <i class="pe-7s-trash"></i>
            </b-button>
          </div>

          <div
            v-if="
              !editingAttribute.values || editingAttribute.values.length === 0
            "
            class="text-muted text-center py-3"
          >
            No values defined yet
          </div>
        </div>

        <!-- Add Value Button -->
        <b-button
          v-if="!isViewMode"
          variant="outline-primary"
          size="sm"
          @click="addValue"
        >
          + Add Value
        </b-button>
      </div>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { apiRequest } from "@/utils/api";
import { useAuth } from "@/composables/useAuth";

const { isAdmin } = useAuth();

interface HierarchyAttribute {
  name: string;
  label: string;
  order: number;
  nameError?: string;
  values?: string[];
}

const isSaving = ref(false);
const settings = ref<{ hierarchy: HierarchyAttribute[] }>({
  hierarchy: [],
});

const showModal = ref(false);
const isViewMode = ref(false);
const editingIndex = ref<number | null>(null);
const editingAttribute = ref<HierarchyAttribute | null>(null);

const modalTitle = computed(() => {
  if (!editingAttribute.value) return "";
  return isViewMode.value
    ? `View Values - ${editingAttribute.value.name}`
    : `Edit Values - ${editingAttribute.value.name}`;
});

const hasErrors = computed(() => {
  return settings.value.hierarchy.some((attr) => attr.nameError);
});

const loadSettings = async () => {
  try {
    const data = await apiRequest("/api/settings/hierarchy");
    settings.value = data;
  } catch (error) {
    console.error("Error loading settings:", error);
  }
};

const validateUniqueName = (index: number) => {
  const current = settings.value.hierarchy[index];
  const names = settings.value.hierarchy.map((attr) =>
    attr.name.trim().toUpperCase(),
  );

  // Clear error first
  current.nameError = undefined;

  if (!current.name.trim()) {
    current.nameError = "Name is required";
    return;
  }

  // Check for duplicates
  const count = names.filter(
    (name) => name === current.name.trim().toUpperCase(),
  ).length;
  if (count > 1) {
    current.nameError = "Duplicate name - must be unique";
  }
};

const addAttribute = () => {
  const newOrder = settings.value.hierarchy.length;
  settings.value.hierarchy.push({
    name: "",
    label: "",
    order: newOrder,
  });
};

const removeAttribute = (index: number) => {
  settings.value.hierarchy.splice(index, 1);
  // Reorder remaining attributes
  settings.value.hierarchy.forEach((attr, i) => {
    attr.order = i;
  });
};

const moveUp = (index: number) => {
  if (index === 0) return;
  const temp = settings.value.hierarchy[index];
  settings.value.hierarchy[index] = settings.value.hierarchy[index - 1];
  settings.value.hierarchy[index - 1] = temp;
  // Update orders
  settings.value.hierarchy.forEach((attr, i) => {
    attr.order = i;
  });
};

const moveDown = (index: number) => {
  if (index === settings.value.hierarchy.length - 1) return;
  const temp = settings.value.hierarchy[index];
  settings.value.hierarchy[index] = settings.value.hierarchy[index + 1];
  settings.value.hierarchy[index + 1] = temp;
  // Update orders
  settings.value.hierarchy.forEach((attr, i) => {
    attr.order = i;
  });
};

const generatePreview = () => {
  if (settings.value.hierarchy.length === 0) {
    return "No attributes defined";
  }

  return settings.value.hierarchy
    .map((attr) => {
      const name = attr.name || "?";
      const example =
        name === "CN"
          ? "test"
          : name === "O"
            ? "myOrg"
            : name === "OU"
              ? "myOrgUnit"
              : name === "DC"
                ? "myNet"
                : "value";
      return `${name}=${example}`;
    })
    .join(",");
};

// Modal functions
const viewAttribute = async (index: number) => {
  const attr = settings.value.hierarchy[index];
  editingIndex.value = index;

  try {
    // Fetch values from backend
    const data = await apiRequest(
      `/api/settings/hierarchy/values/${encodeURIComponent(attr.name)}`,
    );
    editingAttribute.value = {
      ...attr,
      values: data.values || [],
    };
  } catch (error) {
    console.error("Error loading values:", error);
    editingAttribute.value = {
      ...attr,
      values: [],
    };
  }

  isViewMode.value = true;
  showModal.value = true;
};

const editAttribute = async (index: number) => {
  const attr = settings.value.hierarchy[index];
  editingIndex.value = index;

  try {
    // Fetch values from backend
    const data = await apiRequest(
      `/api/settings/hierarchy/values/${encodeURIComponent(attr.name)}`,
    );
    editingAttribute.value = {
      ...attr,
      values: data.values || [],
    };
  } catch (error) {
    console.error("Error loading values:", error);
    editingAttribute.value = {
      ...attr,
      values: [],
    };
  }

  isViewMode.value = false;
  showModal.value = true;
};

const addValue = () => {
  if (editingAttribute.value) {
    if (!editingAttribute.value.values) {
      editingAttribute.value.values = [];
    }
    editingAttribute.value.values.push("");
  }
};

const removeValue = (index: number) => {
  if (editingAttribute.value?.values) {
    editingAttribute.value.values.splice(index, 1);
  }
};

const saveValues = async () => {
  if (editingIndex.value !== null && editingAttribute.value) {
    try {
      // Filter out empty values
      const cleanedValues =
        editingAttribute.value.values?.filter((v) => v.trim() !== "") || [];
      const attributeName = editingAttribute.value.name;

      // Save to backend
      await apiRequest("/api/settings/hierarchy/values", {
        method: "POST",
        body: JSON.stringify({
          attribute_name: attributeName,
          values: cleanedValues,
        }),
      });

      closeModal();
    } catch (error: any) {
      console.error("Error saving values:", error);
      alert("Error: " + (error.message || "Error saving values"));
    }
  }
};

const handleModalOk = async (bvModalEvent: any) => {
  if (isViewMode.value) {
    // Just close if viewing
    closeModal();
  } else {
    // Prevent modal from closing automatically
    bvModalEvent.preventDefault();
    // Call saveValues which will close the modal on success
    await saveValues();
  }
};

const closeModal = () => {
  showModal.value = false;
  editingIndex.value = null;
  editingAttribute.value = null;
  isViewMode.value = false;
};

const handleSave = async () => {
  // Validate all names
  settings.value.hierarchy.forEach((_, index) => validateUniqueName(index));

  if (hasErrors.value) {
    alert("Please fix validation errors before saving");
    return;
  }

  // Show warning about data loss
  const confirmed = confirm(
    "⚠️ WARNING: Changing the hierarchy format will REMOVE ALL FLOWS and rebuild the database!\n\n" +
      "This action cannot be undone. All existing NiFi flow entries will be permanently deleted.\n\n" +
      'Click "OK" if you understand and want to proceed, or "Cancel" to abort.',
  );

  if (!confirmed) {
    return;
  }

  // Second confirmation
  const doubleConfirmed = confirm(
    "Are you absolutely sure?\n\n" +
      "Type of changes: Hierarchy format modification\n" +
      "Impact: ALL flow data will be lost\n\n" +
      'Click "OK" only if you know what you are doing and want to proceed.',
  );

  if (!doubleConfirmed) {
    return;
  }

  isSaving.value = true;
  try {
    // Save settings first
    await apiRequest("/api/settings/hierarchy", {
      method: "POST",
      body: JSON.stringify(settings.value),
    });

    // Recreate the flows table with new hierarchy
    await apiRequest("/api/nifi-flows/recreate-table", {
      method: "POST",
    });

    alert(
      "✓ Hierarchy settings saved successfully!\n✓ NiFi flows table has been recreated with the new hierarchy.",
    );
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

onMounted(() => {
  loadSettings();
});
</script>

<style scoped lang="scss">
@import "./settings-common.scss";

.hierarchy-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.hierarchy-item {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 15px;
  background: #f8f9fa;
  border-radius: 6px;
  border: 1px solid #dee2e6;
}

.hierarchy-order {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #007bff;
  color: white;
  border-radius: 50%;
  font-weight: bold;
  font-size: 14px;
}

.hierarchy-fields {
  flex: 1;
}

.hierarchy-actions {
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;

  button {
    font-size: 12px;
    color: #6c757d;

    &:hover:not(:disabled) {
      color: #007bff;
    }

    &:disabled {
      opacity: 0.3;
    }
  }
}

.preview-box {
  padding: 15px;
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  border-radius: 6px;
  font-family: monospace;
  font-size: 14px;
  color: #212529;
  word-break: break-all;
}

.values-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.value-item {
  display: flex;
  gap: 8px;
  align-items: center;
}
</style>
