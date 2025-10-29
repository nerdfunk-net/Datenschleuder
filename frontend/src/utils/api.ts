/**
 * API utility for making authenticated requests to the backend
 */

const API_BASE_URL = "http://localhost:8000";

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

  const response = await fetch(url, {
    ...options,
    headers,
  });

  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    localStorage.removeItem("token");
    localStorage.removeItem("rememberMe");
    window.location.href = "/login";
    throw new Error("Unauthorized");
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
export function logout() {
  localStorage.removeItem("token");
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
