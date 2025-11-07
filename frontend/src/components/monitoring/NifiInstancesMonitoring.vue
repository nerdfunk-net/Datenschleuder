<template>
  <div class="nifi-instances-monitoring">
    <div class="instance-selector mb-4">
      <label for="instance-select" class="form-label">Select NiFi Instance:</label>
      <select
        id="instance-select"
        v-model="selectedInstanceId"
        class="form-select"
        @change="loadInstanceData"
      >
        <option :value="null">-- Select an instance --</option>
        <option
          v-for="instance in instances"
          :key="instance.id"
          :value="instance.id"
        >
          {{ instance.hierarchy_value }} ({{ instance.nifi_url }})
        </option>
      </select>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <div v-if="selectedInstanceId && !loading && !error && systemDiagnostics" class="monitoring-data">
      <!-- Summary Cards Row -->
      <div class="row g-4 mb-4">
        <!-- Heap Memory Card -->
        <div class="col-md-6 col-lg-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Heap Memory</h6>
              <div class="metric-value">{{ heapUtilization }}</div>
              <div class="progress mt-2" style="height: 8px;">
                <div
                  class="progress-bar"
                  :class="getMemoryUsageClass(heapUtilization)"
                  role="progressbar"
                  :style="{ width: heapUtilization }"
                ></div>
              </div>
              <small class="text-muted d-block mt-2">{{ usedHeap }} / {{ maxHeap }}</small>
              <small class="text-muted d-block" style="font-size: 0.75rem;">max {{ maxHeap }}</small>
            </div>
          </div>
        </div>

        <!-- CPU Card -->
        <div class="col-md-6 col-lg-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">CPU Load</h6>
              <div class="metric-value">{{ cpuLoad }}</div>
              <small class="text-muted">{{ availableProcessors }} processors</small>
            </div>
          </div>
        </div>

        <!-- Total Threads Card -->
        <div class="col-md-6 col-lg-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Threads</h6>
              <div class="metric-value">{{ totalThreads }}</div>
              <small class="text-muted">{{ daemonThreads }} daemon</small>
            </div>
          </div>
        </div>

        <!-- Storage Card -->
        <div class="col-md-6 col-lg-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Content Storage</h6>
              <div class="metric-value">{{ contentStorageUtilization }}</div>
              <small class="text-muted">{{ contentStorageUsed }} / {{ contentStorageTotal }}</small>
            </div>
          </div>
        </div>
      </div>

      <!-- Version and Uptime Info -->
      <div class="row g-4 mb-4">
        <div class="col-md-6">
          <div class="card info-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-3 text-muted">
                <i class="pe-7s-info"></i> Version Information
              </h6>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">NiFi Version:</span>
                  <span class="info-value">{{ nifiVersion }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Build Tag:</span>
                  <span class="info-value">{{ buildTag }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Java Version:</span>
                  <span class="info-value">{{ javaVersion }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">OS:</span>
                  <span class="info-value">{{ osInfo }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-6">
          <div class="card info-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-3 text-muted">
                <i class="pe-7s-clock"></i> System Status
              </h6>
              <div class="info-grid">
                <div class="info-item">
                  <span class="info-label">Uptime:</span>
                  <span class="info-value">{{ uptime }}</span>
                </div>
                <div class="info-item">
                  <span class="info-label">Last Refreshed:</span>
                  <span class="info-value">{{ statsLastRefreshed }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Show Details Button -->
      <div class="text-center mb-4">
        <button class="btn btn-primary btn-lg" @click="showDetailedModal = true">
          <i class="pe-7s-info"></i> Show Detailed Info
        </button>
      </div>
    </div>

    <!-- Detailed Info Modal -->
    <div
      v-if="showDetailedModal"
      class="modal fade show d-block"
      tabindex="-1"
      @click.self="showDetailedModal = false"
    >
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content modern-modal">
          <div class="modal-header gradient-header">
            <h5 class="modal-title text-white">
              <i class="pe-7s-server"></i> Detailed System Diagnostics
            </h5>
            <button
              type="button"
              class="btn-close btn-close-white"
              @click="showDetailedModal = false"
            ></button>
          </div>
          <div class="modal-body">
            <!-- System Information Section -->
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-info"></i> System Information
              </h6>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-key">NiFi Version</span>
                  <span class="detail-value">{{ nifiVersion }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Build Tag</span>
                  <span class="detail-value">{{ buildTag }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Java Version</span>
                  <span class="detail-value">{{ javaVersion }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">OS</span>
                  <span class="detail-value">{{ osInfo }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Uptime</span>
                  <span class="detail-value">{{ uptime }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Last Refreshed</span>
                  <span class="detail-value">{{ statsLastRefreshed }}</span>
                </div>
              </div>
            </div>

            <!-- Memory Section -->
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-box2"></i> Memory Usage
              </h6>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-key">Heap Utilization</span>
                  <span class="detail-value">{{ heapUtilization }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Used Heap</span>
                  <span class="detail-value">{{ usedHeap }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Max Heap</span>
                  <span class="detail-value">{{ maxHeap }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Total Heap</span>
                  <span class="detail-value">{{ totalHeap }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Free Heap</span>
                  <span class="detail-value">{{ freeHeap }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Non-Heap Utilization</span>
                  <span class="detail-value">{{ nonHeapUtilization }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Used Non-Heap</span>
                  <span class="detail-value">{{ usedNonHeap }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Total Non-Heap</span>
                  <span class="detail-value">{{ totalNonHeap }}</span>
                </div>
              </div>
            </div>

            <!-- CPU and Threads Section -->
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-server"></i> CPU & Threads
              </h6>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-key">Available Processors</span>
                  <span class="detail-value">{{ availableProcessors }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Processor Load Average</span>
                  <span class="detail-value">{{ cpuLoad }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Total Threads</span>
                  <span class="detail-value">{{ totalThreads }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Daemon Threads</span>
                  <span class="detail-value">{{ daemonThreads }}</span>
                </div>
              </div>
            </div>

            <!-- Storage Section -->
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-box1"></i> Storage Repositories
              </h6>

              <!-- Content Repository -->
              <div v-if="contentRepoStorage" class="storage-subsection">
                <div class="subsection-title">Content Repository</div>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-key">Utilization</span>
                    <span class="detail-value">{{ contentStorageUtilization }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Used Space</span>
                    <span class="detail-value">{{ contentStorageUsed }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Free Space</span>
                    <span class="detail-value">{{ contentRepoStorage.free_space || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Total Space</span>
                    <span class="detail-value">{{ contentStorageTotal }}</span>
                  </div>
                </div>
              </div>

              <!-- FlowFile Repository -->
              <div v-if="flowFileRepoStorage" class="storage-subsection">
                <div class="subsection-title">FlowFile Repository</div>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-key">Utilization</span>
                    <span class="detail-value">{{ flowFileRepoStorage.utilization || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Used Space</span>
                    <span class="detail-value">{{ flowFileRepoStorage.used_space || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Free Space</span>
                    <span class="detail-value">{{ flowFileRepoStorage.free_space || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Total Space</span>
                    <span class="detail-value">{{ flowFileRepoStorage.total_space || 'N/A' }}</span>
                  </div>
                </div>
              </div>

              <!-- Provenance Repository -->
              <div v-if="provenanceRepoStorage" class="storage-subsection">
                <div class="subsection-title">Provenance Repository</div>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-key">Utilization</span>
                    <span class="detail-value">{{ provenanceRepoStorage.utilization || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Used Space</span>
                    <span class="detail-value">{{ provenanceRepoStorage.used_space || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Free Space</span>
                    <span class="detail-value">{{ provenanceRepoStorage.free_space || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Total Space</span>
                    <span class="detail-value">{{ provenanceRepoStorage.total_space || 'N/A' }}</span>
                  </div>
                </div>
              </div>
            </div>

            <!-- Garbage Collection Section -->
            <div v-if="garbageCollection.length > 0" class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-refresh"></i> Garbage Collection
              </h6>
              <div v-for="(gc, index) in garbageCollection" :key="index" class="storage-subsection">
                <div class="subsection-title">{{ gc.name || `GC ${index + 1}` }}</div>
                <div class="detail-grid">
                  <div class="detail-item">
                    <span class="detail-key">Collection Count</span>
                    <span class="detail-value">{{ gc.collection_count || 'N/A' }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-key">Collection Time</span>
                    <span class="detail-value">{{ gc.collection_time || 'N/A' }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showDetailedModal = false">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showDetailedModal" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { apiRequest } from '@/utils/api';

interface NifiInstance {
  id: number;
  hierarchy_value: string;
  nifi_url: string;
}

const instances = ref<NifiInstance[]>([]);
const selectedInstanceId = ref<number | null>(null);
const systemDiagnostics = ref<any>(null);
const loading = ref(false);
const error = ref<string | null>(null);
const showDetailedModal = ref(false);

onMounted(async () => {
  await loadInstances();
});

const loadInstances = async () => {
  try {
    const response = await apiRequest<NifiInstance[]>('/api/nifi-instances');
    instances.value = response;
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load NiFi instances';
  }
};

const loadInstanceData = async () => {
  if (!selectedInstanceId.value) {
    systemDiagnostics.value = null;
    return;
  }

  loading.value = true;
  error.value = null;

  try {
    const response = await apiRequest<any>(`/api/nifi-instances/${selectedInstanceId.value}/get-system-diagnostics`);
    // Store the data field which contains system_diagnostics
    systemDiagnostics.value = response.data;
  } catch (err: any) {
    error.value = err.message || 'Failed to load system diagnostics';
  } finally {
    loading.value = false;
  }
};

// Computed properties for display
const heapUtilization = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.heap_utilization || 'N/A';
});

const usedHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.used_heap || 'N/A';
});

const maxHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.max_heap || 'N/A';
});

const cpuLoad = computed(() => {
  const load = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.processor_load_average;
  return load !== undefined && load !== null ? `${load.toFixed(2)}` : 'N/A';
});

const availableProcessors = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.available_processors || 'N/A';
});

const totalThreads = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.total_threads || 'N/A';
});

const daemonThreads = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.daemon_threads || 'N/A';
});

const contentStorageUtilization = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  const repos = snapshot?.content_repository_storage_usage;
  if (repos && repos.length > 0) {
    return repos[0].utilization || 'N/A';
  }
  return 'N/A';
});

const contentStorageUsed = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  const repos = snapshot?.content_repository_storage_usage;
  if (repos && repos.length > 0) {
    return repos[0].used_space || 'N/A';
  }
  return 'N/A';
});

const contentStorageTotal = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  const repos = snapshot?.content_repository_storage_usage;
  if (repos && repos.length > 0) {
    return repos[0].total_space || 'N/A';
  }
  return 'N/A';
});

// Version and system info
const nifiVersion = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.version_info?.ni_fi_version || 'N/A';
});

const buildTag = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.version_info?.build_tag || 'N/A';
});

const javaVersion = computed(() => {
  const info = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.version_info;
  if (info?.java_version && info?.java_vendor) {
    return `${info.java_version} (${info.java_vendor})`;
  }
  return 'N/A';
});

const osInfo = computed(() => {
  const info = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.version_info;
  if (info?.os_name && info?.os_version) {
    return `${info.os_name} ${info.os_version} (${info.os_architecture || 'N/A'})`;
  }
  return 'N/A';
});

const uptime = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.uptime || 'N/A';
});

const statsLastRefreshed = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.stats_last_refreshed || 'N/A';
});

// Additional memory properties for detailed view
const totalHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.total_heap || 'N/A';
});

const freeHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.free_heap || 'N/A';
});

const nonHeapUtilization = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.non_heap_utilization || 'N/A';
});

const usedNonHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.used_non_heap || 'N/A';
});

const totalNonHeap = computed(() => {
  return systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot?.total_non_heap || 'N/A';
});

// Storage repository properties
const contentRepoStorage = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  const repos = snapshot?.content_repository_storage_usage;
  return repos && repos.length > 0 ? repos[0] : null;
});

const flowFileRepoStorage = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  return snapshot?.flowfile_repository_storage_usage || null;
});

const provenanceRepoStorage = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  const repos = snapshot?.provenance_repository_storage_usage;
  return repos && repos.length > 0 ? repos[0] : null;
});

// Garbage collection
const garbageCollection = computed(() => {
  const snapshot = systemDiagnostics.value?.system_diagnostics?.aggregate_snapshot;
  return snapshot?.garbage_collection || [];
});

// Utility functions
const formatBytes = (bytes: number | string): string => {
  if (typeof bytes === 'string') return bytes;
  if (!bytes || bytes === 0) return '0 Bytes';

  const k = 1024;
  const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return Math.round((bytes / Math.pow(k, i)) * 100) / 100 + ' ' + sizes[i];
};

const getMemoryUsageClass = (utilization: string): string => {
  const percent = parseFloat(utilization);
  if (percent >= 90) return 'bg-danger';
  if (percent >= 75) return 'bg-warning';
  return 'bg-success';
};
</script>

<style scoped lang="scss">
.nifi-instances-monitoring {
  padding: 0;
}

.instance-selector {
  max-width: 600px;
  
  .form-select {
    padding: 0.75rem;
    font-size: 1rem;
    border-radius: 0.5rem;
    border: 2px solid #e0e0e0;
    transition: all 0.3s ease;
    
    &:focus {
      border-color: #667eea;
      box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
    }
  }
}

.monitoring-data {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.summary-card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.12);
  }
  
  .card-body {
    padding: 1.5rem;
  }
  
  .card-subtitle {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }
  
  .metric-value {
    font-size: 2rem;
    font-weight: 700;
    color: #2c3e50;
    margin: 0.5rem 0;
  }
}

.info-card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  
  .card-body {
    padding: 1.5rem;
  }
  
  .card-subtitle {
    font-size: 0.875rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    
    i {
      margin-right: 0.5rem;
    }
  }
}

.info-grid {
  display: grid;
  gap: 1rem;
}

.info-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.5rem 0;
  border-bottom: 1px solid #f0f0f0;
  
  &:last-child {
    border-bottom: none;
  }
  
  .info-label {
    font-weight: 500;
    color: #6c757d;
    font-size: 0.9rem;
  }
  
  .info-value {
    font-weight: 600;
    color: #2c3e50;
    text-align: right;
    font-size: 0.9rem;
  }
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 0.5rem;
  padding: 0.75rem 2rem;
  font-weight: 600;
  transition: all 0.3s ease;
  
  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
  }
  
  i {
    margin-right: 0.5rem;
  }
}

// Modal styles
.modern-modal {
  border: none;
  border-radius: 1rem;
  overflow: hidden;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  
  .modal-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    border: none;
    padding: 1.5rem 2rem;
    
    .modal-title {
      font-weight: 600;
      font-size: 1.25rem;
      
      i {
        margin-right: 0.5rem;
      }
    }
  }
  
  .modal-body {
    padding: 2rem;
    background-color: #f8f9fa;
  }
  
  .modal-footer {
    border-top: 1px solid #e9ecef;
    padding: 1rem 2rem;
    background-color: #ffffff;
  }
}

.modal-backdrop {
  background-color: rgba(0, 0, 0, 0.5);
}

.progress {
  border-radius: 0.5rem;
  overflow: hidden;
  
  .progress-bar {
    transition: width 0.6s ease;
  }
}

// Detailed diagnostics styling
.detail-section {
  margin-bottom: 2rem;
  
  .section-title {
    font-weight: 600;
    color: #2c3e50;
    margin-bottom: 1rem;
    padding-bottom: 0.5rem;
    border-bottom: 2px solid #e9ecef;
    
    i {
      margin-right: 0.5rem;
      color: #667eea;
    }
  }
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  padding: 0.75rem;
  background: #ffffff;
  border-radius: 6px;
  border-left: 3px solid #667eea;
  
  .detail-key {
    font-size: 0.875rem;
    font-weight: 500;
    color: #6c757d;
    margin-bottom: 0.25rem;
  }
  
  .detail-value {
    font-size: 1rem;
    font-weight: 600;
    color: #2c3e50;
    word-break: break-word;
  }
}

.storage-subsection {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #ffffff;
  border-radius: 8px;
  border: 1px solid #e9ecef;
  
  &:first-child {
    margin-top: 0;
  }
  
  .subsection-title {
    font-weight: 600;
    color: #495057;
    margin-bottom: 1rem;
    font-size: 0.95rem;
  }
  
  .detail-grid {
    gap: 0.75rem;
  }
}
</style>
