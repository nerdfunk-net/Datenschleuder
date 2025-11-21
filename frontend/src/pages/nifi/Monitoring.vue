<template>
  <div class="monitoring-page">
    <div class="page-header">
      <h1 class="page-title">
        NiFi Monitoring
      </h1>
      <p class="page-description">
        Monitor NiFi system diagnostics and flows
      </p>
    </div>

    <!-- Tabs Navigation -->
    <ul class="nav nav-tabs modern-tabs mb-4" role="tablist">
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'instances' }"
          type="button"
          role="tab"
          @click="activeTab = 'instances'"
        >
          <i class="pe-7s-server"></i> NiFi Instances
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'flows' }"
          type="button"
          role="tab"
          @click="activeTab = 'flows'"
        >
          <i class="pe-7s-network"></i> NiFi Flows
        </button>
      </li>
      <li class="nav-item" role="presentation">
        <button
          class="nav-link"
          :class="{ active: activeTab === 'queues' }"
          type="button"
          role="tab"
          @click="activeTab = 'queues'"
        >
          <i class="pe-7s-albums"></i> NiFi Queues
        </button>
      </li>
    </ul>

    <!-- Tab Content -->
    <div class="tab-content">
      <div
        v-show="activeTab === 'instances'"
        class="tab-pane fade"
        :class="{ 'show active': activeTab === 'instances' }"
        role="tabpanel"
      >
        <NifiInstancesMonitoring />
      </div>
      <div
        v-show="activeTab === 'flows'"
        class="tab-pane fade"
        :class="{ 'show active': activeTab === 'flows' }"
        role="tabpanel"
      >
        <NifiFlowsMonitoring />
      </div>
      <div
        v-show="activeTab === 'queues'"
        class="tab-pane fade"
        :class="{ 'show active': activeTab === 'queues' }"
        role="tabpanel"
      >
        <NifiQueuesMonitoring />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import NifiInstancesMonitoring from '@/components/monitoring/NifiInstancesMonitoring.vue';
import NifiFlowsMonitoring from '@/components/monitoring/NifiFlowsMonitoring.vue';
import NifiQueuesMonitoring from '@/components/monitoring/NifiQueuesMonitoring.vue';

// State
const activeTab = ref<'instances' | 'flows' | 'queues'>('instances');
</script>

<style scoped lang="scss">
.monitoring-page {
  padding: 0.5rem 2rem 2rem;
  max-width: 1400px;
  margin: 0 auto;
}

.page-header {
  margin-bottom: 1rem;
}

.page-title {
  font-size: 2rem;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.page-description {
  color: #6c757d;
  margin-bottom: 0;
}

// Modern tabs styling
.modern-tabs {
  border-bottom: 2px solid #e9ecef;
  margin-bottom: 2rem;
  
  .nav-item {
    margin-bottom: -2px;
  }
  
  .nav-link {
    border: none;
    border-bottom: 3px solid transparent;
    color: #6c757d;
    font-weight: 600;
    padding: 1rem 1.5rem;
    transition: all 0.3s ease;
    background: none;
    
    i {
      margin-right: 0.5rem;
    }
    
    &:hover {
      color: #667eea;
      border-bottom-color: #667eea;
      background-color: rgba(102, 126, 234, 0.05);
    }
    
    &.active {
      color: #667eea;
      border-bottom-color: #667eea;
      background: linear-gradient(to bottom, rgba(102, 126, 234, 0.1), transparent);
    }
  }
}

.tab-content {
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
</style>
