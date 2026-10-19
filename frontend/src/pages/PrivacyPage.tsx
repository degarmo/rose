import { CalendarCheck, EyeOff, FileText, HandCoins, Mail, ToggleLeft, Trash2, type LucideIcon } from 'lucide-react'
import { Copy } from '@/components/content/Copy'
import { PageHero } from '@/components/content/PageHero'
import { Section } from '@/components/ui'
import { usePageContent, type PageCopy } from '@/lib/pageContent'
import { useDocumentMeta } from '@/lib/useDocumentMeta'

// Icons for the sections, in order. Their words are editable copy (blocks.1 ...).
const BLOCK_ICONS: LucideIcon[] = [FileText, EyeOff, CalendarCheck, HandCoins, ToggleLeft, Trash2, Mail]

function Block({ copy, n, icon: Icon }: { copy: PageCopy; n: number; icon: LucideIcon }) {
  return (
    <section className="border-t border-border pt-10" aria-labelledby={`privacy-${n}`}>
      <h2 id={`privacy-${n}`} className="flex items-center gap-3 text-3xl text-fg">
        <Icon aria-hidden="true" className="size-6 text-highlight" strokeWidth={1.5} />
        <Copy copy={copy} k={`blocks.${n}.title`} as="span" />
      </h2>
      <Copy copy={copy} k={`blocks.${n}.body`} lines={4} className="mt-6 [&_li]:pl-1 [&_ul]:pl-5" />
    </section>
  )
}

export function PrivacyPage() {
  useDocumentMeta({
    title: 'Privacy',
    description: 'What we collect, what is never public, and how to ask us to delete your information.',
  })
  const copy = usePageContent('privacy')
  const blocks = copy.status === 'loading' ? [1, 2, 3] : copy.items('blocks')

  return (
    <>
      <PageHero copy={copy} placeholder="shadow" />
      <Section width="narrow">
        <div className="space-y-14">
          {blocks.map((n, index) => (
            <Block key={n} copy={copy} n={n} icon={BLOCK_ICONS[index % BLOCK_ICONS.length]} />
          ))}
        </div>
      </Section>
    </>
  )
}
