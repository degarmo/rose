import { Navigate } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { SiteFrame } from '@/components/layout/Layout'
import { ButtonLink, Section } from '@/components/ui'
import { useDocumentMeta } from '@/lib/useDocumentMeta'
import { NotFoundPage } from '../NotFoundPage'

function Explanation({ paused }: { paused: boolean }) {
  useDocumentMeta({ title: 'Member app', noindex: true })
  return (
    <Section spacing="none" className="pb-16 pt-7 lg:pb-24 lg:pt-16">
      <div className="mx-auto flex max-w-[560px] flex-col items-center gap-3 rounded-panel bg-blush px-6 py-8 text-center lg:px-10 lg:py-12">
        <h1 className="text-[1.625rem] leading-[1.15] text-fg lg:text-[2rem]">
          {paused ? 'The member app is paused on your account' : 'The member app comes with membership'}
        </h1>
        <p className="text-sm text-fg-muted-tint lg:text-body">
          {paused
            ? 'Your account page explains why, for how long, and how to appeal.'
            : 'It is a private space where members share photos and news with each other. It is included with most memberships.'}
        </p>
        <div className="mt-2 flex flex-wrap justify-center gap-3">
          {paused ? (
            <ButtonLink to="/account/notices">See my account</ButtonLink>
          ) : (
            <ButtonLink to="/membership">See membership plans</ButtonLink>
          )}
        </div>
      </div>
    </Section>
  )
}

/**
 * /members: the door to the member app. Members whose app is open go to the feed, those
 * who may join go to joining, and anyone else signed in gets a short explanation rather
 * than a dead end. Signed out, it is the site's ordinary 404, and so is any deeper
 * /members address for people without access.
 */
export function MembersEntryPage() {
  const auth = useAuth()
  if (auth.status === 'loading') {
    return (
      <SiteFrame>
        <LoadingState label="Loading" className="justify-center py-16" />
      </SiteFrame>
    )
  }
  const user = auth.user
  if (user?.member_app === 'open') return <Navigate to="/members/feed" replace />
  if (user?.member_app === 'join') return <Navigate to="/members/join-feed" replace />
  return <SiteFrame>{user ? <Explanation paused={user.member_app === 'paused'} /> : <NotFoundPage />}</SiteFrame>
}
