<template>
  <div class="min-vh-100 d-flex">
    <!-- Left Panel - Brand -->
    <div
      class="d-none d-lg-flex col-lg-6 bg-dark position-relative overflow-hidden"
    >
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
        <h2 class="text-white text-center mb-3 fw-bold">
          Datenschleuder
        </h2>
        <p class="text-white-50 text-center mb-0 fs-5">
          Flow Management and Deployment Platform
        </p>
      </div>
    </div>

    <!-- Right Panel - Login Form -->
    <div
      class="col-12 col-lg-6 bg-white d-flex align-items-center justify-content-center p-4"
    >
      <div class="w-100" style="max-width: 420px">
        <!-- Mobile Logo -->
        <div class="d-lg-none text-center mb-5">
          <div
            class="d-inline-flex align-items-center justify-content-center bg-primary rounded-3 p-3 mb-3"
          >
            <i class="pe-7s-server text-white" style="font-size: 2rem"></i>
          </div>
          <h4 class="text-primary fw-bold mb-0">
            Datenschleuder
          </h4>
        </div>

        <!-- Login Header -->
        <div class="text-center mb-5">
          <h2 class="fw-bold text-dark mb-2">
            Sign in to your account
          </h2>
          <p class="text-secondary mb-0">
            Please enter your credentials to continue.
          </p>
          <div
            v-if="!oidcEnabled"
            class="alert alert-info mt-3 text-start"
            style="font-size: 0.875rem"
          >
            <strong>Dev Mode:</strong> Use <code>admin</code> /
            <code>admin</code> to login
          </div>
        </div>

        <!-- OIDC Providers Section -->
        <div v-if="oidcEnabled && oidcProviders.length > 0" class="mb-4">
          <div v-if="isLoadingProviders" class="text-center py-3">
            <b-spinner small />
            <span class="ms-2 text-secondary">Loading sign-in options...</span>
          </div>

          <div v-else>
            <!-- OIDC Provider Buttons -->
            <div
              v-for="provider in oidcProviders"
              :key="provider.provider_id"
              class="mb-3"
            >
              <b-button
                variant="outline-primary"
                size="lg"
                class="w-100 py-3 d-flex align-items-center justify-content-center"
                :disabled="isLoading"
                @click="handleOIDCLogin(provider.provider_id)"
              >
                <i
                  :class="getProviderIcon(provider.icon)"
                  class="me-2"
                  style="font-size: 1.25rem"
                ></i>
                <span class="fw-medium">{{ provider.name }}</span>
              </b-button>
              <small
                v-if="provider.description"
                class="text-secondary d-block mt-1 ms-2"
              >{{ provider.description }}</small>
            </div>

            <!-- Divider -->
            <div
              v-if="allowTraditionalLogin"
              class="d-flex align-items-center my-4"
            >
              <hr class="flex-grow-1" />
              <span class="px-3 text-secondary small">OR</span>
              <hr class="flex-grow-1" />
            </div>
          </div>
        </div>

        <!-- Error Message -->
        <b-alert
          v-if="errorMessage"
          variant="danger"
          dismissible
          @dismissed="errorMessage = ''"
        >
          {{ errorMessage }}
        </b-alert>

        <!-- Traditional Login Form -->
        <form
          v-if="!oidcEnabled || allowTraditionalLogin"
          @submit.prevent="handleLogin"
        >
          <div class="mb-4">
            <label
              for="username"
              class="form-label text-dark fw-medium mb-2"
            >Username</label>
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
            <label
              for="password"
              class="form-label text-dark fw-medium mb-2"
            >Password</label>
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
            <b-form-checkbox
              id="remember"
              v-model="rememberMe"
              class="text-secondary"
            >
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
                <b-spinner small class="me-2" />
                Signing in...
              </span>
              <span v-else>Sign in to Dashboard</span>
            </b-button>
          </div>
        </form>

        <!-- Copyright -->
        <div class="text-center mt-5">
          <p class="text-secondary small mb-0">
            © 2025 Datenschleuder. All rights reserved.
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { login } from "../utils/api";
import api from "../utils/api";

const router = useRouter();

const username = ref("");
const password = ref("");
const rememberMe = ref(false);
const errorMessage = ref("");
const isLoading = ref(false);

// OIDC state
const oidcEnabled = ref(false);
const oidcProviders = ref<
  Array<{
    provider_id: string;
    name: string;
    description: string;
    icon: string;
    display_order: number;
  }>
>([]);
const allowTraditionalLogin = ref(true);
const isLoadingProviders = ref(false);

// Fetch OIDC providers on mount
onMounted(async () => {
  try {
    isLoadingProviders.value = true;

    // Check if OIDC is enabled
    try {
      const enabledResponse = await api.get<{ enabled: boolean }>("/auth/oidc/enabled");
      oidcEnabled.value = enabledResponse.enabled;
    } catch (error) {
      // OIDC endpoint not available or disabled
      console.log("OIDC not available:", error);
      oidcEnabled.value = false;
      return;
    }

    if (oidcEnabled.value) {
      // Fetch provider list
      try {
        const providersResponse = await api.get<{
          providers: Array<{
            provider_id: string;
            name: string;
            description: string;
            icon: string;
            display_order: number;
          }>;
          allow_traditional_login: boolean;
        }>("/auth/oidc/providers");
        oidcProviders.value = providersResponse.providers || [];
        allowTraditionalLogin.value = providersResponse.allow_traditional_login ?? true;
      } catch (error) {
        console.error("Failed to fetch OIDC providers:", error);
        oidcEnabled.value = false;
        // Silently fail - traditional login will still work
      }
    }
  } catch (error) {
    console.error("Failed to initialize OIDC:", error);
    // Silently fail - traditional login will still work
  } finally {
    isLoadingProviders.value = false;
  }
});

const handleLogin = async () => {
  errorMessage.value = "";
  isLoading.value = true;

  try {
    const data = await login(username.value, password.value);

    // Store access token and refresh token
    localStorage.setItem("token", data.access_token);
    if (data.refresh_token) {
      localStorage.setItem("refresh_token", data.refresh_token);
    }
    if (rememberMe.value) {
      localStorage.setItem("rememberMe", "true");
    }

    // Redirect to dashboard
    router.push("/");
  } catch (error: any) {
    console.error("Login error:", error);
    errorMessage.value =
      error.message ||
      "Failed to connect to server. Please check if the backend is running.";
  } finally {
    isLoading.value = false;
  }
};

const handleOIDCLogin = async (providerId: string) => {
  errorMessage.value = "";
  isLoading.value = true;

  try {
    // Build redirect URI
    const redirectUri = `${window.location.origin}/login/callback`;
    const encodedUri = encodeURIComponent(redirectUri);

    // Get authorization URL from backend
    const response = await api.get<{
      authorization_url: string;
      state: string;
      provider_id: string;
    }>(`/auth/oidc/${providerId}/login?redirect_uri=${encodedUri}`);

    // Store state in sessionStorage for validation in callback
    sessionStorage.setItem("oidc_state", response.state);
    sessionStorage.setItem("oidc_provider", providerId);

    // Redirect to identity provider
    window.location.href = response.authorization_url;
  } catch (error: any) {
    console.error("OIDC login error:", error);
    errorMessage.value =
      error.detail || "Failed to initiate SSO login. Please try again.";
    isLoading.value = false;
  }
};

const getProviderIcon = (icon: string) => {
  const iconMap: Record<string, string> = {
    building: "pe-7s-culture",
    flask: "pe-7s-science",
    users: "pe-7s-users",
    shield: "pe-7s-shield",
  };
  return iconMap[icon] || "pe-7s-id";
};
</script>

<style scoped>
.bg-opacity-10 {
  --bs-bg-opacity: 0.1;
}
</style>
