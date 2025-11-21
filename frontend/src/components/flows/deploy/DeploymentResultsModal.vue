<template>
  <b-modal
    v-model="isVisible"
    title="Deployment Results"
    size="lg"
    hide-footer
  >
    <div class="deployment-results">
      <!-- Summary Stats -->
      <div class="results-summary">
        <div class="stat-card success">
          <div class="stat-icon">
            <i class="pe-7s-check"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ results.successCount }}
            </div>
            <div class="stat-label">
              Successful
            </div>
          </div>
        </div>
        <div class="stat-card failed">
          <div class="stat-icon">
            <i class="pe-7s-close"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ results.failCount }}
            </div>
            <div class="stat-label">
              Failed
            </div>
          </div>
        </div>
        <div class="stat-card total">
          <div class="stat-icon">
            <i class="pe-7s-network"></i>
          </div>
          <div class="stat-content">
            <div class="stat-value">
              {{ results.total }}
            </div>
            <div class="stat-label">
              Total
            </div>
          </div>
        </div>
      </div>

      <!-- Successful Deployments -->
      <div
        v-if="results.successful.length > 0"
        class="results-section success-section"
      >
        <h6 class="section-title">
          <i class="pe-7s-check"></i>
          Successful Deployments
        </h6>
        <div class="result-list">
          <div
            v-for="(result, index) in results.successful"
            :key="index"
            class="result-item success"
          >
            <div class="result-header">
              <i class="pe-7s-check-circle"></i>
              <strong>{{ result.config.flowName }}</strong>
              <span
                class="badge"
                :class="
                  result.config.target === 'source'
                    ? 'badge-primary'
                    : 'badge-success'
                "
              >
                {{ result.config.target }}
              </span>
            </div>
            <div class="result-details">
              <div class="detail-row">
                <span class="label">Instance:</span>
                <span>{{ result.config.hierarchyValue }}</span>
              </div>
              <div class="detail-row">
                <span class="label">Process Group:</span>
                <code>{{ result.processGroupName }}</code>
              </div>
              <div v-if="result.processGroupId" class="detail-row">
                <span class="label">ID:</span>
                <code class="small">{{ result.processGroupId }}</code>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Failed Deployments -->
      <div
        v-if="results.failed.length > 0"
        class="results-section failed-section"
      >
        <h6 class="section-title">
          <i class="pe-7s-close"></i>
          Failed Deployments
        </h6>
        <div class="result-list">
          <div
            v-for="(result, index) in results.failed"
            :key="index"
            class="result-item failed"
          >
            <div class="result-header">
              <i class="pe-7s-close-circle"></i>
              <strong>{{ result.config.flowName }}</strong>
              <span
                class="badge"
                :class="
                  result.config.target === 'source'
                    ? 'badge-primary'
                    : 'badge-success'
                "
              >
                {{ result.config.target }}
              </span>
            </div>
            <div class="result-details">
              <div class="detail-row">
                <span class="label">Instance:</span>
                <span>{{ result.config.hierarchyValue }}</span>
              </div>
              <div class="detail-row error">
                <span class="label">Error:</span>
                <span>{{ result.message }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Actions -->
      <div class="results-actions">
        <b-button
          v-if="results.failCount === 0"
          variant="success"
          class="w-100"
          @click="handleDone"
        >
          <i class="pe-7s-check"></i>
          Done - Start New Deployment
        </b-button>
        <b-button
          v-else
          variant="primary"
          class="w-100"
          @click="handleReview"
        >
          <i class="pe-7s-angle-left"></i>
          Review and Fix Issues
        </b-button>
      </div>
    </div>
  </b-modal>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import type { DeploymentResults } from '@/composables/useDeploymentWizard'

interface Props {
  show: boolean
  results: DeploymentResults
}

interface Emits {
  (e: 'update:show', value: boolean): void
  (e: 'done'): void
  (e: 'review'): void
}

const props = defineProps<Props>()
const emit = defineEmits<Emits>()

const isVisible = computed({
  get: () => props.show,
  set: (value) => emit('update:show', value)
})

const handleDone = () => {
  emit('done')
}

const handleReview = () => {
  emit('update:show', false)
  emit('review')
}
</script>

<style scoped lang="scss">
.deployment-results {
  .results-summary {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 15px;
    margin-bottom: 30px;

    .stat-card {
      display: flex;
      align-items: center;
      gap: 15px;
      padding: 20px;
      border-radius: 8px;
      border: 2px solid;

      &.success {
        background: #e8f5e9;
        border-color: #4caf50;

        .stat-icon {
          color: #4caf50;
        }
      }

      &.failed {
        background: #ffebee;
        border-color: #f44336;

        .stat-icon {
          color: #f44336;
        }
      }

      &.total {
        background: #e3f2fd;
        border-color: #2196f3;

        .stat-icon {
          color: #2196f3;
        }
      }

      .stat-icon {
        font-size: 2rem;
      }

      .stat-content {
        .stat-value {
          font-size: 1.5rem;
          font-weight: 600;
          line-height: 1;
          margin-bottom: 4px;
        }

        .stat-label {
          font-size: 0.875rem;
          color: #6c757d;
        }
      }
    }
  }

  .results-section {
    margin-bottom: 25px;

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-size: 1rem;
      font-weight: 600;
      margin-bottom: 15px;
      padding-bottom: 10px;
      border-bottom: 2px solid #e9ecef;

      i {
        font-size: 1.25rem;
      }
    }

    &.success-section .section-title {
      color: #4caf50;
    }

    &.failed-section .section-title {
      color: #f44336;
    }

    .result-list {
      display: flex;
      flex-direction: column;
      gap: 10px;

      .result-item {
        border: 1px solid #e9ecef;
        border-radius: 6px;
        overflow: hidden;

        &.success {
          border-left: 4px solid #4caf50;
        }

        &.failed {
          border-left: 4px solid #f44336;
        }

        .result-header {
          display: flex;
          align-items: center;
          gap: 10px;
          padding: 12px 15px;
          background: #f8f9fa;
          border-bottom: 1px solid #e9ecef;

          i {
            font-size: 1.25rem;
          }

          strong {
            flex: 1;
          }

          .badge {
            padding: 4px 12px;
            border-radius: 12px;
            font-size: 0.75rem;
            font-weight: 500;
            text-transform: uppercase;

            &.badge-primary {
              background: #e3f2fd;
              color: #1976d2;
            }

            &.badge-success {
              background: #e8f5e9;
              color: #388e3c;
            }
          }
        }

        .result-details {
          padding: 15px;

          .detail-row {
            display: flex;
            margin-bottom: 8px;
            font-size: 0.875rem;

            &:last-child {
              margin-bottom: 0;
            }

            &.error {
              .label {
                color: #f44336;
              }

              span:not(.label) {
                color: #d32f2f;
                font-weight: 500;
              }
            }

            .label {
              font-weight: 600;
              color: #6c757d;
              min-width: 140px;
            }

            code {
              background: #e9ecef;
              padding: 2px 6px;
              border-radius: 3px;
              font-size: 0.875rem;

              &.small {
                font-size: 0.75rem;
              }
            }
          }
        }
      }
    }
  }

  .results-actions {
    margin-top: 25px;
    padding-top: 20px;
    border-top: 2px solid #e9ecef;
  }
}
</style>
