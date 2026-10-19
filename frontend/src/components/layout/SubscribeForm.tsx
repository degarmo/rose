import { useId, useState, type FormEvent } from 'react'
import { api, ApiError } from '@/lib/api'
import { Button } from '../ui'

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
      setState({ name: 'error', message: 'Enter a full email address, like name@example.com.' })
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

  const invalid = state.name === 'error'
  return (
    <form noValidate onSubmit={submit} aria-label="Stay in touch" className="relative flex flex-col gap-2">
      <label htmlFor={`${id}-email`} className="font-semibold text-fg">
        Occasional email, never more than monthly
      </label>
      <div className="flex gap-2">
        <input
          id={`${id}-email`}
          name="email"
          type="email"
          inputMode="email"
          autoComplete="email"
          value={email}
          onChange={(event) => {
            setEmail(event.target.value)
            if (invalid) setState({ name: 'idle' })
          }}
          aria-invalid={invalid || undefined}
          aria-describedby={state.name === 'sent' || invalid ? statusId : undefined}
          placeholder="Email address"
          className={
            'h-11 min-w-0 flex-1 rounded-full border bg-canvas px-4 text-sm text-fg placeholder:text-fg-muted focus:outline-none lg:h-10 ' +
            (invalid ? 'border-danger shadow-[inset_0_0_0_0.5px_var(--color-danger)]' : 'border-border focus:border-fg')
          }
        />
        <Button type="submit" variant="dark" disabled={state.name === 'sending'} aria-busy={state.name === 'sending'} className="h-11 px-[18px] lg:h-10">
          {state.name === 'sending' ? 'Sending' : 'Sign up'}
        </Button>
      </div>
      {/* Honeypot: hidden from people and assistive tech, tempting to bots. */}
      <div aria-hidden="true" className="absolute -left-[9999px] h-px w-px overflow-hidden">
        <label>
          Website
          <input type="text" name="website" tabIndex={-1} autoComplete="off" value={website} onChange={(event) => setWebsite(event.target.value)} />
        </label>
      </div>
      <div aria-live="polite" className="text-[0.8125rem]">
        {state.name === 'sent' && (
          <p id={statusId} className="text-fg-muted">
            {state.message}
          </p>
        )}
        {invalid && (
          <p id={statusId} className="text-danger">
            {state.message}
          </p>
        )}
      </div>
    </form>
  )
}
