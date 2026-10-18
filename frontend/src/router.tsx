import type { ComponentType } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { Layout } from './components/layout/Layout'
import { HomePage } from './pages/HomePage'
import { NotFoundPage } from './pages/NotFoundPage'

/**
 * Every page except the home page loads on demand, so the first visit only
 * downloads what it shows. The members area is one chunk of its own, so public
 * visitors never download its code.
 */
const page = (load: () => Promise<ComponentType>) => async () => ({ Component: await load() })
const members = (pick: (module: typeof import('./pages/members/lazy')) => ComponentType) =>
  page(() => import('./pages/members/lazy').then(pick))

export const router = createBrowserRouter([
  {
    path: 'members',
    lazy: members((m) => m.MembersLayout),
    children: [
      { index: true, element: <Navigate to="/members/feed" replace /> },
      { path: 'feed', lazy: members((m) => m.FeedPage) },
      { path: 'p/:id', lazy: members((m) => m.PostPage) },
      { path: 'u/:handle', lazy: members((m) => m.MemberProfilePage) },
      { path: 'directory', lazy: members((m) => m.DirectoryPage) },
      { path: 'notifications', lazy: members((m) => m.NotificationsPage) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', lazy: page(() => import('./pages/AboutPage').then((m) => m.AboutPage)) },
      { path: 'events', lazy: page(() => import('./pages/EventsPage').then((m) => m.EventsPage)) },
      { path: 'events/cancel', lazy: page(() => import('./pages/CancelRSVPPage').then((m) => m.CancelRSVPPage)) },
      { path: 'events/:slug', lazy: page(() => import('./pages/EventPage').then((m) => m.EventPage)) },
      { path: 'education', lazy: page(() => import('./pages/EducationPage').then((m) => m.EducationPage)) },
      { path: 'education/:slug', lazy: page(() => import('./pages/OpportunityPage').then((m) => m.OpportunityPage)) },
      { path: 'journal', lazy: page(() => import('./pages/JournalPage').then((m) => m.JournalPage)) },
      { path: 'journal/:slug', lazy: page(() => import('./pages/JournalPostPage').then((m) => m.JournalPostPage)) },
      { path: 'visit', lazy: page(() => import('./pages/VisitPage').then((m) => m.VisitPage)) },
      { path: 'contact', lazy: page(() => import('./pages/ContactPage').then((m) => m.ContactPage)) },
      { path: 'join', lazy: page(() => import('./pages/join/JoinPage').then((m) => m.JoinPage)) },
      { path: 'join/confirming', lazy: page(() => import('./pages/join/ConfirmingPage').then((m) => m.ConfirmingPage)) },
      // Development only: the API behind it answers 404 unless DEBUG and the sandbox are on.
      { path: 'dev/checkout/:token', lazy: page(() => import('./pages/join/SandboxCheckoutPage').then((m) => m.default)) },
      { path: 'privacy', lazy: page(() => import('./pages/PrivacyPage').then((m) => m.PrivacyPage)) },
      { path: 'account', lazy: page(() => import('./pages/account/AccountPage').then((m) => m.AccountPage)) },
      { path: 'account/login', lazy: page(() => import('./pages/account/LoginPage').then((m) => m.LoginPage)) },
      { path: 'account/register', lazy: page(() => import('./pages/account/RegisterPage').then((m) => m.RegisterPage)) },
      { path: 'account/verify', lazy: page(() => import('./pages/account/VerifyEmailPage').then((m) => m.VerifyEmailPage)) },
      { path: 'account/forgot', lazy: page(() => import('./pages/account/ForgotPasswordPage').then((m) => m.ForgotPasswordPage)) },
      { path: 'account/reset', lazy: page(() => import('./pages/account/ResetPasswordPage').then((m) => m.ResetPasswordPage)) },
      { path: 'account/receipts/:id', lazy: page(() => import('./pages/account/ReceiptPage').then((m) => m.default)) },
      { path: 'account/export', lazy: members((m) => m.ExportDownloadPage) },
      { path: 'members/join-feed', lazy: members((m) => m.JoinFeedPage) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
