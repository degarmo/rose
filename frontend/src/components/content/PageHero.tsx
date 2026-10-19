import type { ReactNode } from 'react'
import type { RemoteImage } from '@/lib/api'
import type { PageCopy } from '@/lib/pageContent'
import { cn } from '@/lib/cn'
import { GUTTER, ImageFrame, type AspectRatio, type PlaceholderTexture } from '../ui'
import { Copy, CopySkeleton } from './Copy'

interface PageHeroProps {
  /** Staff-editable copy: reads `${prefix}.title` and `.lede`. */
  copy?: PageCopy
  prefix?: string
  title?: ReactNode
  lede?: ReactNode
  /** A picture beside the title (design: Home and Plan Your Visit). */
  image?: string
  remoteImage?: RemoteImage | null
  ratio?: AspectRatio
  placeholder?: PlaceholderTexture
  /** Something at the right end of the title row, like the List / Month switch. */
  aside?: ReactNode
  /** Phones show the lead too (the Events and Education phone designs leave it out). */
  phoneLede?: boolean
  children?: ReactNode
}

/**
 * The title block at the top of each website page (design: "Events", "Education",
 * "Contact"): the title in Fraunces 300 at 52px (36 on phones) and a muted lead. With a
 * picture it becomes two columns, the picture on the right.
 */
export function PageHero({ copy, prefix = 'hero', title, lede, image, remoteImage, ratio = '3/2', placeholder = 'rose', aside, phoneLede = true, children }: PageHeroProps) {
  const loading = copy?.status === 'loading'
  const withImage = Boolean(image || remoteImage)
  const heading = (
    <h1 className="text-[2.25rem] font-light leading-[1.05] text-fg lg:text-h1">
      {copy ? (
        loading ? (
          <>
            <span className="sr-only">Loading</span>
            <CopySkeleton lines={1} />
          </>
        ) : (
          <Copy copy={copy} k={`${prefix}.title`} as="span" />
        )
      ) : (
        title
      )}
    </h1>
  )
  // Beside a picture the lead stays narrow; over the full width it runs to one line.
  const leadWidth = withImage ? 'max-w-[520px]' : 'max-w-[760px]'
  const leadText = copy ? (
    <Copy copy={copy} k={`${prefix}.lede`} lines={2} className={cn(leadWidth, 'text-fg-muted lg:text-lead')} />
  ) : (
    lede && <div className={cn(leadWidth, 'text-fg-muted lg:text-lead')}>{lede}</div>
  )

  if (withImage) {
    return (
      <div className={cn('mx-auto grid max-w-[1440px] items-center gap-6 pb-6 pt-7 lg:grid-cols-2 lg:gap-16 lg:py-16', GUTTER)}>
        <div className="flex flex-col gap-3 lg:gap-4">
          {heading}
          {leadText}
          {children}
        </div>
        <ImageFrame image={image} remote={remoteImage} alt="" ratio={ratio} placeholder={placeholder} priority className="hidden rounded-card lg:block" sizes="(min-width: 1024px) 50vw, 100vw" />
      </div>
    )
  }

  return (
    <div className={cn('mx-auto max-w-[1440px] pb-4 pt-7 lg:pb-6 lg:pt-16', GUTTER)}>
      <div className="flex items-center justify-between gap-4 lg:items-end">
        <div className="flex flex-col gap-2">
          {heading}
          {leadText && <div className="hidden lg:block">{leadText}</div>}
        </div>
        {aside}
      </div>
      {leadText && phoneLede && <div className="mt-2 lg:hidden">{leadText}</div>}
      {children}
    </div>
  )
}
