/**
 * API utility for making authenticated requests to the backend
 */

const API_BASE_URL = "http://localhost:8000";

// Flag to prevent multiple concurrent refresh attempts
let isRefreshing = false;
let refreshPromise: Promise<string> | null = null;

/**
 * Refresh the access token using the refresh token
 */
async function refreshAccessToken(): Promise<string> {
  const refreshToken = localStorage.getItem("refresh_token");

  if (!refreshToken) {
    throw new Error("No refresh token available");
  }

  const response = await fetch(`${API_BASE_URL}/api/auth/refresh`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ refresh_token: refreshToken }),
  });

  if (!response.ok) {
    // Refresh token is invalid or expired
    localStorage.removeItem("token");
    localStorage.removeItem("refresh_token");
    localStorage.removeItem("rememberMe");
    window.location.href = "/login";
    throw new Error("Failed to refresh token");
  }

  const data = await response.json();
  localStorage.setItem("token", data.access_token);
  if (data.refresh_token) {
    localStorage.setItem("refresh_token", data.refresh_token);
  }

  return data.access_token;
}

/**
 * Make an authenticated API request
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {},
): Promise<T> {
  const token = localStorage.getItem("token");

  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };

  // Add authorization header if token exists
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const url = endpoint.startsWith("http")
    ? endpoint
    : `${API_BASE_URL}${endpoint}`;

  let response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - try to refresh token
  if (response.status === 401) {
    const refreshToken = localStorage.getItem("refresh_token");

    // Only attempt refresh if we have a refresh token
    if (refreshToken) {
      try {
        // If already refreshing, wait for that to complete
        if (isRefreshing && refreshPromise) {
          await refreshPromise;
        } else {
          // Start a new refresh
          isRefreshing = true;
          refreshPromise = refreshAccessToken();
          await refreshPromise;
          isRefreshing = false;
          refreshPromise = null;
        }

        // Retry the original request with new token
        const newToken = localStorage.getItem("token");
        if (newToken) {
          headers["Authorization"] = `Bearer ${newToken}`;
        }

        response = await fetch(url, {
          ...options,
          headers,
        });
      } catch (error) {
        // Refresh failed, redirect to login
        isRefreshing = false;
        refreshPromise = null;
        localStorage.removeItem("token");
        localStorage.removeItem("refresh_token");
        localStorage.removeItem("rememberMe");
        window.location.href = "/login";
        throw new Error("Session expired");
      }
    } else {
      // No refresh token, redirect to login
      localStorage.removeItem("token");
      localStorage.removeItem("rememberMe");
      window.location.href = "/login";
      throw new Error("Unauthorized");
    }
  }

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Request failed" }));

    // Create error object with proper structure
    const apiError: any = new Error(
      typeof error.detail === "string"
        ? error.detail
        : error.message || `Request failed with status ${response.status}`,
    );
    apiError.status = response.status;
    apiError.detail = error.detail;
    apiError.response = error;

    throw apiError;
  }

  return response.json();
}

/**
 * Login helper
 */
export async function login(username: string, password: string) {
  const formData = new URLSearchParams();
  formData.append("username", username);
  formData.append("password", password);

  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
    },
    body: formData.toString(),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ detail: "Login failed" }));
    throw new Error(error.detail || "Login failed");
  }

  return response.json();
}

/**
 * Get current user info
 */
export async function getCurrentUser() {
  return apiRequest("/api/auth/me");
}

/**
 * Logout helper
 */
export async function logout() {
  const refreshToken = localStorage.getItem("refresh_token");

  // Revoke refresh token on server if available
  if (refreshToken) {
    try {
      await apiRequest("/api/auth/logout", {
        method: "POST",
        body: JSON.stringify({ refresh_token: refreshToken }),
      });
    } catch (error) {
      // Ignore errors during logout
      console.error("Logout error:", error);
    }
  }

  localStorage.removeItem("token");
  localStorage.removeItem("refresh_token");
  localStorage.removeItem("rememberMe");
  window.location.href = "/login";
}

/**
 * Default API object with axios-like interface
 */
const api = {
  get: <T = any>(url: string, config?: RequestInit) =>
    apiRequest<T>(url, { ...config, method: "GET" }),

  post: <T = any>(url: string, data?: any, config?: RequestInit) =>
    apiRequest<T>(url, {
      ...config,
      method: "POST",
      body: data ? JSON.stringify(data) : undefined,
    }),

  put: <T = any>(url: string, data?: any, config?: RequestInit) =>
    apiRequest<T>(url, {
      ...config,
      method: "PUT",
      body: data ? JSON.stringify(data) : undefined,
    }),

  delete: <T = any>(url: string, config?: RequestInit) =>
    apiRequest<T>(url, { ...config, method: "DELETE" }),

  patch: <T = any>(url: string, data?: any, config?: RequestInit) =>
    apiRequest<T>(url, {
      ...config,
      method: "PATCH",
      body: data ? JSON.stringify(data) : undefined,
    }),
};

export default api;
