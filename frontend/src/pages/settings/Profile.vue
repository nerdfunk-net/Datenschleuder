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
                  <b-button variant="outline-primary" size="sm">Change Picture</b-button>
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
              <b-form-input v-model="settings.email" type="email" placeholder="john.doe@example.com" />
            </div>

            <div class="col-md-12">
              <label class="form-label">Username</label>
              <b-form-input v-model="settings.username" disabled />
              <small class="form-text text-muted">Username cannot be changed</small>
            </div>

            <div class="col-md-12">
              <hr class="my-4" />
              <h5 class="mb-3">Change Password</h5>
            </div>

            <div class="col-md-12">
              <label class="form-label">Current Password</label>
              <b-form-input v-model="passwordForm.currentPassword" type="password" />
            </div>

            <div class="col-md-6">
              <label class="form-label">New Password</label>
              <b-form-input v-model="passwordForm.newPassword" type="password" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Confirm New Password</label>
              <b-form-input v-model="passwordForm.confirmPassword" type="password" />
            </div>

            <div class="col-md-12">
              <hr class="my-4" />
              <h5 class="mb-3">Preferences</h5>
            </div>

            <div class="col-md-6">
              <label class="form-label">Language</label>
              <b-form-select v-model="settings.language" :options="languageOptions" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Timezone</label>
              <b-form-select v-model="settings.timezone" :options="timezoneOptions" />
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
            <b-button type="button" variant="outline-secondary" @click="handleReset">Reset</b-button>
            <b-button type="submit" variant="primary" class="ms-2" :disabled="isSaving">
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
import { ref, onMounted } from 'vue'

const isSaving = ref(false)
const settings = ref({
  firstName: '',
  lastName: '',
  email: '',
  username: 'admin',
  language: 'en',
  timezone: 'UTC',
  emailNotifications: true,
  autoLogout: true
})

const passwordForm = ref({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const languageOptions = [
  { value: 'en', text: 'English' },
  { value: 'de', text: 'German' },
  { value: 'fr', text: 'French' },
  { value: 'es', text: 'Spanish' }
]

const timezoneOptions = [
  { value: 'UTC', text: 'UTC' },
  { value: 'America/New_York', text: 'Eastern Time' },
  { value: 'America/Chicago', text: 'Central Time' },
  { value: 'America/Los_Angeles', text: 'Pacific Time' },
  { value: 'Europe/London', text: 'London' },
  { value: 'Europe/Berlin', text: 'Berlin' }
]

const loadSettings = async () => {
  try {
    // TODO: Implement actual API call
    const response = await fetch('/api/proxy/settings/profile')
    if (response.ok) {
      settings.value = await response.json()
    }
  } catch (error) {
    console.error('Error loading settings:', error)
  }
}

const handleSave = async () => {
  // Validate password change if attempted
  if (passwordForm.value.newPassword || passwordForm.value.confirmPassword) {
    if (passwordForm.value.newPassword !== passwordForm.value.confirmPassword) {
      alert('New passwords do not match')
      return
    }
    if (!passwordForm.value.currentPassword) {
      alert('Please enter your current password')
      return
    }
  }

  isSaving.value = true
  try {
    // TODO: Implement actual API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    alert('Profile settings saved successfully!')
    passwordForm.value = {
      currentPassword: '',
      newPassword: '',
      confirmPassword: ''
    }
  } catch (error) {
    console.error('Error saving settings:', error)
    alert('Error saving settings')
  } finally {
    isSaving.value = false
  }
}

const handleReset = () => {
  loadSettings()
  passwordForm.value = {
    currentPassword: '',
    newPassword: '',
    confirmPassword: ''
  }
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped lang="scss">
@import './settings-common.scss';

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
