import { Check, ListChecks, Lock } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { appButtonClasses, ICON } from '@/components/members/app/ui'
import { DoorCode } from '@/components/members/settings/MembershipCard'
import { Card, ResendVerification, StatusChip } from '@/components/members/settings/ui'
import { cn } from '@/lib/cn'
import type { FeedPath, PathStep } from '@/lib/membersApi'

const TITLES: Record<PathStep['key'], string> = {
  email: 'Verify email',
  plan: 'Choose a plan',
  door: 'Get activated at the door',
  age: 'Age check',
  join: 'Join the community',
}

const INCLUDED = 'Included with your account.'

function Detail({ children }: { children: ReactNode }) {
  return <p className="text-fg-muted">{children}</p>
}

/** What a step asks for, and (for the current step only) the way to do it. */
function StepBody({ step, displayName, code }: { step: PathStep; displayName: string; code: 'here' | 'card' | null }) {
  const current = step.state === 'current'
  switch (step.key) {
    case 'email':
      if (step.state === 'done') return null
      return (
        <>
          <Detail>Confirm your email with the link we sent you.</Detail>
          {current && (
            <div className="self-start">
              <ResendVerification sentClassName="text-fg" />
            </div>
          )}
        </>
      )
    case 'plan':
      if (step.state === 'done') return step.included ? <Detail>{INCLUDED}</Detail> : null
      return (
        <>
          <Detail>{step.tier ? `Your plan, ${step.tier}, leaves out the member community.` : 'Pick a plan that includes the member community.'}</Detail>
          {current && (
            <Link to="/membership" className={appButtonClasses('primary', 'self-start px-4')}>
              Compare plans
            </Link>
          )}
        </>
      )
    case 'door':
      if (step.state === 'done') return step.included ? <Detail>{INCLUDED}</Detail> : null
      return (
        <>
          <Detail>
            {step.waiting_for === 'payment'
              ? 'Pay at the front desk and staff switch your membership on. Show them your code.'
              : step.waiting_for === 'id_check'
                ? 'Already paid. Staff switch your membership on at your next visit. Show them your code.'
                : step.waiting_for === 'suspended'
                  ? 'Your membership is on hold. Ask at the front desk.'
                  : 'Once you have a plan, staff switch it on at your next visit.'}
          </Detail>
          {step.reference_code && step.waiting_for !== 'suspended' && <DoorCode code={step.reference_code} />}
        </>
      )
    case 'age':
      if (step.state === 'done') return null
      return (
        <>
          <Detail>
            {step.notice
              ? 'The member community now needs a quick check in person, for everyone. Nothing you shared is lost.'
              : 'Bring a valid photo ID showing you are 18 or older. Staff look at it and hand it straight back.'}
          </Detail>
          {code === 'card' && <Detail>At the door, show the code on your membership card.</Detail>}
          {code === null && (
            <p className="rounded-app bg-surface p-3 text-fg">
              At the door, give your display name: <strong className="font-semibold">{displayName}</strong>
            </p>
          )}
          <p className="flex items-start gap-2 text-meta text-fg-muted">
            <Lock aria-hidden="true" size={16} strokeWidth={ICON.stroke} className="mt-0.5 shrink-0" />
            We never copy or store your ID. Staff only note that they saw it.
          </p>
        </>
      )
    case 'join':
      if (step.state === 'done') return null
      if (step.paused) return <Detail>Your community access is paused. It reopens when the pause ends.</Detail>
      return (
        <>
          <Detail>{step.early ? 'You can read the community guidelines now, before your visit.' : 'Accept the community guidelines and set up your profile.'}</Detail>
          {current && step.can_join && (
            <Link to="/members/join-feed" className={appButtonClasses('primary', 'self-start px-4')}>
              Join the community
            </Link>
          )}
          {step.early && (
            <Link to="/members/join-feed" className={appButtonClasses('secondary', 'self-start px-4')}>
              Read the community guidelines now
            </Link>
          )}
        </>
      )
  }
}

function Marker({ step, number }: { step: PathStep; number: number }) {
  if (step.state === 'done') {
    return (
      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-tint text-tint-fg">
        <Check aria-hidden="true" size={16} strokeWidth={ICON.activeStroke} />
      </span>
    )
  }
  return (
    <span
      aria-hidden="true"
      className={cn(
        'flex size-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold',
        step.state === 'current' ? 'bg-primary text-on-primary' : 'border border-border text-fg-muted',
      )}
    >
      {number}
    </span>
  )
}

/**
 * Home's checklist: what stands between this account and the member community, in order,
 * each with where it stands and (for the next one) what to do. Once all are done, the way in.
 * `cardShowsCode`: the membership card on the same page shows the door code.
 */
export function WhatsMissing({ path, displayName, cardShowsCode }: { path: FeedPath; displayName: string; cardShowsCode: boolean }) {
  const inPath = path.steps.some((step) => step.key === 'door' && step.reference_code && step.waiting_for !== 'suspended')
  const code = inPath ? 'here' : cardShowsCode ? 'card' : null
  return (
    <Card title="What's missing" icon={ListChecks}>
      {path.complete && <p className="mb-2 text-fg">Nothing. The member community is open to you.</p>}
      <ol className="flex flex-col">
        {path.steps.map((step, index) => (
          <li
            key={step.key}
            aria-current={step.state === 'current' ? 'step' : undefined}
            className="flex gap-3 border-b border-border py-3 first:pt-0 last:border-b-0 last:pb-0"
          >
            <Marker step={step} number={index + 1} />
            <div className="flex min-w-0 flex-1 flex-col gap-2">
              <p className="flex min-h-7 items-center justify-between gap-2">
                <span className={cn('font-semibold', step.state === 'upcoming' ? 'text-fg-muted' : 'text-fg')}>{TITLES[step.key]}</span>
                {step.state === 'done' && <StatusChip tone="ok">Done</StatusChip>}
                {step.state === 'current' && <StatusChip tone="wait">{step.key === 'join' && step.paused ? 'Paused' : 'Next'}</StatusChip>}
                {step.state === 'upcoming' && <span className="sr-only">Not yet</span>}
              </p>
              <StepBody step={step} displayName={displayName} code={code} />
            </div>
          </li>
        ))}
      </ol>
      {path.complete && (
        <Link to="/members/feed" className={appButtonClasses('primary', 'mt-4 px-4')}>
          Open the community
        </Link>
      )}
    </Card>
  )
}
