import { NotificationsContent } from '@/components/members/app/NotificationsContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Notifications as a page: on phones, and for anyone who opens the address directly. */
export function NotificationsPage() {
  useDocumentMeta({ title: 'Notifications', noindex: true })
  return (
    <div className="mx-auto w-full max-w-[600px] pt-4 md:pt-8">
      <h1 className="px-6 text-base font-semibold text-fg md:text-2xl">Notifications</h1>
      <p className="px-6 pt-1 text-fg-muted">Only here, never by email.</p>
      <NotificationsContent />
    </div>
  )
}
