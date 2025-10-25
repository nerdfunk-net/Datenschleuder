/**
 * API utility for making authenticated requests to the backend
 */

const API_BASE_URL = 'http://localhost:8000'

/**
 * Make an authenticated API request
 */
export async function apiRequest<T = any>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const token = localStorage.getItem('token')

  const headers: HeadersInit = {
    'Content-Type': 'application/json',
    ...options.headers,
  }

  // Add authorization header if token exists
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`

  const response = await fetch(url, {
    ...options,
    headers,
  })

  // Handle 401 Unauthorized - redirect to login
  if (response.status === 401) {
    localStorage.removeItem('token')
    localStorage.removeItem('rememberMe')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Request failed' }))
    throw new Error(error.detail || `Request failed with status ${response.status}`)
  }

  return response.json()
}

/**
 * Login helper
 */
export async function login(username: string, password: string) {
  const formData = new URLSearchParams()
  formData.append('username', username)
  formData.append('password', password)

  const response = await fetch(`${API_BASE_URL}/api/auth/login`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded',
    },
    body: formData.toString(),
  })

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Login failed' }))
    throw new Error(error.detail || 'Login failed')
  }

  return response.json()
}

/**
 * Get current user info
 */
export async function getCurrentUser() {
  return apiRequest('/api/auth/me')
}

/**
 * Logout helper
 */
export function logout() {
  localStorage.removeItem('token')
  localStorage.removeItem('rememberMe')
  window.location.href = '/login'
}
