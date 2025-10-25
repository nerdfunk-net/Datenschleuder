<template>
  <div class="settings-page">
    <div class="page-card">
      <div class="card-header">
        <h2 class="card-title">Registry Settings</h2>
      </div>

      <div class="card-body">
        <form @submit.prevent="handleSave">
          <div class="row g-4">
            <div class="col-md-12">
              <label class="form-label">Registry URL</label>
              <b-form-input v-model="settings.registryUrl" placeholder="https://registry.example.com" required />
              <small class="form-text text-muted">The base URL for your NiFi Registry instance</small>
            </div>

            <div class="col-md-6">
              <label class="form-label">Username</label>
              <b-form-input v-model="settings.username" placeholder="admin" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Password</label>
              <b-form-input v-model="settings.password" type="password" placeholder="••••••••" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Default Bucket</label>
              <b-form-input v-model="settings.defaultBucket" placeholder="main" />
            </div>

            <div class="col-md-6">
              <label class="form-label">Sync Interval (minutes)</label>
              <b-form-input v-model.number="settings.syncInterval" type="number" min="1" max="1440" />
            </div>

            <div class="col-md-12">
              <b-form-checkbox v-model="settings.autoSync">
                Enable Automatic Synchronization
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
  registryUrl: '',
  username: '',
  password: '',
  defaultBucket: 'main',
  syncInterval: 30,
  autoSync: false
})

const loadSettings = async () => {
  try {
    // TODO: Implement actual API call
    const response = await fetch('/api/proxy/settings/registry')
    if (response.ok) {
      settings.value = await response.json()
    }
  } catch (error) {
    console.error('Error loading settings:', error)
  }
}

const handleSave = async () => {
  isSaving.value = true
  try {
    // TODO: Implement actual API call
    await new Promise(resolve => setTimeout(resolve, 1000))
    alert('Registry settings saved successfully!')
  } catch (error) {
    console.error('Error saving settings:', error)
    alert('Error saving settings')
  } finally {
    isSaving.value = false
  }
}

const handleReset = () => {
  loadSettings()
}

onMounted(() => {
  loadSettings()
})
</script>

<style scoped lang="scss">
@import './settings-common.scss';
</style>
