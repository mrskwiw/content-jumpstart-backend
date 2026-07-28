/* eslint-disable react-refresh/only-export-components -- route config module: exports the `router` object (non-component) by design (HMR/DX rule, not correctness). */
import { createBrowserRouter, Navigate, useLocation } from 'react-router-dom';
import { Suspense } from 'react';
import ProtectedRoute from '@/components/layout/ProtectedRoute';
import RootRedirect from '@/components/RootRedirect';
import AppLayout from '@/components/layout/AppLayout';
import { lazyWithRetry } from '@/utils/chunkRetry';
import { ErrorBoundary } from '@/components/ErrorBoundary';

// Lazy load page components with automatic retry on chunk load failures
const Login = lazyWithRetry(() => import('@/pages/Login'));
const ForgotPassword = lazyWithRetry(() => import('@/pages/ForgotPassword'));
const ResetPassword = lazyWithRetry(() => import('@/pages/ResetPassword'));
const PortfolioNotice = lazyWithRetry(() => import('@/pages/PortfolioNotice'));
const Overview = lazyWithRetry(() => import('@/pages/Overview'));
const Projects = lazyWithRetry(() => import('@/pages/Projects'));
const ProjectDetail = lazyWithRetry(() => import('@/pages/ProjectDetail'));
const Deliverables = lazyWithRetry(() => import('@/pages/Deliverables'));
const Wizard = lazyWithRetry(() => import('@/pages/Wizard'));
const Settings = lazyWithRetry(() => import('@/pages/Settings'));

// NEW: Priority 1 pages
const Clients = lazyWithRetry(() => import('@/pages/Clients'));
const NewClient = lazyWithRetry(() => import('@/pages/NewClient'));
const ClientDetail = lazyWithRetry(() => import('@/pages/ClientDetail'));
const KeywordEditor = lazyWithRetry(() => import('@/pages/KeywordEditor'));
const ContentReview = lazyWithRetry(() => import('@/pages/ContentReview'));

// NEW: Priority 2 pages
const Analytics = lazyWithRetry(() => import('@/pages/Analytics'));
const Calendar = lazyWithRetry(() => import('@/pages/Calendar'));
const TemplateLibrary = lazyWithRetry(() => import('@/pages/TemplateLibrary'));

// Distribution (Phase 10) + Engagement analytics (Phase 11)
const Connections = lazyWithRetry(() => import('@/pages/Distribution/Connections'));
const PublishingQueue = lazyWithRetry(() => import('@/pages/Distribution/Queue'));
const Engagement = lazyWithRetry(() => import('@/pages/Engagement'));

// Media generation (Phase 12)
const MediaGenerate = lazyWithRetry(() => import('@/pages/Media/Generate'));
const MediaJobs = lazyWithRetry(() => import('@/pages/Media/Jobs'));

// NEW: Priority 3 pages
const Team = lazyWithRetry(() => import('@/pages/Team'));
const Notifications = lazyWithRetry(() => import('@/pages/Notifications'));
const AuditTrail = lazyWithRetry(() => import('@/pages/AuditTrail'));

// Research Tools pages
const ResearchToolsLibrary = lazyWithRetry(() => import('@/pages/ResearchTools/Library'));
const ResearchToolsResults = lazyWithRetry(() => import('@/pages/ResearchTools/Results'));
const ResearchToolsAnalytics = lazyWithRetry(() => import('@/pages/ResearchTools/Analytics'));
const ResearchToolsClientResearch = lazyWithRetry(() => import('@/pages/ResearchTools/ClientResearch'));

// Settings pages
const SettingsIntegrations = lazyWithRetry(() => import('@/pages/Settings/Integrations'));

// Payment pages
const PaymentSuccess = lazyWithRetry(() => import('@/pages/PaymentSuccess'));

// Legal pages
const PrivacyPolicy = lazyWithRetry(() => import('@/pages/PrivacyPolicy'));
const TermsOfService = lazyWithRetry(() => import('@/pages/TermsOfService'));
const CookiePolicy = lazyWithRetry(() => import('@/pages/CookiePolicy'));
const RefundPolicy = lazyWithRetry(() => import('@/pages/RefundPolicy'));

// Loading fallback component
const PageLoader = () => (
  <div className="flex h-screen items-center justify-center">
    <div className="text-center">
      <div className="inline-block h-8 w-8 animate-spin rounded-full border-4 border-solid border-blue-600 border-r-transparent"></div>
      <p className="mt-4 text-sm text-slate-600">Loading...</p>
    </div>
  </div>
);

// Resets the boundary when the route changes. Because every route reuses the
// same <RouteBoundary> element at the same tree position, React keeps a single
// ErrorBoundary instance mounted across navigation; keying its reset on
// location.pathname clears a prior page's crash instead of poisoning the SPA.
const RouteBoundary = ({ children }: { children: React.ReactNode }) => {
  const location = useLocation();
  return <ErrorBoundary resetKey={location.pathname}>{children}</ErrorBoundary>;
};

// Wrapper to add Suspense and ErrorBoundary to lazy loaded components
const withSuspense = (Component: React.LazyExoticComponent<React.ComponentType>) => (
  <RouteBoundary>
    <Suspense fallback={<PageLoader />}>
      <Component />
    </Suspense>
  </RouteBoundary>
);

export const router = createBrowserRouter([
  {
    path: '/',
    element: <RootRedirect />,
  },
  {
    path: '/login',
    element: withSuspense(Login),
  },
  {
    path: '/forgot-password',
    element: withSuspense(ForgotPassword),
  },
  {
    path: '/reset-password',
    element: withSuspense(ResetPassword),
  },
  {
    path: '/portfolio-notice',
    element: withSuspense(PortfolioNotice),
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
      { path: 'clients/new', element: withSuspense(NewClient) },
      { path: 'clients/:clientId', element: withSuspense(ClientDetail) },
      { path: 'clients/:clientId/keywords', element: withSuspense(KeywordEditor) },
      { path: 'content-review', element: withSuspense(ContentReview) },
      { path: 'deliverables', element: withSuspense(Deliverables) },
      { path: 'analytics', element: withSuspense(Analytics) },
      { path: 'engagement', element: withSuspense(Engagement) },
      { path: 'media/generate', element: withSuspense(MediaGenerate) },
      { path: 'media/jobs', element: withSuspense(MediaJobs) },
      { path: 'distribution/queue', element: withSuspense(PublishingQueue) },
      { path: 'settings/connections', element: withSuspense(Connections) },
      { path: 'calendar', element: withSuspense(Calendar) },
      { path: 'templates', element: withSuspense(TemplateLibrary) },
      { path: 'team', element: withSuspense(Team) },
      { path: 'notifications', element: withSuspense(Notifications) },
      { path: 'audit', element: withSuspense(AuditTrail) },
      { path: 'wizard', element: withSuspense(Wizard) },
      { path: 'settings', element: withSuspense(Settings) },
      { path: 'settings/integrations', element: withSuspense(SettingsIntegrations) },
      // Research Tools section
      { path: 'research-tools/library', element: withSuspense(ResearchToolsLibrary) },
      { path: 'research-tools/results', element: withSuspense(ResearchToolsResults) },
      { path: 'research-tools/analytics', element: withSuspense(ResearchToolsAnalytics) },
      { path: 'research-tools/client-research', element: withSuspense(ResearchToolsClientResearch) },
    ],
  },
  {
    path: '/payment-success',
    element: withSuspense(PaymentSuccess),
  },
  {
    path: '/privacy',
    element: withSuspense(PrivacyPolicy),
  },
  {
    // Back-compat alias for the original route.
    path: '/privacy-policy',
    element: <Navigate to="/privacy" replace />,
  },
  {
    path: '/terms',
    element: withSuspense(TermsOfService),
  },
  {
    path: '/cookies',
    element: withSuspense(CookiePolicy),
  },
  {
    // Back-compat alias.
    path: '/cookie-policy',
    element: <Navigate to="/cookies" replace />,
  },
  {
    path: '/refund',
    element: withSuspense(RefundPolicy),
  },
  {
    path: '*',
    element: <Navigate to="/" replace />,
  },
]);
