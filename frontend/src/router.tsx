import type { ComponentType } from 'react'
import { createBrowserRouter, Navigate } from 'react-router'
import { Layout } from './components/layout/Layout'
import { AccountMoved } from './pages/account/AccountMoved'
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
    children: [
      // The door: the feed, joining, or a short explanation (never a bare dead end).
      { index: true, lazy: members((m) => m.MembersEntryPage) },
      // The emailed download link: the token is the credential, so it opens signed in or out.
      { path: 'settings/privacy/export', lazy: members((m) => m.ExportDownloadPage) },
      {
        lazy: members((m) => m.AppShell),
        children: [
          { path: 'feed', lazy: members((m) => m.FeedPage) },
          { path: 'explore', lazy: members((m) => m.ExplorePage) },
          { path: 'search', lazy: members((m) => m.SearchPage) },
          { path: 'notifications', lazy: members((m) => m.NotificationsPage) },
          { path: 'p/:id', lazy: members((m) => m.PostPage) },
          { path: 'u/:handle', lazy: members((m) => m.MemberProfilePage) },
          { path: 'u/:handle/saved', lazy: members((m) => m.MemberProfilePage) },
          { path: 'saved', lazy: members((m) => m.SavedPage) },
          // The account screens: open to every signed-in person, feed or not.
          { path: 'home', lazy: members((m) => m.HomePage) },
          { path: 'settings', lazy: members((m) => m.SettingsPage) },
          { path: 'settings/:section', lazy: members((m) => m.SettingsPage) },
          { path: 'settings/membership/receipts/:id', lazy: members((m) => m.ReceiptPage) },
          { path: 'report', lazy: members((m) => m.ReportConcernPage) },
          // The staff section: team roles only, after the staff two-step login.
          { path: 'staff', lazy: members((m) => m.StaffIndexPage) },
          { path: 'staff/door', lazy: members((m) => m.StaffDoorPage) },
          { path: 'staff/reports', lazy: members((m) => m.StaffReportsPage) },
          { path: 'staff/reports/:id', lazy: members((m) => m.StaffReportPage) },
          { path: 'staff/appeals/:id', lazy: members((m) => m.StaffAppealPage) },
          { path: 'staff/members', lazy: members((m) => m.StaffMembersPage) },
          { path: 'staff/members/:handle', lazy: members((m) => m.StaffMemberPage) },
          { path: 'staff/team', lazy: members((m) => m.StaffTeamPage) },
          // The old address of member search.
          { path: 'directory', element: <Navigate to="/members/search" replace /> },
          { path: '*', element: <NotFoundPage /> },
        ],
      },
    ],
  },
  {
    element: <Layout />,
    children: [
      { index: true, element: <HomePage /> },
      { path: 'about', lazy: page(() => import('./pages/AboutPage').then((m) => m.AboutPage)) },
      { path: 'about/staff', lazy: page(() => import('./pages/StaffPage').then((m) => m.StaffPage)) },
      { path: 'guests', lazy: page(() => import('./pages/GuestsPage').then((m) => m.GuestsPage)) },
      { path: 'faq', lazy: page(() => import('./pages/FAQPage').then((m) => m.FAQPage)) },
      { path: 'house-rules', lazy: page(() => import('./pages/HouseRulesPage').then((m) => m.HouseRulesPage)) },
      { path: 'rentals', lazy: page(() => import('./pages/RentalsPage').then((m) => m.RentalsPage)) },
      { path: 'get-involved/volunteer', lazy: page(() => import('./pages/VolunteerPage').then((m) => m.VolunteerPage)) },
      { path: 'get-involved/donate', lazy: page(() => import('./pages/DonatePage').then((m) => m.DonatePage)) },
      { path: 'subscribe/confirm', lazy: page(() => import('./pages/SubscriptionPages').then((m) => m.ConfirmSubscriptionPage)) },
      { path: 'unsubscribe', lazy: page(() => import('./pages/SubscriptionPages').then((m) => m.UnsubscribePage)) },
      // The old Gallery lives on as the journal (the server answers /gallery with a 301 too).
      { path: 'gallery', element: <Navigate to="/journal" replace /> },
      { path: 'events', lazy: page(() => import('./pages/EventsPage').then((m) => m.EventsPage)) },
      { path: 'events/cancel', lazy: page(() => import('./pages/CancelRSVPPage').then((m) => m.CancelRSVPPage)) },
      { path: 'events/:slug', lazy: page(() => import('./pages/EventPage').then((m) => m.EventPage)) },
      { path: 'education', lazy: page(() => import('./pages/EducationPage').then((m) => m.EducationPage)) },
      { path: 'education/:slug', lazy: page(() => import('./pages/OpportunityPage').then((m) => m.OpportunityPage)) },
      { path: 'journal', lazy: page(() => import('./pages/JournalPage').then((m) => m.JournalPage)) },
      { path: 'journal/:slug', lazy: page(() => import('./pages/JournalPostPage').then((m) => m.JournalPostPage)) },
      { path: 'visit', lazy: page(() => import('./pages/VisitPage').then((m) => m.VisitPage)) },
      { path: 'contact', lazy: page(() => import('./pages/ContactPage').then((m) => m.ContactPage)) },
      { path: 'report-a-concern', lazy: page(() => import('./pages/ConcernPage').then((m) => m.ConcernPage)) },
      { path: 'membership', lazy: page(() => import('./pages/MembershipPage').then((m) => m.MembershipPage)) },
      { path: 'join', lazy: page(() => import('./pages/join/JoinPage').then((m) => m.JoinPage)) },
      { path: 'join/confirming', lazy: page(() => import('./pages/join/ConfirmingPage').then((m) => m.ConfirmingPage)) },
      // Development only: the API behind it answers 404 unless DEBUG and the sandbox are on.
      { path: 'dev/checkout/:token', lazy: page(() => import('./pages/join/SandboxCheckoutPage').then((m) => m.default)) },
      { path: 'privacy', lazy: page(() => import('./pages/PrivacyPage').then((m) => m.PrivacyPage)) },
      // The old account page moved into the member app's Settings.
      { path: 'account', element: <AccountMoved to="settings" /> },
      { path: 'account/notices', element: <AccountMoved to="notices" /> },
      { path: 'account/export', element: <AccountMoved to="export" /> },
      { path: 'account/receipts/:id', element: <AccountMoved to="receipt" /> },
      { path: 'account/login', lazy: page(() => import('./pages/account/LoginPage').then((m) => m.LoginPage)) },
      { path: 'account/register', lazy: page(() => import('./pages/account/RegisterPage').then((m) => m.RegisterPage)) },
      { path: 'account/verify', lazy: page(() => import('./pages/account/VerifyEmailPage').then((m) => m.VerifyEmailPage)) },
      { path: 'account/forgot', lazy: page(() => import('./pages/account/ForgotPasswordPage').then((m) => m.ForgotPasswordPage)) },
      { path: 'account/reset', lazy: page(() => import('./pages/account/ResetPasswordPage').then((m) => m.ResetPasswordPage)) },
      { path: 'members/join-feed', lazy: members((m) => m.JoinFeedPage) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
