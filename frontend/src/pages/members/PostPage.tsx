import { ArrowLeft } from 'lucide-react'
import { useNavigate, useParams } from 'react-router'
import { PostDetail } from '@/components/members/app/PostDetail'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

/** One post as its own page: phones, and anyone who opens the address directly. */
export function PostPage() {
  useDocumentMeta({ title: 'Post', noindex: true })
  const { id = '' } = useParams()
  const navigate = useNavigate()
  return (
    <div className="mx-auto w-full max-w-[470px] px-3 pb-6 sm:px-0 md:pt-8">
      <div className="-mx-3 mb-1 flex h-11 items-center border-b border-border px-1 sm:mx-0">
        <button
          type="button"
          onClick={() => (window.history.length > 1 ? navigate(-1) : navigate('/members/feed'))}
          className="inline-flex size-10 items-center justify-center text-fg"
        >
          <ArrowLeft aria-hidden="true" className="size-6" strokeWidth={1.75} />
          <span className="sr-only">Back</span>
        </button>
        <p className="flex-1 pr-10 text-center text-base font-semibold text-fg">Post</p>
      </div>
      <PostDetail key={id} id={id} layout="page" notFound={<NotFoundPage />} />
    </div>
  )
}
