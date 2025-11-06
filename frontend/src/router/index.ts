import {
  createRouter,
  createWebHistory,
  type RouteRecordRaw,
} from "vue-router";

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
        path: "nifi/install",
        name: "nifi-install",
        component: () => import("../pages/nifi/Install.vue"),
      },
      {
        path: "nifi/parameter",
        name: "nifi-parameter",
        component: () => import("../pages/settings/Parameter.vue"),
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
    ],
  },
];

const router = createRouter({
  history: createWebHistory(),
  routes,
});

// Authentication guard
router.beforeEach((to, from, next) => {
  const isAuthenticated = localStorage.getItem("token");
  const requiresAuth = to.meta.requiresAuth !== false;

  if (requiresAuth && !isAuthenticated) {
    // Redirect to login if not authenticated
    next({ name: "login" });
  } else if (to.name === "login" && isAuthenticated) {
    // Redirect to dashboard if already logged in
    next({ path: "/" });
  } else {
    next();
  }
});

export default router;
