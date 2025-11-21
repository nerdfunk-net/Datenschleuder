<template>
  <div class="settings-page">
    <div class="page-card">
      <!-- Header -->
      <div class="card-header d-flex justify-content-between align-items-center">
        <div>
          <h2 class="card-title">
            User Management
          </h2>
          <p class="text-muted mb-0 small">
            Manage users, roles, and permissions
          </p>
        </div>
        <b-button variant="primary" @click="showCreateModal">
          <i class="pe-7s-plus"></i> Add User
        </b-button>
      </div>

      <!-- Loading State -->
      <div v-if="isLoading" class="text-center py-5">
        <b-spinner variant="primary" />
        <p class="mt-3 text-muted">
          Loading users...
        </p>
      </div>

      <!-- Users Table -->
      <div v-else-if="users.length > 0" class="table-responsive">
        <table class="table users-table">
          <thead>
            <tr>
              <th style="width: 35%">
                Username
              </th>
              <th style="width: 20%">
                Role
              </th>
              <th style="width: 20%">
                Status
              </th>
              <th style="width: 15%">
                Created
              </th>
              <th style="width: 10%" class="text-end">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="user in users" :key="user.id" :class="{ 'table-warning': !user.is_active }">
              <td>
                <div class="d-flex align-items-center">
                  <div
                    class="user-avatar"
                    :class="{ 'bg-danger': user.is_superuser, 'bg-primary': !user.is_superuser, 'opacity-50': !user.is_active }"
                  >
                    <i class="pe-7s-user"></i>
                  </div>
                  <div class="ms-3">
                    <div class="fw-medium">
                      {{ user.username }}
                      <span v-if="!user.is_active" class="badge bg-warning text-dark ms-2">
                        <i class="pe-7s-attention"></i> Pending Approval
                      </span>
                    </div>
                    <small v-if="user.username === 'admin'" class="text-muted">
                      <i class="pe-7s-lock"></i> System Account
                    </small>
                    <small v-else-if="user.is_oidc_user" class="text-muted">
                      <i class="pe-7s-cloud"></i> OIDC User
                    </small>
                  </div>
                </div>
              </td>
              <td>
                <span
                  :class="[
                    'badge',
                    user.is_superuser ? 'bg-danger' : 'bg-success',
                  ]"
                >
                  {{ user.is_superuser ? "Admin" : "User" }}
                </span>
              </td>
              <td>
                <span
                  :class="[
                    'badge',
                    user.is_active ? 'bg-success' : 'bg-secondary',
                  ]"
                >
                  {{ user.is_active ? "Active" : "Inactive" }}
                </span>
              </td>
              <td class="text-muted small">
                {{ formatDate(user.created_at) }}
              </td>
              <td class="text-end">
                <div class="btn-group btn-group-sm">
                  <b-button
                    variant="outline-primary"
                    size="sm"
                    :disabled="user.username === 'admin'"
                    title="Edit user"
                    @click="editUser(user)"
                  >
                    <i class="pe-7s-pen"></i>
                  </b-button>
                  <b-button
                    variant="outline-danger"
                    size="sm"
                    :disabled="user.username === 'admin'"
                    title="Delete user"
                    @click="confirmDelete(user)"
                  >
                    <i class="pe-7s-trash"></i>
                  </b-button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Empty State -->
      <div v-else class="text-center py-5">
        <i class="pe-7s-users" style="font-size: 4rem; color: #6c757d"></i>
        <h4 class="mt-3">
          No Users Found
        </h4>
        <p class="text-muted">
          Create your first user to get started
        </p>
      </div>
    </div>

    <!-- Create/Edit User Modal -->
    <b-modal
      v-model="isModalVisible"
      :title="editingUser ? 'Edit User' : 'Create New User'"
      size="lg"
      :ok-title="editingUser ? 'Update User' : 'Create User'"
      ok-variant="primary"
      cancel-title="Cancel"
      cancel-variant="secondary"
      :ok-disabled="isSaving"
      centered
      @hidden="resetForm"
      @ok="handleModalOk"
    >
      <div>
        <div class="row">
          <div class="col-12 mb-3">
            <label class="form-label">Username</label>
            <input
              v-model="formData.username"
              type="text"
              class="form-control"
              :disabled="!!editingUser"
              placeholder="Enter username"
              required
              autocomplete="off"
            />
            <small v-if="editingUser" class="text-muted">
              Username cannot be changed
            </small>
          </div>

          <div class="col-12 mb-3">
            <label v-if="!editingUser || canChangePassword" class="form-label">Password</label>
            <input
              v-if="!editingUser || canChangePassword"
              v-model="formData.password"
              type="password"
              class="form-control"
              :placeholder="
                editingUser
                  ? 'Leave empty to keep current password'
                  : 'Enter password'
              "
              :required="!editingUser"
              autocomplete="new-password"
            />
            <small v-if="editingUser && editingUser.is_oidc_user" class="text-warning d-block mt-1">
              <i class="pe-7s-attention"></i> Password cannot be changed for OIDC users
            </small>
          </div>

          <div class="col-md-6 mb-3">
            <label class="form-label">Role</label>
            <select
              v-model="formData.is_superuser"
              class="form-select"
              :disabled="!!(editingUser && editingUser.username === 'admin')"
            >
              <option :value="false">
                User
              </option>
              <option :value="true">
                Admin
              </option>
            </select>
            <small v-if="editingUser && editingUser.username === 'admin'" class="text-muted d-block mt-1">
              <i class="pe-7s-lock"></i> Admin role cannot be changed
            </small>
          </div>

          <div class="col-md-6 mb-3">
            <label class="form-label">Status</label>
            <select
              v-model="formData.is_active"
              class="form-select"
              :disabled="!!(editingUser && editingUser.username === 'admin')"
            >
              <option :value="true">
                Active
              </option>
              <option :value="false">
                Inactive
              </option>
            </select>
          </div>
        </div>

        <div v-if="editingUser && editingUser.is_oidc_user" class="alert alert-info mb-0">
          <i class="pe-7s-info"></i> This user authenticates via OIDC. Some properties cannot be modified.
        </div>

        <div v-if="modalError" class="alert alert-danger alert-dismissible fade show mb-0 mt-3" role="alert">
          {{ modalError }}
          <button
            type="button"
            class="btn-close"
            aria-label="Close"
            @click="modalError = ''"
          ></button>
        </div>
      </div>
    </b-modal>

    <!-- Delete Confirmation Modal -->
    <b-modal
      v-model="isDeleteModalVisible"
      title="Delete User"
      ok-variant="danger"
      ok-title="Delete"
      @ok="deleteUser"
    >
      <p>
        Are you sure you want to delete user
        <strong>{{ userToDelete?.username }}</strong>?
      </p>
      <p class="text-danger mb-0">
        This action cannot be undone.
      </p>
    </b-modal>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import api from "../../utils/api";

interface User {
  id: number;
  username: string;
  is_active: boolean;
  is_superuser: boolean;
  is_oidc_user: boolean;
  created_at: string;
}

const users = ref<User[]>([]);
const isLoading = ref(false);
const isModalVisible = ref(false);
const isDeleteModalVisible = ref(false);
const isSaving = ref(false);
const editingUser = ref<User | null>(null);
const userToDelete = ref<User | null>(null);
const modalError = ref("");

const formData = ref({
  username: "",
  password: "",
  is_superuser: false,
  is_active: true,
});

const canChangePassword = computed(() => {
  return !editingUser.value || !editingUser.value.is_oidc_user;
});

const loadUsers = async () => {
  isLoading.value = true;
  try {
    const response = await api.get<User[]>("/api/users");
    console.log("Loaded users:", response);
    users.value = response;
  } catch (error: any) {
    console.error("Failed to load users:", error);
  } finally {
    isLoading.value = false;
  }
};

const showCreateModal = () => {
  editingUser.value = null;
  resetForm();
  isModalVisible.value = true;
};

const editUser = (user: User) => {
  editingUser.value = user;
  formData.value = {
    username: user.username,
    password: "",
    is_superuser: user.is_superuser,
    is_active: user.is_active,
  };
  isModalVisible.value = true;
};

const handleModalOk = async (bvModalEvent: any) => {
  console.log("=== handleModalOk CALLED ===");
  // Prevent modal from closing automatically
  bvModalEvent.preventDefault();
  await saveUser();
};

const saveUser = async () => {
  console.log("=== saveUser CALLED ===");
  console.log("editingUser:", editingUser.value);
  console.log("formData:", formData.value);
  
  modalError.value = "";
  isSaving.value = true;

  try {
    if (editingUser.value) {
      // Update existing user
      const updateData: any = {
        is_superuser: formData.value.is_superuser,
        is_active: formData.value.is_active,
      };
      if (formData.value.password) {
        updateData.password = formData.value.password;
      }

      console.log("Updating user:", editingUser.value.id, updateData);
      await api.put(`/api/users/${editingUser.value.id}`, updateData);
      console.log("User updated successfully");
    } else {
      // Create new user
      const createData = {
        username: formData.value.username,
        password: formData.value.password,
        is_superuser: formData.value.is_superuser,
        is_active: formData.value.is_active,
      };
      console.log("Creating user:", createData);
      await api.post("/api/users", createData);
      console.log("User created successfully");
    }

    isModalVisible.value = false;
    await loadUsers();
  } catch (error: any) {
    console.error("Failed to save user:", error);
    modalError.value = error.detail || error.message || "Failed to save user";
  } finally {
    isSaving.value = false;
  }
};

const confirmDelete = (user: User) => {
  userToDelete.value = user;
  isDeleteModalVisible.value = true;
};

const deleteUser = async () => {
  if (!userToDelete.value) return;

  try {
    await api.delete(`/api/users/${userToDelete.value.id}`);
    await loadUsers();
  } catch (error: any) {
    console.error("Failed to delete user:", error);
    alert(error.detail || "Failed to delete user");
  }
};

const resetForm = () => {
  formData.value = {
    username: "",
    password: "",
    is_superuser: false,
    is_active: true,
  };
  modalError.value = "";
};

const formatDate = (dateString: string) => {
  const date = new Date(dateString);
  return date.toLocaleDateString() + " " + date.toLocaleTimeString();
};

onMounted(() => {
  loadUsers();
});
</script>

<style scoped lang="scss">
@import "./settings-common.scss";

.users-table {
  margin-bottom: 0;

  thead {
    background: #f8f9fa;
    
    th {
      font-weight: 600;
      color: #495057;
      border-bottom: 2px solid #dee2e6;
      padding: 1rem;
      font-size: 0.875rem;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }
  }

  tbody {
    tr {
      transition: background-color 0.15s ease;

      &:hover {
        background-color: #f8f9fa;
      }

      &.table-warning {
        background-color: #fff3cd !important;
        
        &:hover {
          background-color: #ffe69c !important;
        }
      }

      td {
        padding: 1rem;
        vertical-align: middle;
        border-bottom: 1px solid #e9ecef;
      }
    }
  }
}

.user-avatar {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 1.25rem;
}

.badge {
  font-weight: 500;
  padding: 0.35em 0.65em;
  font-size: 0.75rem;
  display: inline-block;
  min-width: 60px;
  text-align: center;

  i {
    font-size: 0.875rem;
  }

  &.bg-danger {
    background-color: #dc3545 !important;
    color: white !important;
  }

  &.bg-success {
    background-color: #28a745 !important;
    color: white !important;
  }

  &.bg-secondary {
    background-color: #6c757d !important;
    color: white !important;
  }

  &.bg-info {
    background-color: #17a2b8 !important;
    color: white !important;
  }
}

.btn-group-sm .btn {
  padding: 0.25rem 0.5rem;
  font-size: 0.875rem;

  i {
    font-size: 1rem;
  }
}

.alert {
  border-radius: 6px;
  
  i {
    margin-right: 0.5rem;
  }
}

// Modal styling
:deep(.modal-header) {
  background: #f8f9fa;
  border-bottom: 2px solid #dee2e6;
}

:deep(.modal-title) {
  font-weight: 600;
  color: #2c3e50;
}

:deep(.form-label) {
  font-weight: 600;
  color: #495057;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
}

:deep(.form-control) {
  border-radius: 6px;
  
  &:focus {
    border-color: #4a90e2;
    box-shadow: 0 0 0 0.2rem rgba(74, 144, 226, 0.25);
  }
}

:deep(.form-select) {
  border-radius: 6px;
  
  &:focus {
    border-color: #4a90e2;
    box-shadow: 0 0 0 0.2rem rgba(74, 144, 226, 0.25);
  }
}
</style>
