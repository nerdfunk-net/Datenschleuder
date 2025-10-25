# Stack

TypeScript, vue3, tailwind, fastapi, postgres

# general

This app has a web frontend and a python backend. The frontend is built with Vue 3 and TypeScript, using the Composition API. The backend is a FastAPI application.
The frontend and backend communicate via RESTful APIs. The frontend handles user interactions, state management, and rendering, while the backend manages data processing, storage, and business logic. The frontend should not call the backend directly, but instead use the provided API endpoints and vue as proxy.
THe frontend should be built with a focus on modularity, reusability, and maintainability. Use composables for shared logic and state management. Follow best practices for Vue 3 and TypeScript development.
Use the directory structure and coding standards outlined below.

# Directory Structure

```
./frontend
├── public/                 # Static assets (favicon, index.html, etc.)
├── src/
│   ├── assets/             # Images, fonts, and other static resources
│   ├── components/         # Reusable Vue components
│   ├── composables/        # Reusable logic and state management (useXxx.ts)
│   ├── views/              # Page-level components (routed views)
│   ├── layouts/            # Layout components (e.g., MainLayout.vue)
│   ├── stores/             # Pinia stores for global state management
│   ├── services/           # API calls and business logic
│   ├── router/             # Vue Router setup and route definitions
│   ├── styles/             # Global styles (e.g., Tailwind config, variables)
│   ├── utils/              # Utility functions and helpers
│   ├── App.vue             # Root Vue component
│   ├── main.ts             # Application entry point
├── tests/                  # Unit and integration tests
├── .eslintrc.js            # ESLint configuration
├── .prettierrc             # Prettier configuration
├── tsconfig.json           # TypeScript configuration
├── vite.config.ts          # Vite configuration
└── package.json            # Project metadata and dependencies

./backend
├── app/                    # Main application code
│   ├── api/                # API route definitions
│   ├── core/               # Core application logic (config, security, etc.)
│   ├── models/             # Database models and schemas
│   ├── services/           # Business logic and service layer
│   ├── utils/              # Utility functions and helpers
│   ├── main.py             # Application entry point
├── tests/                  # Unit and integration tests
├── .env                    # Environment variables
└── requirements.txt        # Python dependencies
```

# Project coding standards

## General Vue 3 + TypeScript Standards
- Enable full TypeScript support with `strict: true` in `tsconfig.json`.
- Prefer `defineProps` and `defineEmits` over the Options API style.
- Use `ref`, `reactive`, `computed`, and `watch` from `vue` for reactivity.
- Avoid using `any`; define or infer proper types wherever possible.

## Naming Conventions
- Use `PascalCase` for component names (e.g., `UserCard.vue`, `NavBar.vue`).
- Use `camelCase` for variables, props, emits, and composables.
- Prefix composable functions with `use` (e.g., `useAuth`, `useUserStore`).
- Use `UPPER_CASE` for constants and enums.

## Folder and Component Structure
- Structure by feature: group components, composables, stores, and assets by domain.
- Place shared components in a `components/` directory and composables in a `composables/` directory.
- Use `stores/` for Pinia stores or global state.
- Keep components focused—split large components into smaller parts.

## Code Quality and Maintainability
- Prefer composables for reusable logic and shared state.
- Avoid deeply nested reactivity—prefer computed properties or flattened state.
- Extract business logic from components into services or composables.
- Use `eslint` and `prettier` with Vue and TypeScript plugins for formatting and linting.
- Document props and emits clearly using JSDoc-style comments.

## Styling
- Use `:scoped` styles in SFCs to prevent global style conflicts.
- Prefer utility-first CSS (e.g., Tailwind CSS) or BEM naming if writing raw CSS/SCSS.
- Co-locate styles within components for maintainability.
- Use CSS variables for theme tokens and consistency.

## State Management
- Use **Pinia** for global state management.
- Define stores with `defineStore` and export composable-like hooks.
- Keep stores small and focused on a specific concern.
- Use `ref` and `computed` for reactive state inside stores.

## Testing
- Use `vitest` or `jest` with `@vue/test-utils` for unit and integration tests.
- Test components in isolation with mocked props, emits, and stores.
- Include tests for all major states: success, loading, and error.
- Use `msw` or custom mocks for API testing in complex components.

## Error Handling and Logging
- Use `try/catch` blocks around API calls or async operations.
- Display user-friendly error messages in the UI using modals, toasts, or banners.
- Use a centralized logging service or composable for app-wide error tracking.
- Avoid exposing raw error messages from APIs directly to users.

## Security Best Practices
- Avoid using `v-html` unless sanitized content is guaranteed.
- Never hardcode credentials, API keys, or tokens in code.
- Use environment variables securely and load them via `import.meta.env`.
- Validate and sanitize all form inputs and outputs.
- Use route guards and role-based access controls where needed.
