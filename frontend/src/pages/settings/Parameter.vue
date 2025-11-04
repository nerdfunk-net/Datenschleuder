<template>
  <div class="settings-page">
    <div class="page-header mb-4">
      <h2>Parameter Contexts</h2>
      <b-button
        variant="primary"
        @click="showCreateModal"
        class="new-context-btn"
      >
        <i class="pe-7s-plus"></i> New Parameter Context
      </b-button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <b-spinner></b-spinner>
      <p class="text-muted mt-2">Loading parameter contexts...</p>
    </div>

    <!-- Parameter Contexts by Instance -->
    <div v-else>
      <div v-for="instance in instances" :key="instance.id" class="mb-5">
        <h4 class="mb-3">
          <span class="badge bg-primary"
            >{{ instance.hierarchy_attribute }}={{
              instance.hierarchy_value
            }}</span
          >
          <span class="text-muted ms-2">{{ instance.nifi_url }}</span>
        </h4>

        <!-- Loading state for instance -->
        <div v-if="instanceLoading[instance.id]" class="text-center py-3">
          <b-spinner small></b-spinner>
          <span class="text-muted ms-2">Loading...</span>
        </div>

        <!-- Parameter Contexts Table -->
        <b-table
          v-else-if="parameterContextsByInstance[instance.id]?.length > 0"
          :items="parameterContextsByInstance[instance.id]"
          :fields="tableFields"
          striped
          hover
          responsive
          small
        >
          <template #cell(name)="data">
            <strong>{{ data.value }}</strong>
          </template>

          <template #cell(description)="data">
            <span class="text-muted">{{ data.value || "No description" }}</span>
          </template>

          <template #cell(parameter_count)="data">
            <span class="param-count"
              >{{ data.item.parameters?.length || 0 }} parameters</span
            >
          </template>

          <template #cell(actions)="data">
            <div class="action-buttons">
              <b-button
                variant="outline-primary"
                size="sm"
                @click="editParameterContext(instance.id, data.item)"
                title="Edit"
              >
                <i class="pe-7s-pen"></i>
              </b-button>
              <b-button
                variant="outline-secondary"
                size="sm"
                @click="copyParameterContext(instance.id, data.item)"
                title="Copy"
              >
                <i class="pe-7s-copy-file"></i>
              </b-button>
              <b-button
                variant="outline-danger"
                size="sm"
                @click="deleteParameterContext(instance.id, data.item)"
                title="Remove"
              >
                <i class="pe-7s-trash"></i>
              </b-button>
            </div>
          </template>
        </b-table>

        <!-- Empty state for instance -->
        <div v-else class="alert alert-info">
          <i class="pe-7s-info"></i> No parameter contexts found for this
          instance.
        </div>
      </div>

      <!-- Empty state -->
      <div v-if="instances.length === 0" class="alert alert-warning">
        <i class="pe-7s-attention"></i> No NiFi instances configured. Please
        configure a NiFi instance first.
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <b-modal
      v-model="showModal"
      :title="
        modalMode === 'create'
          ? 'Create Parameter Context'
          : 'Edit Parameter Context'
      "
      size="xl"
      @hidden="resetForm"
      ok-title="Save"
      cancel-title="Cancel"
      @ok="handleSave"
      :ok-disabled="saving"
      modal-class="parameter-modal"
      body-class="compact-modal-body"
    >
      <form @submit.prevent="handleSave">
        <!-- NiFi Instance Selection (only for create) -->
        <div v-if="modalMode === 'create'" class="mb-2">
          <label class="form-label compact-label">NiFi Instance</label>
          <b-form-select
            v-model="form.instance_id"
            :options="instanceOptions"
            required
            :disabled="modalMode !== 'create'"
            size="sm"
          ></b-form-select>
        </div>

        <!-- Name -->
        <div class="mb-2">
          <label class="form-label compact-label"
            >Name <span class="text-danger">*</span></label
          >
          <b-form-input
            v-model="form.name"
            required
            placeholder="Enter parameter context name"
            size="sm"
          ></b-form-input>
        </div>

        <!-- Description -->
        <div class="mb-2">
          <label class="form-label compact-label">Description</label>
          <b-form-textarea
            v-model="form.description"
            rows="2"
            placeholder="Enter description (optional)"
            size="sm"
          ></b-form-textarea>
        </div>

        <!-- Parameters Table -->
        <div class="mb-2">
          <label class="form-label compact-label">Parameters</label>
          <b-table
            :items="form.parameters"
            :fields="parameterFields"
            small
            bordered
          >
            <template #cell(name)="data">
              <b-form-input
                v-model="data.item.name"
                size="sm"
                :disabled="data.item.isExisting"
                placeholder="Parameter name"
              ></b-form-input>
            </template>

            <template #cell(value)="data">
              <b-form-input
                v-if="!data.item.sensitive"
                v-model="data.item.value"
                size="sm"
                placeholder="Parameter value"
                @input="markParameterAsLocal(data.item)"
              ></b-form-input>
              <b-form-input
                v-else
                v-model="data.item.value"
                type="password"
                size="sm"
                placeholder="Sensitive value"
                @input="markParameterAsLocal(data.item)"
              ></b-form-input>
            </template>

            <template #cell(description)="data">
              <b-form-input
                v-model="data.item.description"
                size="sm"
                placeholder="Description (optional)"
              ></b-form-input>
            </template>

            <template #cell(sensitive)="data">
              <b-form-checkbox
                v-model="data.item.sensitive"
                switch
              ></b-form-checkbox>
            </template>

            <template #cell(status)="data">
              <span
                v-if="data.item.inheritedFrom"
                :class="data.item.isOverridden ? 'status-overridden' : 'status-inherited'"
              >
                <i :class="data.item.isOverridden ? 'pe-7s-refresh-2' : 'pe-7s-link'"></i>
                {{ data.item.isOverridden ? 'Overridden' : 'Inherited' }} from {{ data.item.inheritedFrom }}
              </span>
              <span v-else class="status-local">
                <i class="pe-7s-home"></i> Local
              </span>
            </template>

            <template #cell(actions)="data">
              <b-button
                variant="link"
                size="sm"
                class="text-danger"
                @click="removeParameter(data.index)"
              >
                <i class="pe-7s-trash"></i>
              </b-button>
            </template>
          </b-table>

          <b-button
            variant="outline-primary"
            size="sm"
            @click="addParameter"
          >
            <i class="pe-7s-plus"></i> Add Parameter
          </b-button>
          <b-button
            v-if="modalMode === 'edit'"
            variant="outline-secondary"
            size="sm"
            @click.prevent.stop="showInheritanceModal"
            class="ms-2"
            type="button"
          >
            <i class="pe-7s-link"></i> Edit Inheritance
          </b-button>
        </div>
      </form>
    </b-modal>

    <!-- Inheritance Management Modal -->
    <b-modal
      ref="inheritanceModal"
      title="🔗 Manage Parameter Context Inheritance"
      size="xl"
      modal-class="inheritance-modal"
      body-class="compact-modal-body"
      :hide-header-close="false"
      :no-close-on-backdrop="true"
      :no-close-on-esc="true"
      hide-footer
      @show="onInheritanceModalShow"
      @shown="onInheritanceModalShown"
      @hide="onInheritanceModalHide"
      @hidden="onInheritanceModalHidden"
    >

      <div class="inheritance-container">
        <!-- Available Parameter Contexts -->
        <div class="inheritance-panel">
          <h5 class="panel-title">Available Parameter Contexts</h5>
          <div class="context-list available-list">
            <div
              v-for="context in availableContexts"
              :key="context.id"
              class="context-item"
              draggable="true"
              @dragstart="onDragStart($event, context, 'available')"
              @dragend="onDragEnd"
            >
              <i class="pe-7s-menu"></i>
              <span class="context-name">{{ context.name }}</span>
            </div>
            <div v-if="availableContexts.length === 0" class="empty-state">
              All contexts are already inherited
            </div>
          </div>
        </div>

        <!-- Arrow -->
        <div class="arrow-container">
          <i class="pe-7s-angle-right"></i>
        </div>

        <!-- Inherited Parameter Contexts -->
        <div class="inheritance-panel">
          <h5 class="panel-title">Inherited Parameter Contexts (in order)</h5>
          <div
            class="context-list inherited-list"
            @dragover="onDragOver"
            @drop="onDrop($event, 'inherited')"
          >
            <div
              v-for="(context, index) in inheritedContexts"
              :key="context.id"
              class="context-item inherited-item"
              draggable="true"
              @dragstart="onDragStart($event, context, 'inherited')"
              @dragend="onDragEnd"
              @dragover="onDragOver"
              @drop="onDropReorder($event, index)"
            >
              <i class="pe-7s-menu drag-handle"></i>
              <span class="context-name">{{ context.name }}</span>
              <span class="order-badge">{{ index + 1 }}</span>
              <b-button
                variant="link"
                size="sm"
                class="remove-btn"
                @click="removeFromInherited(index)"
              >
                <i class="pe-7s-close-circle"></i>
              </b-button>
            </div>
            <div v-if="inheritedContexts.length === 0" class="empty-state">
              Drag contexts here to inherit parameters
            </div>
          </div>
        </div>
      </div>

      <!-- Custom Footer -->
      <div class="custom-modal-footer">
        <b-button variant="secondary" @click="closeInheritanceModal">
          Cancel
        </b-button>
        <b-button
          variant="primary"
          @click.prevent.stop="saveInheritance"
          :disabled="savingInheritance"
          type="button"
        >
          Save
        </b-button>
      </div>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import api from "@/utils/api";

// Simple notification helper
const showError = (message: string) => alert("Error: " + message);
const showSuccess = (message: string) => alert("Success: " + message);

// State
const loading = ref(false);
const instances = ref<any[]>([]);
const parameterContextsByInstance = ref<Record<number, any[]>>({});
const instanceLoading = ref<Record<number, boolean>>({});
const showModal = ref(false);
const modalMode = ref<"create" | "edit">("create");
const saving = ref(false);

// Inheritance modal state
const inheritanceModal = ref<any>(null);
const savingInheritance = ref(false);
const availableContexts = ref<any[]>([]);
const inheritedContexts = ref<any[]>([]);
const draggedItem = ref<any>(null);
const draggedFrom = ref<string>("");
const allParameterContexts = ref<any[]>([]);

// Form
const form = ref({
  instance_id: null as number | null,
  context_id: null as string | null,
  name: "",
  description: "",
  parameters: [] as any[],
  inherited_parameter_contexts: [] as string[],
});

// Table fields
const tableFields = [
  { key: "name", label: "Name", sortable: true },
  { key: "description", label: "Description", sortable: true },
  { key: "parameter_count", label: "Parameters", sortable: true },
  { key: "actions", label: "Actions", class: "text-end" },
];

const parameterFields = [
  { key: "name", label: "Name", thStyle: { width: "20%" } },
  { key: "value", label: "Value", thStyle: { width: "25%" } },
  { key: "description", label: "Description", thStyle: { width: "20%" } },
  { key: "sensitive", label: "Sensitive", thStyle: { width: "10%" } },
  { key: "status", label: "Status", thStyle: { width: "20%" } },
  { key: "actions", label: "", class: "text-end", thStyle: { width: "5%" } },
];

// Computed
const instanceOptions = computed(() => {
  return instances.value.map((instance) => ({
    value: instance.id,
    text: `${instance.hierarchy_attribute}=${instance.hierarchy_value} (${instance.nifi_url})`,
  }));
});

// Helper functions for inheritance
async function buildInheritedParametersMap(
  instanceId: number,
  inheritedContextIds: any[]
) {
  console.log("buildInheritedParametersMap called with:", { instanceId, inheritedContextIds });

  const inheritedMap = new Map<
    string,
    { value: string; description: string; sensitive: boolean; contextName: string }
  >();

  // Process each inherited context in order
  for (const inheritedContext of inheritedContextIds) {
    try {
      const contextId =
        typeof inheritedContext === "object" ? inheritedContext.id : inheritedContext;

      console.log(`Fetching inherited context: ${contextId}`);

      const response = await api.get(
        `/api/nifi-instances/${instanceId}/parameter-contexts/${contextId}`
      );

      console.log("Inherited context response:", response);

      // Handle different response structures
      const contextDetails = response.parameter_context || response.data || response;

      console.log("Inherited context details:", contextDetails);

      // Add or overwrite parameters from this context
      if (contextDetails.parameters && contextDetails.parameters.length > 0) {
        console.log(`Found ${contextDetails.parameters.length} parameters in inherited context`);
        for (const param of contextDetails.parameters) {
          inheritedMap.set(param.name, {
            value: param.value || "",
            description: param.description || "",
            sensitive: param.sensitive || false,
            contextName: contextDetails.name,
          });
        }
      } else {
        console.log("No parameters in inherited context");
      }
    } catch (error: any) {
      console.error(`Failed to load inherited context:`, error);
    }
  }

  console.log("Final inherited map:", inheritedMap);
  return inheritedMap;
}

function buildCombinedParametersList(localParams: any[], inheritedMap: Map<string, any>) {
  const combinedParams: any[] = [];
  const processedKeys = new Set<string>();

  // First, add local parameters (these may override inherited ones)
  for (const param of localParams) {
    const inheritedParam = inheritedMap.get(param.name);

    combinedParams.push({
      name: param.name,
      value: param.value || "",
      description: param.description || "",
      sensitive: param.sensitive || false,
      isExisting: true,
      isLocal: true, // This parameter is defined locally
      inheritedFrom: inheritedParam ? inheritedParam.contextName : null,
      isOverridden: !!inheritedParam, // True if this overrides an inherited param
    });

    processedKeys.add(param.name);
  }

  // Then, add inherited parameters that aren't overridden
  for (const [key, inheritedParam] of inheritedMap.entries()) {
    if (!processedKeys.has(key)) {
      combinedParams.push({
        name: key,
        value: inheritedParam.value,
        description: inheritedParam.description,
        sensitive: inheritedParam.sensitive,
        isExisting: true,
        isLocal: false, // This parameter is only inherited, not local
        inheritedFrom: inheritedParam.contextName,
        isOverridden: false,
      });
    }
  }

  return combinedParams;
}

// Methods
async function loadInstances() {
  try {
    loading.value = true;
    const response = await api.get("/api/nifi-instances/");
    instances.value = response;

    // Load parameter contexts for each instance
    for (const instance of instances.value) {
      await loadParameterContexts(instance.id);
    }
  } catch (error: any) {
    showError(error.message || "Failed to load NiFi instances");
  } finally {
    loading.value = false;
  }
}

async function loadParameterContexts(instanceId: number) {
  try {
    instanceLoading.value[instanceId] = true;
    const response = await api.get(
      `/api/nifi-instances/${instanceId}/get-parameters`,
    );

    console.log(
      `Loaded parameter contexts for instance ${instanceId}:`,
      response,
    );

    if (response.status === "success") {
      // Force reactive update by creating a new object
      parameterContextsByInstance.value = {
        ...parameterContextsByInstance.value,
        [instanceId]: response.parameter_contexts,
      };
      console.log(
        `Updated parameterContextsByInstance[${instanceId}] with ${response.parameter_contexts.length} contexts`,
      );
    } else {
      parameterContextsByInstance.value = {
        ...parameterContextsByInstance.value,
        [instanceId]: [],
      };
      if (response.message) {
        console.warn(
          `Failed to load parameters for instance ${instanceId}:`,
          response.message,
        );
      }
    }
  } catch (error: any) {
    console.error(
      `Error loading parameters for instance ${instanceId}:`,
      error,
    );
    parameterContextsByInstance.value = {
      ...parameterContextsByInstance.value,
      [instanceId]: [],
    };
  } finally {
    instanceLoading.value[instanceId] = false;
  }
}

function showCreateModal() {
  modalMode.value = "create";
  resetForm();
  showModal.value = true;
}

async function editParameterContext(instanceId: number, context: any) {
  console.log("editParameterContext called with:", { instanceId, context });

  modalMode.value = "edit";
  loading.value = true;

  try {
    // Fetch detailed parameter context configuration
    console.log(`Fetching: /api/nifi-instances/${instanceId}/parameter-contexts/${context.id}`);

    const response = await api.get(
      `/api/nifi-instances/${instanceId}/parameter-contexts/${context.id}`
    );

    console.log("API Response:", response);

    // Handle different response structures
    const detailedContext = response.parameter_context || response.data || response;

    console.log("Detailed context:", detailedContext);

    // Build inherited parameters map
    const inheritedParams = await buildInheritedParametersMap(
      instanceId,
      detailedContext.inherited_parameter_contexts || []
    );

    // Get local parameters
    const localParams = detailedContext.parameters || [];

    console.log("Local params:", localParams);
    console.log("Inherited params:", inheritedParams);

    // Build combined parameters list with inheritance info
    const combinedParams = buildCombinedParametersList(localParams, inheritedParams);

    console.log("Combined params:", combinedParams);

    form.value = {
      instance_id: instanceId,
      context_id: context.id,
      name: detailedContext.name || context.name,
      description: detailedContext.description || "",
      parameters: combinedParams,
      inherited_parameter_contexts: detailedContext.inherited_parameter_contexts || [],
    };

    showModal.value = true;
  } catch (error: any) {
    console.error("Error loading parameter context:", error);
    showError(error.message || "Failed to load parameter context details");
  } finally {
    loading.value = false;
  }
}

function copyParameterContext(instanceId: number, context: any) {
  modalMode.value = "create";
  form.value = {
    instance_id: instanceId,
    context_id: null,
    name: `copy_of_${context.name}`,
    description: context.description || "",
    parameters: context.parameters.map((p: any) => ({
      name: p.name,
      value: p.value || "",
      description: p.description || "",
      sensitive: p.sensitive || false,
      isExisting: false,
      isLocal: true,
      inheritedFrom: null,
      isOverridden: false,
    })),
    inherited_parameter_contexts: [],
  };
  showModal.value = true;
}

async function deleteParameterContext(instanceId: number, context: any) {
  if (
    !confirm(
      `Are you sure you want to delete parameter context "${context.name}"?`,
    )
  ) {
    return;
  }

  try {
    await api.delete(
      `/api/nifi-instances/${instanceId}/parameter-contexts/${context.id}`,
    );
    showSuccess("Parameter context deleted successfully");
    await loadParameterContexts(instanceId);
  } catch (error: any) {
    showError(error.message || "Failed to delete parameter context");
  }
}

function addParameter() {
  form.value.parameters.push({
    name: "",
    value: "",
    description: "",
    sensitive: false,
    isExisting: false,
    isLocal: true,
    inheritedFrom: null,
    isOverridden: false,
  });
}

function markParameterAsLocal(parameter: any) {
  // When editing an inherited parameter, mark it as local (overridden)
  if (!parameter.isLocal && parameter.inheritedFrom) {
    parameter.isLocal = true;
    parameter.isOverridden = true;
  }
}

function removeParameter(index: number) {
  form.value.parameters.splice(index, 1);
}

async function handleSave(bvModalEvent?: any) {
  // Prevent modal from closing automatically
  if (bvModalEvent) {
    bvModalEvent.preventDefault();
  }

  console.log("handleSave called", {
    modalMode: modalMode.value,
    form: form.value,
  });

  if (!form.value.name) {
    showError("Please enter a name for the parameter context");
    return;
  }

  if (modalMode.value === "create" && !form.value.instance_id) {
    showError("Please select a NiFi instance");
    return;
  }

  if (modalMode.value === "edit" && !form.value.instance_id) {
    showError("Instance ID is missing");
    return;
  }

  if (modalMode.value === "edit" && !form.value.context_id) {
    showError("Context ID is missing");
    return;
  }

  try {
    saving.value = true;

    const payload = {
      name: form.value.name,
      description: form.value.description || undefined,
      inherited_parameter_contexts: form.value.inherited_parameter_contexts.length > 0
        ? form.value.inherited_parameter_contexts
        : [],  // Send empty array instead of null to clear inheritance
      parameters: form.value.parameters
        .filter((p) => p.name && p.isLocal) // Only include local parameters with names
        .map((p) => ({
          name: p.name,
          description: p.description || undefined,
          sensitive: p.sensitive || false,
          value: p.value || undefined,
        })),
    };

    console.log("Sending request:", {
      mode: modalMode.value,
      instanceId: form.value.instance_id,
      contextId: form.value.context_id,
      payload,
      originalParameters: form.value.parameters,
    });

    if (modalMode.value === "create") {
      const result = await api.post(
        `/api/nifi-instances/${form.value.instance_id}/parameter-contexts`,
        payload,
      );
      console.log("Create result:", result);
      await loadParameterContexts(form.value.instance_id!);
    } else if (modalMode.value === "edit") {
      const result = await api.put(
        `/api/nifi-instances/${form.value.instance_id}/parameter-contexts/${form.value.context_id}`,
        payload,
      );
      console.log("Update result:", result);
      await loadParameterContexts(form.value.instance_id!);
    }

    showModal.value = false;
  } catch (error: any) {
    console.error("Save error:", error);
    showError(
      error.message || `Failed to ${modalMode.value} parameter context`,
    );
  } finally {
    saving.value = false;
  }
}

function resetForm() {
  form.value = {
    instance_id: instances.value.length > 0 ? instances.value[0].id : null,
    context_id: null,
    name: "",
    description: "",
    parameters: [],
    inherited_parameter_contexts: [],
  };
}

// Inheritance management methods
async function showInheritanceModal() {
  console.log("showInheritanceModal called");

  if (!form.value.instance_id) {
    showError("Instance ID is missing");
    return;
  }

  try {
    // Fetch all parameter contexts for this instance
    console.log("Fetching all parameter contexts for instance:", form.value.instance_id);
    const response = await api.get(
      `/api/nifi-instances/${form.value.instance_id}/get-parameters`
    );

    console.log("Parameter contexts response:", response);

    if (response.status === "success") {
      allParameterContexts.value = response.parameter_contexts;

      // Use the locally stored inherited contexts from the form (not from server)
      // This ensures we show the current state including unsaved changes
      const inheritedIds = form.value.inherited_parameter_contexts || [];

      console.log("Using local inherited_parameter_contexts:", inheritedIds);

      // Map inherited IDs to full context objects in order
      inheritedContexts.value = inheritedIds
        .map((id: string) => allParameterContexts.value.find((ctx) => ctx.id === id))
        .filter((ctx: any) => ctx !== undefined);

      // Build available contexts (excluding current context and already inherited)
      const inheritedIdSet = new Set(inheritedIds);
      availableContexts.value = allParameterContexts.value.filter(
        (ctx) => ctx.id !== form.value.context_id && !inheritedIdSet.has(ctx.id)
      );

      console.log("Available contexts:", availableContexts.value);
      console.log("Inherited contexts:", inheritedContexts.value);
      console.log("Opening inheritance modal");

      // Use $refs to manually show the modal with a small delay
      // to ensure the DOM is ready
      setTimeout(() => {
        if (inheritanceModal.value) {
          console.log("Calling inheritanceModal.show()");
          inheritanceModal.value.show();
          console.log("inheritanceModal.show() called");
        } else {
          console.error("inheritanceModal ref is null");
        }
      }, 100);
    }
  } catch (error: any) {
    showError(error.message || "Failed to load parameter contexts");
  }
}

function onInheritanceModalShow(event: any) {
  console.log("onInheritanceModalShow - modal is showing", event);
}

function onInheritanceModalShown() {
  console.log("onInheritanceModalShown - modal is fully shown");
}

function onModalOk(event: any) {
  console.log("onModalOk - preventing default OK behavior");
  event.preventDefault();
}

function onInheritanceModalHide(event: any) {
  console.log("onInheritanceModalHide - modal is hiding", event);

  // Check if the modal is being closed unexpectedly
  if (event && event.trigger) {
    console.log("Hide trigger:", event.trigger);

    // Prevent closing if triggered by OK button
    if (event.trigger === 'ok') {
      console.log("Preventing OK trigger close");
      event.preventDefault();
    }
  }
}

function onInheritanceModalHidden() {
  console.log("onInheritanceModalHidden - modal is hidden");

  availableContexts.value = [];
  inheritedContexts.value = [];
  draggedItem.value = null;
  draggedFrom.value = "";
}

function closeInheritanceModal() {
  console.log("closeInheritanceModal called");
  console.trace("closeInheritanceModal stack trace");
  if (inheritanceModal.value) {
    inheritanceModal.value.hide();
  }
}

// Drag and drop handlers
function onDragStart(event: DragEvent, context: any, from: string) {
  draggedItem.value = context;
  draggedFrom.value = from;
  if (event.target instanceof HTMLElement) {
    event.target.classList.add("dragging");
  }
}

function onDragEnd(event: DragEvent) {
  if (event.target instanceof HTMLElement) {
    event.target.classList.remove("dragging");
  }
}

function onDragOver(event: DragEvent) {
  event.preventDefault();
}

function onDrop(event: DragEvent, to: string) {
  event.preventDefault();

  if (!draggedItem.value) return;

  if (draggedFrom.value === "available" && to === "inherited") {
    // Add to inherited list
    inheritedContexts.value.push(draggedItem.value);
    // Remove from available list
    availableContexts.value = availableContexts.value.filter(
      (ctx) => ctx.id !== draggedItem.value.id
    );
  }

  draggedItem.value = null;
  draggedFrom.value = "";
}

function onDropReorder(event: DragEvent, targetIndex: number) {
  event.preventDefault();
  event.stopPropagation();

  if (!draggedItem.value || draggedFrom.value !== "inherited") return;

  // Find current index
  const currentIndex = inheritedContexts.value.findIndex(
    (ctx) => ctx.id === draggedItem.value.id
  );

  if (currentIndex === -1 || currentIndex === targetIndex) return;

  // Remove from current position
  const item = inheritedContexts.value.splice(currentIndex, 1)[0];

  // Insert at new position
  const newIndex = currentIndex < targetIndex ? targetIndex : targetIndex;
  inheritedContexts.value.splice(newIndex, 0, item);
}

function removeFromInherited(index: number) {
  const removed = inheritedContexts.value.splice(index, 1)[0];
  availableContexts.value.push(removed);
}

async function saveInheritance() {
  console.log("=== saveInheritance called ===");
  console.log("Inherited contexts:", inheritedContexts.value);

  // Build the list of inherited context IDs in order
  const inheritedIds = inheritedContexts.value.map((ctx) => ctx.id);

  console.log("Updating form with inheritance IDs:", inheritedIds);

  // Update the form with new inherited contexts (local copy only)
  form.value.inherited_parameter_contexts = inheritedIds;

  // Close the inheritance modal
  if (inheritanceModal.value) {
    inheritanceModal.value.hide();
  }

  // Rebuild parameters list with new inheritance
  await rebuildParametersWithInheritance();
}

async function rebuildParametersWithInheritance() {
  if (!form.value.instance_id) return;

  try {
    console.log("Rebuilding parameters with inheritance:", form.value.inherited_parameter_contexts);

    // Build inherited parameters map from the new inheritance list
    const inheritedParams = await buildInheritedParametersMap(
      form.value.instance_id,
      form.value.inherited_parameter_contexts
    );

    // Get current local parameters (only those marked as local)
    const localParams = form.value.parameters.filter((p) => p.isLocal);

    console.log("Local params:", localParams);
    console.log("Inherited params:", inheritedParams);

    // Build combined parameters list with new inheritance info
    const combinedParams = buildCombinedParametersList(localParams, inheritedParams);

    console.log("Combined params after inheritance update:", combinedParams);

    // Update form parameters
    form.value.parameters = combinedParams;
  } catch (error: any) {
    console.error("Error rebuilding parameters:", error);
    showError("Failed to update parameters with new inheritance");
  }
}

onMounted(() => {
  loadInstances();
});
</script>

<style scoped>
.settings-page {
  padding: 0;
}

.page-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 1rem 1.5rem;
  border-radius: 8px;
  margin-bottom: 2rem;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.page-header h2 {
  color: white;
  margin: 0;
  font-size: 1.5rem;
  font-weight: 600;
}

.new-context-btn {
  background: white !important;
  color: #667eea !important;
  border: none !important;
  font-weight: 600 !important;
  padding: 0.5rem 1.25rem !important;
  border-radius: 6px !important;
  transition: all 0.3s ease !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1) !important;
}

.new-context-btn:hover {
  background: #f8f9fa !important;
  color: #764ba2 !important;
  transform: translateY(-1px) !important;
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15) !important;
}

.new-context-btn i {
  margin-right: 0.5rem;
}

h4 .badge {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%) !important;
  color: white;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 600;
}

h4 .text-muted {
  color: #6c757d !important;
  font-size: 0.9rem;
  font-weight: normal;
}

/* Table styling */
:deep(.table) {
  background: white;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border: 1px solid #e9ecef;
}

:deep(.table thead th) {
  background: #667eea;
  color: white;
  border: none;
  padding: 0.375rem 0.5rem;
  font-weight: 600;
  text-transform: uppercase;
  font-size: 0.7rem;
  letter-spacing: 0.3px;
  border-right: 1px solid rgba(255, 255, 255, 0.1);
}

:deep(.table thead th:last-child) {
  border-right: none;
}

:deep(.table tbody tr) {
  border-bottom: 1px solid #e9ecef;
  transition: background-color 0.2s ease;
}

:deep(.table tbody tr:hover) {
  background-color: #f8f9fa;
}

:deep(.table tbody tr:last-child) {
  border-bottom: none;
}

:deep(.table tbody td) {
  padding: 0.375rem 0.5rem;
  vertical-align: middle;
  color: #2c3e50;
  border-right: 1px solid #f1f3f5;
  font-size: 0.875rem;
}

:deep(.table tbody td:last-child) {
  border-right: none;
}

:deep(.table tbody td strong) {
  color: #1a202c;
  font-weight: 600;
  font-size: 0.875rem;
}

:deep(.table tbody td .text-muted) {
  color: #6c757d !important;
  font-size: 0.875rem;
}

:deep(.table tbody td .param-count) {
  color: #2c3e50;
  font-weight: 500;
  font-size: 0.875rem;
}

:deep(.table .badge) {
  background: #667eea;
  color: white;
  padding: 0.35rem 0.75rem;
  border-radius: 4px;
  font-weight: 500;
  font-size: 0.8rem;
}

/* Action buttons */
.action-buttons {
  display: flex;
  gap: 0.25rem;
  justify-content: flex-end;
}

:deep(.action-buttons .btn) {
  padding: 0.15rem 0.4rem;
  border-radius: 3px;
  transition: all 0.2s ease;
}

:deep(.action-buttons .btn:focus, .action-buttons .btn:active) {
  box-shadow: none !important;
  outline: none !important;
}

:deep(.action-buttons .btn i) {
  font-size: 0.9rem;
}

:deep(.action-buttons .btn-outline-primary) {
  color: #667eea;
  border-color: #667eea;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-primary:hover) {
  background-color: #667eea;
  border-color: #667eea;
  color: white;
}

:deep(
  .action-buttons .btn-outline-primary:focus,
  .action-buttons .btn-outline-primary:active
) {
  color: #667eea !important;
  border-color: #667eea !important;
  background-color: transparent !important;
}

:deep(.action-buttons .btn-outline-secondary) {
  color: #6c757d;
  border-color: #6c757d;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-secondary:hover) {
  background-color: #6c757d;
  border-color: #6c757d;
  color: white;
}

:deep(
  .action-buttons .btn-outline-secondary:focus,
  .action-buttons .btn-outline-secondary:active
) {
  color: #6c757d !important;
  border-color: #6c757d !important;
  background-color: transparent !important;
}

:deep(.action-buttons .btn-outline-danger) {
  color: #dc3545;
  border-color: #dc3545;
  background-color: transparent;
}

:deep(.action-buttons .btn-outline-danger:hover) {
  background-color: #dc3545;
  border-color: #dc3545;
  color: white;
}

:deep(
  .action-buttons .btn-outline-danger:focus,
  .action-buttons .btn-outline-danger:active
) {
  color: #dc3545 !important;
  border-color: #dc3545 !important;
  background-color: transparent !important;
}

/* Alert styling */
.alert {
  border-radius: 8px;
  border: none;
  padding: 1rem 1.5rem;
}

.alert-info {
  background: linear-gradient(
    135deg,
    rgba(102, 126, 234, 0.1) 0%,
    rgba(118, 75, 162, 0.1) 100%
  );
  color: #667eea;
  border-left: 4px solid #667eea;
}

.alert-warning {
  background: linear-gradient(
    135deg,
    rgba(255, 193, 7, 0.1) 0%,
    rgba(255, 152, 0, 0.1) 100%
  );
  color: #ff9800;
  border-left: 4px solid #ff9800;
}

/* Loading spinner */
.text-center {
  padding: 3rem;
}

:deep(.spinner-border) {
  color: #667eea;
}

/* Compact modal styling */
.compact-modal-body {
  padding: 0.75rem 1rem !important;
}

.compact-label {
  font-size: 0.875rem;
  font-weight: 600;
  margin-bottom: 0.25rem;
}

/* Parameter status indicators */
.status-inherited {
  color: #17a2b8;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-inherited i {
  margin-right: 0.25rem;
}

.status-overridden {
  color: #ff9800;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-overridden i {
  margin-right: 0.25rem;
}

.status-local {
  color: #28a745;
  font-size: 0.8rem;
  font-weight: 500;
}

.status-local i {
  margin-right: 0.25rem;
}

/* Inheritance modal styling */
.inheritance-container {
  display: flex;
  gap: 1rem;
  align-items: stretch;
  min-height: 400px;
}

.inheritance-panel {
  flex: 1;
  display: flex;
  flex-direction: column;
}

.panel-title {
  font-size: 1rem;
  font-weight: 600;
  color: #667eea;
  margin-bottom: 0.75rem;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #667eea;
}

.context-list {
  flex: 1;
  border: 2px dashed #e9ecef;
  border-radius: 8px;
  padding: 0.75rem;
  min-height: 300px;
  overflow-y: auto;
  background: #f8f9fa;
}

.inherited-list {
  border-color: #667eea;
  background: #f0f2ff;
}

.context-item {
  background: white;
  border: 1px solid #e9ecef;
  border-radius: 6px;
  padding: 0.75rem;
  margin-bottom: 0.5rem;
  cursor: move;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  transition: all 0.2s ease;
}

.context-item:hover {
  border-color: #667eea;
  box-shadow: 0 2px 4px rgba(102, 126, 234, 0.2);
  transform: translateY(-1px);
}

.context-item.dragging {
  opacity: 0.5;
}

.context-item i.pe-7s-menu {
  color: #6c757d;
  font-size: 1.2rem;
}

.context-name {
  flex: 1;
  font-weight: 500;
  color: #2c3e50;
}

.inherited-item {
  background: linear-gradient(135deg, #ffffff 0%, #f0f2ff 100%);
  border-color: #667eea;
}

.order-badge {
  background: #667eea;
  color: white;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.remove-btn {
  padding: 0;
  color: #dc3545;
}

.remove-btn:hover {
  color: #c82333;
}

.remove-btn i {
  font-size: 1.2rem;
}

.arrow-container {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.5rem;
}

.arrow-container i {
  font-size: 2rem;
  color: #667eea;
}

.empty-state {
  text-align: center;
  color: #6c757d;
  font-style: italic;
  padding: 2rem;
}

.drag-handle {
  cursor: grab;
}

.drag-handle:active {
  cursor: grabbing;
}

.custom-modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 1rem 0 0 0;
  border-top: 1px solid #e9ecef;
  margin-top: 1rem;
}
</style>

<style lang="scss">
/* Modal styling - copied from flow-modal */
.parameter-modal {
  .modal-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 12px 20px;
    border-bottom: none;

    .modal-title {
      color: white;
      font-weight: 600;
    }

    .btn-close {
      filter: brightness(0) invert(1);
      opacity: 0.8;

      &:hover {
        opacity: 1;
      }
    }
  }
}

/* Hide default modal footer in inheritance modal */
.inheritance-modal {
  .modal-footer {
    display: none !important;
  }
}
</style>
