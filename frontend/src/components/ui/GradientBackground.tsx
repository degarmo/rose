import { cn } from '@/lib/cn'

/**
 * A soft pastel glow behind a section (the "Aurora" gradient: violet, butter, pink and sky
 * washes over a lavender-to-blush base), dimmed in the dark appearance. Decorative only.
 * Put it inside a `relative isolate` parent; it fills the parent and sits behind its content.
 */
export function GradientBackground({ className }: { className?: string }) {
  return <div aria-hidden="true" className={cn('gradient-aurora absolute inset-0 -z-10', className)} />
}
