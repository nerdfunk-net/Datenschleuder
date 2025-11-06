import { ref, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';
import { useNotificationsStore } from '@/stores/notifications';

/**
 * Session timeout configuration (in milliseconds)
 * Default: 30 minutes of inactivity
 */
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes
const WARNING_TIME = 5 * 60 * 1000; // Show warning 5 minutes before timeout

/**
 * Composable for managing session timeout based on user activity
 * Automatically redirects to login when session expires due to inactivity
 */
export function useSessionTimeout() {
  const router = useRouter();
  const notificationsStore = useNotificationsStore();
  const inactivityTimer = ref<number | null>(null);
  const warningTimer = ref<number | null>(null);
  const isWarningShown = ref(false);

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
    isWarningShown.value = false;
  };

  /**
   * Handle session timeout - logout and redirect to login
   */
  const handleTimeout = () => {
    localStorage.removeItem('token');
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
    if (!token) {
      return;
    }

    // Clear existing timers
    clearTimers();

    // Set warning timer (5 minutes before timeout)
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
