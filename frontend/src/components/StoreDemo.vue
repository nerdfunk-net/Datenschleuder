<!--
  Store Demo Component
  Demonstrates how to use Pinia stores in the ArchitectUI template
-->
<template>
  <div class="store-demo">
    <div class="card">
      <div class="card-header">
        <h5>Pinia Store Demo</h5>
      </div>
      <div class="card-body">
        <!-- Dashboard Store Demo -->
        <div class="mb-4">
          <h6>Dashboard Store</h6>
          <div class="row">
            <div
              v-for="stat in dashboardStore.statsWithTrends"
              :key="stat.key"
              class="col-md-4"
            >
              <div class="card mb-3">
                <div class="card-body">
                  <h6>{{ stat.label }}</h6>
                  <div class="h4 mb-0">
                    {{ stat.value }}
                  </div>
                  <small :class="stat.trendColor">
                    <font-awesome-icon :icon="stat.trendIcon" />
                    {{ stat.formattedChange }}
                  </small>
                </div>
              </div>
            </div>
          </div>
          <div class="mb-3">
            <strong>Pending Tasks:</strong>
            {{ dashboardStore.pendingTasksCount }}
          </div>
          <div class="mb-3">
            <strong>Total Revenue:</strong> ${{ dashboardStore.totalRevenue }}
          </div>
          <div class="mb-3">
            <button
              class="btn btn-primary me-2"
              @click="dashboardStore.refreshDashboard()"
            >
              <font-awesome-icon icon="refresh" />
              Refresh Dashboard
            </button>
            <button class="btn btn-success" @click="addDemoTask">
              <font-awesome-icon icon="plus" />
              Add Demo Task
            </button>
          </div>
        </div>

        <!-- UI Store Demo -->
        <div class="mb-4">
          <h6>UI Store</h6>
          <div class="mb-3">
            <strong>Current Theme:</strong> {{ uiStore.theme }}
            <button
              class="btn btn-sm btn-outline-secondary ms-2"
              @click="toggleTheme"
            >
              Toggle Theme
            </button>
          </div>
          <div class="mb-3">
            <strong>Sidebar Collapsed:</strong> {{ uiStore.sidebarCollapsed }}
            <button
              class="btn btn-sm btn-outline-secondary ms-2"
              @click="uiStore.toggleSidebar()"
            >
              Toggle Sidebar
            </button>
          </div>
          <div class="mb-3">
            <strong>Page Title:</strong> {{ uiStore.pageTitle }}
            <button
              class="btn btn-sm btn-outline-secondary ms-2"
              @click="updatePageTitle"
            >
              Update Page Title
            </button>
          </div>
          <div class="mb-3">
            <strong>Mobile View:</strong> {{ uiStore.isMobile }}
          </div>
        </div>

        <!-- Notifications Store Demo -->
        <div class="mb-4">
          <h6>Notifications Store</h6>
          <div class="mb-3">
            <strong>Unread Count:</strong> {{ notificationsStore.unreadCount }}
          </div>
          <div class="mb-3">
            <button
              class="btn btn-success btn-sm me-2"
              @click="notificationsStore.success('Success message!')"
            >
              Success
            </button>
            <button
              class="btn btn-danger btn-sm me-2"
              @click="notificationsStore.error('Error message!')"
            >
              Error
            </button>
            <button
              class="btn btn-warning btn-sm me-2"
              @click="notificationsStore.warning('Warning message!')"
            >
              Warning
            </button>
            <button
              class="btn btn-info btn-sm me-2"
              @click="notificationsStore.info('Info message!')"
            >
              Info
            </button>
          </div>
          <div class="mb-3">
            <button
              class="btn btn-primary me-2"
              @click="notificationsStore.showDemoNotifications()"
            >
              Show Demo Notifications
            </button>
            <button
              class="btn btn-outline-secondary"
              @click="notificationsStore.clearAll()"
            >
              Clear All
            </button>
          </div>
        </div>

        <!-- Active Notifications -->
        <div v-if="notificationsStore.notifications.length > 0">
          <h6>Active Notifications</h6>
          <div class="list-group">
            <div
              v-for="notification in notificationsStore.notifications"
              :key="notification.id"
              class="list-group-item d-flex justify-content-between align-items-center"
              :class="{ 'list-group-item-light': notification.read }"
            >
              <div>
                <font-awesome-icon
                  :icon="notification.icon"
                  :class="notification.type"
                />
                <strong class="ms-2">{{
                  notification.title || notification.type.toUpperCase()
                }}</strong>
                <div class="small text-muted">
                  {{ notification.message }}
                </div>
              </div>
              <div>
                <button
                  v-if="!notification.read"
                  class="btn btn-sm btn-outline-primary me-2"
                  @click="notificationsStore.markAsRead(notification.id)"
                >
                  Mark Read
                </button>
                <button
                  class="btn btn-sm btn-outline-danger"
                  @click="
                    notificationsStore.removeNotification(notification.id)
                  "
                >
                  <font-awesome-icon icon="times" />
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { useDashboardStore } from "@/stores/dashboard";
import { useUIStore } from "@/stores/ui";
import { useNotificationsStore } from "@/stores/notifications";

export default {
  name: "StoreDemo",
  setup() {
    const dashboardStore = useDashboardStore();
    const uiStore = useUIStore();
    const notificationsStore = useNotificationsStore();

    // Demo methods
    const toggleTheme = () => {
      const newTheme = uiStore.theme === "light" ? "dark" : "light";
      uiStore.setTheme(newTheme);
    };

    const updatePageTitle = () => {
      const titles = ["Dashboard", "Analytics", "Reports", "Settings"];
      const randomTitle = titles[Math.floor(Math.random() * titles.length)];
      uiStore.setPageTitle(randomTitle, `Updated to ${randomTitle}`);
    };

    const addDemoTask = () => {
      const tasks = [
        {
          title: "Review dashboard metrics",
          description: "Check latest performance data",
        },
        {
          title: "Update user documentation",
          description: "Add new feature guides",
        },
        { title: "Optimize API calls", description: "Reduce load times" },
        {
          title: "Fix responsive issues",
          description: "Mobile layout improvements",
        },
      ];

      const randomTask = tasks[Math.floor(Math.random() * tasks.length)];
      dashboardStore.addTodoTask(randomTask);

      notificationsStore.success(`Added task: ${randomTask.title}`);
    };

    return {
      dashboardStore,
      uiStore,
      notificationsStore,
      toggleTheme,
      updatePageTitle,
      addDemoTask,
    };
  },
};
</script>

<style scoped>
.store-demo {
  max-width: 1200px;
  margin: 0 auto;
  padding: 20px;
}

.text-success {
  color: #28a745 !important;
}

.text-danger {
  color: #dc3545 !important;
}

.text-warning {
  color: #ffc107 !important;
}

.text-info {
  color: #17a2b8 !important;
}
</style>
