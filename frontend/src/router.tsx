import { createBrowserRouter } from 'react-router'
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
import { JoinPage } from './pages/JoinPage'
import { JournalPage } from './pages/JournalPage'
import { JournalPostPage } from './pages/JournalPostPage'
import { NotFoundPage } from './pages/NotFoundPage'
import { OpportunityPage } from './pages/OpportunityPage'
import { PrivacyPage } from './pages/PrivacyPage'
import { VisitPage } from './pages/VisitPage'

export const router = createBrowserRouter([
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
      { path: 'privacy', element: <PrivacyPage /> },
      { path: 'account', element: <AccountPage /> },
      { path: 'account/login', element: <LoginPage /> },
      { path: 'account/register', element: <RegisterPage /> },
      { path: 'account/verify', element: <VerifyEmailPage /> },
      { path: 'account/forgot', element: <ForgotPasswordPage /> },
      { path: 'account/reset', element: <ResetPasswordPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
