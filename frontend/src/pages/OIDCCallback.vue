<template>
  <div class="min-vh-100 d-flex align-items-center justify-content-center bg-light">
    <div class="text-center">
      <div v-if="isProcessing" class="mb-4">
        <b-spinner variant="primary" style="width: 3rem; height: 3rem" />
        <h4 class="mt-4 text-dark">
          Completing sign-in...
        </h4>
        <p class="text-secondary">
          Please wait while we authenticate you.
        </p>
      </div>

      <div v-if="errorMessage" class="card shadow-sm" style="max-width: 500px">
        <div class="card-body p-4">
          <div class="text-danger mb-3">
            <i class="pe-7s-attention" style="font-size: 3rem"></i>
          </div>
          <h4 class="text-dark mb-3">
            Authentication Failed
          </h4>
          <p class="text-secondary mb-4">
            {{ errorMessage }}
          </p>
          <b-button variant="primary" size="lg" @click="redirectToLogin">
            <i class="pe-7s-back me-2"></i>
            Back to Login
          </b-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import api from "../utils/api";

const router = useRouter();
const route = useRoute();

const isProcessing = ref(true);
const errorMessage = ref("");

onMounted(async () => {
  try {
    // Extract code and state from URL query parameters
    const code = route.query.code as string;
    const state = route.query.state as string;

    if (!code) {
      throw new Error("Authorization code not found in callback URL");
    }

    // Validate state parameter
    const storedState = sessionStorage.getItem("oidc_state");
    const storedProvider = sessionStorage.getItem("oidc_provider");

    if (!storedState || !storedProvider) {
      throw new Error("OIDC session not found. Please try again.");
    }

    if (state !== storedState) {
      throw new Error("Invalid state parameter. Possible CSRF attack detected.");
    }

    // Extract provider ID from state
    const providerId = state.split(":")[0];
    if (providerId !== storedProvider) {
      throw new Error("Provider mismatch in state parameter.");
    }

    // Exchange code for token via backend
    const response = await api.post<{
      access_token: string;
      token_type: string;
    }>(`/auth/oidc/${providerId}/callback`, {
      code,
      state,
    });

    // Clear OIDC session data
    sessionStorage.removeItem("oidc_state");
    sessionStorage.removeItem("oidc_provider");

    // Store access token
    localStorage.setItem("token", response.access_token);

    // Redirect to dashboard
    router.push("/");
  } catch (error: any) {
    console.error("OIDC callback error:", error);

    // Clear OIDC session data on error
    sessionStorage.removeItem("oidc_state");
    sessionStorage.removeItem("oidc_provider");

    // Display error message
    if (error.detail) {
      errorMessage.value = error.detail;
    } else if (error.message) {
      errorMessage.value = error.message;
    } else {
      errorMessage.value =
        "An unexpected error occurred during authentication. Please try again.";
    }

    isProcessing.value = false;
  }
});

const redirectToLogin = () => {
  router.push("/login");
};
</script>

<style scoped>
.card {
  border: none;
  border-radius: 1rem;
}
</style>
