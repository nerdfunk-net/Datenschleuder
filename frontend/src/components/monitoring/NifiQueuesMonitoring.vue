<template>
  <div class="nifi-queues-monitoring">
    <!-- Instance Selection -->
    <div class="card mb-4">
      <div class="card-body">
        <h5 class="card-title mb-3">
          <i class="pe-7s-server"></i> Select NiFi Instance
        </h5>
        <div class="row align-items-end">
          <div class="col-md-6">
            <label class="form-label">NiFi Instance</label>
            <select
              v-model="selectedInstanceId"
              class="form-select"
              @change="onInstanceChange"
            >
              <option :value="null">
                -- Select an instance --
              </option>
              <option
                v-for="instance in instances"
                :key="instance.id"
                :value="instance.id"
              >
                {{ instance.hierarchy_value }}
              </option>
            </select>
          </div>
          <div class="col-md-6">
            <button
              class="btn btn-primary"
              :disabled="!selectedInstanceId || checking"
              @click="checkAllQueues"
            >
              <i
                class="pe-7s-refresh"
                :class="{ spinning: checking }"
              ></i>
              {{ checking ? 'Checking...' : 'Check All Queues' }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-muted">
        Loading instances...
      </p>
    </div>

    <!-- Error State -->
    <div v-if="error" class="alert alert-danger" role="alert">
      <i class="pe-7s-attention"></i> {{ error }}
    </div>

    <!-- Queues Table -->
    <div v-if="connections.length > 0" class="card">
      <div class="card-body">
        <h5 class="card-title mb-3">
          <i class="pe-7s-albums"></i> Connection Queues ({{ connections.length }} total)
        </h5>

        <!-- Summary Stats -->
        <div class="row mb-4">
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-label">
                Total Connections
              </div>
              <div class="stat-value">
                {{ connections.length }}
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-label">
                Queued Connections
              </div>
              <div class="stat-value text-warning">
                {{ queuedConnectionsCount }}
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-label">
                Total FlowFiles
              </div>
              <div class="stat-value text-info">
                {{ totalFlowFiles }}
              </div>
            </div>
          </div>
          <div class="col-md-3">
            <div class="stat-card">
              <div class="stat-label">
                Total Size
              </div>
              <div class="stat-value text-success">
                {{ totalQueuedSize }}
              </div>
            </div>
          </div>
        </div>

        <!-- Table -->
        <div class="table-responsive">
          <table class="table table-hover table-striped">
            <thead>
              <tr>
                <th>Connection Name</th>
                <th>Source</th>
                <th>Source Type</th>
                <th>Destination</th>
                <th>Destination Type</th>
                <th class="text-end">
                  Queued
                </th>
                <th class="text-end sortable" @click="toggleSort('flowFilesIn')">
                  FlowFiles In
                  <i
                    class="sort-icon"
                    :class="{
                      'pe-7s-angle-up': sortField === 'flowFilesIn' && sortDirection === 'asc',
                      'pe-7s-angle-down': sortField === 'flowFilesIn' && sortDirection === 'desc',
                      'pe-7s-left-right': sortField !== 'flowFilesIn'
                    }"
                  ></i>
                </th>
                <th class="text-end sortable" @click="toggleSort('flowFilesOut')">
                  FlowFiles Out
                  <i
                    class="sort-icon"
                    :class="{
                      'pe-7s-angle-up': sortField === 'flowFilesOut' && sortDirection === 'asc',
                      'pe-7s-angle-down': sortField === 'flowFilesOut' && sortDirection === 'desc',
                      'pe-7s-left-right': sortField !== 'flowFilesOut'
                    }"
                  ></i>
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="connection in sortedConnections"
                :key="connection.id"
                :class="{ 'table-warning': hasQueue(connection) }"
              >
                <td>
                  <a
                    v-if="getNiFiUrl(connection)"
                    :href="getNiFiUrl(connection)"
                    target="_blank"
                    class="connection-link"
                    :title="'Open in NiFi'"
                  >
                    <span v-if="connection.name" class="fw-semibold">{{ connection.name }}</span>
                    <span v-else class="fst-italic">Unnamed</span>
                  </a>
                  <span v-else>
                    <span v-if="connection.name" class="fw-semibold">{{ connection.name }}</span>
                    <span v-else class="text-muted fst-italic">Unnamed</span>
                  </span>
                </td>
                <td>{{ connection.source?.name || 'N/A' }}</td>
                <td>
                  <span class="badge" :class="getTypeBadgeClass(connection.source?.type)">
                    {{ formatType(connection.source?.type) }}
                  </span>
                </td>
                <td>{{ connection.destination?.name || 'N/A' }}</td>
                <td>
                  <span class="badge" :class="getTypeBadgeClass(connection.destination?.type)">
                    {{ formatType(connection.destination?.type) }}
                  </span>
                </td>
                <td class="text-end">
                  <span
                    v-if="hasQueue(connection)"
                    class="badge bg-warning text-dark"
                  >
                    {{ connection.status?.aggregate_snapshot?.queued || '0' }}
                  </span>
                  <span v-else class="text-muted">
                    {{ connection.status?.aggregate_snapshot?.queued || '0' }}
                  </span>
                </td>
                <td class="text-end">
                  {{ connection.status?.aggregate_snapshot?.flow_files_in || 0 }}
                </td>
                <td class="text-end">
                  {{ connection.status?.aggregate_snapshot?.flow_files_out || 0 }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <!-- Empty State -->
    <div
      v-if="!loading && !error && connections.length === 0 && selectedInstanceId && hasChecked"
      class="alert alert-info"
      role="alert"
    >
      <i class="pe-7s-info"></i> No connections found for this instance.
    </div>

    <!-- No Instance Selected -->
    <div
      v-if="!loading && !error && !selectedInstanceId"
      class="alert alert-secondary"
      role="alert"
    >
      <i class="pe-7s-info"></i> Please select a NiFi instance to view queues.
    </div>
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

interface Connection {
  id: string;
  name: string;
  parent_group_id: string;
  type: string | null;
  comments: string | null;
  source: {
    id: string;
    name: string;
    type: string;
    group_id: string;
  };
  destination: {
    id: string;
    name: string;
    type: string;
    group_id: string;
  };
  status: {
    aggregate_snapshot: {
      active_thread_count: number | null;
      bytes_in: number;
      bytes_out: number;
      flow_files_in: number;
      flow_files_out: number;
      queued: string;
    };
  };
}

// State
const instances = ref<NifiInstance[]>([]);
const selectedInstanceId = ref<number | null>(null);
const connections = ref<Connection[]>([]);
const loading = ref(false);
const checking = ref(false);
const error = ref<string | null>(null);
const hasChecked = ref(false);
const sortField = ref<'flowFilesIn' | 'flowFilesOut' | null>(null);
const sortDirection = ref<'asc' | 'desc'>('desc');

// Load instances on mount
onMounted(async () => {
  await loadInstances();
});

// Load NiFi instances
const loadInstances = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await apiRequest<NifiInstance[]>(
      '/api/nifi-instances/'
    );
    instances.value = response || [];
    
    // Auto-select first instance if only one exists
    if (instances.value.length === 1) {
      selectedInstanceId.value = instances.value[0].id;
    }
    // Clear selection if previously selected instance no longer exists
    else if (selectedInstanceId.value && !instances.value.find(inst => inst.id === selectedInstanceId.value)) {
      selectedInstanceId.value = null;
      connections.value = [];
      hasChecked.value = false;
    }
  } catch (err: any) {
    console.error('Failed to load instances:', err);
    error.value = err.detail || 'Failed to load NiFi instances';
  } finally {
    loading.value = false;
  }
};

// Handle instance change
const onInstanceChange = () => {
  connections.value = [];
  hasChecked.value = false;
  error.value = null;
};

// Check all queues
const checkAllQueues = async () => {
  if (!selectedInstanceId.value) return;

  checking.value = true;
  error.value = null;
  hasChecked.value = false;

  try {
    const response = await apiRequest<{
      status: string;
      components: Connection[];
      count: number;
    }>(
      `/api/nifi/${selectedInstanceId.value}/list-all-by-kind?kind=connections`
    );

    connections.value = response.components || [];
    hasChecked.value = true;
  } catch (err: any) {
    console.error('Failed to check queues:', err);
    error.value = err.detail || 'Failed to check queues';
    connections.value = [];
  } finally {
    checking.value = false;
  }
};

// Check if connection has queued items
const hasQueue = (connection: Connection): boolean => {
  const queued = connection.status?.aggregate_snapshot?.queued || '0';
  // Parse the queued string (e.g., "16 (0 bytes)" or "0 (0 bytes)")
  const match = queued.match(/^(\d+)/);
  return match ? parseInt(match[1], 10) > 0 : false;
};

// Toggle sort field and direction
const toggleSort = (field: 'flowFilesIn' | 'flowFilesOut') => {
  if (sortField.value === field) {
    // Toggle direction if same field
    sortDirection.value = sortDirection.value === 'asc' ? 'desc' : 'asc';
  } else {
    // Set new field with descending by default
    sortField.value = field;
    sortDirection.value = 'desc';
  }
};

// Computed: Sorted connections
const sortedConnections = computed(() => {
  let sorted = [...connections.value];

  // Apply custom sorting if a sort field is selected
  if (sortField.value) {
    sorted.sort((a, b) => {
      let aValue = 0;
      let bValue = 0;

      if (sortField.value === 'flowFilesIn') {
        aValue = a.status?.aggregate_snapshot?.flow_files_in || 0;
        bValue = b.status?.aggregate_snapshot?.flow_files_in || 0;
      } else if (sortField.value === 'flowFilesOut') {
        aValue = a.status?.aggregate_snapshot?.flow_files_out || 0;
        bValue = b.status?.aggregate_snapshot?.flow_files_out || 0;
      }

      if (sortDirection.value === 'asc') {
        return aValue - bValue;
      } else {
        return bValue - aValue;
      }
    });
  } else {
    // Default sorting: queued first, then by name
    sorted.sort((a, b) => {
      const aQueued = hasQueue(a);
      const bQueued = hasQueue(b);

      // Sort queued connections first
      if (aQueued && !bQueued) return -1;
      if (!aQueued && bQueued) return 1;

      // Then by name
      const aName = a.name || '';
      const bName = b.name || '';
      return aName.localeCompare(bName);
    });
  }

  return sorted;
});

// Computed: Count of connections with queued items
const queuedConnectionsCount = computed(() => {
  return connections.value.filter(hasQueue).length;
});

// Computed: Total flow files queued
const totalFlowFiles = computed(() => {
  return connections.value.reduce((sum, conn) => {
    const queued = conn.status?.aggregate_snapshot?.queued || '0';
    const match = queued.match(/^(\d+)/);
    return sum + (match ? parseInt(match[1], 10) : 0);
  }, 0);
});

// Computed: Total queued size
const totalQueuedSize = computed(() => {
  let totalBytes = 0;

  connections.value.forEach(conn => {
    const queued = conn.status?.aggregate_snapshot?.queued || '0';
    // Parse size from string like "16 (1.5 KB)"
    const match = queued.match(/\(([^)]+)\)/);
    if (match) {
      const sizeStr = match[1].trim();
      totalBytes += parseSizeToBytes(sizeStr);
    }
  });

  return formatBytes(totalBytes);
});

// Parse size string to bytes
const parseSizeToBytes = (sizeStr: string): number => {
  const match = sizeStr.match(/([\d.]+)\s*(bytes|KB|MB|GB|TB)?/i);
  if (!match) return 0;

  const value = parseFloat(match[1]);
  const unit = (match[2] || 'bytes').toUpperCase();

  const multipliers: Record<string, number> = {
    'BYTES': 1,
    'KB': 1024,
    'MB': 1024 * 1024,
    'GB': 1024 * 1024 * 1024,
    'TB': 1024 * 1024 * 1024 * 1024,
  };

  return value * (multipliers[unit] || 1);
};

// Format bytes to human-readable string
const formatBytes = (bytes: number): string => {
  if (bytes === 0) return '0 bytes';

  const k = 1024;
  const sizes = ['bytes', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

// Get badge class for component type
const getTypeBadgeClass = (type: string | undefined): string => {
  if (!type) return 'badge-type-secondary';

  switch (type) {
    case 'PROCESSOR':
      return 'badge-type-processor';
    case 'INPUT_PORT':
      return 'badge-type-input';
    case 'OUTPUT_PORT':
      return 'badge-type-output';
    case 'FUNNEL':
      return 'badge-type-funnel';
    default:
      return 'badge-type-secondary';
  }
};

// Format component type for display
const formatType = (type: string | undefined): string => {
  if (!type) return 'N/A';

  return type
    .replace(/_/g, ' ')
    .toLowerCase()
    .replace(/\b\w/g, (c) => c.toUpperCase());
};

// Get NiFi URL for connection
const getNiFiUrl = (connection: Connection): string | undefined => {
  if (!selectedInstanceId.value || !connection.parent_group_id) {
    return undefined;
  }

  // Find the selected instance to get the NiFi URL
  const instance = instances.value.find(inst => inst.id === selectedInstanceId.value);
  if (!instance) {
    return undefined;
  }

  // Convert nifi-api URL to nifi URL
  let nifiUrl = instance.nifi_url;
  if (nifiUrl.includes('/nifi-api')) {
    nifiUrl = nifiUrl.replace('/nifi-api', '/nifi');
  } else if (nifiUrl.endsWith('/')) {
    nifiUrl = nifiUrl.slice(0, -1) + '/nifi';
  } else {
    nifiUrl = nifiUrl + '/nifi';
  }

  // Build the full URL to the parent process group
  return `${nifiUrl}/#/process-groups/${connection.parent_group_id}`;
};
</script>

<style scoped lang="scss">
.nifi-queues-monitoring {
  padding: 0;
}

.card {
  border-radius: 0.75rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: none;
}

.card-title {
  font-weight: 600;
  color: #2c3e50;

  i {
    margin-right: 0.5rem;
    color: #667eea;
  }
}

.stat-card {
  background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
  padding: 1rem;
  border-radius: 0.5rem;
  text-align: center;

  .stat-label {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    color: #6c757d;
    margin-bottom: 0.5rem;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 700;
    color: #2c3e50;
  }
}

.table {
  margin-bottom: 0;

  thead {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;

    th {
      border: none;
      font-weight: 600;
      padding: 1rem;
      vertical-align: middle;

      &.sortable {
        cursor: pointer;
        user-select: none;
        transition: all 0.2s ease;

        &:hover {
          background-color: rgba(255, 255, 255, 0.1);
        }

        .sort-icon {
          margin-left: 0.5rem;
          font-size: 0.875rem;
          opacity: 0.7;
          transition: opacity 0.2s ease;
        }

        &:hover .sort-icon {
          opacity: 1;
        }
      }
    }
  }

  tbody {
    tr {
      transition: all 0.2s ease;

      &:hover {
        background-color: rgba(102, 126, 234, 0.05);
        transform: scale(1.005);
        box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
      }

      &.table-warning {
        background-color: rgba(255, 193, 7, 0.1);

        &:hover {
          background-color: rgba(255, 193, 7, 0.15);
        }
      }

      td {
        padding: 0.875rem 1rem;
        vertical-align: middle;
      }
    }
  }
}

.badge {
  padding: 0.35rem 0.65rem;
  font-weight: 600;
  font-size: 0.75rem;
}

// Custom badge styles with blue text for better visibility
.badge-type-processor {
  background-color: #e3f2fd;
  color: #1976d2;
  border: 1px solid #90caf9;
}

.badge-type-input {
  background-color: #e8f5e9;
  color: #2e7d32;
  border: 1px solid #81c784;
}

.badge-type-output {
  background-color: #e1f5fe;
  color: #0277bd;
  border: 1px solid #4fc3f7;
}

.badge-type-funnel {
  background-color: #fff9c4;
  color: #f57f17;
  border: 1px solid #fff176;
}

.badge-type-secondary {
  background-color: #f5f5f5;
  color: #616161;
  border: 1px solid #e0e0e0;
}

.connection-link {
  color: #667eea;
  text-decoration: underline;
  text-decoration-style: dotted;
  transition: all 0.2s ease;

  &:hover {
    color: #4a5fce;
    text-decoration-style: solid;
  }
}

.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.alert {
  border-radius: 0.75rem;
  border: none;

  i {
    margin-right: 0.5rem;
  }
}
</style>
