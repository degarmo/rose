import type { ElementType } from 'react'
import { cn } from '@/lib/cn'
import type { PageCopy } from '@/lib/pageContent'
import { SectionHeading } from '../ui'
import { RICH_TEXT } from './richText'

interface CopyProps {
  copy: PageCopy
  /** The content key, e.g. "hero.title". */
  k: string
  as?: ElementType
  className?: string
  id?: string
  /** Skeleton lines shown while the page's copy loads. */
  lines?: number
}

/**
 * One piece of staff-editable copy. Formatted values were sanitised on the
 * server; plain values keep their line breaks. While loading it shows a
 * skeleton of about the right size; a missing key renders nothing.
 */
export function Copy({ copy, k, as: Tag = 'p', className, id, lines = 1 }: CopyProps) {
  if (copy.status === 'loading') return <CopySkeleton lines={lines} className={className} />
  const entry = copy.entry(k)
  if (!entry || !entry.value) return null
  if (entry.format === 'rich') {
    // Formatted copy may hold paragraphs, which cannot sit inside a <p>.
    const RichTag = Tag === 'p' ? 'div' : Tag
    const prose = RichTag === 'div'
    return (
      <RichTag
        id={id}
        className={cn(prose ? RICH_TEXT : '[&_em]:text-link', className)}
        // Sanitised on the server (nh3) to a small allow-list of tags.
        dangerouslySetInnerHTML={{ __html: entry.value }}
      />
    )
  }
  return (
    <Tag id={id} className={cn('whitespace-pre-line', className)}>
      {entry.value}
    </Tag>
  )
}

export function CopySkeleton({ lines = 1, className }: { lines?: number; className?: string }) {
  return (
    <span aria-hidden="true" className={cn('block animate-pulse', className)}>
      {Array.from({ length: lines }, (_, index) => (
        <span
          key={index}
          className={cn('mb-2 block h-[1em] rounded bg-surface', index === lines - 1 && lines > 1 ? 'w-2/3' : 'w-full')}
        />
      ))}
    </span>
  )
}

interface CopyHeadingProps {
  copy: PageCopy
  /** Reads `${prefix}.title` and `${prefix}.lede`. */
  prefix: string
  id?: string
  /** A rose link at the end of the title row, like "All events". */
  action?: { to: string; label: string }
  className?: string
}

/** A SectionHeading whose words come from the page's editable copy. */
export function CopyHeading({ copy, prefix, id, action, className }: CopyHeadingProps) {
  const lede = copy.status === 'loading' || copy.entry(`${prefix}.lede`)
  return (
    <SectionHeading
      id={id}
      action={action}
      className={className}
      title={copy.status === 'loading' ? <CopySkeleton /> : <Copy copy={copy} k={`${prefix}.title`} as="span" />}
      lede={lede ? <Copy copy={copy} k={`${prefix}.lede`} as="div" lines={2} /> : undefined}
    />
  )
}
