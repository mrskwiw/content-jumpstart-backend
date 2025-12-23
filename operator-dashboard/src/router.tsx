import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Suspense } from 'react';
import ProtectedRoute from '@/components/layout/ProtectedRoute';
import AppLayout from '@/components/layout/AppLayout';
import { lazyWithRetry } from '@/utils/chunkRetry';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Lazy load page components with automatic retry on chunk load failures
const Login = lazyWithRetry(() => import('@/pages/Login'));
const Overview = lazyWithRetry(() => import('@/pages/Overview'));
const Projects = lazyWithRetry(() => import('@/pages/Projects'));
const ProjectDetail = lazyWithRetry(() => import('@/pages/ProjectDetail'));
const Deliverables = lazyWithRetry(() => import('@/pages/Deliverables'));
const Wizard = lazyWithRetry(() => import('@/pages/Wizard'));
const Settings = lazyWithRetry(() => import('@/pages/Settings'));

// NEW: Priority 1 pages
const Clients = lazyWithRetry(() => import('@/pages/Clients'));
const ClientDetail = lazyWithRetry(() => import('@/pages/ClientDetail'));
const ContentReview = lazyWithRetry(() => import('@/pages/ContentReview'));

// NEW: Priority 2 pages
const Analytics = lazyWithRetry(() => import('@/pages/Analytics'));
const Calendar = lazyWithRetry(() => import('@/pages/Calendar'));
const TemplateLibrary = lazyWithRetry(() => import('@/pages/TemplateLibrary'));

// NEW: Priority 3 pages
const Team = lazyWithRetry(() => import('@/pages/Team'));
const Notifications = lazyWithRetry(() => import('@/pages/Notifications'));
const AuditTrail = lazyWithRetry(() => import('@/pages/AuditTrail'));

// Loading fallback component
const PageLoader = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="text-center">
      <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
      <p className="mt-4 text-sm text-slate-600">Loading...</p>
    </div>
  </div>
);

// Wrapper to add Suspense and ErrorBoundary to lazy loaded components
const withSuspense = (Component: React.LazyExoticComponent<any>) => (
  <ErrorBoundary>
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  </ErrorBoundary>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Navigate to="/dashboard" replace />,
  },
  {
    path: '/login',
    element: withSuspense(Login),
  },
  {
    path: '/dashboard',
    element: (
      <ProtectedRoute>
        <AppLayout />
      </ProtectedRoute>
    ),
    children: [
      { index: true, element: withSuspense(Overview) },
      { path: 'projects', element: withSuspense(Projects) },
      { path: 'projects/:projectId', element: withSuspense(ProjectDetail) },
      { path: 'clients', element: withSuspense(Clients) },
      { path: 'clients/:clientId', element: withSuspense(ClientDetail) },
      { path: 'content-review', element: withSuspense(ContentReview) },
      { path: 'deliverables', element: withSuspense(Deliverables) },
      { path: 'analytics', element: withSuspense(Analytics) },
      { path: 'calendar', element: withSuspense(Calendar) },
      { path: 'templates', element: withSuspense(TemplateLibrary) },
      { path: 'team', element: withSuspense(Team) },
      { path: 'notifications', element: withSuspense(Notifications) },
      { path: 'audit', element: withSuspense(AuditTrail) },
      { path: 'wizard', element: withSuspense(Wizard) },
      { path: 'settings', element: withSuspense(Settings) },
    ],
  },
  {
    path: '*',
    element: <Navigate to="/dashboard" replace />,
  },
]);
