import { PhoneBar } from '@/components/members/app/Nav'
import { NotificationsContent } from '@/components/members/app/NotificationsContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Notifications as a page: on phones, and for anyone who opens the address directly. */
export function NotificationsPage() {
  useDocumentMeta({ title: 'Notifications', noindex: true })
  return (
    <>
      <PhoneBar back title={<h1 className="truncate text-base font-semibold">Notifications</h1>} />
      <div className="mx-auto w-full max-w-[600px] md:pt-8">
        <h1 className="hidden px-6 pb-4 text-2xl font-semibold text-fg md:block">Notifications</h1>
        <NotificationsContent />
      </div>
    </>
  )
}
