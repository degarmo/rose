import { createBrowserRouter } from 'react-router'
import { Layout } from './components/layout/Layout'
import { AboutPage } from './pages/AboutPage'
import { ContactPage } from './pages/ContactPage'
import { EducationPage } from './pages/EducationPage'
import { HomePage } from './pages/HomePage'
import { JoinPage } from './pages/JoinPage'
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
      { path: 'education', element: <EducationPage /> },
      { path: 'education/:slug', element: <OpportunityPage /> },
      { path: 'visit', element: <VisitPage /> },
      { path: 'contact', element: <ContactPage /> },
      { path: 'join', element: <JoinPage /> },
      { path: 'privacy', element: <PrivacyPage /> },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
])
