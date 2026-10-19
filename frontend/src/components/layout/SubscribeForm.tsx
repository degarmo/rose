import { CircleAlert, CircleCheck } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { api, ApiError } from '@/lib/api'
import { Button } from '../ui'
import { fieldClasses } from '../ui/fieldStyles'

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

type State = { name: 'idle' } | { name: 'sending' } | { name: 'sent'; message: string } | { name: 'error'; message: string }

/**
 * The footer's email list sign-up. Double opt-in: the answer is the same
 * "check your inbox" whether or not the address is already on the list.
 */
export function SubscribeForm() {
  const id = useId()
  const [email, setEmail] = useState('')
  const [website, setWebsite] = useState('')
  const [state, setState] = useState<State>({ name: 'idle' })
  const statusId = `${id}-status`

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (!EMAIL_PATTERN.test(email.trim())) {
      setState({ name: 'error', message: 'Enter a full email address.' })
      return
    }
    setState({ name: 'sending' })
    try {
      const result = await api.subscribe(email.trim(), website)
      setState({ name: 'sent', message: result.detail })
      setEmail('')
    } catch (error) {
      const message =
        error instanceof ApiError && error.isRateLimited
          ? 'Too many attempts. Please try again later.'
          : error instanceof Error
            ? error.message
            : 'Please try again.'
      setState({ name: 'error', message })
    }
  }

  return (
    <form noValidate onSubmit={submit} aria-label="Stay in touch" className="flex flex-col gap-3">
      <label htmlFor={`${id}-email`} className="text-sm text-fg-muted">
        Occasional news and the evenings ahead. Confirm from your inbox; leave in one click.
      </label>
      <div className="flex flex-col gap-2 sm:flex-row">
        <input
          id={`${id}-email`}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value)
            if (state.name === 'error') setState({ name: 'idle' })
          }}
          aria-invalid={state.name === 'error' || undefined}
          aria-describedby={state.name === 'sent' || state.name === 'error' ? statusId : undefined}
          placeholder="you@example.org"
          className={fieldClasses(state.name === 'error', 'min-w-0 flex-1')}
        />
        <Button type="submit" disabled={state.name === 'sending'} aria-busy={state.name === 'sending'}>
          {state.name === 'sending' ? 'Sending' : 'Subscribe'}
        </Button>
      </div>
      {/* Honeypot: hidden from people and assistive tech, tempting to bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(event) => setWebsite(event.target.value)} />
        </label>
      </div>
      <div aria-live="polite">
        {state.name === 'sent' && (
          <p id={statusId} className="flex items-center gap-2 text-sm text-success">
            <CircleCheck aria-hidden="true" className="size-4 shrink-0" />
            {state.message}
          </p>
        )}
        {state.name === 'error' && (
          <p id={statusId} className="flex items-center gap-2 text-sm text-danger">
            <CircleAlert aria-hidden="true" className="size-4 shrink-0" />
            {state.message}
          </p>
        )}
      </div>
    </form>
  )
}
