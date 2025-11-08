<template>
  <div class="settings-page">
    <div class="page-card">
      <div class="card-header">
        <h2 class="card-title">Profile Settings</h2>
      </div>

      <div class="card-body">
        <form @submit.prevent="handleSave">
          <div class="row g-4">
            <div class="col-md-6">
              <label class="form-label">First Name</label>
              <b-form-input v-model="settings.firstName" placeholder="John" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Last Name</label>
              <b-form-input v-model="settings.lastName" placeholder="Doe" />
            </div>

            <div class="col-md-12">
              <label class="form-label">Email</label>
              <b-form-input
                v-model="settings.email"
                type="email"
                placeholder="john.doe@example.com"
              />
            </div>

            <div class="col-md-12">
              <label class="form-label">Username</label>
              <b-form-input v-model="settings.username" disabled />
              <small class="form-text text-muted"
                >Username cannot be changed</small
              >
            </div>

            <div class="col-md-12">
              <hr class="my-4" />
              <h5 class="mb-3">Change Password</h5>
              <b-alert v-if="isOIDCUser" variant="info" show>
                <i class="pe-7s-info me-2"></i>
                You are logged in via OIDC. Password changes must be made through your identity provider.
              </b-alert>
            </div>

            <div v-if="!isOIDCUser" class="col-md-12">
              <label class="form-label">Current Password</label>
              <b-form-input
                v-model="passwordForm.currentPassword"
                type="password"
              />
            </div>

            <div v-if="!isOIDCUser" class="col-md-6">
              <label class="form-label">New Password</label>
              <b-form-input
                v-model="passwordForm.newPassword"
                type="password"
              />
            </div>

            <div v-if="!isOIDCUser" class="col-md-6">
              <label class="form-label">Confirm New Password</label>
              <b-form-input
                v-model="passwordForm.confirmPassword"
                type="password"
              />
            </div>
          </div>

          <div class="card-footer">
            <b-button
              type="button"
              variant="outline-secondary"
              @click="handleReset"
              >Reset</b-button
            >
            <b-button
              type="submit"
              variant="primary"
              class="ms-2"
              :disabled="isSaving"
            >
              <b-spinner v-if="isSaving" small class="me-2"></b-spinner>
              Save Settings
            </b-button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import api from "../../utils/api";

interface UserProfile {
  id: number;
  username: string;
  first_name: string | null;
  last_name: string | null;
  email: string | null;
  is_active: boolean;
  is_superuser: boolean;
  is_oidc_user: boolean;
  created_at: string;
}

const isSaving = ref(false);
const isLoading = ref(false);
const currentUser = ref<UserProfile | null>(null);
const settings = ref({
  firstName: "",
  lastName: "",
  email: "",
  username: "",
});

const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isOIDCUser = computed(() => currentUser.value?.is_oidc_user || false);

const loadSettings = async () => {
  isLoading.value = true;
  try {
    const response = await api.get<UserProfile>("/api/users/me");
    currentUser.value = response;
    settings.value.username = response.username;
    settings.value.firstName = response.first_name || "";
    settings.value.lastName = response.last_name || "";
    settings.value.email = response.email || "";
  } catch (error) {
    console.error("Error loading profile:", error);
  } finally {
    isLoading.value = false;
  }
};

const handleSave = async () => {
  isSaving.value = true;

  try {
    // Save profile information (first name, last name, email)
    await api.put("/api/users/me", {
      first_name: settings.value.firstName || null,
      last_name: settings.value.lastName || null,
      email: settings.value.email || null,
    });

    // If password change is attempted, save it separately
    if (passwordForm.value.newPassword || passwordForm.value.confirmPassword) {
      if (isOIDCUser.value) {
        alert("OIDC users cannot change password. Please use your identity provider.");
        isSaving.value = false;
        return;
      }

      if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
        alert("New passwords do not match");
        isSaving.value = false;
        return;
      }
      if (!passwordForm.value.currentPassword) {
        alert("Please enter your current password");
        isSaving.value = false;
        return;
      }
      if (passwordForm.value.newPassword.length < 6) {
        alert("New password must be at least 6 characters");
        isSaving.value = false;
        return;
      }

      // Save password change
      await api.post("/api/users/me/change-password", {
        current_password: passwordForm.value.currentPassword,
        new_password: passwordForm.value.newPassword,
      });

      passwordForm.value = {
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      };

      alert("Profile and password updated successfully!");
    } else {
      alert("Profile settings saved successfully!");
    }

    // Reload user data
    await loadSettings();
  } catch (error: any) {
    console.error("Error saving profile:", error);
    alert(error.detail || "Error saving profile settings");
  } finally {
    isSaving.value = false;
  }
};

const handleReset = () => {
  loadSettings();
  passwordForm.value = {
    currentPassword: "",
    newPassword: "",
    confirmPassword: "",
  };
};

onMounted(() => {
  loadSettings();
});
</script>

<style scoped lang="scss">
@import "./settings-common.scss";
</style>
