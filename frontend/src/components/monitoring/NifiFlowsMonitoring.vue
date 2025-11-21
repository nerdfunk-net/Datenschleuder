<template>
  <div class="nifi-flows-monitoring">
    <div v-if="loading" class="text-center py-5">
      <div class="spinner-border text-primary" role="status">
        <span class="visually-hidden">Loading...</span>
      </div>
      <p class="mt-3 text-muted">
        Loading flows...
      </p>
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
        <div class="filter-section">
          <input
            v-model="searchFilter"
            type="text"
            class="form-control filter-input"
            placeholder="Filter by flow name..."
            @input="highlightedFlowId = null"
          />
        </div>

        <!-- Status Filter -->
        <div v-click-outside="() => showStatusDropdown = false" class="filter-dropdown">
          <button
            class="btn btn-outline-secondary dropdown-toggle"
            type="button"
            @click="showStatusDropdown = !showStatusDropdown"
          >
            <i class="pe-7s-filter"></i>
            Status
            <span v-if="statusFilter.length > 0" class="badge bg-primary ms-1">{{ statusFilter.length }}</span>
          </button>
          <ul class="dropdown-menu dropdown-menu-checkboxes" :class="{ show: showStatusDropdown }" @click.stop>
            <li>
              <div class="dropdown-item">
                <input
                  id="status-green"
                  v-model="statusFilter"
                  type="checkbox"
                  value="healthy"
                  class="form-check-input me-2"
                />
                <label for="status-green" class="form-check-label">
                  <span class="status-indicator status-green"></span> Green
                </label>
              </div>
            </li>
            <li>
              <div class="dropdown-item">
                <input
                  id="status-yellow"
                  v-model="statusFilter"
                  type="checkbox"
                  value="warning"
                  class="form-check-input me-2"
                />
                <label for="status-yellow" class="form-check-label">
                  <span class="status-indicator status-yellow"></span> Yellow
                </label>
              </div>
            </li>
            <li>
              <div class="dropdown-item">
                <input
                  id="status-red"
                  v-model="statusFilter"
                  type="checkbox"
                  value="unhealthy"
                  class="form-check-input me-2"
                />
                <label for="status-red" class="form-check-label">
                  <span class="status-indicator status-red"></span> Red
                </label>
              </div>
            </li>
            <li>
              <div class="dropdown-item">
                <input
                  id="status-unknown"
                  v-model="statusFilter"
                  type="checkbox"
                  value="unknown"
                  class="form-check-input me-2"
                />
                <label for="status-unknown" class="form-check-label">
                  <span class="status-indicator status-gray"></span> Unknown
                </label>
              </div>
            </li>
          </ul>
        </div>

        <!-- Instance Filter -->
        <div class="filter-dropdown">
          <select
            v-model="instanceFilter"
            class="form-select"
          >
            <option :value="null">
              All Instances
            </option>
            <option v-for="instance in instances" :key="instance.id" :value="instance.id">
              {{ instance.hierarchy_value }}
            </option>
          </select>
        </div>

        <button
          class="btn btn-primary"
          :disabled="checking"
          @click="showCheckAllModal = true"
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
              <h6 class="card-subtitle mb-2 text-muted">
                Total Flows
              </h6>
              <div class="metric-value">
                {{ flows.length }}
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">
                Healthy
              </h6>
              <div class="metric-value text-success">
                {{ healthyFlowsCount }}
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">
                Issues
              </h6>
              <div class="metric-value text-danger">
                {{ unhealthyFlowsCount }}
              </div>
            </div>
          </div>
        </div>
        <div class="col-md-3">
          <div class="card summary-card">
            <div class="card-body">
              <h6 class="card-subtitle mb-2 text-muted">
                Unknown
              </h6>
              <div class="metric-value text-secondary">
                {{ unknownStatusFlowsCount }}
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Flow Widgets Grid -->
      <div class="flows-grid">
        <template v-for="flow in filteredFlows" :key="flow.id">
          <!-- Source Widget -->
          <div 
            class="flow-widget"
            :class="[
              getStatusClass(flow, 'source'),
              { 'highlighted': highlightedFlowId === flow.id }
            ]"
            @click="handleFlowClick(flow, 'source')"
          >
            <div class="flow-widget-header">
              <div class="flow-widget-title-container">
                <span class="flow-type-badge source-badge">Source</span>
                <div
                  class="flow-widget-title"
                  :class="{ 'clickable-title': getNiFiUrl(flow, 'source') }"
                  :title="getNiFiUrl(flow, 'source') ? 'Click to open in NiFi' : ''"
                  @click="getNiFiUrl(flow, 'source') && openNiFiProcessGroup(flow, 'source', $event)"
                >
                  {{ getFlowDisplayName(flow, 'source') }}
                </div>
              </div>
              <div class="flow-widget-actions">
                <button 
                  class="btn-info-icon"
                  :disabled="!getFlowItemStatus(flow, 'source')"
                  title="View details"
                  @click.stop="viewProcessGroupDetails(flow, 'source')"
                >
                  <i class="pe-7s-info"></i>
                </button>
                <div class="flow-widget-status-icon">
                  <i v-if="getFlowStatus(flow, 'source') === 'healthy'" class="pe-7s-check"></i>
                  <i v-else-if="getFlowStatus(flow, 'source') === 'unhealthy'" class="pe-7s-close"></i>
                  <i v-else-if="getFlowStatus(flow, 'source') === 'warning'" class="pe-7s-attention"></i>
                  <i v-else class="pe-7s-help1"></i>
                </div>
              </div>
            </div>
            <div class="flow-widget-body">
              <div class="flow-widget-info">
                <span class="info-label">Flow ID:</span>
                <span class="info-value">#{{ flow.id }}</span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'source')" class="flow-widget-info">
                <span class="info-label" title="running / stopped / invalid / disabled">Status:</span>
                <span class="info-value">
                  {{ getProcessorCounts(flow, 'source') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'source')" class="flow-widget-info">
                <span class="info-label" title="flow_files_in (bytes_in) / flow_files_out (bytes_out) / flow_files_sent (bytes_sent)">I/O:</span>
                <span class="info-value">
                  {{ getFlowFileStats(flow, 'source') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'source')" class="flow-widget-info">
                <span class="info-label" title="queued / queued_count / queued_size">Queue:</span>
                <span class="info-value">
                  {{ getQueueStats(flow, 'source') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'source')" class="flow-widget-info">
                <span class="info-label" title="Number of error bulletins">Bulletins:</span>
                <span class="info-value" :class="{ 'text-danger': getBulletinCount(flow, 'source') > 0 }">
                  {{ getBulletinInfo(flow, 'source') }}
                </span>
              </div>
            </div>
            <div class="flow-widget-footer">
              <span 
                class="status-text clickable"
                @click="handleStatusClick(flow, 'source', $event)"
              >
                {{ getStatusText(flow, 'source') }}
              </span>
            </div>
          </div>

          <!-- Destination Widget -->
          <div 
            class="flow-widget"
            :class="[
              getStatusClass(flow, 'destination'),
              { 'highlighted': highlightedFlowId === flow.id }
            ]"
            @click="handleFlowClick(flow, 'destination')"
          >
            <div class="flow-widget-header">
              <div class="flow-widget-title-container">
                <span class="flow-type-badge dest-badge">Destination</span>
                <div
                  class="flow-widget-title"
                  :class="{ 'clickable-title': getNiFiUrl(flow, 'destination') }"
                  :title="getNiFiUrl(flow, 'destination') ? 'Click to open in NiFi' : ''"
                  @click="getNiFiUrl(flow, 'destination') && openNiFiProcessGroup(flow, 'destination', $event)"
                >
                  {{ getFlowDisplayName(flow, 'destination') }}
                </div>
              </div>
              <div class="flow-widget-actions">
                <button 
                  class="btn-info-icon"
                  :disabled="!getFlowItemStatus(flow, 'destination')"
                  title="View details"
                  @click.stop="viewProcessGroupDetails(flow, 'destination')"
                >
                  <i class="pe-7s-info"></i>
                </button>
                <div class="flow-widget-status-icon">
                  <i v-if="getFlowStatus(flow, 'destination') === 'healthy'" class="pe-7s-check"></i>
                  <i v-else-if="getFlowStatus(flow, 'destination') === 'unhealthy'" class="pe-7s-close"></i>
                  <i v-else-if="getFlowStatus(flow, 'destination') === 'warning'" class="pe-7s-attention"></i>
                  <i v-else class="pe-7s-help1"></i>
                </div>
              </div>
            </div>
            <div class="flow-widget-body">
              <div class="flow-widget-info">
                <span class="info-label">Flow ID:</span>
                <span class="info-value">#{{ flow.id }}</span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'destination')" class="flow-widget-info">
                <span class="info-label" title="running / stopped / invalid / disabled">Status:</span>
                <span class="info-value">
                  {{ getProcessorCounts(flow, 'destination') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'destination')" class="flow-widget-info">
                <span class="info-label" title="flow_files_in (bytes_in) / flow_files_out (bytes_out) / flow_files_sent (bytes_sent)">I/O:</span>
                <span class="info-value">
                  {{ getFlowFileStats(flow, 'destination') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'destination')" class="flow-widget-info">
                <span class="info-label" title="queued / queued_count / queued_size">Queue:</span>
                <span class="info-value">
                  {{ getQueueStats(flow, 'destination') }}
                </span>
              </div>
              <div v-if="getFlowItemStatus(flow, 'destination')" class="flow-widget-info">
                <span class="info-label" title="Number of error bulletins">Bulletins:</span>
                <span class="info-value" :class="{ 'text-danger': getBulletinCount(flow, 'destination') > 0 }">
                  {{ getBulletinInfo(flow, 'destination') }}
                </span>
              </div>
            </div>
            <div class="flow-widget-footer">
              <span 
                class="status-text clickable"
                @click="handleStatusClick(flow, 'destination', $event)"
              >
                {{ getStatusText(flow, 'destination') }}
              </span>
            </div>
          </div>
        </template>
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
              <i class="pe-7s-network"></i> Flow Details: {{ getFlowDisplayName(selectedFlow, selectedFlowType || 'destination') }}
              <span class="flow-type-badge-modal" :class="selectedFlowType === 'source' ? 'source-badge' : 'dest-badge'">
                {{ selectedFlowType === 'source' ? 'Source' : 'Destination' }}
              </span>
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
                <div v-if="selectedFlow.name" class="detail-item">
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
                        'bg-success': getFlowStatus(selectedFlow, selectedFlowType || 'destination') === 'healthy',
                        'bg-danger': getFlowStatus(selectedFlow, selectedFlowType || 'destination') === 'unhealthy',
                        'bg-secondary': getFlowStatus(selectedFlow, selectedFlowType || 'destination') === 'unknown'
                      }"
                    >
                      {{ getStatusText(selectedFlow, selectedFlowType || 'destination') }}
                    </span>
                  </span>
                </div>
              </div>
            </div>

            <div v-if="selectedFlow.src_connection_param || selectedFlow.dest_connection_param" class="detail-section">
              <h6 class="section-title">
                <i class="pe-7s-network"></i> Connection Parameters
              </h6>
              <div class="detail-grid">
                <div v-if="selectedFlow.src_connection_param" class="detail-item">
                  <span class="detail-key">Source Connection</span>
                  <span class="detail-value">{{ selectedFlow.src_connection_param }}</span>
                </div>
                <div v-if="selectedFlow.dest_connection_param" class="detail-item">
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
            <p class="text-muted mb-3">
              Select a NiFi instance to check all flows:
            </p>
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
                    <br />
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
              <p class="mb-0">
                {{ selectedPGData.data.message || 'This flow has not been deployed to the NiFi instance.' }}
              </p>
            </div>

            <!-- Status Summary -->
            <div v-if="!selectedPGData.data?.not_deployed" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-graph2"></i> Processor Status
              </h6>
              <div class="row g-3">
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">
                      Running
                    </div>
                    <div class="stat-value text-success">
                      {{ selectedPGData.data?.running_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">
                      Stopped
                    </div>
                    <div class="stat-value text-danger">
                      {{ selectedPGData.data?.stopped_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">
                      Disabled
                    </div>
                    <div class="stat-value text-warning">
                      {{ selectedPGData.data?.disabled_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="stat-card">
                    <div class="stat-label">
                      Invalid
                    </div>
                    <div class="stat-value text-danger">
                      {{ selectedPGData.data?.invalid_count || 0 }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Ports Summary -->
            <div v-if="!selectedPGData.data?.not_deployed" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-share"></i> Ports
              </h6>
              <div class="row g-3">
                <div class="col-md-3">
                  <div class="metric-card">
                    <div class="metric-label">
                      Input Ports
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data?.input_port_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="metric-card">
                    <div class="metric-label">
                      Output Ports
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data?.output_port_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="metric-card">
                    <div class="metric-label">
                      Local Input
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data?.local_input_port_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-3">
                  <div class="metric-card">
                    <div class="metric-label">
                      Local Output
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data?.local_output_port_count || 0 }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Aggregate Snapshot -->
            <div v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.status?.aggregate_snapshot" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-graph1"></i> Performance Metrics
              </h6>
              <div class="row g-3">
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Active Threads
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.active_thread_count || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Queued FlowFiles
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_queued || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Queued (5 min)
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.queued || '0' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Throughput -->
            <div v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.status?.aggregate_snapshot" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-graph2"></i> Throughput (5 min average)
              </h6>
              <div class="row g-3">
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Input
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.input || '0' }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Output
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.output || '0' }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Read
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.read || '0' }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Written
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.written || '0' }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Transferred
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.transferred || '0' }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Received
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.received || '0' }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Data Volumes -->
            <div v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.status?.aggregate_snapshot" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-server"></i> Data Volumes
              </h6>
              <div class="row g-3">
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes In
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_in) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes Out
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_out) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes Queued
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_queued) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes Read
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_read) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes Written
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_written) }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      Bytes Transferred
                    </div>
                    <div class="metric-value">
                      {{ formatBytes(selectedPGData.data.status.aggregate_snapshot.bytes_transferred) }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- FlowFile Counts -->
            <div v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.status?.aggregate_snapshot" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-albums"></i> FlowFile Statistics
              </h6>
              <div class="row g-3">
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      FlowFiles In
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_in || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      FlowFiles Out
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_out || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      FlowFiles Transferred
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_transferred || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      FlowFiles Received
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_received || 0 }}
                    </div>
                  </div>
                </div>
                <div class="col-md-4">
                  <div class="metric-card">
                    <div class="metric-label">
                      FlowFiles Sent
                    </div>
                    <div class="metric-value">
                      {{ selectedPGData.data.status.aggregate_snapshot.flow_files_sent || 0 }}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            <!-- Bulletins -->
            <div v-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.bulletins && selectedPGData.data.bulletins.length > 0" class="detail-section mb-4">
              <h6 class="section-title">
                <i class="pe-7s-attention"></i> Bulletins ({{ selectedPGData.data.bulletins.length }})
              </h6>
              <div v-for="(bulletin, idx) in selectedPGData.data.bulletins" :key="idx" class="alert alert-warning">
                <strong>{{ bulletin.bulletin?.source_name || 'Unknown' }}:</strong>
                {{ bulletin.bulletin?.message || 'No message' }}
              </div>
            </div>
            <div v-else-if="!selectedPGData.data?.not_deployed && selectedPGData.data?.bulletins" class="alert alert-success">
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
import { ref, computed, onMounted, onBeforeUnmount } from 'vue';
import { apiRequest } from '@/utils/api';

// Click outside directive
const vClickOutside = {
  mounted(el: any, binding: any) {
    el.clickOutsideEvent = (event: Event) => {
      if (!(el === event.target || el.contains(event.target))) {
        binding.value(event);
      }
    };
    document.addEventListener('click', el.clickOutsideEvent);
  },
  unmounted(el: any) {
    document.removeEventListener('click', el.clickOutsideEvent);
  },
};

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
const selectedFlowType = ref<'source' | 'destination' | null>(null);

// Flow statuses now store source and destination separately
// Key format: "flowId_source" or "flowId_destination"
const flowStatuses = ref<Record<string, ProcessGroupStatus>>({});

// Filter and highlight
const searchFilter = ref<string>('');
const highlightedFlowId = ref<number | null>(null);
const statusFilter = ref<string[]>([]);
const instanceFilter = ref<number | null>(null);
const showStatusDropdown = ref(false);

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
    
    // Step 3: Check deployment paths for this instance
    const instanceDeploymentPath = deploymentPaths[instanceId.toString()];
    if (!instanceDeploymentPath) {
      console.warn(`No deployment path configured for instance ${instanceId}`);
      return;
    }
    
    // Step 4: Check each flow - both source AND destination
    for (const flow of flows.value) {
      // Check SOURCE
      await checkFlowPart(flow, 'source', instanceId, instanceDeploymentPath.source_path.path, hierarchyConfig, pathToIdMap);
      
      // Check DESTINATION
      await checkFlowPart(flow, 'destination', instanceId, instanceDeploymentPath.dest_path.path, hierarchyConfig, pathToIdMap);
    }
  } catch (err: any) {
    console.error('Failed to check flows:', err);
    error.value = `Failed to check flows: ${err.message || 'Unknown error'}`;
  } finally {
    checking.value = false;
  }
};

const checkFlowPart = async (
  flow: Flow,
  flowType: 'source' | 'destination',
  instanceId: number,
  basePath: string,
  hierarchyConfig: Array<{ name: string; order: number }>,
  pathToIdMap: Map<string, string>
) => {
  try {
    // Build expected path for this flow part
    const prefix = flowType === 'source' ? 'src_' : 'dest_';
    const hierarchyParts: string[] = [];
    
    // Add hierarchy values in order (o, ou, cn, etc.)
    // SKIP the first level (dc) as it's already in the deployment path
    for (let i = 1; i < hierarchyConfig.length; i++) {
      const hierarchyAttr = hierarchyConfig[i];
      // The attribute key in the flow object includes the full hierarchy name
      // e.g., "src_datenschleuder_dc", "dest_datenschleuder_o"
      const attrKey = `${prefix}${hierarchyAttr.name}`;
      const attrValue = flow[attrKey];
      if (attrValue) {
        hierarchyParts.push(attrValue);
      }
    }
    
    // Build full expected path - only add slash and hierarchy if we have parts
    let expectedPath = basePath;
    if (hierarchyParts.length > 0) {
      expectedPath = `${basePath}/${hierarchyParts.join('/')}`;
    }
    
    // Find matching process group ID
    const processGroupId = pathToIdMap.get(expectedPath);
    
    const flowKey = getFlowItemKey(flow.id, flowType);
    
    if (!processGroupId) {
      // Flow not deployed
      flowStatuses.value[flowKey] = {
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
      console.warn(`Flow ${flow.id} ${flowType} not found at expected path: ${expectedPath}`);
      return;
    }
    
    // Get the process group status using the ID
    const response = await apiRequest<ProcessGroupStatus>(
      `/api/nifi-instances/${instanceId}/process-group/${processGroupId}/status`
    );
    
    flowStatuses.value[flowKey] = response;
  } catch (err: any) {
    // Handle errors
    const flowKey = getFlowItemKey(flow.id, flowType);
    if (err.status === 404 || err.message?.includes('404')) {
      flowStatuses.value[flowKey] = {
        status: 'not_deployed',
        instance_id: instanceId,
        process_group_id: '',
        detail: 'not_deployed',
        data: {
          not_deployed: true,
          message: 'Flow not found / Not deployed'
        }
      } as ProcessGroupStatus;
      console.warn(`Flow ${flow.id} ${flowType} not found in NiFi instance ${instanceId}`);
    } else {
      console.error(`Failed to check flow ${flow.id} ${flowType}:`, err);
    }
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

  // Parse queued_count - it might be a string like "0" or a number
  let queuedCount = 0;
  const queuedCountValue = data.status?.aggregate_snapshot?.queued_count;
  if (queuedCountValue !== undefined && queuedCountValue !== null) {
    queuedCount = typeof queuedCountValue === 'string' ? parseInt(queuedCountValue, 10) : queuedCountValue;
  }

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
const filteredFlows = computed(() => {
  let result = flows.value;

  // Apply search filter
  if (searchFilter.value.trim()) {
    const search = searchFilter.value.toLowerCase();
    result = result.filter(flow => {
      // Check flow name
      const flowName = (flow.name || '').toLowerCase();
      if (flowName.includes(search)) {
        return true;
      }

      // Check all hierarchy attributes (src_ and dest_)
      for (const key in flow) {
        if ((key.startsWith('src_') || key.startsWith('dest_')) &&
            key !== 'src_connection_param' &&
            key !== 'dest_connection_param' &&
            key !== 'src_template_id' &&
            key !== 'dest_template_id') {
          const value = String(flow[key] || '').toLowerCase();
          if (value.includes(search)) {
            return true;
          }
        }
      }

      return false;
    });
  }

  // Apply status filter - only show flows where at least one side (source or destination) matches
  if (statusFilter.value.length > 0) {
    result = result.filter(flow => {
      const sourceStatus = getFlowStatus(flow, 'source');
      const destStatus = getFlowStatus(flow, 'destination');

      return statusFilter.value.includes(sourceStatus) || statusFilter.value.includes(destStatus);
    });
  }

  // Apply instance filter - only show flows that were checked against this instance
  if (instanceFilter.value !== null) {
    result = result.filter(flow => {
      // Check if either source or destination has status data from this instance
      const sourceStatus = getFlowItemStatus(flow, 'source');
      const destStatus = getFlowItemStatus(flow, 'destination');

      return (sourceStatus && sourceStatus.instance_id === instanceFilter.value) ||
             (destStatus && destStatus.instance_id === instanceFilter.value);
    });
  }

  return result;
});

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
  // Total items = flows * 2 (source + destination)
  const totalItems = flows.value.length * 2;
  return totalItems - Object.keys(flowStatuses.value).length;
});

// Helper functions
const getFlowItemKey = (flowId: number, flowType: 'source' | 'destination'): string => {
  return `${flowId}_${flowType}`;
};

const getFlowItemStatus = (flow: Flow, flowType: 'source' | 'destination'): ProcessGroupStatus | undefined => {
  return flowStatuses.value[getFlowItemKey(flow.id, flowType)];
};

const getFlowDisplayName = (flow: Flow, flowType: 'source' | 'destination'): string => {
  // Safety check
  if (!flow) {
    return 'Unnamed Flow';
  }
  
  // Get flow name from database (the 'name' field)
  const flowName = flow.name || 'Unnamed';
  
  // Get hierarchy prefix based on flow type
  const prefix = flowType === 'source' ? 'src_' : 'dest_';
  
  // Build path display from hierarchy values
  const hierarchyParts: string[] = [];
  const hierarchyKeys = Object.keys(flow)
    .filter(key => key.startsWith(prefix) && 
            key !== `${prefix}connection_param` && 
            key !== `${prefix}template_id`)
    .sort();
  
  for (const key of hierarchyKeys) {
    const value = flow[key];
    if (value) {
      hierarchyParts.push(value);
    }
  }
  
  // Build display name
  if (hierarchyParts.length > 0) {
    return `${flowName} / ${hierarchyParts.join('/')}`;
  }
  
  // Fallback to just flow name
  return flowName;
};

const getFlowStatus = (flow: Flow, flowType: 'source' | 'destination'): 'healthy' | 'unhealthy' | 'warning' | 'unknown' => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData) return 'unknown';
  return determineFlowStatus(statusData);
};

const getStatusClass = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const status = getFlowStatus(flow, flowType);
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

const getStatusText = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const statusData = getFlowItemStatus(flow, flowType);
  
  // Check for not deployed status
  if (statusData?.data?.not_deployed) {
    return 'Not Deployed';
  }
  
  const status = getFlowStatus(flow, flowType);
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

const viewFlowDetails = (flow: Flow, flowType: 'source' | 'destination') => {
  selectedFlow.value = flow;
  selectedFlowType.value = flowType;
  showDetailsModal.value = true;
};

const viewProcessGroupDetails = (flow: Flow, flowType: 'source' | 'destination') => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (statusData) {
    selectedPGData.value = statusData;
    selectedFlowType.value = flowType;
    showPGDetailsModal.value = true;
  }
};

const handleFlowClick = (flow: Flow, flowType: 'source' | 'destination') => {
  // Toggle highlight: if already highlighted, remove it; otherwise highlight this flow
  if (highlightedFlowId.value === flow.id) {
    highlightedFlowId.value = null;
  } else {
    highlightedFlowId.value = flow.id;
  }
};

const handleStatusClick = (flow: Flow, flowType: 'source' | 'destination', event: MouseEvent) => {
  // Stop propagation to prevent card click handler
  event.stopPropagation();
  
  // Open the process group details modal (NiFi status data)
  viewProcessGroupDetails(flow, flowType);
};

const formatDateLong = (dateString: string): string => {
  if (!dateString) return 'N/A';
  const date = new Date(dateString);
  return date.toLocaleString();
};

const formatBytes = (bytes: number | undefined): string => {
  if (bytes === undefined || bytes === null || bytes === 0) return '0 B';

  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(2))} ${sizes[i]}`;
};

const getProcessorCounts = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData?.data) return 'N/A';

  const data = statusData.data;
  const running = data.running_count || 0;
  const stopped = data.stopped_count || 0;
  const invalid = data.invalid_count || 0;
  const disabled = data.disabled_count || 0;

  return `${running}/${stopped}/${invalid}/${disabled}`;
};

const getFlowFileStats = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData?.data?.status?.aggregate_snapshot) return 'N/A';

  const snapshot = statusData.data.status.aggregate_snapshot;
  const flowFilesIn = snapshot.flow_files_in || 0;
  const bytesIn = formatBytes(snapshot.bytes_in);
  const flowFilesOut = snapshot.flow_files_out || 0;
  const bytesOut = formatBytes(snapshot.bytes_out);
  const flowFilesSent = snapshot.flow_files_sent || 0;
  const bytesSent = formatBytes(snapshot.bytes_sent);

  return `${flowFilesIn}(${bytesIn})/${flowFilesOut}(${bytesOut})/${flowFilesSent}(${bytesSent})`;
};

const getQueueStats = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData?.data?.status?.aggregate_snapshot) return 'N/A';

  const snapshot = statusData.data.status.aggregate_snapshot;
  const queued = snapshot.queued || '0';
  const queuedCount = snapshot.queued_count || '0';
  const queuedSize = snapshot.queued_size || '0 bytes';

  return `${queued}/${queuedCount}/${queuedSize}`;
};

const getBulletinCount = (flow: Flow, flowType: 'source' | 'destination'): number => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData?.data) return 0;

  const bulletins = statusData.data.bulletins || [];
  return bulletins.length;
};

const getBulletinInfo = (flow: Flow, flowType: 'source' | 'destination'): string => {
  const count = getBulletinCount(flow, flowType);
  return count > 0 ? `${count} issue${count > 1 ? 's' : ''}` : 'None';
};

const getNiFiUrl = (flow: Flow, flowType: 'source' | 'destination'): string | null => {
  const statusData = getFlowItemStatus(flow, flowType);
  if (!statusData?.instance_id || !statusData?.process_group_id) {
    return null;
  }

  // Find the instance to get the NiFi URL
  const instance = instances.value.find(inst => inst.id === statusData.instance_id);
  if (!instance) {
    return null;
  }

  // Convert nifi-api URL to nifi URL
  // Example: https://localhost:8443/nifi-api -> https://localhost:8443/nifi
  let nifiUrl = instance.nifi_url;
  if (nifiUrl.includes('/nifi-api')) {
    nifiUrl = nifiUrl.replace('/nifi-api', '/nifi');
  } else if (nifiUrl.endsWith('/')) {
    nifiUrl = nifiUrl.slice(0, -1) + '/nifi';
  } else {
    nifiUrl = nifiUrl + '/nifi';
  }

  // Build the full URL to the process group
  return `${nifiUrl}/#/process-groups/${statusData.process_group_id}`;
};

const openNiFiProcessGroup = (flow: Flow, flowType: 'source' | 'destination', event: MouseEvent) => {
  event.stopPropagation();
  const url = getNiFiUrl(flow, flowType);
  if (url) {
    window.open(url, '_blank');
  }
};
</script>

<style scoped lang="scss">
.nifi-flows-monitoring {
  padding: 0;
}

.action-bar {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 1rem;
  flex-wrap: wrap;

  .filter-section {
    flex: 1;
    max-width: 400px;
    min-width: 200px;
  }

  .filter-input {
    border-radius: 0.5rem;
    padding: 0.5rem 1rem;
    border: 1px solid #dee2e6;
    transition: all 0.2s ease;

    &:focus {
      border-color: #667eea;
      box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
      outline: none;
    }
  }

  .filter-dropdown {
    min-width: 150px;
    position: relative;

    .form-select {
      border-radius: 0.5rem;
      padding: 0.5rem 1rem;
      border: 1px solid #dee2e6;
      transition: all 0.2s ease;

      &:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 0.2rem rgba(102, 126, 234, 0.25);
        outline: none;
      }
    }

    .dropdown-toggle::after {
      margin-left: 0.5rem;
    }
  }

  .btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    white-space: nowrap;
  }
}

.dropdown-menu-checkboxes {
  padding: 0.5rem 0;
  min-width: 200px;
  position: absolute;
  top: 100%;
  left: 0;
  z-index: 1000;
  display: none;
  background-color: #fff;
  border: 1px solid rgba(0, 0, 0, 0.15);
  border-radius: 0.5rem;
  box-shadow: 0 0.5rem 1rem rgba(0, 0, 0, 0.15);
  margin-top: 0.25rem;

  &.show {
    display: block;
  }

  .dropdown-item {
    padding: 0.5rem 1rem;
    cursor: pointer;
    display: flex;
    align-items: center;

    &:hover {
      background-color: #f8f9fa;
    }

    .form-check-input {
      cursor: pointer;
      margin-top: 0;
    }

    .form-check-label {
      cursor: pointer;
      margin: 0;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      flex: 1;
    }
  }
}

.status-indicator {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;

  &.status-green {
    background-color: #28a745;
  }

  &.status-yellow {
    background-color: #ffc107;
  }

  &.status-red {
    background-color: #dc3545;
  }

  &.status-gray {
    background-color: #6c757d;
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
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-top: 1.5rem;
}

.flow-widget {
  border-radius: 0.5rem;
  padding: 0.75rem;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.08);

  &:hover {
    transform: translateY(-2px);
    box-shadow: 0 3px 8px rgba(0, 0, 0, 0.12);
  }

  &.highlighted {
    box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.5);
    transform: scale(1.01);
    z-index: 10;
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
  margin-bottom: 0.5rem;
  padding-bottom: 0.5rem;
  border-bottom: 1px solid rgba(0, 0, 0, 0.1);
}

.flow-widget-title-container {
  flex: 1;
  padding-right: 0.5rem;
}

.flow-type-badge {
  display: inline-block;
  font-size: 0.6rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 0.1rem 0.3rem;
  border-radius: 0.2rem;
  margin-bottom: 0.25rem;
}

.source-badge {
  background-color: #3498db;
  color: white;
}

.dest-badge {
  background-color: #9b59b6;
  color: white;
}

.flow-type-badge-modal {
  display: inline-block;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  margin-left: 0.5rem;
}

.flow-widget-actions {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.btn-info-icon {
  background: none;
  border: none;
  padding: 0.2rem 0.4rem;
  cursor: pointer;
  border-radius: 0.2rem;
  transition: all 0.2s ease;
  color: #667eea;
  font-size: 1rem;

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
  font-size: 0.85rem;
  font-weight: 600;
  color: #2c3e50;
  line-height: 1.2;
  flex: 1;
  padding-right: 0.5rem;

  &.clickable-title {
    color: #667eea;
    cursor: pointer;
    text-decoration: underline;
    text-decoration-style: dotted;
    transition: all 0.2s ease;

    &:hover {
      color: #4a5fce;
      text-decoration-style: solid;
    }
  }
}

.flow-widget-status-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.flow-widget-body {
  margin-bottom: 0.5rem;
}

.flow-widget-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  margin-bottom: 0.3rem;

  .info-label {
    color: #6c757d;
    font-weight: 500;
    cursor: help;
    text-decoration: underline dotted;

    &:hover {
      color: #495057;
    }
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
  padding-top: 0.4rem;
  border-top: 1px solid rgba(0, 0, 0, 0.1);
  text-align: center;

  .status-text {
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.3px;
    color: #495057;
    
    &.clickable {
      cursor: pointer;
      transition: all 0.2s ease;
      padding: 0.25rem 0.5rem;
      border-radius: 0.25rem;
      display: inline-block;
      
      &:hover {
        background-color: rgba(0, 0, 0, 0.05);
        color: #667eea;
        transform: scale(1.05);
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
