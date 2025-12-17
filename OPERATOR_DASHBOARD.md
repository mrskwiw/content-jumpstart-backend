# Operator Dashboard

**Internal UI for Content Generation Workflow Management**

## Overview

The Operator Dashboard is the **internal operator UI** for managing the 30-Day Content Jumpstart content generation system. It provides a comprehensive interface for operators to manage projects, execute generation workflows, perform quality assurance, and deliver completed content to clients.

**Version:** 1.0 (Foundation)
**Status:** In Development
**Tech Stack:** React + TypeScript + Vite + Tailwind CSS
**Location:** `Project/operator-dashboard/`

---

## Key Distinction

**Operator Dashboard vs. Client Portal:**

| Feature | Operator Dashboard | Client Portal |
|---------|-------------------|---------------|
| **Purpose** | Internal operator workflow management | Client self-service |
| **Users** | Internal operators, content managers | External clients |
| **Access** | Internal network only | Public-facing |
| **Features** | Project creation, generation, QA, export | Brief submission, deliverable downloads |
| **Directory** | `operator-dashboard/` | `portal/` |
| **Status** | **Active Development** (Primary) | On hold |

**Use the Operator Dashboard for internal workflow management.**

---

## Architecture & Integration

### Tech Stack

- **Frontend:** React + TypeScript + Vite
- **Styling:** Tailwind CSS + shadcn/ui components
- **State Management:**
  - React Query for server state
  - Zustand for local UI state (filters, wizard progress)
- **Routing:** React Router v6 (nested routes under `/dashboard/*`)
- **API Client:** Axios with interceptors
- **Authentication:** JWT tokens with refresh

### Backend Integration

The dashboard assumes the following backend API endpoints exist:

**Projects API:**
- `GET /api/projects` - List all projects
- `POST /api/projects` - Create new project
- `GET /api/projects/:id` - Get project details
- `PATCH /api/projects/:id` - Update project

**Runs API:**
- `GET /api/runs` - List generation runs
- `POST /api/runs` - Create new run
- `GET /api/runs/:id` - Get run details

**Deliverables API:**
- `GET /api/deliverables` - List deliverables
- `PATCH /api/deliverables/:id/mark-delivered` - Mark as delivered

**Generator API:**
- `POST /api/generator/generate-all` - Generate all posts
- `POST /api/generator/regenerate` - Regenerate specific posts

**Research Tools API:**
- `GET /api/research/tools` - List available tools
- `POST /api/research/run` - Run research tool

**Audit API:**
- `GET /api/audit/:projectId` - Get audit trail
- `POST /api/audit` - Create audit entry

---

## Features

### Implemented Features

#### 1. Authentication & Layout
- JWT-based authentication with refresh tokens
- Protected routes with AuthContext
- Shared layout with sidebar and topbar
- Error boundary for crash recovery

#### 2. Dashboard
- Client search with typeahead
- Project filters (status, client name, date range)
- Projects table with status indicators
- Deliverables grouped by client with status chips
- "Mark Delivered" functionality

#### 3. Project Wizard (Multi-Step)

**Step 1: Client Profile**
- Zod-validated form
- Client name, business description, ideal customer
- Tone preferences, platform selection

**Step 2: Template Selection**
- Display 15 available templates
- Template count validation
- Preview template structure

**Step 3: Generation**
- "Generate All" button
- Real-time progress tracking
- Generation logs display
- Error handling

**Step 4: Quality Gate**
- Automated flagging:
  - Post length (too short/too long)
  - Readability score (Flesch Reading Ease)
  - Missing CTAs
  - Platform-specific requirements
- Bulk regenerate or targeted regenerate
- Quality notes and comments
- Block export if unresolved flags exist

**Step 5: Export**
- Format selection (TXT, DOCX)
- Option to include audit log
- Creates Deliverable record
- Logs AuditEntry for compliance

#### 4. Deliverables Management
- List view with filters
- Detail drawer showing:
  - File path
  - Run ID
  - Checksum (placeholder)
  - Status
- Mark Delivered dialog with:
  - Timestamp (default: now)
  - Proof URL
  - Delivery notes
  - Automatic audit logging

#### 5. Research Panel (Optional)
- Display available research tools
- Run research add-ons
- Attach outputs to project briefs
- View research run history

### Planned Features

#### Quality Gate Enhancements
- Custom readability thresholds
- Per-platform length bounds configuration
- AI-powered content suggestions
- Tone consistency scoring

#### Integration Features
- Direct integration with `03_post_generator.py`
- Real-time WebSocket updates for long-running tasks
- Batch operations for multiple projects

#### Advanced Analytics
- Template performance tracking
- Client satisfaction metrics
- Time-to-delivery analytics

---

## Directory Structure

```
operator-dashboard/
├── src/
│   ├── api/                    # API client modules
│   │   ├── auth.ts            # Authentication API
│   │   ├── client.ts          # Axios client setup
│   │   ├── projects.ts        # Projects API
│   │   ├── runs.ts            # Generation runs API
│   │   ├── deliverables.ts   # Deliverables API
│   │   ├── generator.ts       # Content generator API
│   │   ├── posts.ts           # Posts API
│   │   ├── research.ts        # Research tools API
│   │   └── audit.ts           # Audit trail API
│   │
│   ├── components/            # React components
│   │   ├── layout/
│   │   │   ├── AppLayout.tsx
│   │   │   └── ProtectedRoute.tsx
│   │   ├── wizard/
│   │   │   ├── WizardStepper.tsx
│   │   │   ├── GenerationPanel.tsx
│   │   │   ├── QualityGatePanel.tsx
│   │   │   └── ExportPanel.tsx
│   │   └── deliverables/
│   │       └── DeliverableDrawer.tsx
│   │
│   ├── contexts/              # React contexts
│   │   └── AuthContext.tsx   # Auth state management
│   │
│   ├── pages/                 # Page components
│   │   ├── Dashboard.tsx     # Main dashboard
│   │   ├── Login.tsx         # Login page
│   │   └── ProjectWizard.tsx # Project wizard
│   │
│   ├── types/                 # TypeScript types
│   │   └── models.ts         # Data models
│   │
│   ├── App.tsx               # Main app component
│   └── main.tsx              # Entry point
│
├── public/                    # Static assets
├── dist/                      # Build output
├── node_modules/             # Dependencies
│
├── components.json           # shadcn/ui config
├── eslint.config.js          # ESLint configuration
├── jest.config.cjs           # Jest testing config
├── jest.setup.ts             # Jest setup
├── package.json              # Dependencies
├── postcss.config.js         # PostCSS config
├── tailwind.config.js        # Tailwind config
├── tsconfig.json             # TypeScript config
├── vite.config.ts            # Vite config
│
├── IMPLEMENTATION_PLAN.md    # Detailed implementation plan
└── README.md                 # Setup & usage guide
```

---

## Setup & Installation

### Prerequisites

- Node.js 18+ and npm
- Backend API running (or mock API for development)

### Installation

```bash
# Navigate to operator-dashboard
cd Project/operator-dashboard

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Edit .env and set VITE_API_URL to your backend URL
```

### Environment Variables

Create `.env` file:

```bash
# Backend API URL
VITE_API_URL=http://localhost:8000

# Optional: Enable debug mode
VITE_DEBUG=true
```

### Development

```bash
# Start development server
npm run dev

# Application available at http://localhost:5173
```

### Building for Production

```bash
# Build optimized production bundle
npm run build

# Preview production build
npm run preview

# Output in dist/ directory
```

### Testing

```bash
# Run unit tests
npm run test

# Run tests with coverage
npm run test:coverage

# Run tests in watch mode
npm run test:watch
```

---

## Data Models

### Client
```typescript
interface Client {
  client_id: string;
  name: string;
  email: string;
  company: string;
  created_at: string;
}
```

### Project
```typescript
interface Project {
  project_id: string;
  client_id: string;
  client_name: string;
  status: 'draft' | 'processing' | 'qa_review' | 'ready' | 'delivered';
  package_tier: string;
  posts_count: number;
  created_at: string;
  last_run?: string;
}
```

### Run
```typescript
interface Run {
  run_id: string;
  project_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  posts_generated: number;
  started_at: string;
  completed_at?: string;
}
```

### PostDraft
```typescript
interface PostDraft {
  post_id: string;
  run_id: string;
  content: string;
  template_id: number;
  word_count: number;
  readability_score?: number;
  has_cta: boolean;
  platform: string;
  flags: QualityFlag[];
}
```

### Deliverable
```typescript
interface Deliverable {
  deliverable_id: string;
  project_id: string;
  run_id: string;
  file_path: string;
  format: 'txt' | 'docx';
  status: 'draft' | 'ready' | 'delivered';
  checksum?: string;
  created_at: string;
  delivered_at?: string;
  proof_url?: string;
  notes?: string;
}
```

### AuditEntry
```typescript
interface AuditEntry {
  audit_id: string;
  project_id: string;
  action: string;
  user_id: string;
  timestamp: string;
  details: Record<string, any>;
}
```

---

## Routing Structure

```
/                           → Redirect to /login or /dashboard
/login                      → Login page
/dashboard                  → Main dashboard (protected)
  /dashboard/projects       → Projects list
  /dashboard/wizard         → Project wizard
  /dashboard/deliverables   → Deliverables list
  /dashboard/research       → Research tools panel
  /dashboard/settings       → Settings (future)
```

---

## Service Modules

### API Services

All API calls are centralized in `src/api/`:

**Example: Projects Service**
```typescript
// src/api/projects.ts
import client from './client';

export const projectsApi = {
  list: async (clientName?: string) => {
    const response = await client.get('/api/projects', {
      params: { client_name: clientName }
    });
    return response.data;
  },

  create: async (data: CreateProjectRequest) => {
    const response = await client.post('/api/projects', data);
    return response.data;
  },

  getById: async (projectId: string) => {
    const response = await client.get(`/api/projects/${projectId}`);
    return response.data;
  }
};
```

### Guards & Validation

**Relative Path Guards:**
```typescript
// Prevent path traversal attacks
function validateRelativePath(path: string): boolean {
  return !path.includes('..') && !path.startsWith('/');
}
```

**Zod Schemas:**
```typescript
import { z } from 'zod';

export const ClientProfileSchema = z.object({
  client_name: z.string().min(1, "Client name required"),
  business_description: z.string().min(10),
  ideal_customer: z.string().min(10),
  tone_preference: z.enum(['professional', 'conversational', 'friendly']),
  platform: z.enum(['linkedin', 'twitter', 'facebook', 'blog'])
});
```

---

## Quality Gate System

### Automated Flags

The Quality Gate automatically flags posts that fail validation:

**Length Checks:**
- Too short: < 75 words
- Too long: > 350 words
- Platform-specific: e.g., Twitter > 280 chars

**Readability Checks:**
- Flesch Reading Ease score < threshold (configurable)
- Grade level too high for target audience

**CTA Checks:**
- Missing call-to-action
- Weak CTA (generic phrases)

**Platform Checks:**
- LinkedIn: Hook not in first 140 characters
- Twitter: Exceeds character limit
- Blog: Missing subheadings

### Regeneration Workflow

**Bulk Regenerate:**
1. Select all flagged posts
2. Click "Regenerate All"
3. System calls `/api/generator/regenerate` with post IDs
4. Progress bar shows regeneration status
5. New posts replace flagged posts
6. Quality gate re-runs validation

**Targeted Regenerate:**
1. Click "Regenerate" on specific post
2. Optional: Add regeneration notes
3. System regenerates single post
4. Post updated in UI
5. Validation re-runs

### Export Blocking

**Export is blocked if:**
- Any posts have unresolved flags
- Readability scores below threshold
- Missing required metadata

**Operator must:**
- Regenerate flagged posts, OR
- Add approval notes explaining why flags are acceptable

---

## Testing Strategy

### Unit Tests

Test individual components and services:

```typescript
// Example: service mapper test
describe('mapProjectResponse', () => {
  it('should map API response to UI model', () => {
    const apiResponse = { project_id: '123', ... };
    const uiModel = mapProjectResponse(apiResponse);
    expect(uiModel.projectId).toBe('123');
  });
});
```

### React Testing Library

Test UI components:

```typescript
import { render, screen } from '@testing-library/react';
import Dashboard from './Dashboard';

describe('Dashboard', () => {
  it('should render search input', () => {
    render(<Dashboard />);
    expect(screen.getByPlaceholderText('Search clients...')).toBeInTheDocument();
  });
});
```

### Integration Tests

Test complete workflows:

```typescript
describe('Project Wizard Flow', () => {
  it('should complete full workflow: create → generate → QA → export → deliver', async () => {
    // Mock service calls
    // Render wizard
    // Fill in client profile
    // Select templates
    // Click "Generate All"
    // Wait for completion
    // Check quality flags
    // Regenerate if needed
    // Export deliverable
    // Mark delivered
    // Verify audit entry created
  });
});
```

---

## Security

### Input Validation

- Zod schemas on all forms
- Sanitize rendered text (prevent XSS)
- Enforce relative paths (prevent traversal)

### Authentication

- JWT tokens stored in memory (not localStorage)
- Refresh token rotation
- Auto-logout on token expiry

### Authorization

- Role-based UI gating
- Least-privileged actions
- Audit logging for all mutations

### OWASP Compliance

- CSRF protection
- XSS prevention
- SQL injection prevention (backend)
- Secure headers

---

## Open Questions

From the implementation plan:

1. **Readability formula/threshold:** What Flesch Reading Ease score is acceptable? Currently using 60 (8th-9th grade).

2. **Per-platform length bounds:** Should we allow operators to configure min/max/optimal lengths per platform?

3. **Docx export:** Use server-side merge with `Jumpstart_Deliverable_Template.docx` or client-side generation?

4. **Data source:** Should API use SQLite, JSON adapters, or direct file system access for briefs/outputs?

5. **Roles/claims:** What granularity for feature gating? (e.g., operator, admin, super-admin)

6. **Audit retention:** How long to keep audit entries? Archive strategy?

7. **Delivery proof format:** URL only, or support file uploads?

---

## Build Order (TODO)

Per the implementation plan:

1. ✅ Add React Query provider + layout shell with nested routes
2. ✅ Integrate toasts/error boundary
3. ✅ Implement models and Zod schemas
4. ✅ Set up Zustand slices for filters/wizard
5. ✅ Add service modules (projects, runs, deliverables, audit, generator, research)
6. ⚠️ Replace placeholder Dashboard with search/filter, projects table, deliverables list
7. ⚠️ Build Project Wizard steps with validation, generation progress, quality gate
8. ⚠️ Add Deliverable detail drawer and status transitions
9. ⚠️ (Optional) Research panel
10. ⚠️ Testing: unit + RTL + integration

---

## Integration with Python Backend

The Operator Dashboard is designed to work with the Python backend from the main content generation system.

### Expected API Contract

**Generation Endpoint:**
```bash
POST /api/generator/generate-all
Content-Type: application/json

{
  "client_brief": { ... },
  "num_posts": 30,
  "platform": "linkedin",
  "templates": [1, 3, 5, ...]  # optional
}

Response:
{
  "run_id": "abc123",
  "posts": [ ... ],
  "status": "completed"
}
```

**Quality Check Endpoint:**
```bash
POST /api/qa/validate
Content-Type: application/json

{
  "posts": [ ... ]
}

Response:
{
  "overall_passed": true,
  "quality_score": 0.87,
  "issues": [
    { "post_id": "123", "flag": "too_short", "severity": "high" }
  ]
}
```

### CLI Integration

The dashboard can also trigger the CLI directly:

```typescript
// src/api/generator.ts
export const generateViaCLI = async (clientName: string, briefPath: string) => {
  const response = await client.post('/api/cli/generate', {
    command: `python 03_post_generator.py generate ${briefPath} -c "${clientName}"`
  });
  return response.data;
};
```

---

## Support & Documentation

**Primary Documentation:**
- `IMPLEMENTATION_PLAN.md` - Detailed implementation plan
- `README.md` - Setup & usage guide
- This file - Architecture & feature overview

**Related Documentation:**
- `../CLAUDE.md` - Repository guide
- `../Project/CLAUDE.md` - Python backend guide
- `../portal/README.md` - Client portal (different system)

**For Issues:**
- Check browser console for errors
- Review API network calls in DevTools
- Check backend logs for API errors
- Verify environment variables are set

---

## Deployment (Future)

### Production Build

```bash
npm run build
# Output: dist/
```

### Deployment Options

**Option 1: Static Hosting**
- Upload `dist/` to S3, Netlify, Vercel
- Configure redirects for SPA routing
- Set environment variables for production API

**Option 2: Docker**
```dockerfile
FROM node:18-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci --production
COPY . .
RUN npm run build
CMD ["npm", "run", "preview"]
```

**Option 3: Serve with Backend**
- Build frontend → `dist/`
- Serve from FastAPI static files:
  ```python
  from fastapi.staticfiles import StaticFiles
  app.mount("/", StaticFiles(directory="dist", html=True))
  ```

---

**Current Status:** Foundation Implemented
**Active Development:** Core features (Dashboard, Wizard, Quality Gate)
**Use Case:** Internal operator workflow for 30-Day Content Jumpstart system
