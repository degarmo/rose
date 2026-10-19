import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { isExternalUrl } from '@/lib/format'

/**
 * The website's buttons (design system: "Public site · 48px pill, 40px compact").
 * primary   rose fill, white text
 * secondary 1px border, page text
 * outline   1px text-coloured border
 * dark      text-coloured fill (the footer's Sign up)
 * link      rose text, weight 600 (callers add the arrow)
 */
export type ButtonVariant = 'primary' | 'secondary' | 'outline' | 'dark' | 'link'
/** lg 48px, md 40px, sm 36px. */
export type ButtonSize = 'sm' | 'md' | 'lg'

const base =
  'inline-flex shrink-0 items-center justify-center gap-2 whitespace-nowrap font-semibold transition-colors duration-150 ease-out disabled:cursor-not-allowed aria-disabled:cursor-not-allowed'

const variants: Record<ButtonVariant, string> = {
  primary: 'rounded-full bg-primary text-on-primary hover:bg-primary-hover',
  secondary: 'rounded-full border border-border bg-canvas text-fg hover:border-fg-muted',
  outline: 'rounded-full border border-fg bg-canvas text-fg hover:bg-surface',
  dark: 'rounded-full bg-fg text-canvas hover:bg-fg/85',
  link: 'text-link hover:text-primary-hover',
}

/** Disabled pills turn grey rather than fading (design system: "Disabled"). */
const disabled =
  'disabled:border-control disabled:bg-control disabled:text-fg-faint aria-disabled:border-control aria-disabled:bg-control aria-disabled:text-fg-faint'

const sizes: Record<ButtonSize, string> = {
  sm: 'h-9 px-4 text-[0.8125rem]',
  md: 'h-10 px-5 text-sm',
  lg: 'h-12 px-7 text-[0.9375rem]',
}

function buttonClasses(variant: ButtonVariant = 'primary', size: ButtonSize = 'md', className?: string) {
  return cn(base, variants[variant], variant === 'link' ? 'min-h-6 text-sm' : cn(sizes[size], disabled), className)
}

interface CommonProps {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  children: ReactNode
}

type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ variant = 'primary', size = 'md', className, type = 'button', ...rest }: ButtonProps) {
  return <button type={type} className={buttonClasses(variant, size, className)} {...rest} />
}

interface ButtonLinkProps extends CommonProps {
  to: string
  'aria-label'?: string
}

/** A link styled as a button. Internal paths use the router; others are plain anchors. */
export function ButtonLink({ to, variant = 'primary', size = 'md', className, children, ...rest }: ButtonLinkProps) {
  const cls = buttonClasses(variant, size, className)
  if (isExternalUrl(to)) {
    return (
      <a href={to} className={cls} rel="noopener noreferrer" {...rest}>
        {children}
      </a>
    )
  }
  return (
    <Link to={to} className={cls} {...rest}>
      {children}
    </Link>
  )
}
