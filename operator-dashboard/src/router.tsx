import { createBrowserRouter, Navigate } from 'react-router-dom';
import { lazy, Suspense } from 'react';
import ProtectedRoute from '@/components/layout/ProtectedRoute';
import AppLayout from '@/components/layout/AppLayout';

// Lazy load page components for code splitting
const Login = lazy(() => import('@/pages/Login'));
const Overview = lazy(() => import('@/pages/Overview'));
const Projects = lazy(() => import('@/pages/Projects'));
const ProjectDetail = lazy(() => import('@/pages/ProjectDetail'));
const Deliverables = lazy(() => import('@/pages/Deliverables'));
const Wizard = lazy(() => import('@/pages/Wizard'));
const Settings = lazy(() => import('@/pages/Settings'));

// NEW: Priority 1 pages
const Clients = lazy(() => import('@/pages/Clients'));
const ClientDetail = lazy(() => import('@/pages/ClientDetail'));
const ContentReview = lazy(() => import('@/pages/ContentReview'));

// NEW: Priority 2 pages
const Analytics = lazy(() => import('@/pages/Analytics'));
const Calendar = lazy(() => import('@/pages/Calendar'));
const TemplateLibrary = lazy(() => import('@/pages/TemplateLibrary'));

// NEW: Priority 3 pages
const Team = lazy(() => import('@/pages/Team'));
const Notifications = lazy(() => import('@/pages/Notifications'));
const AuditTrail = lazy(() => import('@/pages/AuditTrail'));

// Loading fallback component
const PageLoader = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="text-center">
      <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
      <p className="mt-4 text-sm text-slate-600">Loading...</p>
    </div>
  </div>
);

// Wrapper to add Suspense boundary to lazy loaded components
const withSuspense = (Component: React.LazyExoticComponent<any>) => (
  <Suspense fallback={<PageLoader />}>
    <Component />
  </Suspense>
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
      { path: 'content', element: withSuspense(ContentReview) },
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
