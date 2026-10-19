import { useNavigate } from 'react-router'
import { SearchContent } from '@/components/members/app/SearchContent'
import { useMediaQuery, MEDIA } from '@/components/members/app/useMediaQuery'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/**
 * Search as a page: on phones (design: the field and Cancel in the top bar), and for
 * anyone who opens the address directly on a larger screen.
 */
export function SearchPage() {
  useDocumentMeta({ title: 'Search', noindex: true })
  const navigate = useNavigate()
  const tablet = useMediaQuery(MEDIA.tablet)
  if (!tablet) {
    return (
      <div className="flex flex-col pt-1">
        <h1 className="sr-only">Search</h1>
        <SearchContent autoFocus onCancel={() => navigate('/members/feed')} />
      </div>
    )
  }
  return (
    <div className="mx-auto flex w-full max-w-[600px] flex-col pt-8">
      <h1 className="px-6 text-2xl font-semibold text-fg">Search</h1>
      <SearchContent />
    </div>
  )
}
