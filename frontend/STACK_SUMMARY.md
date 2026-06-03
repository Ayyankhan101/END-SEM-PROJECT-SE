# Frontend Stack Summary

This file explains the frontend stack used in `frontend/`, why each dependency was chosen instead of common alternatives, the main functionalities, and how the pieces work together.

## 1. Build Tool

- **Vite 5**
- **Why used:** much faster than Create React App or raw Webpack for development. It supports native ESM, instant hot module replacement (HMR), and optimized production builds with minimal configuration.
- **Alternative:** CRA/Webpack.
  - CRA is slower to start and rebuild.
  - Webpack requires more manual configuration.
- **Role:** powers development server, asset bundling, module resolution, and output generation.

## 2. Language

- **TypeScript 5.3**
- **Why used:** adds compile-time type checking, improves IDE autocomplete, catches type mismatches early, and makes refactoring safer.
- **Alternative:** plain JavaScript.
  - JavaScript is easier to start with but has weaker guarantees and less tooling support for large apps.
- **Role:** ensures consistent data shapes for components, API payloads, hooks, and shared types.

## 3. UI Framework

- **React 18**
- **Why used:** component-based architecture, a large ecosystem, declarative UI, fiber renderer with concurrent features.
- **Alternative:** Vue, Angular, Svelte.
  - Vue/Angular are also capable, but this project already adopts React patterns in code.
  - Svelte is lighter but has a different learning curve and a smaller React-like ecosystem.
- **Role:** builds pages and reusable UI elements across the app.

## 4. Routing

- **react-router-dom 6**
- **Why used:** declarative client-side routing with nested routes, route guards, and easy integration with React components.
- **Alternative:** Remix/Next.js routing, manual history handling.
  - Those are heavier or require different app structure.
- **Role:** enables `/login`, `/containers`, `/alerts`, `/topology`, and protected routes.

## 5. HTTP Client

- **Axios 1.6**
- **Why used:** easy promise API, built-in JSON handling, interceptors for JWT refresh and request/response handling.
- **Alternative:** fetch API.
  - `fetch` works, but Axios simplifies error handling and supports interceptors more cleanly.
- **Role:** communicates with backend API routes under `/api`, attaches auth tokens, and centralizes request logic.

## 6. Styling

- **Tailwind CSS 3**
- **Why used:** utility-first CSS that enables rapid UIs, consistent spacing/colors, and tree-shaking of unused styles.
- **Alternative:** CSS modules, styled-components, plain CSS.
  - Tailwind reduces custom CSS boilerplate and keeps styles close to markup.
- **Role:** styles buttons, layouts, responsiveness, and themes with low code overhead.

## 7. Charts / Visualization

- **Recharts 2**
- **Why used:** declarative chart components for React, good default visuals, easy integration with data arrays.
- **Alternative:** Chart.js, D3, Victory.
  - Chart.js is less React idiomatic.
  - D3 is powerful but more complex for simple dashboards.
- **Role:** renders dashboard KPIs, metrics, and trend charts.

## 8. Icons

- **Lucide React**
- **Why used:** lightweight, tree-shakeable icons with simple JSX usage.
- **Alternative:** Font Awesome, Heroicons.
  - Lucide is smaller and easier to customize inline.
- **Role:** provides UI icons for navigation, buttons, status badges, and actions.

## 9. Real-time Communication

- **socket.io-client 4**
- **Why used:** reliable WebSocket abstraction with auto-reconnect and fallback transports.
- **Alternative:** native WebSocket.
  - Native websockets require more manual reconnection and event handling.
- **Role:** streams live container/host metrics, updates UI state in real time, and keeps dashboards fresh.

## 10. 3D Visualization

- **three** + **@react-three/fiber**
- **Why used:** GPU-accelerated 3D rendering in browser, React-friendly wrapper through `@react-three/fiber`.
- **Alternative:** plain Canvas/SVG, 2D visualizations.
  - Three.js enables interactive topology views that 2D tools can’t match easily.
- **Role:** renders the `/topology` 3D cluster view and interactive node layouts.

## 11. Terminal Emulator

- **xterm.js** + **@xterm/addon-fit**
- **Why used:** in-browser terminal with ANSI support, resizing, shell-like behavior.
- **Alternative:** custom text area or no terminal.
  - Custom terminal lacks compatibility with real shell output.
- **Role:** allows container shell access and interactive command sessions.

## 12. Code Editor

- **@monaco-editor/react**
- **Why used:** embeds Monaco editor (same engine as VS Code) with syntax highlighting and editing features.
- **Alternative:** CodeMirror.
  - CodeMirror is also solid but Monaco gives a VS Code-like experience and multi-language support.
- **Role:** edits config files, YAML compose stacks, and other code-like content in the browser.

## 13. Testing

- **Vitest**
- **Why used:** native Vite compatibility, fast test execution, built-in watch mode.
- **Alternative:** Jest.
  - Jest is mature but slower and requires more configuration with Vite.
- **Role:** runs unit/integration tests, especially for components and services.

- **Testing Library**
- **Why used:** tests React components by user behavior, not implementation details.
- **Alternative:** Enzyme.
  - Enzyme is outdated for React 18 and less aligned with modern testing practices.
- **Role:** verifies UI flows, component interactions, and accessibility.

## 14. Virtualized List

- **Virtua**
- **Why used:** renders only visible rows for very large lists, avoiding DOM performance issues.
- **Alternative:** plain mapping over arrays.
  - Plain rendering of thousands of items can become slow or crash the browser.
- **Role:** efficiently displays large container or host lists in UI pages.

## 15. Authentication

- **JWT-based auth stored in localStorage**
- **Why used:** simple token-based auth for SPA, works with backend JWT access and refresh flow.
- **Alternative:** cookie-based sessions.
  - Cookie sessions can be more secure but require backend session management and same-site cookie handling.
- **Role:** manages login, token storage, protected routes, and automatic refresh on 401 responses.

## 16. State Management

- **React Context** for global auth state
- **Why used:** sufficient for app-wide auth and theme state without introducing Redux or MobX.
- **Alternative:** Redux, Zustand.
  - Redux is more powerful but heavier and adds boilerplate.
- **Role:** stores current user, tokens, auth status, and provides state to protected components.

- **Component-local state** for page-level UI interactions
- **Role:** handles form state, filters, modal visibility, and local UI controls.

## 17. Project Structure

- `src/components/` — reusable UI pieces like cards, tables, layout wrappers
- `src/pages/` — route-level pages such as Dashboard, Containers, Alerts, Security, Topology
- `src/services/` — API client setup, Axios interceptors, request helpers
- `src/contexts/` — React providers for auth/theme/notifications
- `src/hooks/` — custom hooks for WebSocket, fetch logic, and shared behaviors
- `src/types/` — app-specific TypeScript definitions
- `src/utils/` — helper functions, formatters, and shared utilities

## 18. Routes and Functionality

The frontend is organized around protected SPA routes:

- `/login` — login screen, auth flow, token handling
- `/` — dashboard overview with KPIs and summary charts
- `/containers` — list and manage containers, search/filter, health status
- `/container/:id` — container detail, logs, actions, shell access
- `/hosts` — host management and resource overview
- `/alerts` — alert history and notifications
- `/alert-rules` — configure alert conditions
- `/schedules` — schedule container actions
- `/stacks` — manage Docker Compose stacks
- `/security` — scanner and CVE analysis
- `/ai` — AI-generated insights and analysis
- `/topology` — interactive 3D cluster visualization
- `/backup` — backup operations and restore management
- `/audit` — audit logging and history
- `/settings` — theme, notifications, application preferences
- `/users` — user/admin management where applicable
- `/docker` — resources like images and volumes
- `/notifications` — notification channels and webhooks

## 19. How it all comes together

1. **Startup:** `main.tsx` mounts React and wraps the app in providers.
2. **Routing:** `App.tsx` defines routes with `react-router-dom` and protects them through auth logic.
3. **Auth:** login stores JWT in `localStorage`; `AuthContext` exposes user state.
4. **API:** Axios instance in `src/services/` adds auth headers and refresh behavior.
5. **Live updates:** `socket.io-client` connects to backend socket endpoints, updating container/metric state in real time.
6. **UI:** React pages consume API data, hooks, and contexts to display dashboards, lists, and details.
7. **Styling:** Tailwind classes give consistent responsive styling across components.
8. **Advanced features:** Xterm handles container shell access, Monaco editor edits config content, and Three.js renders topology.
9. **Build:** Vite bundles the app for production into `dist`, using the proxy config during development so `/api` and `/ws` go to the backend.

## 20. Summary

This frontend is designed as a modern React SPA with strong developer experience and fast iteration. The stack choices prioritize:

- speed (`Vite`, `React`)
- developer safety (`TypeScript`, `Vitest`)
- real-time operations (`socket.io-client`)
- rich UI experiences (`Tailwind`, `Recharts`, `Monaco`, `xterm.js`, `Three.js`)
- simplicity in state handling (React Context instead of Redux)

If you want, I can also create a shorter one-page version or map each stack item to the exact files where it is used.