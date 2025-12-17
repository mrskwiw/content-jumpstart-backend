# Content Jumpstart Portal - Frontend

React + TypeScript + Vite frontend for the Content Jumpstart operator dashboard.

## Status

**Foundation Complete** ✅
- React + TypeScript + Vite setup
- Tailwind CSS styling
- React Router navigation
- Axios API client with automatic token refresh
- Authentication context
- Protected routes
- Login and Registration pages
- Basic dashboard layout

## Tech Stack

- **Framework:** React 18 + TypeScript
- **Build Tool:** Vite
- **Routing:** React Router v6
- **HTTP Client:** Axios
- **State Management:** React Query (TanStack Query)
- **Styling:** Tailwind CSS
- **Forms:** React Hook Form + Zod validation
- **Icons:** Lucide React

## Getting Started

### Prerequisites

- Node.js 18+ and npm
- Backend API running at `http://localhost:8000`

### Installation

```bash
# Navigate to frontend directory
cd project/portal/frontend

# Install dependencies
npm install

# Start development server
npm run dev
```

The app will be available at `http://localhost:3000`.

## Project Structure

```
frontend/
├── src/
│   ├── components/      # Reusable UI components
│   │   └── ProtectedRoute.tsx  # Auth guard for routes
│   ├── contexts/        # React contexts
│   │   └── AuthContext.tsx     # Authentication state
│   ├── lib/             # Utilities and configurations
│   │   └── api.ts               # API client and endpoints
│   ├── pages/           # Page components
│   │   ├── LoginPage.tsx
│   │   ├── RegisterPage.tsx
│   │   ├── DashboardPage.tsx
│   │   ├── ProjectsPage.tsx      # TODO
│   │   ├── ProjectDetailPage.tsx # TODO
│   │   └── NewProjectPage.tsx    # TODO
│   ├── App.tsx          # Main app with routing
│   ├── main.tsx         # Entry point
│   └── index.css        # Global styles
├── public/              # Static assets
├── index.html           # HTML template
├── package.json         # Dependencies
├── vite.config.ts       # Vite configuration
├── tailwind.config.js   # Tailwind configuration
└── tsconfig.json        # TypeScript configuration
```

## API Integration

The frontend connects to the FastAPI backend via the `api` object in `src/lib/api.ts`.

### Available API Functions

**Authentication:**
- `api.register(data)` - Create new account
- `api.login(email, password)` - Sign in

**Projects:**
- `api.getProjects(statusFilter?)` - List projects
- `api.getProject(projectId)` - Get project details
- `api.createProject(data)` - Create new project
- `api.updateProjectStatus(projectId, status)` - Update status
- `api.getProjectDashboard(projectId)` - Get dashboard stats

**Briefs:**
- `api.getBrief(briefId)` - Get brief
- `api.submitBrief(projectId, data)` - Submit brief
- `api.updateBrief(briefId, data)` - Update brief

**File Uploads:**
- `api.uploadFile(projectId, file, fileType)` - Upload file
- `api.getProjectFiles(projectId)` - List files
- `api.deleteFile(fileId)` - Delete file

**Deliverables:**
- `api.getProjectDeliverables(projectId)` - List deliverables
- `api.getDeliverable(deliverableId)` - Get deliverable metadata
- `api.downloadDeliverable(deliverableId)` - Download file

### Automatic Token Refresh

The API client automatically handles token refresh:
1. If a request returns 401, it attempts to refresh the access token
2. If refresh succeeds, the original request is retried
3. If refresh fails, the user is redirected to login

## Authentication Flow

1. **User logs in** → Receives access token (30 min) + refresh token (7 days)
2. **Tokens stored** in localStorage
3. **API requests** include access token in Authorization header
4. **Token expires** → Automatic refresh using refresh token
5. **Refresh fails** → Redirect to login

## Development Tasks

### Completed ✅
- [x] Project setup (Vite + React + TypeScript)
- [x] Tailwind CSS configuration
- [x] API client with token refresh
- [x] Authentication context
- [x] Protected routes
- [x] Login page
- [x] Registration page
- [x] Basic dashboard layout

### Next Steps 🚧
- [ ] Install npm dependencies (`npm install`)
- [ ] Build project list view with filtering and sorting
- [ ] Create project detail page with stats cards
- [ ] Implement brief submission form
- [ ] Build file upload interface with drag-and-drop
- [ ] Create deliverables download page
- [ ] Add loading states and error handling
- [ ] Implement responsive design for mobile
- [ ] Add analytics dashboard (if Phase 11 complete)
- [ ] Build revision management interface (Week 4)

## Available Scripts

```bash
# Start development server
npm run dev

# Build for production
npm run build

# Preview production build
npm run preview

# Run linter
npm run lint
```

## Environment Variables

No environment variables needed for development (proxies to localhost:8000).

For production deployment, configure the API base URL in `src/lib/api.ts`.

## Deployment

```bash
# Build production bundle
npm run build

# Output will be in dist/
# Serve with any static hosting service
```

The frontend is a static SPA that can be deployed to:
- Vercel
- Netlify
- AWS S3 + CloudFront
- GitHub Pages
- Any static hosting

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Contributing

This is part of the 30-Day Content Jumpstart system.

See main project documentation in `../../PHASE_12_PORTAL_PLAN.md`.

---

**Status:** Foundation Complete (Day 1 of Frontend Development)
**Next Milestone:** Complete project list and detail views
