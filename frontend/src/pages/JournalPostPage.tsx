import { ArrowLeft } from 'lucide-react'
import { useParams } from 'react-router'
import { PostView } from '@/components/content/PostView'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, Section } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

/** One journal post on its own page (no design of its own: laid out like the Event detail body). */
export function JournalPostPage() {
  const { slug = '' } = useParams()
  const state = useAsync(() => api.journalPost(slug), slug)
  useDocumentMeta({ title: 'Journal' })

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) {
    return <NotFoundPage />
  }

  return (
    // Room for the post while it loads, so the footer does not jump.
    <Section spacing="none" className={cn('pb-10 pt-6 lg:pb-16 lg:pt-10', state.status === 'loading' && 'min-h-[100svh]')}>
      <ButtonLink to="/journal" variant="link" className="mb-5 lg:mb-8">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Journal
      </ButtonLink>
      {state.status === 'loading' && <LoadingState label="Loading post" />}
      {state.status === 'error' && <ErrorState title="This post did not load" onRetry={state.retry} />}
      {state.status === 'success' && (
        <div className="max-w-[1120px]">
          <PostView post={state.data} headingLevel="h1" />
        </div>
      )}
    </Section>
  )
}
