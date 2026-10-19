import { CircleCheck, EyeOff, Lock, Users } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'
import { Navigate, useNavigate, useSearchParams } from 'react-router'
import { ErrorState, LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { GuidelinesText } from '@/components/members/GuidelinesText'
import { AvatarPicker, BIO_LIMIT } from '@/components/members/ProfileSettings'
import { Button, CheckboxBox, FormField, Input, Section, Textarea, Toggle, useToast } from '@/components/ui'
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
    <div className="flex flex-col gap-4 lg:gap-5">
      <div className="relative">
        <div
          ref={scroller}
          tabIndex={0}
          role="region"
          aria-label="Community guidelines"
          className="h-[300px] overflow-y-auto rounded-card border border-border p-5 text-sm focus-visible:outline-2 focus-visible:outline-link lg:h-[360px] lg:px-8 lg:py-7 lg:text-[0.9375rem]"
        >
          <h2 className="mb-4 text-xl font-light text-fg lg:text-card-title">{account.guidelines.title}</h2>
          <GuidelinesText body={account.guidelines.body} />
          <p className="mt-6 text-[0.8125rem] text-fg-muted">Version {account.guidelines.version}</p>
        </div>
        {/* The fade says "there is more"; it goes once the end has been reached. */}
        <div
          aria-hidden="true"
          className={cn(
            'pointer-events-none absolute inset-x-px bottom-px h-[70px] rounded-b-card bg-linear-to-b from-transparent to-canvas transition-opacity lg:h-20',
            reachedEnd && 'opacity-0',
          )}
        />
      </div>
      <p className={cn('text-[0.8125rem]', reachedEnd ? 'text-link' : 'text-fg-muted')} aria-live="polite">
        {reachedEnd ? 'Thank you for reading to the end.' : 'Scroll to the end to enable the checkbox.'}
      </p>
      <div className="flex items-start gap-3">
        <CheckboxBox id={agreeId} disabled={!reachedEnd} checked={agreed} onChange={(e) => setAgreed(e.target.checked)} className="mt-px lg:mt-0.5" />
        <label htmlFor={agreeId} className={cn('text-sm lg:text-[0.9375rem]', reachedEnd ? 'text-fg' : 'text-fg-muted')}>
          I agree to the community guidelines
        </label>
      </div>
      <Button size="lg" className="mt-1 self-start" disabled={!agreed} onClick={onAgree}>
        Continue
      </Button>
    </div>
  )
}

const STEP_LABELS: Record<Exclude<Step, 'avatar'>, string> = { about: 'About', guidelines: 'Guidelines', profile: 'Profile' }

/** Joining the member feed (nearest design: "Join step 2"): about, the guidelines, then a profile. */
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
  const position = steps.indexOf(step) + 1
  const title = step === 'avatar' ? 'You are in.' : account.participating ? 'Updated guidelines' : 'Join the member feed'
  const lede =
    step === 'avatar'
      ? 'Add a profile picture now, or skip and do it later from your profile.'
      : step === 'about'
        ? 'The member feed is a private space to share photos and words with other members. It is off unless you turn it on, and you can step away at any time.'
        : step === 'guidelines'
          ? 'Please read them to the end. They are short on purpose, and hosts hold everyone to them.'
          : 'How you appear to other members. You can change it later.'

  return (
    <Section spacing="none" className="pb-16 pt-8 lg:pb-24 lg:pt-16">
      <div className="grid gap-5 lg:grid-cols-[420px_1fr] lg:gap-20">
        <div className="flex flex-col gap-3 lg:gap-4">
          {step !== 'avatar' && !account.participating && (
            <div className="flex flex-col gap-3">
              <div aria-hidden="true" className="flex gap-1.5 lg:max-w-[240px]">
                {steps.map((s, index) => (
                  <span key={s} className={cn('h-[3px] flex-1 rounded-sm', index < position ? 'bg-primary' : 'bg-border')} />
                ))}
              </div>
              <p className="text-xs font-semibold text-fg-muted">
                Step {position} of 3 &middot; {STEP_LABELS[step]}
              </p>
            </div>
          )}
          <h1 className="text-[2rem] font-light leading-[1.05] text-fg lg:text-h2-lg">{title}</h1>
          <p className="text-base text-fg-muted">{lede}</p>
        </div>

        <div className="min-w-0">
          {step === 'about' && (
            <div className="flex flex-col gap-5">
              <ul className="flex flex-col gap-4 rounded-card border border-border p-5 text-fg-muted lg:px-8 lg:py-7">
                <li className="flex gap-3"><Users aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-link" />Only members with feed access who have joined can see it. It is never public and never indexed.</li>
                <li className="flex gap-3"><EyeOff aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-link" />Never shown to anyone: your email, your legal name, or which events you RSVP to.</li>
                <li className="flex gap-3"><Lock aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-link" />Like counts are only for the author. Nobody can see who liked a post or who follows whom.</li>
                <li className="flex gap-3"><CircleCheck aria-hidden="true" className="mt-0.5 size-5 shrink-0 text-link" />Photos lose their hidden location data, and each copy someone views carries a faint mark with their name, so leaks can be traced.</li>
              </ul>
              <Button size="lg" className="self-start" onClick={() => setStep('guidelines')}>Read the guidelines</Button>
            </div>
          )}
          {step === 'guidelines' && <GuidelinesGate account={account} onAgree={() => void agree()} />}
          {step === 'profile' && (
            <form
              className="flex flex-col gap-6 lg:max-w-[480px]"
              onSubmit={(event) => {
                event.preventDefault()
                void join()
              }}
              aria-label="Set up your feed profile"
            >
              <FormField label="Display name" hint="Change it from your account page." optionalLabel="">
                {(field) => <Input {...field} value={account.profile.display_name} readOnly />}
              </FormField>
              <div>
                <FormField label="Short bio" hint="No real names, workplaces or anything identifying." optionalLabel="Optional">
                  {(field) => <Textarea {...field} rows={3} maxLength={BIO_LIMIT} value={bio} onChange={(e) => setBio(e.target.value)} />}
                </FormField>
                <p className="mt-1 text-right text-xs text-fg-muted">{bio.length} / {BIO_LIMIT}</p>
              </div>
              <Toggle label="Hide me from the member directory" hint="Recommended. People can still find you through your posts." checked={hidden} onChange={setHidden} />
              <Button type="submit" size="lg" className="self-start" disabled={busy} aria-busy={busy}>
                {busy ? 'Joining' : 'Join the feed'}
              </Button>
            </form>
          )}
          {step === 'avatar' && (
            <div className="flex flex-col gap-6 rounded-card border border-border p-5 lg:px-8 lg:py-7">
              <AvatarPicker onSaved={() => navigate('/members/feed', { replace: true })} />
              <Button variant="secondary" className="self-start" onClick={() => navigate('/members/feed', { replace: true })}>
                Skip for now
              </Button>
            </div>
          )}
        </div>
      </div>
    </Section>
  )
}
