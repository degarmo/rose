import { useState } from 'react'
import { ConcernForm } from '@/components/content/ConcernForm'
import { PhoneBar } from '@/components/members/app/Nav'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** In the app: report something that happened at an event. Posts, comments and profiles
 * are reported from their own menus. */
export function ReportConcernPage() {
  useDocumentMeta({ title: 'Report a concern', noindex: true })
  const [sent, setSent] = useState(false)
  return (
    <>
      <PhoneBar back title={<h1 className="truncate text-base font-semibold">Report a concern</h1>} />
      <div className="mx-auto w-full max-w-[632px] px-4 pb-10 pt-4 md:pt-10">
        <h1 className="hidden pb-2 text-xl font-semibold text-fg md:block">Report a concern</h1>
        <p className="pb-6 text-fg-muted">
          Something that happened at an event or the club. The person you mention is never told who wrote, and you will see when it has been reviewed.
        </p>
        {sent ? (
          <p role="status" className="rounded-app bg-surface p-4 text-fg">
            Thank you. Our team has it. You can see when it has been reviewed on your account page.
          </p>
        ) : (
          <ConcernForm onSent={() => setSent(true)} submitClass="self-start" />
        )}
      </div>
    </>
  )
}
