<template>
  <div class="nifi-flows-monitoring">
    <div class="flows-header mb-4">
      <p class="text-muted">Monitor the status and health of all configured NiFi flows across instances.</p>
    </div>

    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
    </div>

    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <div v-if="!loading && !error && flows.length === 0" class="alert alert-info">
      <i class="pe-7s-info"></i> No flows found. Please create and deploy flows first.
    </div>

    <div v-if="!loading && !error && flows.length > 0" class="flows-container">
      <!-- Summary Cards -->
      <div class="row g-4 mb-4">
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Total Flows</h6>
              <div class="metric-value">{{ flows.length }}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Active Flows</h6>
              <div class="metric-value text-success">{{ activeFlowsCount }}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Deployed</h6>
              <div class="metric-value text-primary">{{ deployedFlowsCount }}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Instances</h6>
              <div class="metric-value">{{ uniqueInstancesCount }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Flows Table -->
      <div class="card flows-table-card">
        <div class="card-header">
          <h5 class="mb-0">
            <i class="pe-7s-network"></i> Flow Status Overview
          </h5>
        </div>
        <div class="card-body p-0">
          <div class="table-responsive">
            <table class="table table-hover mb-0">
              <thead>
                <tr>
                  <th>Flow Name</th>
                  <th>Registry</th>
                  <th>Version</th>
                  <th>Source</th>
                  <th>Destination</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="flow in flows" :key="flow.id">
                  <td>
                    <div class="fw-semibold">{{ flow.flow_name }}</div>
                    <small class="text-muted">{{ flow.bucket_name }}</small>
                  </td>
                  <td>
                    <span class="badge bg-secondary">{{ flow.registry_name }}</span>
                  </td>
                  <td>
                    <span class="badge bg-info">v{{ flow.version }}</span>
                  </td>
                  <td>
                    <div v-if="flow.src_connection_param">
                      <small class="text-muted">{{ flow.src_connection_param }}</small>
                    </div>
                    <div v-else>
                      <span class="text-muted">-</span>
                    </div>
                  </td>
                  <td>
                    <div v-if="flow.dest_connection_param">
                      <small class="text-muted">{{ flow.dest_connection_param }}</small>
                    </div>
                    <div v-else>
                      <span class="text-muted">-</span>
                    </div>
                  </td>
                  <td>
                    <span 
                      class="badge"
                      :class="getStatusBadgeClass(flow)"
                    >
                      {{ getFlowStatus(flow) }}
                    </span>
                  </td>
                  <td>
                    <button 
                      class="btn btn-sm btn-outline-primary me-2"
                      @click="viewFlowDetails(flow)"
                      title="View details"
                    >
                      <i class="pe-7s-info"></i>
                    </button>
                    <button 
                      class="btn btn-sm btn-outline-secondary"
                      @click="refreshFlowStatus(flow)"
                      title="Refresh status"
                    >
                      <i class="pe-7s-refresh"></i>
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- Flow Details Modal -->
    <div
      v-if="selectedFlow && showDetailsModal"
      class="modal fade show d-block"
      tabindex="-1"
      @click.self="showDetailsModal = false"
    >
      <div class="modal-dialog modal-lg modal-dialog-scrollable">
        <div class="modal-content modern-modal">
          <div class="modal-header gradient-header">
            <h5 class="modal-title text-white">
              <i class="pe-7s-network"></i> Flow Details: {{ selectedFlow.flow_name }}
            </h5>
            <button
              type="button"
              class="btn-close btn-close-white"
              @click="showDetailsModal = false"
            ></button>
          </div>
          <div class="modal-body">
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-info"></i> Flow Information
              </h6>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-key">Flow Name</span>
                  <span class="detail-value">{{ selectedFlow.flow_name }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Bucket</span>
                  <span class="detail-value">{{ selectedFlow.bucket_name }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Registry</span>
                  <span class="detail-value">{{ selectedFlow.registry_name }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Version</span>
                  <span class="detail-value">{{ selectedFlow.version }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Flow ID</span>
                  <span class="detail-value">{{ selectedFlow.flow_id }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Bucket ID</span>
                  <span class="detail-value">{{ selectedFlow.bucket_id }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section" v-if="selectedFlow.src_connection_param || selectedFlow.dest_connection_param">
              <h6 class="section-title">
                <i class="pe-7s-network"></i> Connection Parameters
              </h6>
              <div class="detail-grid">
                <div class="detail-item" v-if="selectedFlow.src_connection_param">
                  <span class="detail-key">Source Connection</span>
                  <span class="detail-value">{{ selectedFlow.src_connection_param }}</span>
                </div>
                <div class="detail-item" v-if="selectedFlow.dest_connection_param">
                  <span class="detail-key">Destination Connection</span>
                  <span class="detail-value">{{ selectedFlow.dest_connection_param }}</span>
                </div>
              </div>
            </div>

            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-date"></i> Metadata
              </h6>
              <div class="detail-grid">
                <div class="detail-item">
                  <span class="detail-key">Created</span>
                  <span class="detail-value">{{ formatDate(selectedFlow.created_at) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Last Updated</span>
                  <span class="detail-value">{{ formatDate(selectedFlow.updated_at) }}</span>
                </div>
              </div>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showDetailsModal = false">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showDetailsModal" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { flowService } from '@/services/flowService';

interface Flow {
  id: number;
  flow_name: string;
  bucket_name: string;
  registry_name: string;
  version: number;
  flow_id: string;
  bucket_id: string;
  src_connection_param?: string;
  dest_connection_param?: string;
  created_at: string;
  updated_at: string;
}

const flows = ref<Flow[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedFlow = ref<Flow | null>(null);
const showDetailsModal = ref(false);

onMounted(async () => {
  await loadFlows();
});

const loadFlows = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await flowService.getFlows();
    flows.value = response;
  } catch (err: any) {
    error.value = err.response?.data?.detail || 'Failed to load flows';
  } finally {
    loading.value = false;
  }
};

// Computed properties
const activeFlowsCount = computed(() => {
  return flows.value.filter(flow => flow.src_connection_param || flow.dest_connection_param).length;
});

const deployedFlowsCount = computed(() => {
  return flows.value.filter(flow => flow.version > 0).length;
});

const uniqueInstancesCount = computed(() => {
  const uniqueParams = new Set<string>();
  flows.value.forEach(flow => {
    if (flow.src_connection_param) uniqueParams.add(flow.src_connection_param);
    if (flow.dest_connection_param) uniqueParams.add(flow.dest_connection_param);
  });
  return uniqueParams.size;
});

// Helper functions
const getFlowStatus = (flow: Flow): string => {
  if (flow.src_connection_param && flow.dest_connection_param) {
    return 'Active';
  } else if (flow.src_connection_param || flow.dest_connection_param) {
    return 'Partially Active';
  }
  return 'Configured';
};

const getStatusBadgeClass = (flow: Flow): string => {
  const status = getFlowStatus(flow);
  switch (status) {
    case 'Active':
      return 'bg-success';
    case 'Partially Active':
      return 'bg-warning';
    default:
      return 'bg-secondary';
  }
};

const viewFlowDetails = (flow: Flow) => {
  selectedFlow.value = flow;
  showDetailsModal.value = true;
};

const refreshFlowStatus = async (flow: Flow) => {
  // Placeholder for future implementation to check actual flow status from NiFi
  console.log('Refreshing status for flow:', flow.flow_name);
  // In future, this could call NiFi API to get real-time processor status
};

const formatDate = (dateString: string): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};
</script>

<style scoped lang="scss">
.nifi-flows-monitoring {
  padding: 0;
}

.flows-header {
  margin-bottom: 1.5rem;
}

.flows-container {
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

.flows-table-card {
  border: none;
  border-radius: 1rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  
  .card-header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    border: none;
    padding: 1.5rem 2rem;
    border-radius: 1rem 1rem 0 0;
    
    h5 {
      margin: 0;
      font-weight: 600;
      
      i {
        margin-right: 0.5rem;
      }
    }
  }
  
  .table {
    th {
      font-weight: 600;
      text-transform: uppercase;
      font-size: 0.875rem;
      color: #6c757d;
      letter-spacing: 0.5px;
      padding: 1rem;
      border-bottom: 2px solid #e9ecef;
    }
    
    td {
      padding: 1rem;
      vertical-align: middle;
    }
    
    tbody tr {
      transition: all 0.2s ease;
      
      &:hover {
        background-color: #f8f9fa;
      }
    }
  }
}

.btn-outline-primary,
.btn-outline-secondary {
  border-radius: 0.5rem;
  padding: 0.375rem 0.75rem;
  transition: all 0.2s ease;
  
  &:hover {
    transform: translateY(-2px);
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
</style>
