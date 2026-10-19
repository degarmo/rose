import { useEffect, type ReactNode } from 'react'
import { Outlet, ScrollRestoration, useLocation } from 'react-router'
import { isPrivatePath } from '@/lib/useDocumentMeta'
import { Footer } from './Footer'
import { Header } from './Header'

/** The website's header, main area and footer, around `children`. */
export function SiteFrame({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className="flex-1">
        {children}
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  )
}

export function Layout() {
  const { pathname } = useLocation()

  useEffect(() => {
    if (isPrivatePath(pathname)) {
      document.head.querySelector('meta[name="robots"]')?.setAttribute('content', 'noindex, nofollow')
    }
  }, [pathname])

  return (
    <SiteFrame>
      <Outlet />
    </SiteFrame>
  )
}
