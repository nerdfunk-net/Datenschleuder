import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useNotificationsStore } from '@/stores/notifications';

/**
 * Session timeout configuration (in milliseconds)
 * Note: Access tokens expire after 30 minutes on the backend
 * We'll refresh them automatically on user activity
 */
const TOKEN_REFRESH_INTERVAL = 25 * 60 * 1000; // Refresh token every 25 minutes (5 min before expiry)
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes of inactivity
const WARNING_TIME = 5 * 60 * 1000; // Show warning 5 minutes before inactivity timeout

/**
 * Refresh the access token using the refresh token
 */
async function refreshToken(): Promise<void> {
  const refreshToken = localStorage.getItem('refresh_token');

  if (!refreshToken) {
    return;
  }

  try {
    const response = await fetch(`/api/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (response.ok) {
      const data = await response.json();
      localStorage.setItem('token', data.access_token);
      if (data.refresh_token) {
        localStorage.setItem('refresh_token', data.refresh_token);
      }
    }
  } catch (error) {
    console.error('Failed to refresh token:', error);
  }
}

/**
 * Composable for managing session timeout based on user activity
 * Automatically refreshes tokens on activity and redirects to login on inactivity
 */
export function useSessionTimeout() {
  const router = useRouter();
  const notificationsStore = useNotificationsStore();
  const inactivityTimer = ref<number | null>(null);
  const warningTimer = ref<number | null>(null);
  const tokenRefreshTimer = ref<number | null>(null);
  const isWarningShown = ref(false);
  const lastActivityTime = ref<number>(Date.now());

  /**
   * Events that indicate user activity
   */
  const activityEvents = [
    'mousedown',
    'mousemove',
    'keypress',
    'scroll',
    'touchstart',
    'click',
  ];

  /**
   * Clear existing timers
   */
  const clearTimers = () => {
    if (inactivityTimer.value) {
      window.clearTimeout(inactivityTimer.value);
      inactivityTimer.value = null;
    }
    if (warningTimer.value) {
      window.clearTimeout(warningTimer.value);
      warningTimer.value = null;
    }
    if (tokenRefreshTimer.value) {
      window.clearTimeout(tokenRefreshTimer.value);
      tokenRefreshTimer.value = null;
    }
    isWarningShown.value = false;
  };

  /**
   * Handle session timeout - logout and redirect to login
   */
  const handleTimeout = () => {
    localStorage.removeItem('token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('rememberMe');
    clearTimers();

    // Show notification before redirect
    notificationsStore.warning('Your session has expired due to inactivity. Please login again.', {
      title: 'Session Expired',
      duration: 3000,
    });

    // Small delay to show the notification
    setTimeout(() => {
      router.push({ name: 'login' });
    }, 500);
  };

  /**
   * Show warning before timeout
   */
  const showWarning = () => {
    isWarningShown.value = true;
    
    notificationsStore.warning('Your session will expire in 5 minutes due to inactivity. Move your mouse or click anywhere to stay logged in.', {
      title: 'Session Warning',
      duration: 10000, // Show warning for 10 seconds
    });
  };

  /**
   * Reset the inactivity timer
   * Called on every user activity
   */
  const resetTimer = () => {
    // Only reset if user is authenticated
    const token = localStorage.getItem('token');
    const refreshTokenValue = localStorage.getItem('refresh_token');
    if (!token) {
      return;
    }

    const now = Date.now();
    const timeSinceLastActivity = now - lastActivityTime.value;
    lastActivityTime.value = now;

    // Clear existing timers
    clearTimers();

    // If user was active and it's been more than 25 minutes since last activity,
    // refresh the access token proactively
    if (refreshTokenValue && timeSinceLastActivity > TOKEN_REFRESH_INTERVAL) {
      refreshToken();
    }

    // Set token refresh timer (25 minutes from now)
    if (refreshTokenValue) {
      tokenRefreshTimer.value = window.setTimeout(() => {
        refreshToken();
      }, TOKEN_REFRESH_INTERVAL);
    }

    // Set warning timer (5 minutes before inactivity timeout)
    warningTimer.value = window.setTimeout(() => {
      showWarning();
    }, INACTIVITY_TIMEOUT - WARNING_TIME);

    // Set inactivity timeout
    inactivityTimer.value = window.setTimeout(() => {
      handleTimeout();
    }, INACTIVITY_TIMEOUT);
  };

  /**
   * Initialize session timeout monitoring
   */
  const startMonitoring = () => {
    // Only monitor if user is authenticated
    const token = localStorage.getItem('token');
    if (!token) {
      return;
    }

    // Initial timer setup
    resetTimer();

    // Add event listeners for user activity
    activityEvents.forEach((event) => {
      window.addEventListener(event, resetTimer, true);
    });
  };

  /**
   * Stop session timeout monitoring
   */
  const stopMonitoring = () => {
    clearTimers();
    
    // Remove event listeners
    activityEvents.forEach((event) => {
      window.removeEventListener(event, resetTimer, true);
    });
  };

  /**
   * Lifecycle hooks
   */
  onMounted(() => {
    startMonitoring();
  });

  onUnmounted(() => {
    stopMonitoring();
  });

  return {
    resetTimer,
    startMonitoring,
    stopMonitoring,
    isWarningShown,
  };
}
