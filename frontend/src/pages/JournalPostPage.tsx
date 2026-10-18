import { ArrowLeft } from 'lucide-react'
import { useParams } from 'react-router'
import { PostView } from '@/components/content/PostView'
import { ErrorState, LoadingState } from '@/components/content/States'
import { ButtonLink, Section } from '@/components/ui'
import { api, ApiError } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from './NotFoundPage'

export function JournalPostPage() {
  const { slug = '' } = useParams()
  const state = useAsync(() => api.journalPost(slug), slug)
  useDocumentMeta({ title: 'Journal' })

  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) {
    return <NotFoundPage />
  }

  return (
    // Room for the post while it loads, so the footer does not jump.
    <Section width="default" className={state.status === 'loading' ? 'min-h-[100svh] pt-32' : 'pt-32'}>
      <ButtonLink to="/journal" variant="link" className="mb-8">
        <ArrowLeft aria-hidden="true" className="size-4" />
        Journal
      </ButtonLink>
      {state.status === 'loading' && <LoadingState label="Loading post" />}
      {state.status === 'error' && <ErrorState title="This post did not load" onRetry={state.retry} />}
      {state.status === 'success' && <PostView post={state.data} headingLevel="h1" />}
    </Section>
  )
}
