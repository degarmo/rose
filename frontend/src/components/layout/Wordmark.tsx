import { Link } from 'react-router'

export function Wordmark({ onNavigate }: { onNavigate?: () => void }) {
  return (
    <Link to="/" onClick={onNavigate} className="group inline-flex min-h-11 items-center gap-3">
      <span
        aria-hidden="true"
        className="inline-flex size-9 items-center justify-center rounded-full border border-highlight/60 font-display text-lg text-fg transition-colors duration-500 group-hover:border-highlight"
      >
        R
      </span>
      <span className="font-display text-2xl tracking-wide text-fg">Rose</span>
    </Link>
  )
}
