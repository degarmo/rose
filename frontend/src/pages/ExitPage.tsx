import { useEffect } from 'react'

/** Deliberately generic: no name, no branding, nothing that hints at the site. */
export function ExitPage() {
  useEffect(() => {
    document.title = 'Page unavailable'
    document.head.querySelector('meta[name="robots"]')?.setAttribute('content', 'noindex, nofollow')
    document.head.querySelector('meta[name="description"]')?.setAttribute('content', '')
    document.head.querySelector('meta[name="theme-color"]')?.setAttribute('content', '#ffffff')
  }, [])

  return (
    <main className="flex min-h-dvh items-center justify-center bg-white px-6 font-sans text-neutral-700">
      <div className="max-w-sm text-center">
        <h1 className="font-sans text-xl font-medium text-neutral-900">This page is not available.</h1>
        <p className="mt-3 text-sm leading-relaxed">You can close this tab.</p>
      </div>
    </main>
  )
}
