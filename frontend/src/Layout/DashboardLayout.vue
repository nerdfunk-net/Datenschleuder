<template>
  <div class="ds-app-container">
    <!-- Sidebar -->
    <aside class="ds-sidebar" :class="{ 'ds-collapsed': isSidebarCollapsed }">
      <div class="ds-sidebar-header">
        <div class="ds-logo">
          <i class="pe-7s-server"></i>
          <span v-if="!isSidebarCollapsed" class="ds-logo-text"
            >Datenschleuder</span
          >
        </div>
        <button class="ds-toggle-btn" @click="toggleSidebar">
          <i
            :class="
              isSidebarCollapsed ? 'pe-7s-angle-right' : 'pe-7s-angle-left'
            "
          ></i>
        </button>
      </div>

      <nav class="ds-sidebar-nav">
        <!-- Flows Menu -->
        <div class="ds-nav-section">
          <div class="ds-nav-item" @click="toggleMenu('flows')">
            <i class="pe-7s-network"></i>
            <span v-if="!isSidebarCollapsed" class="ds-nav-text">Flows</span>
            <i
              v-if="!isSidebarCollapsed"
              :class="menuState.flows ? 'pe-7s-angle-up' : 'pe-7s-angle-down'"
              class="ds-nav-arrow"
            ></i>
          </div>
          <div
            v-if="menuState.flows && !isSidebarCollapsed"
            class="ds-nav-submenu"
          >
            <router-link
              to="/flows/manage"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Manage</span>
            </router-link>
            <router-link
              to="/flows/deploy"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Deploy</span>
            </router-link>
          </div>
        </div>

        <!-- NiFi Menu -->
        <div class="ds-nav-section">
          <div class="ds-nav-item" @click="toggleMenu('nifi')">
            <i class="pe-7s-server"></i>
            <span v-if="!isSidebarCollapsed" class="ds-nav-text">NiFi</span>
            <i
              v-if="!isSidebarCollapsed"
              :class="menuState.nifi ? 'pe-7s-angle-up' : 'pe-7s-angle-down'"
              class="ds-nav-arrow"
            ></i>
          </div>
          <div
            v-if="menuState.nifi && !isSidebarCollapsed"
            class="ds-nav-submenu"
          >
            <router-link
              to="/nifi/monitoring"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Monitoring</span>
            </router-link>
            <router-link
              to="/nifi/parameter"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Parameter</span>
            </router-link>
            <router-link
              to="/nifi/install"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Install</span>
            </router-link>
          </div>
        </div>

        <!-- Settings Menu -->
        <div class="ds-nav-section">
          <div class="ds-nav-item" @click="toggleMenu('settings')">
            <i class="pe-7s-config"></i>
            <span v-if="!isSidebarCollapsed" class="ds-nav-text">Settings</span>
            <i
              v-if="!isSidebarCollapsed"
              :class="
                menuState.settings ? 'pe-7s-angle-up' : 'pe-7s-angle-down'
              "
              class="ds-nav-arrow"
            ></i>
          </div>
          <div
            v-if="menuState.settings && !isSidebarCollapsed"
            class="ds-nav-submenu"
          >
            <router-link
              to="/settings/nifi"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Nifi</span>
            </router-link>
            <router-link
              to="/settings/registry"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Registry</span>
            </router-link>
            <router-link
              to="/settings/hierarchy"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Hierarchy</span>
            </router-link>
            <router-link
              to="/settings/deploy"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Deploy</span>
            </router-link>
            <router-link
              v-if="isAdmin"
              to="/settings/users"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Users</span>
            </router-link>
            <router-link
              to="/settings/profile"
              class="ds-nav-subitem"
              active-class="ds-active"
            >
              <span>Profile</span>
            </router-link>
          </div>
        </div>
      </nav>

      <!-- Sidebar Footer -->
      <div class="ds-sidebar-footer">
        <div class="ds-user-info" @click="logout">
          <i class="pe-7s-power"></i>
          <span v-if="!isSidebarCollapsed" class="ds-nav-text">Logout</span>
        </div>
      </div>
    </aside>

    <!-- Main Content -->
    <div class="ds-main-content">
      <!-- Top Header -->
      <header class="ds-top-header">
        <div class="ds-header-content">
          <h1 class="ds-page-title">{{ pageTitle }}</h1>
          <div class="ds-header-actions">
            <span class="ds-user-badge">
              <i class="pe-7s-user"></i>
              {{ username }}
              <span v-if="isAdmin" class="badge bg-danger ms-2">Admin</span>
            </span>
          </div>
        </div>
      </header>

      <!-- Page Content -->
      <div class="ds-content-wrapper">
        <router-view></router-view>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import api from "@/utils/api";

const router = useRouter();
const route = useRoute();

const isSidebarCollapsed = ref(false);
const menuState = ref({
  nifi: false,
  flows: true,
  settings: false,
});

const username = ref("Admin User");
const isAdmin = ref(false);

// Load current user info
onMounted(async () => {
  try {
    const response = await api.get("/api/users/me");
    username.value = response.username;
    isAdmin.value = response.is_superuser;
    console.log("Current user:", response);
    console.log("Is admin:", response.is_superuser);
  } catch (error) {
    console.error("Failed to load user info:", error);
  }
});

const pageTitle = computed(() => {
  const titles: Record<string, string> = {
    "/nifi/monitoring": "NiFi Monitoring",
    "/nifi/parameter": "Parameter Contexts",
    "/nifi/install": "NiFi Installation",
    "/flows/manage": "Manage Flows",
    "/flows/deploy": "Deploy Flows",
    "/settings/nifi": "NiFi Settings",
    "/settings/registry": "Registry Settings",
    "/settings/hierarchy": "Hierarchy Settings",
    "/settings/deploy": "Deployment Settings",
    "/settings/profile": "Profile Settings",
    "/settings/users": "User Management",
  };
  return titles[route.path] || "Dashboard";
});

const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};

const toggleMenu = (menu: "nifi" | "flows" | "settings") => {
  if (!isSidebarCollapsed.value) {
    menuState.value[menu] = !menuState.value[menu];
  }
};

const logout = () => {
  localStorage.removeItem("token");
  router.push("/login");
};
</script>

<style scoped lang="scss">
// Use ds- prefix for all classes to avoid conflicts with template styles
.ds-app-container {
  display: flex !important;
  flex-direction: row !important;
  height: 100vh !important;
  width: 100vw !important;
  overflow: hidden !important;
  background-color: #f5f7fa !important;
  position: fixed !important;
  top: 0 !important;
  left: 0 !important;
  right: 0 !important;
  bottom: 0 !important;
  margin: 0 !important;
  padding: 0 !important;
}

.ds-sidebar {
  width: 260px !important;
  min-width: 260px !important;
  max-width: 260px !important;
  background: linear-gradient(135deg, #2c3e50 0%, #34495e 100%) !important;
  color: white !important;
  display: flex !important;
  flex-direction: column !important;
  flex-shrink: 0 !important;
  transition: all 0.3s ease !important;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1) !important;
  position: relative !important;
  z-index: 100 !important;

  &.ds-collapsed {
    width: 70px !important;
    min-width: 70px !important;
    max-width: 70px !important;
  }
}

.ds-sidebar-header {
  padding: 20px !important;
  display: flex !important;
  align-items: center !important;
  justify-content: space-between !important;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1) !important;
  flex-shrink: 0 !important;
}

.ds-logo {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  font-size: 1.5rem !important;
  font-weight: bold !important;

  i {
    font-size: 2rem !important;
    color: #4a90e2 !important;
  }

  .ds-logo-text {
    white-space: nowrap !important;
    overflow: hidden !important;
  }
}

.ds-toggle-btn {
  background: rgba(255, 255, 255, 0.1) !important;
  border: none !important;
  color: white !important;
  width: 30px !important;
  height: 30px !important;
  border-radius: 4px !important;
  cursor: pointer !important;
  display: flex !important;
  align-items: center !important;
  justify-content: center !important;
  transition: background 0.2s !important;

  &:hover {
    background: rgba(255, 255, 255, 0.2) !important;
  }
}

.ds-sidebar-nav {
  flex: 1 !important;
  padding: 20px 0 !important;
  overflow-y: auto !important;
}

.ds-nav-section {
  margin-bottom: 10px !important;
}

.ds-nav-item {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  padding: 12px 20px !important;
  cursor: pointer !important;
  transition: all 0.2s !important;
  color: rgba(255, 255, 255, 0.8) !important;

  i {
    font-size: 1.3rem !important;
    min-width: 24px !important;
  }

  .ds-nav-text {
    flex: 1 !important;
    white-space: nowrap !important;
    overflow: hidden !important;
  }

  .ds-nav-arrow {
    font-size: 1rem !important;
    margin-left: auto !important;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
  }
}

.ds-nav-submenu {
  background: rgba(0, 0, 0, 0.2) !important;
  padding: 5px 0 !important;
}

.ds-nav-subitem {
  display: block !important;
  padding: 10px 20px 10px 56px !important;
  color: rgba(255, 255, 255, 0.7) !important;
  text-decoration: none !important;
  transition: all 0.2s !important;
  font-size: 0.95rem !important;

  &:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
  }

  &.ds-active {
    background: rgba(74, 144, 226, 0.3) !important;
    color: #4a90e2 !important;
    border-left: 3px solid #4a90e2 !important;
  }
}

.ds-sidebar-footer {
  padding: 20px !important;
  border-top: 1px solid rgba(255, 255, 255, 0.1) !important;
  flex-shrink: 0 !important;
}

.ds-user-info {
  display: flex !important;
  align-items: center !important;
  gap: 12px !important;
  padding: 10px !important;
  cursor: pointer !important;
  border-radius: 4px !important;
  transition: background 0.2s !important;
  color: rgba(255, 255, 255, 0.8) !important;

  i {
    font-size: 1.3rem !important;
  }

  &:hover {
    background: rgba(255, 255, 255, 0.1) !important;
    color: white !important;
  }
}

.ds-main-content {
  flex: 1 !important;
  display: flex !important;
  flex-direction: column !important;
  overflow: hidden !important;
  min-width: 0 !important;
  position: relative !important;
}

.ds-top-header {
  background: white !important;
  padding: 20px 30px !important;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05) !important;
  z-index: 10 !important;
  flex-shrink: 0 !important;
}

.ds-header-content {
  display: flex !important;
  justify-content: space-between !important;
  align-items: center !important;
}

.ds-page-title {
  font-size: 1.5rem !important;
  font-weight: 600 !important;
  color: #2c3e50 !important;
  margin: 0 !important;
}

.ds-header-actions {
  display: flex !important;
  gap: 15px !important;
  align-items: center !important;
}

.ds-user-badge {
  display: flex !important;
  align-items: center !important;
  gap: 8px !important;
  padding: 8px 16px !important;
  background: #f5f7fa !important;
  border-radius: 20px !important;
  color: #5a6c7d !important;
  font-size: 0.9rem !important;

  i {
    font-size: 1.1rem !important;
  }
}

.ds-content-wrapper {
  flex: 1 !important;
  padding: 30px !important;
  overflow-y: auto !important;
  overflow-x: hidden !important;
  background: #f5f7fa !important;
}
</style>
