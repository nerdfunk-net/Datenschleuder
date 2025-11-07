import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";
import api from "@/utils/api";

const routes: RouteRecordRaw[] = [
  {
    path: "/login",
    name: "login",
    component: () => import("../pages/Login.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/login/callback",
    name: "oidc-callback",
    component: () => import("../pages/OIDCCallback.vue"),
    meta: { requiresAuth: false },
  },
  {
    path: "/",
    component: () => import("../Layout/DashboardLayout.vue"),
    meta: { requiresAuth: true },
    children: [
      {
        path: "",
        redirect: "/flows/manage",
      },
      {
        path: "nifi/monitoring",
        name: "nifi-monitoring",
        component: () => import("../pages/nifi/Monitoring.vue"),
      },
      {
        path: "nifi/parameter",
        name: "nifi-parameter",
        component: () => import("../pages/settings/Parameter.vue"),
      },
      {
        path: "nifi/install",
        name: "nifi-install",
        component: () => import("../pages/nifi/Install.vue"),
      },
      {
        path: "flows/manage",
        name: "flows-manage",
        component: () => import("../pages/flows/Manage.vue"),
      },
      {
        path: "flows/deploy",
        name: "flows-deploy",
        component: () => import("../pages/flows/Deploy.vue"),
      },
      {
        path: "settings/nifi",
        name: "settings-nifi",
        component: () => import("../pages/settings/Nifi.vue"),
      },
      {
        path: "settings/registry",
        name: "settings-registry",
        component: () => import("../pages/settings/Registry.vue"),
      },
      {
        path: "settings/hierarchy",
        name: "settings-hierarchy",
        component: () => import("../pages/settings/Hierarchy.vue"),
      },
      {
        path: "settings/deploy",
        name: "settings-deploy",
        component: () => import("../pages/settings/Deploy.vue"),
      },
      {
        path: "settings/profile",
        name: "settings-profile",
        component: () => import("../pages/settings/Profile.vue"),
      },
      {
        path: "settings/users",
        name: "settings-users",
        component: () => import("../pages/settings/Users.vue"),
        meta: { requiresAdmin: true },
      },
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Authentication and authorization guard
router.beforeEach(async (to, from, next) => {
  const isAuthenticated = localStorage.getItem("token");
  const requiresAuth = to.meta.requiresAuth !== false;
  const requiresAdmin = to.meta.requiresAdmin === true;

  if (requiresAuth && !isAuthenticated) {
    // Redirect to login if not authenticated
    next({ name: "login" });
  } else if (to.name === "login" && isAuthenticated) {
    // Redirect to dashboard if already logged in
    next({ path: "/" });
  } else if (requiresAdmin && isAuthenticated) {
    // Check if user is admin for admin-only routes
    try {
      const user = await api.get("/api/users/me");
      if (user.is_superuser) {
        next();
      } else {
        // Non-admin trying to access admin page
        next({ path: "/flows/manage" });
      }
    } catch (error) {
      console.error("Failed to verify admin status:", error);
      // If API call fails, redirect to login
      localStorage.removeItem("token");
      next({ name: "login" });
    }
  } else {
    next();
  }
});

export default router;
