# Datenschleuder Frontend

A modern Vue 3 + TypeScript frontend for the Datenschleuder flow management platform.

## Features

- **Authentication**: Secure login with JWT token management
- **Flow Management**: Create, edit, and manage data flows with filtering and pagination
- **Flow Deployment**: Deploy flows with real-time status updates
- **Settings Management**: Configure NiFi, Registry, Data Format, and Profile settings
- **Modern UI**: Built with Bootstrap 5, Vue 3, and TypeScript

## Tech Stack

- Vue 3 with Composition API
- TypeScript
- Vue Router 4
- Pinia (State Management)
- Bootstrap 5 + Bootstrap Vue Next
- Vite (Build Tool)
- SCSS for styling

## Project Structure

```
frontend/
├── src/
│   ├── pages/              # Application pages
│   │   ├── Login.vue       # Login page
│   │   ├── flows/          # Flow management pages
│   │   │   ├── Manage.vue  # Flow management table
│   │   │   └── Deploy.vue  # Flow deployment
│   │   └── settings/       # Settings pages
│   │       ├── Nifi.vue
│   │       ├── Registry.vue
│   │       ├── DataFormat.vue
│   │       └── Profile.vue
│   ├── Layout/             # Layout components
│   │   └── DashboardLayout.vue  # Main dashboard layout
│   ├── router/             # Vue Router configuration
│   ├── stores/             # Pinia stores
│   ├── assets/             # Static assets and styles
│   └── main.ts             # Application entry point
├── public/                 # Public static files
└── package.json            # Dependencies and scripts
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

```bash
cd frontend
npm install
```

### Development

Start the development server:

```bash
npm run dev
```

The application will be available at `http://localhost:8087`

### Building for Production

```bash
npm run build
```

The production build will be created in the `dist/` directory.

### Preview Production Build

```bash
npm run preview
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint
- `npm run format` - Format code with Prettier
- `npm run type-check` - Run TypeScript type checking

## Authentication

The app uses JWT token-based authentication. Tokens are stored in localStorage and automatically included in API requests to the backend via the `/api/proxy/` endpoint.

### Development Login

For testing and development purposes, a temporary login bypass is available:

- **Username:** `admin`
- **Password:** `admin`

⚠️ This bypass will be removed once the backend authentication is integrated.

### Authentication Flow

1. User enters credentials on login page
2. Frontend sends POST request to `/api/proxy/auth/login`
3. Backend validates credentials and returns JWT token
4. Token is stored in localStorage
5. Router guards check for token before allowing access to protected routes
6. Token is sent with all API requests in Authorization header

## API Integration

All API calls are proxied through `/api/proxy/[...path]` which forwards requests to the FastAPI backend. This is configured in the project according to the architecture guidelines.

### Example API Call

```typescript
const response = await fetch('/api/proxy/flows', {
  method: 'GET',
  headers: {
    'Authorization': `Bearer ${localStorage.getItem('token')}`
  }
})
```

## Routes

### Public Routes
- `/login` - Login page

### Protected Routes (require authentication)
- `/flows/manage` - Flow management table
- `/flows/deploy` - Flow deployment interface
- `/settings/nifi` - NiFi settings
- `/settings/registry` - Registry settings
- `/settings/data-format` - Data format settings
- `/settings/profile` - User profile settings

## Styling

The app uses a modern, light theme with grey and blue colors:
- Primary color: #4a90e2 (blue)
- Background: #f5f7fa (light grey)
- Sidebar: Dark gradient (#2c3e50 to #34495e)

Custom styles are written in SCSS and follow a component-scoped approach.

## Development Notes

- All components use Vue 3 Composition API with `<script setup>`
- TypeScript is used for type safety
- Components are lazy-loaded for better performance
- Authentication state is managed via localStorage
- Router guards prevent unauthorized access

## TODO

The following features are marked with `TODO` comments and need backend integration:

1. **Authentication**: Connect to actual backend authentication endpoint
2. **Flow Management**: Implement real API calls for CRUD operations
3. **Flow Deployment**: Connect to backend deployment API
4. **Settings**: Implement settings persistence via backend
5. **Error Handling**: Add comprehensive error handling and user feedback

## License

© 2025 Datenschleuder. All rights reserved.
