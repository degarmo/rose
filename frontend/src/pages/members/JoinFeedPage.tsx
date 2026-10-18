import { CircleCheck, EyeOff, Lock, Users } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { GuidelinesText } from '@/components/members/GuidelinesText'
import { AvatarPicker, BIO_LIMIT } from '@/components/members/ProfileSettings'
import { Toggle } from '@/components/members/Toggle'
import { Button, Card, FormField, Input, Section, Textarea, useToast } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { cn } from '@/lib/cn'
import { feedAccount, type FeedAccount } from '@/lib/membersApi'
import { useAsync } from '@/lib/useAsync'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

type Step = 'about' | 'guidelines' | 'profile' | 'avatar'

function GuidelinesGate({ account, onAgree }: { account: FeedAccount; onAgree: () => void }) {
  const [reachedEnd, setReachedEnd] = useState(false)
  const [agreed, setAgreed] = useState(false)
  const scroller = useRef<HTMLDivElement>(null)
  const agreeId = useId()

  useEffect(() => {
    const element = scroller.current
    if (!element) return
    const check = () => {
      if (element.scrollTop + element.clientHeight >= element.scrollHeight - 12) setReachedEnd(true)
    }
    check()
    element.addEventListener('scroll', check, { passive: true })
    return () => element.removeEventListener('scroll', check)
  }, [])

  if (!account.guidelines) return null
  return (
    <div>
      <div
        ref={scroller}
        tabIndex={0}
        aria-label="Community guidelines"
        className="max-h-[50dvh] overflow-y-auto rounded-xl border border-border bg-surface-sunken p-5"
      >
        <h2 className="mb-4 text-2xl text-fg">{account.guidelines.title}</h2>
        <GuidelinesText body={account.guidelines.body} />
        <p className="mt-6 text-sm text-fg-subtle">Version {account.guidelines.version}</p>
      </div>
      <p className="mt-3 text-sm text-fg-subtle" aria-live="polite">
        {reachedEnd ? 'Thank you for reading to the end.' : 'Scroll to the end to continue.'}
      </p>
      <div className="mt-4 flex items-start gap-3">
        <input
          id={agreeId}
          type="checkbox"
          disabled={!reachedEnd}
          checked={agreed}
          onChange={(e) => setAgreed(e.target.checked)}
          className="mt-1 size-5 accent-[var(--color-primary)] disabled:opacity-40"
        />
        <label htmlFor={agreeId} className={cn('text-fg', !reachedEnd && 'text-fg-subtle')}>
          I agree to the community guidelines
        </label>
      </div>
      <Button className="mt-6" disabled={!agreed} onClick={onAgree}>
        Continue
      </Button>
    </div>
  )
}

export function JoinFeedPage() {
  useDocumentMeta({ title: 'Member feed', noindex: true })
  const auth = useAuth()
  const navigate = useNavigate()
  const toast = useToast()
  const [params] = useSearchParams()
  const reacceptOnly = params.get('guidelines') === '1'
  const state = useAsync(() => feedAccount.get(), `feed-account|${auth.user?.display_name ?? ''}`)
  const [step, setStep] = useState<Step>(reacceptOnly ? 'guidelines' : 'about')
  const [bio, setBio] = useState('')
  const [hidden, setHidden] = useState(true)
  const [busy, setBusy] = useState(false)

  if (auth.status === 'loading') return <Section className="pt-32"><LoadingState label="Loading" /></Section>
  if (!auth.user) return <Navigate to="/account/login?next=%2Fmembers%2Fjoin-feed" replace />
  if (state.status === 'error' && state.error instanceof ApiError && state.error.isNotFound) return <NotFoundPage />
  if (state.status === 'loading') return <Section className="pt-32"><LoadingState label="Loading" /></Section>
  if (state.status === 'error') return <Section className="pt-32"><ErrorState title="This page did not load" onRetry={state.retry} /></Section>
  const account = state.data
  if (!account.can_join) return <NotFoundPage />

  async function agree() {
    if (!account.guidelines) return
    if (account.participating) {
      setBusy(true)
      try {
        await feedAccount.acceptGuidelines(account.guidelines.version)
        toast.show({ tone: 'success', title: 'Thank you. You can post again.' })
        navigate('/members/feed', { replace: true })
      } catch (error) {
        toast.show({ tone: 'error', title: error instanceof Error ? error.message : 'Please try again.' })
      } finally {
        setBusy(false)
      }
      return
    }
    setBio(account.profile.bio)
    setHidden(account.profile.hide_from_directory)
    setStep('profile')
  }

  async function join() {
    if (!account.guidelines) return
    setBusy(true)
    try {
      await feedAccount.join(account.guidelines.version, bio, hidden)
      setStep('avatar')
    } catch (error) {
      toast.show({ tone: 'error', title: 'You were not added to the feed', message: error instanceof Error ? error.message : undefined })
    } finally {
      setBusy(false)
    }
  }

  const steps: Step[] = ['about', 'guidelines', 'profile']
  return (
    <Section width="narrow" className="pt-28">
      <p className="text-xs font-semibold uppercase tracking-[0.28em] text-highlight">Member feed</p>
      <h1 className="mt-3 text-4xl text-fg sm:text-5xl">
        {step === 'avatar' ? 'You are in.' : account.participating ? 'Updated guidelines' : 'Join the member feed'}
      </h1>
      {step !== 'avatar' && !account.participating && (
        <ol className="mt-6 flex gap-2" aria-label="Steps">
          {steps.map((s, index) => (
            <li key={s} aria-current={s === step ? 'step' : undefined} className={cn('h-1 flex-1 rounded-full', steps.indexOf(step) >= index ? 'bg-highlight' : 'bg-border')}>
              <span className="sr-only">Step {index + 1}</span>
            </li>
          ))}
        </ol>
      )}

      <Card className="mt-8 p-6 sm:p-8">
        {step === 'about' && (
          <div className="flex flex-col gap-6">
            <p className="leading-relaxed text-fg-muted">
              The member feed is a private space to share photos and words with other members. It is off unless you turn it on, and you can step away at any time.
            </p>
            <ul className="flex flex-col gap-4 text-fg-muted">
              <li className="flex gap-3"><Users aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-highlight" />Only members with feed access who have joined can see it. It is never public and never indexed.</li>
              <li className="flex gap-3"><EyeOff aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-highlight" />Never shown to anyone: your email, your legal name, or which events you RSVP to.</li>
              <li className="flex gap-3"><Lock aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-highlight" />Like counts are only for the author. Nobody can see who liked a post or who follows whom.</li>
              <li className="flex gap-3"><CircleCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-highlight" />Photos lose their hidden location data, and each copy someone views carries a faint mark with their name, so leaks can be traced.</li>
            </ul>
            <Button className="self-start" onClick={() => setStep('guidelines')}>Read the guidelines</Button>
          </div>
        )}
        {step === 'guidelines' && <GuidelinesGate account={account} onAgree={() => void agree()} />}
        {step === 'profile' && (
          <form
            className="flex flex-col gap-6"
            onSubmit={(event) => {
              event.preventDefault()
              void join()
            }}
            aria-label="Set up your feed profile"
          >
            <FormField label="Display name" hint="Change it from your account page." optionalLabel="">
              {(field) => <Input {...field} value={account.profile.display_name} readOnly />}
            </FormField>
            <FormField label="Short bio" hint="No real names, workplaces or anything identifying." optionalLabel="Optional">
              {(field) => <Textarea {...field} rows={3} maxLength={BIO_LIMIT} value={bio} onChange={(e) => setBio(e.target.value)} />}
            </FormField>
            <p className="-mt-4 text-right text-xs text-fg-subtle">{bio.length} / {BIO_LIMIT}</p>
            <Toggle label="Hide me from the member directory" hint="Recommended. People can still find you through your posts." checked={hidden} onChange={setHidden} />
            <Button type="submit" size="lg" disabled={busy} aria-busy={busy}>
              {busy ? 'Joining' : 'Join the feed'}
            </Button>
          </form>
        )}
        {step === 'avatar' && (
          <div className="flex flex-col gap-6">
            <p className="text-fg-muted">Add a profile picture now, or skip and do it later from your profile.</p>
            <AvatarPicker onSaved={() => navigate('/members/feed', { replace: true })} />
            <Button variant="ghost" className="self-start" onClick={() => navigate('/members/feed', { replace: true })}>
              Skip for now
            </Button>
          </div>
        )}
      </Card>
    </Section>
  )
}
