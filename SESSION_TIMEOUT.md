# Session Timeout Feature

## Overview
The application now includes an **activity-based session timeout** system that automatically logs users out after a period of inactivity.

## How It Works

### Session Duration
- **Inactivity Timeout**: 30 minutes
- **Warning Before Timeout**: 5 minutes (user gets notified at 25 minutes of inactivity)

### Activity Detection
The system monitors the following user activities:
- Mouse movements
- Mouse clicks
- Keyboard input
- Scrolling
- Touch events (for mobile devices)

### User Experience
1. **Active Session**: As long as the user interacts with the application, the session timer resets automatically
2. **Warning Notification**: After 25 minutes of inactivity, a warning notification appears: "Your session will expire in 5 minutes due to inactivity"
3. **Session Expiration**: After 30 minutes of total inactivity, the user is automatically logged out and redirected to the login page with a notification

## Configuration

You can adjust the timeout duration by modifying the constants in `/frontend/src/composables/useSessionTimeout.ts`:

```typescript
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes in milliseconds
const WARNING_TIME = 5 * 60 * 1000; // Warning shown 5 minutes before timeout
```

## Technical Implementation

### Files Modified/Created:
1. **`/frontend/src/composables/useSessionTimeout.ts`** (NEW)
   - Core composable that manages session timeout logic
   - Handles timer management and activity tracking
   - Integrates with notification system

2. **`/frontend/src/App.vue`** (MODIFIED)
   - Initializes the session timeout monitoring on app start
   - Ensures monitoring is active across all pages

### Key Features:
- ✅ Automatic timer reset on user activity
- ✅ Visual warning notifications before timeout
- ✅ Graceful session expiration with notification
- ✅ Automatic redirect to login page
- ✅ No impact on authenticated API calls
- ✅ Works seamlessly with existing authentication system

## Testing

To test the session timeout:

1. **Quick Test** (modify timeout values temporarily):
   ```typescript
   const INACTIVITY_TIMEOUT = 2 * 60 * 1000; // 2 minutes
   const WARNING_TIME = 30 * 1000; // 30 seconds warning
   ```

2. **Test Scenarios**:
   - Login and remain inactive for the timeout duration
   - Verify warning notification appears at the correct time
   - Move mouse or click - timer should reset
   - Let it expire - should redirect to login

## Benefits

1. **Security**: Prevents unauthorized access from unattended sessions
2. **User-Friendly**: Only logs out inactive users, not active ones
3. **Transparent**: Users get clear warnings before being logged out
4. **Configurable**: Easy to adjust timeout duration based on requirements
5. **Efficient**: Minimal performance impact, uses native browser APIs

## Future Enhancements

Potential improvements could include:
- Configurable timeout duration per user role
- "Stay Logged In" option on the warning notification
- Session extension API call to refresh server-side tokens
- Display remaining time in the warning notification
