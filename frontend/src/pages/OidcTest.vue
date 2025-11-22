<template>
  <div class="container-fluid mt-4 mb-5">
    <div class="row">
      <div class="col-12">
        <div class="card">
          <div class="card-header">
            <h4 class="card-title">
              <i class="pe-7s-shield"></i> OIDC Authentication Test
            </h4>
            <p class="card-category">
              Test OIDC authentication for frontend and backend without requiring login
            </p>
          </div>
          <div class="card-body" style="max-height: calc(100vh - 200px); overflow-y: auto; padding-bottom: 2rem;">
            <!-- Test Type Selection -->
            <div class="row mb-4">
              <div class="col-md-12">
                <label class="form-label">Test Type</label>
                <b-form-select v-model="testType" :options="testTypeOptions" />
              </div>
            </div>

            <!-- Provider Selection -->
            <div class="row mb-3">
              <div class="col-md-6">
                <label class="form-label">Select OIDC Provider</label>
                <b-form-select
                  v-model="selectedProvider"
                  :options="providerOptions"
                  @change="loadProviderConfig"
                />
              </div>
              <div class="col-md-6 d-flex align-items-end">
                <b-button
                  variant="secondary"
                  class="me-2"
                  @click="loadProviders"
                >
                  <i class="pe-7s-refresh-2"></i> Reload Providers
                </b-button>
                <b-button variant="info" @click="resetToDefaults">
                  <i class="pe-7s-back"></i> Reset to Provider Defaults
                </b-button>
              </div>
            </div>

            <hr />

            <!-- Configuration Form -->
            <div class="row g-3">
              <div class="col-md-6">
                <label class="form-label">Provider Name</label>
                <b-form-input v-model="config.name" placeholder="My Provider" />
              </div>

              <div class="col-md-6">
                <label class="form-label">Provider ID</label>
                <b-form-input
                  v-model="config.provider_id"
                  placeholder="my_provider"
                />
              </div>

              <div class="col-md-12">
                <label class="form-label">Discovery URL</label>
                <b-form-input
                  v-model="config.discovery_url"
                  placeholder="https://keycloak.example.com/realms/myrealm/.well-known/openid-configuration"
                />
                <small class="form-text text-muted">
                  OpenID Connect discovery endpoint
                </small>
              </div>

              <div class="col-md-6">
                <label class="form-label">Client ID</label>
                <b-form-input
                  v-model="config.client_id"
                  placeholder="my-client-id"
                />
              </div>

              <div class="col-md-6">
                <label class="form-label">Client Secret</label>
                <b-form-input
                  v-model="config.client_secret"
                  type="password"
                  placeholder="••••••••"
                />
              </div>

              <div class="col-md-12">
                <label class="form-label">Redirect URI</label>
                <b-form-input
                  v-model="config.redirect_uri"
                  placeholder="http://localhost:5173/oidc-callback"
                />
              </div>

              <div class="col-md-6">
                <label class="form-label">Scope</label>
                <b-form-input
                  v-model="config.scope"
                  placeholder="openid profile email"
                />
              </div>

              <div class="col-md-6">
                <label class="form-label">Response Type</label>
                <b-form-input
                  v-model="config.response_type"
                  placeholder="code"
                />
              </div>

              <!-- Backend-specific options -->
              <div v-if="testType === 'backend'" class="col-md-12">
                <hr />
                <h5>Backend NiFi Connection Settings</h5>
              </div>

              <div v-if="testType === 'backend'" class="col-md-12">
                <label class="form-label">NiFi URL</label>
                <b-form-input
                  v-model="nifiConfig.nifi_url"
                  placeholder="https://nifi.example.com:8443/nifi-api"
                />
              </div>

              <div v-if="testType === 'backend'" class="col-md-4">
                <b-form-checkbox v-model="nifiConfig.use_ssl">
                  Use SSL/TLS
                </b-form-checkbox>
              </div>

              <div v-if="testType === 'backend'" class="col-md-4">
                <b-form-checkbox v-model="nifiConfig.verify_ssl">
                  Verify SSL Certificate
                </b-form-checkbox>
              </div>

              <div v-if="testType === 'backend'" class="col-md-4">
                <b-form-checkbox v-model="nifiConfig.check_hostname">
                  Check Hostname
                </b-form-checkbox>
              </div>

              <!-- Action Buttons -->
              <div class="col-md-12 mt-4 mb-3">
                <b-button
                  variant="primary"
                  size="lg"
                  class="me-2"
                  :disabled="testing"
                  @click="testAuthentication"
                >
                  <span v-if="testing">
                    <i class="pe-7s-refresh-2 fa-spin"></i> Testing...
                  </span>
                  <span v-else>
                    <i class="pe-7s-check"></i>
                    {{ testType === "frontend" ? "Test Frontend Auth" : "Test Backend Auth" }}
                  </span>
                </b-button>
                <b-button variant="secondary" @click="clearResults">
                  <i class="pe-7s-trash"></i> Clear Results
                </b-button>
              </div>
            </div>

            <!-- Test Results -->
            <div v-if="testResult" class="mt-4">
              <hr />
              <h5>Test Results</h5>
              <div
                :class="[
                  'alert',
                  testResult.success ? 'alert-success' : 'alert-danger',
                ]"
              >
                <strong>{{
                  testResult.success ? "✓ Success" : "✗ Failed"
                }}</strong>
                <p class="mb-0 mt-2">
                  {{ testResult.message }}
                </p>
              </div>

              <!-- Detailed Response -->
              <div v-if="testResult.details" class="card mt-3">
                <div class="card-header">
                  <h6 class="mb-0">
                    Detailed Response
                  </h6>
                </div>
                <div class="card-body">
                  <pre
                    class="bg-light p-3 rounded"
                    style="max-height: 500px; overflow-y: auto"
                  ><code>{{ formatJson(testResult.details) }}</code></pre>
                </div>
              </div>

              <!-- Error Details -->
              <div v-if="testResult.error" class="card mt-3">
                <div class="card-header bg-danger text-white">
                  <h6 class="mb-0">
                    Error Details
                  </h6>
                </div>
                <div class="card-body">
                  <pre
                    class="bg-light p-3 rounded text-danger"
                    style="max-height: 300px; overflow-y: auto"
                  ><code>{{ testResult.error }}</code></pre>
                </div>
              </div>

              <!-- Steps Taken -->
              <div v-if="testResult.steps && testResult.steps.length > 0" class="mt-3">
                <h6>Authentication Steps:</h6>
                <ol class="list-group list-group-numbered">
                  <li
                    v-for="(step, index) in testResult.steps"
                    :key="index"
                    class="list-group-item"
                  >
                    {{ step }}
                  </li>
                </ol>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";

interface OIDCProvider {
  provider_id: string;
  name: string;
  discovery_url: string;
  client_id: string;
  client_secret: string;
  redirect_uri: string;
  scope: string;
  response_type: string;
  enabled: boolean;
  backend?: boolean;
}

interface TestResult {
  success: boolean;
  message: string;
  details?: any;
  error?: string;
  steps?: string[];
}

const testType = ref<"frontend" | "backend">("frontend");
const testTypeOptions = [
  { value: "frontend", text: "Frontend OIDC Authentication" },
  { value: "backend", text: "Backend NiFi OIDC Authentication" },
];

const providers = ref<OIDCProvider[]>([]);
const selectedProvider = ref<string>("");
const testing = ref(false);
const testResult = ref<TestResult | null>(null);

const config = ref({
  name: "",
  provider_id: "",
  discovery_url: "",
  client_id: "",
  client_secret: "",
  redirect_uri: "http://localhost:5173/oidc-callback",
  scope: "openid profile email",
  response_type: "code",
});

const nifiConfig = ref({
  nifi_url: "https://localhost:8443/nifi-api",
  use_ssl: true,
  verify_ssl: false,
  check_hostname: false,
});

const providerOptions = computed(() => {
  if (providers.value.length === 0) {
    return [{ value: "", text: "No providers available" }];
  }
  return [
    { value: "", text: "-- Select a provider --" },
    ...providers.value.map((p) => ({
      value: p.provider_id,
      text: `${p.name} (${p.provider_id})${p.backend ? " [Backend]" : ""}`,
    })),
  ];
});

const loadProviders = async () => {
  try {
    // Try to load all providers (both frontend and backend)
    const response = await fetch("/auth/oidc/test/providers");
    const data = await response.json();
    providers.value = data.providers || [];
  } catch (error) {
    console.error("Error loading providers:", error);
    alert("Failed to load OIDC providers. Check console for details.");
  }
};

const loadProviderConfig = () => {
  if (!selectedProvider.value) return;

  const provider = providers.value.find(
    (p) => p.provider_id === selectedProvider.value
  );
  if (provider) {
    config.value = {
      name: provider.name,
      provider_id: provider.provider_id,
      discovery_url: provider.discovery_url,
      client_id: provider.client_id,
      client_secret: provider.client_secret || "",
      redirect_uri: provider.redirect_uri,
      scope: provider.scope,
      response_type: provider.response_type,
    };
  }
};

const resetToDefaults = () => {
  if (selectedProvider.value) {
    loadProviderConfig();
  } else {
    config.value = {
      name: "",
      provider_id: "",
      discovery_url: "",
      client_id: "",
      client_secret: "",
      redirect_uri: "http://localhost:5173/oidc-callback",
      scope: "openid profile email",
      response_type: "code",
    };
  }
};

const testAuthentication = async () => {
  testing.value = true;
  testResult.value = null;

  try {
    if (testType.value === "frontend") {
      await testFrontendAuth();
    } else {
      await testBackendAuth();
    }
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: "Test failed with exception",
      error: error.message || JSON.stringify(error),
    };
  } finally {
    testing.value = false;
  }
};

const testFrontendAuth = async () => {
  try {
    const response = await fetch("/auth/oidc/test/frontend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        discovery_url: config.value.discovery_url,
        client_id: config.value.client_id,
        client_secret: config.value.client_secret,
        redirect_uri: config.value.redirect_uri,
        scope: config.value.scope,
        response_type: config.value.response_type,
      }),
    });

    const data = await response.json();
    testResult.value = {
      success: data.status === "success",
      message: data.message || "Frontend OIDC configuration test completed",
      details: data.details || data,
      error: data.error,
      steps: data.steps,
    };
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: "Failed to test frontend OIDC",
      error: error.message,
    };
  }
};

const testBackendAuth = async () => {
  try {
    const response = await fetch("/auth/oidc/test/backend", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        discovery_url: config.value.discovery_url,
        client_id: config.value.client_id,
        client_secret: config.value.client_secret,
        nifi_url: nifiConfig.value.nifi_url,
        verify_ssl: nifiConfig.value.verify_ssl,
      }),
    });

    const data = await response.json();
    testResult.value = {
      success: data.status === "success",
      message: data.message || "Backend NiFi OIDC authentication test completed",
      details: data.details || data,
      error: data.error,
      steps: data.steps,
    };
  } catch (error: any) {
    testResult.value = {
      success: false,
      message: "Failed to test backend OIDC",
      error: error.message,
    };
  }
};

const clearResults = () => {
  testResult.value = null;
};

const formatJson = (obj: any): string => {
  return JSON.stringify(obj, null, 2);
};

onMounted(() => {
  loadProviders();
});
</script>

<style scoped>
.card {
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

pre {
  margin-bottom: 0;
  font-size: 0.875rem;
}

code {
  color: #333;
}

.fa-spin {
  animation: fa-spin 1s infinite linear;
}

@keyframes fa-spin {
  0% {
    transform: rotate(0deg);
  }
  100% {
    transform: rotate(360deg);
  }
}

.list-group-item {
  background-color: #f8f9fa;
  border: 1px solid #dee2e6;
  margin-bottom: 0.5rem;
}
</style>
