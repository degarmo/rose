import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { Link } from 'react-router'
import { cn } from '@/lib/cn'
import { isExternalUrl } from '@/lib/format'

export type ButtonVariant = 'primary' | 'ghost' | 'link'
export type ButtonSize = 'md' | 'lg'

const base =
  'inline-flex items-center justify-center gap-2 font-sans font-medium tracking-wide transition-colors duration-300 ease-velvet disabled:cursor-not-allowed disabled:opacity-50 aria-disabled:cursor-not-allowed aria-disabled:opacity-50'

const variants: Record<ButtonVariant, string> = {
  primary:
    'rounded-control bg-primary text-on-primary hover:bg-primary-hover active:bg-primary-hover shadow-[0_0_0_1px_rgb(0_0_0/0.06)_inset]',
  ghost:
    'rounded-control border border-border-strong text-fg hover:border-highlight hover:text-accent active:bg-surface-raised',
  link: 'text-accent underline decoration-highlight/60 underline-offset-[6px] hover:decoration-highlight hover:text-fg',
}

const sizes: Record<ButtonSize, string> = {
  md: 'min-h-11 px-5 text-sm',
  lg: 'min-h-12 px-7 text-base',
}

function classes(variant: ButtonVariant, size: ButtonSize, className?: string) {
  return cn(base, variants[variant], variant === 'link' ? 'min-h-11 text-sm' : sizes[size], className)
}

interface CommonProps {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
  children: ReactNode
}

type ButtonProps = CommonProps & ButtonHTMLAttributes<HTMLButtonElement>

export function Button({ variant = 'primary', size = 'md', className, type = 'button', ...rest }: ButtonProps) {
  return <button type={type} className={classes(variant, size, className)} {...rest} />
}

interface ButtonLinkProps extends CommonProps {
  to: string
  'aria-label'?: string
}

/** A link styled as a button. Internal paths use the router; others are plain anchors. */
export function ButtonLink({ to, variant = 'primary', size = 'md', className, children, ...rest }: ButtonLinkProps) {
  const cls = classes(variant, size, className)
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
