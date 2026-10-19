import { useParams } from 'react-router'
import { PhoneBar } from '@/components/members/app/Nav'
import { PostDetail } from '@/components/members/app/PostDetail'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

/** Post detail as a page (design: "Post detail · phone"), and for anyone who opens the address directly. */
export function PostPage() {
  useDocumentMeta({ title: 'Post', noindex: true })
  const { id = '' } = useParams()
  return (
    <>
      <PhoneBar back title="Post" rule />
      <div className="mx-auto w-full max-w-[470px] pb-6 md:pt-6">
        <PostDetail key={id} id={id} layout="page" notFound={<NotFoundPage />} />
      </div>
    </>
  )
}
