<template>
  <div class="settings-page">
    <div class="page-card">
      <div class="card-header">
        <h2 class="card-title">Profile Settings</h2>
      </div>

      <div class="card-body">
        <form @submit.prevent="handleSave">
          <div class="row g-4">
            <div class="col-md-12">
              <div class="profile-avatar">
                <div class="avatar-preview">
                  <i class="pe-7s-user"></i>
                </div>
                <div class="avatar-info">
                  <h5>Profile Picture</h5>
                  <p class="text-muted">Upload a profile picture (max 2MB)</p>
                  <b-button variant="outline-primary" size="sm"
                    >Change Picture</b-button
                  >
                </div>
              </div>
            </div>

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

            <div class="col-md-12">
              <hr class="my-4" />
              <h5 class="mb-3">Preferences</h5>
            </div>

            <div class="col-md-6">
              <label class="form-label">Language</label>
              <b-form-select
                v-model="settings.language"
                :options="languageOptions"
              />
            </div>

            <div class="col-md-6">
              <label class="form-label">Timezone</label>
              <b-form-select
                v-model="settings.timezone"
                :options="timezoneOptions"
              />
            </div>

            <div class="col-md-12">
              <b-form-checkbox v-model="settings.emailNotifications">
                Receive email notifications
              </b-form-checkbox>
            </div>

            <div class="col-md-12">
              <b-form-checkbox v-model="settings.autoLogout">
                Auto logout after 30 minutes of inactivity
              </b-form-checkbox>
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
  language: "en",
  timezone: "UTC",
  emailNotifications: true,
  autoLogout: true,
});

const passwordForm = ref({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const isOIDCUser = computed(() => currentUser.value?.is_oidc_user || false);

const languageOptions = [
  { value: "en", text: "English" },
  { value: "de", text: "German" },
  { value: "fr", text: "French" },
  { value: "es", text: "Spanish" },
];

const timezoneOptions = [
  { value: "UTC", text: "UTC" },
  { value: "America/New_York", text: "Eastern Time" },
  { value: "America/Chicago", text: "Central Time" },
  { value: "America/Los_Angeles", text: "Pacific Time" },
  { value: "Europe/London", text: "London" },
  { value: "Europe/Berlin", text: "Berlin" },
];

const loadSettings = async () => {
  isLoading.value = true;
  try {
    const response = await api.get<UserProfile>("/api/users/me");
    currentUser.value = response;
    settings.value.username = response.username;
  } catch (error) {
    console.error("Error loading profile:", error);
  } finally {
    isLoading.value = false;
  }
};

const handleSave = async () => {
  // Validate password change if attempted
  if (passwordForm.value.newPassword || passwordForm.value.confirmPassword) {
    if (isOIDCUser.value) {
      alert("OIDC users cannot change password. Please use your identity provider.");
      return;
    }

    if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
      alert("New passwords do not match");
      return;
    }
    if (!passwordForm.value.currentPassword) {
      alert("Please enter your current password");
      return;
    }
    if (passwordForm.value.newPassword.length < 6) {
      alert("New password must be at least 6 characters");
      return;
    }

    // Save password change
    isSaving.value = true;
    try {
      await api.post("/api/users/me/change-password", {
        current_password: passwordForm.value.currentPassword,
        new_password: passwordForm.value.newPassword,
      });
      alert("Password changed successfully!");
      passwordForm.value = {
        currentPassword: "",
        newPassword: "",
        confirmPassword: "",
      };
    } catch (error: any) {
      console.error("Error changing password:", error);
      alert(error.detail || "Error changing password");
    } finally {
      isSaving.value = false;
    }
  } else {
    // TODO: Save other profile settings when implemented
    alert("Profile settings saved successfully!");
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

.profile-avatar {
  display: flex;
  gap: 20px;
  align-items: center;
  padding: 20px;
  background: #f8f9fa;
  border-radius: 8px;
}

.avatar-preview {
  width: 100px;
  height: 100px;
  border-radius: 50%;
  background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  font-size: 3rem;
}

.avatar-info {
  h5 {
    margin-bottom: 5px;
  }

  p {
    margin-bottom: 10px;
    font-size: 0.875rem;
  }
}
</style>
