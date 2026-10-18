import type { ComponentType } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { Layout } from './components/layout/Layout'
import { AboutPage } from './pages/AboutPage'
import { AccountPage } from './pages/account/AccountPage'
import { ForgotPasswordPage } from './pages/account/ForgotPasswordPage'
import { LoginPage } from './pages/account/LoginPage'
import { RegisterPage } from './pages/account/RegisterPage'
import { ResetPasswordPage } from './pages/account/ResetPasswordPage'
import { VerifyEmailPage } from './pages/account/VerifyEmailPage'
import { CancelRSVPPage } from './pages/CancelRSVPPage'
import { ContactPage } from './pages/ContactPage'
import { EducationPage } from './pages/EducationPage'
import { EventPage } from './pages/EventPage'
import { EventsPage } from './pages/EventsPage'
import { HomePage } from './pages/HomePage'
import { ConfirmingPage } from './pages/join/ConfirmingPage'
import { JoinPage } from './pages/join/JoinPage'
import { JournalPage } from './pages/JournalPage'
import { JournalPostPage } from './pages/JournalPostPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OpportunityPage } from './pages/OpportunityPage'
import { PrivacyPage } from './pages/PrivacyPage'
import { VisitPage } from './pages/VisitPage'

// The members area loads on demand, so public visitors never download its code.
const membersPage = (load: () => Promise<{ default: ComponentType }>) => async () => ({
  Component: (await load()).default,
})

export const router = createBrowserRouter([
  {
    path: 'members',
    lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.MembersLayout }))),
    children: [
      { index: true, element: <Navigate to="/members/feed" replace /> },
      { path: 'feed', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.FeedPage }))) },
      { path: 'p/:id', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.PostPage }))) },
      { path: 'u/:handle', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.MemberProfilePage }))) },
      { path: 'directory', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.DirectoryPage }))) },
      { path: 'notifications', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.NotificationsPage }))) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', element: <AboutPage /> },
      { path: 'events', element: <EventsPage /> },
      { path: 'events/cancel', element: <CancelRSVPPage /> },
      { path: 'events/:slug', element: <EventPage /> },
      { path: 'education', element: <EducationPage /> },
      { path: 'education/:slug', element: <OpportunityPage /> },
      { path: 'journal', element: <JournalPage /> },
      { path: 'journal/:slug', element: <JournalPostPage /> },
      { path: 'visit', element: <VisitPage /> },
      { path: 'contact', element: <ContactPage /> },
      { path: 'join', element: <JoinPage /> },
      { path: 'join/confirming', element: <ConfirmingPage /> },
      // Development only: the API behind it answers 404 unless DEBUG and the sandbox are on.
      { path: 'dev/checkout/:token', lazy: membersPage(() => import('./pages/join/SandboxCheckoutPage')) },
      { path: 'privacy', element: <PrivacyPage /> },
      { path: 'account', element: <AccountPage /> },
      { path: 'account/login', element: <LoginPage /> },
      { path: 'account/register', element: <RegisterPage /> },
      { path: 'account/verify', element: <VerifyEmailPage /> },
      { path: 'account/forgot', element: <ForgotPasswordPage /> },
      { path: 'account/reset', element: <ResetPasswordPage /> },
      { path: 'account/receipts/:id', lazy: membersPage(() => import('./pages/account/ReceiptPage')) },
      { path: 'account/export', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.ExportDownloadPage }))) },
      { path: 'members/join-feed', lazy: membersPage(() => import('./pages/members/lazy').then((m) => ({ default: m.JoinFeedPage }))) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
