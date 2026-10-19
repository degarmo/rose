import { SearchContent } from '@/components/members/app/SearchContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

/** Search as a page: on phones, and for anyone who opens the address directly. */
export function SearchPage() {
  useDocumentMeta({ title: 'Search', noindex: true })
  return (
    <div className="mx-auto flex w-full max-w-[600px] flex-col pt-4 md:pt-8">
      <h1 className="px-4 pb-4 text-base font-semibold text-fg md:text-2xl">Search</h1>
      <SearchContent />
    </div>
  )
}
