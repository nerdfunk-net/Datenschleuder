<template>
  <div class="nifi-flows-monitoring">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-muted">Loading flows...</p>
    </div>

    <div v-if="error" class="alert alert-danger">
      {{ error }}
    </div>

    <div v-if="!loading && !error && flows.length === 0" class="alert alert-info">
      <i class="pe-7s-info"></i> No flows found. Please create flows first.
    </div>

    <div v-if="!loading && !error && flows.length > 0" class="flows-container">
      <!-- Action Bar -->
      <div class="action-bar mb-4">
        <button 
          class="btn btn-primary"
          @click="showCheckAllModal = true"
          :disabled="checking"
        >
          <i class="pe-7s-refresh" :class="{ 'spinning': checking }"></i>
          {{ checking ? 'Checking...' : 'Check All' }}
        </button>
      </div>

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
              <h6 class="card-subtitle mb-2 text-muted">Healthy</h6>
              <div class="metric-value text-success">{{ healthyFlowsCount }}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Issues</h6>
              <div class="metric-value text-danger">{{ unhealthyFlowsCount }}</div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">Unknown</h6>
              <div class="metric-value text-secondary">{{ unknownStatusFlowsCount }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Flow Widgets Grid -->
      <div class="flows-grid">
        <div 
          v-for="flow in flows" 
          :key="flow.id"
          class="flow-widget"
          :class="getStatusClass(flow)"
          @click="viewFlowDetails(flow)"
        >
          <div class="flow-widget-header">
            <div class="flow-widget-title">{{ getFlowDisplayName(flow) }}</div>
            <div class="flow-widget-actions">
              <button 
                class="btn-info-icon"
                @click.stop="viewProcessGroupDetails(flow)"
                :disabled="!flowStatuses[flow.id]"
                title="View details"
              >
                <i class="pe-7s-info"></i>
              </button>
              <div class="flow-widget-status-icon">
                <i v-if="getFlowStatus(flow) === 'healthy'" class="pe-7s-check"></i>
                <i v-else-if="getFlowStatus(flow) === 'unhealthy'" class="pe-7s-close"></i>
                <i v-else-if="getFlowStatus(flow) === 'warning'" class="pe-7s-attention"></i>
                <i v-else class="pe-7s-help1"></i>
              </div>
            </div>
          </div>
          <div class="flow-widget-body">
            <div class="flow-widget-info">
              <span class="info-label">Registry:</span>
              <span class="info-value">{{ flow.registry_name }}</span>
            </div>
            <div class="flow-widget-info">
              <span class="info-label">Version:</span>
              <span class="info-value">v{{ flow.version }}</span>
            </div>
            <div class="flow-widget-info" v-if="flow.src_connection_param">
              <span class="info-label">Source:</span>
              <span class="info-value">{{ flow.src_connection_param }}</span>
            </div>
            <div class="flow-widget-info" v-if="flow.dest_connection_param">
              <span class="info-label">Dest:</span>
              <span class="info-value">{{ flow.dest_connection_param }}</span>
            </div>
          </div>
          <div class="flow-widget-footer">
            <span class="status-text">{{ getStatusText(flow) }}</span>
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
              <i class="pe-7s-network"></i> Flow Details: {{ getFlowDisplayName(selectedFlow) }}
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
                <div class="detail-item" v-if="selectedFlow.name">
                  <span class="detail-key">Flow Name</span>
                  <span class="detail-value">{{ selectedFlow.name }}</span>
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
                  <span class="detail-key">Status</span>
                  <span class="detail-value">
                    <span 
                      class="badge"
                      :class="{
                        'bg-success': getFlowStatus(selectedFlow) === 'healthy',
                        'bg-danger': getFlowStatus(selectedFlow) === 'unhealthy',
                        'bg-secondary': getFlowStatus(selectedFlow) === 'unknown'
                      }"
                    >
                      {{ getStatusText(selectedFlow) }}
                    </span>
                  </span>
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
                  <span class="detail-value">{{ formatDateLong(selectedFlow.created_at) }}</span>
                </div>
                <div class="detail-item">
                  <span class="detail-key">Last Updated</span>
                  <span class="detail-value">{{ formatDateLong(selectedFlow.updated_at) }}</span>
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

    <!-- Check All Modal -->
    <div
      v-if="showCheckAllModal"
      class="modal fade show d-block"
      tabindex="-1"
      @click.self="showCheckAllModal = false"
    >
      <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content modern-modal">
          <div class="modal-header gradient-header">
            <h5 class="modal-title text-white">
              <i class="pe-7s-network"></i> Select NiFi Instance
            </h5>
            <button
              type="button"
              class="btn-close btn-close-white"
              @click="showCheckAllModal = false"
            ></button>
          </div>
          <div class="modal-body">
            <p class="text-muted mb-3">Select a NiFi instance to check all flows:</p>
            <div v-if="loadingInstances" class="text-center py-3">
              <div class="spinner-border spinner-border-sm text-primary"></div>
            </div>
            <div v-else-if="instances.length === 0" class="alert alert-warning">
              No NiFi instances found.
            </div>
            <div v-else class="list-group">
              <button
                v-for="instance in instances"
                :key="instance.id"
                type="button"
                class="list-group-item list-group-item-action"
                @click="checkAllFlows(instance.id)"
              >
                <div class="d-flex justify-content-between align-items-center">
                  <div>
                    <strong>{{ instance.hierarchy_value }}</strong>
                    <br>
                    <small class="text-muted">{{ instance.nifi_url }}</small>
                  </div>
                  <i class="pe-7s-angle-right"></i>
                </div>
              </button>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showCheckAllModal = false">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showCheckAllModal" class="modal-backdrop fade show"></div>

    <!-- Process Group Details Modal -->
    <div
      v-if="showPGDetailsModal && selectedPGData"
      class="modal fade show d-block"
      tabindex="-1"
      @click.self="showPGDetailsModal = false"
    >
      <div class="modal-dialog modal-xl modal-dialog-scrollable">
        <div class="modal-content modern-modal">
          <div class="modal-header gradient-header">
            <h5 class="modal-title text-white">
              <i class="pe-7s-network"></i> Process Group Status: {{ selectedPGData.data?.component?.name || 'Unknown' }}
            </h5>
            <button
              type="button"
              class="btn-close btn-close-white"
              @click="showPGDetailsModal = false"
            ></button>
          </div>
          <div class="modal-body">
            <!-- Not Deployed Message -->
            <div v-if="selectedPGData.data?.not_deployed" class="alert alert-danger">
              <h5><i class="pe-7s-attention"></i> Flow Not Deployed</h5>
              <p class="mb-0">{{ selectedPGData.data.message || 'This flow has not been deployed to the NiFi instance.' }}</p>
            </div>

            <!-- Status Summary -->
            <div class="detail-section mb-4" v-if="!selectedPGData.data?.not_deployed">
              <h6 class="section-title">
                <i class="pe-7s-graph2"></i> Status Summary
              </h6>
              <div class="row g-3">
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">Running</div>
                    <div class="stat-value text-success">{{ selectedPGData.data?.running_count || 0 }}</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">Stopped</div>
                    <div class="stat-value text-danger">{{ selectedPGData.data?.stopped_count || 0 }}</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">Disabled</div>
                    <div class="stat-value text-warning">{{ selectedPGData.data?.disabled_count || 0 }}</div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">Invalid</div>
                    <div class="stat-value text-danger">{{ selectedPGData.data?.invalid_count || 0 }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Aggregate Snapshot -->
            <div class="detail-section mb-4" v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.status?.aggregate_snapshot">
              <h6 class="section-title">
                <i class="pe-7s-graph1"></i> Flow Metrics
              </h6>
              <div class="row g-3">
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Queued</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.queued }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Input</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.input }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Output</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.output }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Active Threads</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.active_thread_count }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Read</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.read }}</div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">Written</div>
                    <div class="metric-value">{{ selectedPGData.data.status.aggregate_snapshot.written }}</div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Bulletins -->
            <div class="detail-section mb-4" v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.bulletins && selectedPGData.data.bulletins.length > 0">
              <h6 class="section-title">
                <i class="pe-7s-attention"></i> Bulletins ({{ selectedPGData.data.bulletins.length }})
              </h6>
              <div class="alert alert-warning" v-for="(bulletin, idx) in selectedPGData.data.bulletins" :key="idx">
                <strong>{{ bulletin.bulletin?.source_name || 'Unknown' }}:</strong>
                {{ bulletin.bulletin?.message || 'No message' }}
              </div>
            </div>
            <div class="alert alert-success" v-else-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.bulletins">
              <i class="pe-7s-check"></i> No bulletins - all processors are running normally.
            </div>

            <!-- Raw JSON -->
            <div class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-file"></i> Raw Response
              </h6>
              <pre class="json-viewer">{{ JSON.stringify(selectedPGData.data, null, 2) }}</pre>
            </div>
          </div>
          <div class="modal-footer">
            <button type="button" class="btn btn-secondary" @click="showPGDetailsModal = false">
              Close
            </button>
          </div>
        </div>
      </div>
    </div>
    <div v-if="showPGDetailsModal" class="modal-backdrop fade show"></div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue';
import { apiRequest } from '@/utils/api';

interface Flow {
  id: number;
  name?: string;  // Optional flow name from the database
  bucket_name: string;
  registry_name: string;
  version: number;
  flow_id: string;
  bucket_id: string;
  src_connection_param?: string;
  dest_connection_param?: string;
  created_at: string;
  updated_at: string;
  // Dynamic hierarchy fields - these will be present as src_{attr} and dest_{attr}
  [key: string]: any;
}

interface NiFiInstance {
  id: number;
  hierarchy_attribute: string;
  hierarchy_value: string;
  nifi_url: string;
  use_ssl: boolean;
  verify_ssl: boolean;
}

interface ProcessGroupStatus {
  status: string;
  instance_id: number;
  process_group_id: string;
  detail: string;
  data: any;
}

const flows = ref<Flow[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const selectedFlow = ref<Flow | null>(null);
const showDetailsModal = ref(false);
const showCheckAllModal = ref(false);
const showPGDetailsModal = ref(false);
const checking = ref(false);
const instances = ref<NiFiInstance[]>([]);
const loadingInstances = ref(false);
const selectedPGData = ref<ProcessGroupStatus | null>(null);

// Flow statuses now store real status data
const flowStatuses = ref<Record<number, ProcessGroupStatus>>({});

onMounted(async () => {
  await loadFlows();
  await loadInstances();
});

const loadFlows = async () => {
  loading.value = true;
  error.value = null;

  try {
    const response = await apiRequest<{ flows: Flow[] }>('/api/nifi-flows/');
    flows.value = response.flows || [];
  } catch (err: any) {
    error.value = err.message || 'Failed to load flows';
  } finally {
    loading.value = false;
  }
};

const loadInstances = async () => {
  loadingInstances.value = true;
  try {
    const response = await apiRequest<NiFiInstance[]>('/api/nifi-instances/');
    instances.value = response || [];
  } catch (err: any) {
    console.error('Failed to load instances:', err);
  } finally {
    loadingInstances.value = false;
  }
};

const checkAllFlows = async (instanceId: number) => {
  showCheckAllModal.value = false;
  checking.value = true;
  flowStatuses.value = {}; // Reset statuses

  try {
    // Step 1: Load settings (hierarchy config and deployment paths)
    const settingsResponse = await apiRequest<{
      global: any;
      paths: Record<string, {
        source_path: { id: string; path: string };
        dest_path: { id: string; path: string };
      }>;
    }>('/api/settings/deploy');
    
    const hierarchyResponse = await apiRequest<{
      hierarchy: Array<{ name: string; label: string; order: number }>;
    }>('/api/settings/hierarchy');
    
    const deploymentPaths = settingsResponse.paths;
    const hierarchyConfig = hierarchyResponse.hierarchy.sort((a, b) => a.order - b.order);
    
    // Step 2: Get all process group paths from NiFi
    const allPathsResponse = await apiRequest<{
      status: string;
      process_groups: Array<{
        id: string;
        name: string;
        parent_group_id: string | null;
        path: Array<{ id: string; name: string; parent_group_id: string | null }>;
        depth: number;
      }>;
      count: number;
      root_id: string;
    }>(`/api/nifi-instances/${instanceId}/get-all-paths`);
    
    // Build a map of full path string -> process group ID
    const pathToIdMap = new Map<string, string>();
    allPathsResponse.process_groups.forEach(pg => {
      // Build path string from root to leaf: "NiFi Flow/To net1/o1/ou1/srvlx007"
      const pathString = pg.path.slice().reverse().map(p => p.name).join('/');
      pathToIdMap.set(pathString, pg.id);
    });
    
    console.log('Path to ID mapping:', Object.fromEntries(pathToIdMap));
    
    // Step 3: Check deployment paths for this instance
    const instanceDeploymentPath = deploymentPaths[instanceId.toString()];
    if (!instanceDeploymentPath) {
      console.warn(`No deployment path configured for instance ${instanceId}`);
      return;
    }
    
    const destBasePath = instanceDeploymentPath.dest_path.path; // e.g., "NiFi Flow/To net1"
    
    // Step 4: Check each flow
    for (const flow of flows.value) {
      try {
        // Build expected path for this flow
        // Path format: {dest_base_path}/{dest_hierarchy_values}
        // Example: "NiFi Flow/To net1/o1/ou1/srvlx007"
        
        const hierarchyParts: string[] = [];
        
        // Add hierarchy values in order (o, ou, cn, etc.)
        for (const hierarchyAttr of hierarchyConfig) {
          const attrKey = `dest_${hierarchyAttr.name.replace('datenschleuder_', '')}`;
          const attrValue = flow[attrKey];
          if (attrValue) {
            hierarchyParts.push(attrValue);
          }
        }
        
        // Build full expected path
        const expectedPath = `${destBasePath}/${hierarchyParts.join('/')}`;
        console.log(`Flow ${flow.id} (${flow.name}): Expected path = "${expectedPath}"`);
        
        // Find matching process group ID
        const processGroupId = pathToIdMap.get(expectedPath);
        
        if (!processGroupId) {
          // Flow not deployed
          flowStatuses.value[flow.id] = {
            status: 'not_deployed',
            instance_id: instanceId,
            process_group_id: '',
            detail: 'not_deployed',
            data: {
              not_deployed: true,
              message: 'Flow not found / Not deployed',
              expected_path: expectedPath
            }
          } as ProcessGroupStatus;
          console.warn(`Flow ${flow.id} not found at expected path: ${expectedPath}`);
          continue;
        }
        
        // Get the process group status using the ID
        const response = await apiRequest<ProcessGroupStatus>(
          `/api/nifi-instances/${instanceId}/process-group/${processGroupId}/status`
        );
        
        flowStatuses.value[flow.id] = response;
      } catch (err: any) {
        // Handle errors
        if (err.status === 404 || err.message?.includes('404')) {
          flowStatuses.value[flow.id] = {
            status: 'not_deployed',
            instance_id: instanceId,
            process_group_id: '',
            detail: 'not_deployed',
            data: {
              not_deployed: true,
              message: 'Flow not found / Not deployed'
            }
          } as ProcessGroupStatus;
          console.warn(`Flow ${flow.id} not found in NiFi instance ${instanceId}`);
        } else {
          console.error(`Failed to check flow ${flow.id}:`, err);
        }
      }
    }
  } catch (err: any) {
    console.error('Failed to check flows:', err);
    error.value = `Failed to check flows: ${err.message || 'Unknown error'}`;
  } finally {
    checking.value = false;
  }
};

const determineFlowStatus = (statusData: ProcessGroupStatus): 'healthy' | 'unhealthy' | 'warning' | 'unknown' => {
  if (!statusData?.data) return 'unknown';
  
  const data = statusData.data;
  
  // Check if flow is not deployed
  if (data.not_deployed) {
    return 'unhealthy';
  }
  
  const bulletins = data.bulletins || [];
  const stoppedCount = data.stopped_count || 0;
  const disabledCount = data.disabled_count || 0;
  const invalidCount = data.invalid_count || 0;
  const queuedCount = data.status?.aggregate_snapshot?.queued_count || 0;
  
  // Green: No bulletins and all counts are 0
  if (bulletins.length === 0 && stoppedCount === 0 && disabledCount === 0 && invalidCount === 0 && queuedCount === 0) {
    return 'healthy';
  }
  
  // Red: Bulletins exist or stopped_count is not zero
  if (bulletins.length > 0 || stoppedCount > 0) {
    return 'unhealthy';
  }
  
  // Yellow: Otherwise (disabled, invalid, or queued items)
  return 'warning';
};

// Computed properties
const healthyFlowsCount = computed(() => {
  return Object.values(flowStatuses.value).filter(status => 
    determineFlowStatus(status) === 'healthy'
  ).length;
});

const unhealthyFlowsCount = computed(() => {
  return Object.values(flowStatuses.value).filter(status => 
    determineFlowStatus(status) === 'unhealthy'
  ).length;
});

const unknownStatusFlowsCount = computed(() => {
  return flows.value.length - Object.keys(flowStatuses.value).length;
});

// Helper functions
const getFlowDisplayName = (flow: Flow): string => {
  // Safety check
  if (!flow) {
    return 'Unnamed Flow';
  }
  
  // Get flow name from database (the 'name' field)
  const flowName = flow.name || 'Unnamed';
  
  // Build shortened path display: flow_name → path_last_part/hierarchy_parts
  // Example: "flow_srvlx007 → To net1/ou1/srvlx007"
  
  // Get destination hierarchy values
  const hierarchyParts: string[] = [];
  const destHierarchyKeys = Object.keys(flow)
    .filter(key => key.startsWith('dest_') && 
            key !== 'dest_connection_param' && 
            key !== 'dest_template_id')
    .sort();
  
  for (const key of destHierarchyKeys) {
    const value = flow[key];
    if (value) {
      hierarchyParts.push(value);
    }
  }
  
  // If we have hierarchy parts, show shortened format
  if (hierarchyParts.length > 0) {
    // Extract last part of deployment path (e.g., "To net1" from "NiFi Flow/To net1")
    // We'll get this from the status data if available, otherwise just show hierarchy
    const statusData = flowStatuses.value[flow.id];
    let pathDisplay = '';
    
    if (statusData?.data?.expected_path) {
      // Extract deployment direction from expected path
      // e.g., "NiFi Flow/To net1/o1/ou1/srvlx007" -> "To net1"
      const pathParts = statusData.data.expected_path.split('/');
      if (pathParts.length >= 2) {
        pathDisplay = pathParts[1]; // Get "To net1" part
      }
    }
    
    // Build display: "flow_name → PathPart/hierarchy"
    const hierarchyDisplay = hierarchyParts.join('/');
    if (pathDisplay) {
      return `${flowName} → ${pathDisplay}/${hierarchyDisplay}`;
    } else {
      return `${flowName} → ${hierarchyDisplay}`;
    }
  }
  
  // Fallback to just flow name
  return flowName;
};

const getFlowStatus = (flow: Flow): 'healthy' | 'unhealthy' | 'warning' | 'unknown' => {
  const statusData = flowStatuses.value[flow.id];
  if (!statusData) return 'unknown';
  return determineFlowStatus(statusData);
};

const getStatusClass = (flow: Flow): string => {
  const status = getFlowStatus(flow);
  switch (status) {
    case 'healthy':
      return 'status-healthy';
    case 'unhealthy':
      return 'status-unhealthy';
    case 'warning':
      return 'status-warning';
    default:
      return 'status-unknown';
  }
};

const getStatusText = (flow: Flow): string => {
  const statusData = flowStatuses.value[flow.id];
  
  // Check for not deployed status
  if (statusData?.data?.not_deployed) {
    return 'Not Deployed';
  }
  
  const status = getFlowStatus(flow);
  switch (status) {
    case 'healthy':
      return 'Healthy';
    case 'unhealthy':
      return 'Issues Detected';
    case 'warning':
      return 'Warning';
    default:
      return 'Status Unknown';
  }
};

const viewFlowDetails = (flow: Flow) => {
  selectedFlow.value = flow;
  showDetailsModal.value = true;
};

const viewProcessGroupDetails = (flow: Flow) => {
  const statusData = flowStatuses.value[flow.id];
  if (statusData) {
    selectedPGData.value = statusData;
    showPGDetailsModal.value = true;
  }
};

const formatDateLong = (dateString: string): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};
</script>

<style scoped lang="scss">
.nifi-flows-monitoring {
  padding: 0;
}

.action-bar {
  display: flex;
  justify-content: flex-end;
  gap: 0.5rem;
  
  .btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
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

// Flow Widgets Grid
.flows-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

.flow-widget {
  border-radius: 0.75rem;
  padding: 1rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.08);
  
  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }
  
  &.status-unknown {
    background-color: #e9ecef;
    border: 1px solid #dee2e6;
    
    .flow-widget-status-icon {
      color: #6c757d;
    }
  }
  
  &.status-healthy {
    background-color: #d4edda;
    border: 1px solid #c3e6cb;
    
    .flow-widget-status-icon {
      color: #155724;
    }
  }
  
  &.status-unhealthy {
    background-color: #f8d7da;
    border: 1px solid #f5c6cb;
    
    .flow-widget-status-icon {
      color: #721c24;
    }
  }
  
  &.status-warning {
    background-color: #fff3cd;
    border: 1px solid #ffeaa7;
    
    .flow-widget-status-icon {
      color: #856404;
    }
  }
}

.flow-widget-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.75rem;
  padding-bottom: 0.75rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.flow-widget-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-info-icon {
  background: none;
  border: none;
  padding: 0.25rem 0.5rem;
  cursor: pointer;
  border-radius: 0.25rem;
  transition: all 0.2s ease;
  color: #667eea;
  font-size: 1.1rem;
  
  &:hover:not(:disabled) {
    background-color: rgba(102, 126, 234, 0.1);
    transform: scale(1.1);
  }
  
  &:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }
}

.flow-widget-title {
  font-size: 0.9rem;
  font-weight: 600;
  color: #2c3e50;
  line-height: 1.3;
  flex: 1;
  padding-right: 0.5rem;
}

.flow-widget-status-icon {
  font-size: 1.25rem;
  flex-shrink: 0;
}

.flow-widget-body {
  margin-bottom: 0.75rem;
}

.flow-widget-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.8rem;
  margin-bottom: 0.4rem;
  
  .info-label {
    color: #6c757d;
    font-weight: 500;
  }
  
  .info-value {
    color: #2c3e50;
    font-weight: 600;
    text-align: right;
    max-width: 60%;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.flow-widget-footer {
  padding-top: 0.5rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  text-align: center;
  
  .status-text {
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
    color: #495057;
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

// Additional modal styles
.stat-card {
  background: #ffffff;
  border-radius: 0.5rem;
  padding: 1rem;
  text-align: center;
  border: 1px solid #e9ecef;
  
  .stat-label {
    font-size: 0.875rem;
    color: #6c757d;
    font-weight: 500;
    margin-bottom: 0.5rem;
  }
  
  .stat-value {
    font-size: 1.75rem;
    font-weight: 700;
  }
}

.metric-card {
  background: #ffffff;
  border-radius: 0.5rem;
  padding: 0.75rem;
  border: 1px solid #e9ecef;
  
  .metric-label {
    font-size: 0.75rem;
    color: #6c757d;
    font-weight: 500;
    margin-bottom: 0.25rem;
  }
  
  .metric-value {
    font-size: 1.25rem;
    font-weight: 700;
    color: #2c3e50;
  }
}

.json-viewer {
  background: #2d3748;
  color: #e2e8f0;
  border-radius: 0.5rem;
  padding: 1rem;
  max-height: 400px;
  overflow: auto;
  font-size: 0.875rem;
  font-family: 'Monaco', 'Courier New', monospace;
}

.list-group-item-action {
  cursor: pointer;
  transition: all 0.2s ease;
  
  &:hover {
    background-color: #f8f9fa;
    transform: translateX(5px);
  }
}
</style>
