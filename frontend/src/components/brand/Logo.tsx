import type { CSSProperties } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { config } from '@/lib/config'

/**
 * The club's emblem, made by scripts/build_brand_assets.py into /brand: `full` is the whole
 * neon emblem (about 2.06 : 1), `mark` the rose alone (square), for small or tight places.
 * WebP with a PNG fallback; the browser picks a width from `sizes`. Its height is held
 * before the file arrives (a `className` height, such as the header's responsive one,
 * replaces it), so nothing shifts while it loads. The alt text is the site's display name
 * (a setting, never written in the code).
 */
const VARIANTS = {
  full: { file: 'emblem', widths: [120, 240, 480, 960], ratio: 960 / 466 },
  mark: { file: 'rose', widths: [64, 128, 256, 512], ratio: 1 },
} as const

export type LogoVariant = keyof typeof VARIANTS

function srcSet(variant: LogoVariant, format: 'webp' | 'png') {
  const { file, widths } = VARIANTS[variant]
  return widths.map((width) => `/brand/${file}-${width}.${format} ${width}w`).join(', ')
}

interface LogoProps {
  variant?: LogoVariant
  /** The height it shows at, in CSS pixels (a `className` height overrides it, for responsive heights). */
  height: number
  /** Overrides the width the browser chooses for, when the height changes with the screen. */
  sizes?: string
  /** A link to Home: the header and the member app's bars. */
  to?: string
  onNavigate?: () => void
  /** Beside the name already (an avatar by a handle): no alt text. */
  decorative?: boolean
  /** The first thing on the page: fetched at once. */
  priority?: boolean
  className?: string
}

export function Logo({ variant = 'full', height, sizes, to, onNavigate, decorative = false, priority = false, className }: LogoProps) {
  const { file, widths, ratio } = VARIANTS[variant]
  const width = Math.round(height * ratio)
  const chosen = sizes ?? `${width}px`
  const picture = (
    <picture className="contents">
      <source type="image/webp" srcSet={srcSet(variant, 'webp')} sizes={chosen} />
      <img
        src={`/brand/${file}-${widths[1]}.png`}
        srcSet={srcSet(variant, 'png')}
        sizes={chosen}
        width={width}
        height={height}
        alt={decorative ? '' : config.displayName}
        loading={priority ? 'eager' : 'lazy'}
        decoding="async"
        draggable={false}
        style={{ '--logo-height': `${height}px` } as CSSProperties}
        className={cn('block h-[var(--logo-height)] w-auto max-w-none select-none', className)}
      />
    </picture>
  )
  if (!to) return picture
  return (
    <Link to={to} onClick={onNavigate} className="inline-flex shrink-0 items-center">
      {picture}
    </Link>
  )
}
