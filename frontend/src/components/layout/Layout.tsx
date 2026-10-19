import { useEffect } from 'react'
import { Outlet, ScrollRestoration, useLocation } from 'react-router'
import { isPrivatePath } from '@/lib/useDocumentMeta'
import { Footer } from './Footer'
import { Header } from './Header'

export function Layout() {
  const { pathname } = useLocation()

  useEffect(() => {
    if (isPrivatePath(pathname)) {
      document.head.querySelector('meta[name="robots"]')?.setAttribute('content', 'noindex, nofollow')
    }
  }, [pathname])

  return (
    <div className="flex min-h-dvh flex-col">
      <Header />
      <main id="main" className="flex-1">
        <Outlet />
      </main>
      <Footer />
      <ScrollRestoration />
    </div>
  )
}
