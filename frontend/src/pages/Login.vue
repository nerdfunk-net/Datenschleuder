<template>
  <div class="min-vh-100 d-flex">
    <!-- Left Panel - Brand -->
    <div class="d-none d-lg-flex col-lg-6 bg-dark position-relative overflow-hidden">
      <div
        class="position-absolute w-100 h-100"
        style="background: linear-gradient(135deg, #4a90e2 0%, #357abd 100%)"
      ></div>
      <div
        class="d-flex flex-column justify-content-center align-items-center text-white p-5 position-relative"
        style="z-index: 2"
      >
        <div class="mb-4">
          <div class="bg-white bg-opacity-10 rounded-4 p-4">
            <i class="pe-7s-server text-white" style="font-size: 3rem"></i>
          </div>
        </div>
        <h2 class="text-white text-center mb-3 fw-bold">Datenschleuder</h2>
        <p class="text-white-50 text-center mb-0 fs-5">
          Flow Management and Deployment Platform
        </p>
      </div>
    </div>

    <!-- Right Panel - Login Form -->
    <div class="col-12 col-lg-6 bg-white d-flex align-items-center justify-content-center p-4">
      <div class="w-100" style="max-width: 420px">
        <!-- Mobile Logo -->
        <div class="d-lg-none text-center mb-5">
          <div class="d-inline-flex align-items-center justify-content-center bg-primary rounded-3 p-3 mb-3">
            <i class="pe-7s-server text-white" style="font-size: 2rem"></i>
          </div>
          <h4 class="text-primary fw-bold mb-0">Datenschleuder</h4>
        </div>

        <!-- Login Header -->
        <div class="text-center mb-5">
          <h2 class="fw-bold text-dark mb-2">Sign in to your account</h2>
          <p class="text-secondary mb-0">Please enter your credentials to continue.</p>
          <div class="alert alert-info mt-3 text-start" style="font-size: 0.875rem;">
            <strong>Dev Mode:</strong> Use <code>admin</code> / <code>admin</code> to login
          </div>
        </div>

        <!-- Error Message -->
        <b-alert v-if="errorMessage" variant="danger" dismissible @dismissed="errorMessage = ''">
          {{ errorMessage }}
        </b-alert>

        <!-- Login Form -->
        <form @submit.prevent="handleLogin">
          <div class="mb-4">
            <label for="username" class="form-label text-dark fw-medium mb-2">Username</label>
            <b-form-input
              id="username"
              v-model="username"
              type="text"
              size="lg"
              placeholder="Enter your username"
              class="py-3"
              required
            />
          </div>

          <div class="mb-4">
            <label for="password" class="form-label text-dark fw-medium mb-2">Password</label>
            <b-form-input
              id="password"
              v-model="password"
              type="password"
              size="lg"
              placeholder="Enter your password"
              class="py-3"
              required
            />
          </div>

          <div class="d-flex justify-content-between align-items-center mb-4">
            <b-form-checkbox id="remember" v-model="rememberMe" class="text-secondary">
              Remember me
            </b-form-checkbox>
          </div>

          <div class="d-grid mb-4">
            <b-button
              type="submit"
              variant="primary"
              size="lg"
              class="fw-medium py-3"
              :disabled="isLoading"
            >
              <span v-if="isLoading">
                <b-spinner small class="me-2"></b-spinner>
                Signing in...
              </span>
              <span v-else>Sign in to Dashboard</span>
            </b-button>
          </div>
        </form>

        <!-- Copyright -->
        <div class="text-center mt-5">
          <p class="text-secondary small mb-0">© 2025 Datenschleuder. All rights reserved.</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { login } from '../utils/api'

const router = useRouter()

const username = ref('')
const password = ref('')
const rememberMe = ref(false)
const errorMessage = ref('')
const isLoading = ref(false)

const handleLogin = async () => {
  errorMessage.value = ''
  isLoading.value = true

  try {
    const data = await login(username.value, password.value)

    // Store access token
    localStorage.setItem('token', data.access_token)
    if (rememberMe.value) {
      localStorage.setItem('rememberMe', 'true')
    }

    // Redirect to dashboard
    router.push('/')
  } catch (error: any) {
    console.error('Login error:', error)
    errorMessage.value = error.message || 'Failed to connect to server. Please check if the backend is running.'
  } finally {
    isLoading.value = false
  }
}
</script>

<style scoped>
.bg-opacity-10 {
  --bs-bg-opacity: 0.1;
}
</style>
