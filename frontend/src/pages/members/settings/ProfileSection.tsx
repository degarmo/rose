import { Check, ImageIcon, Moon, Sun } from 'lucide-react'
import { useState, type FormEvent } from 'react'
import { useAuth } from '@/components/layout/authContext'
import { Avatar } from '@/components/members/Avatar'
import { AppButton } from '@/components/members/app/primitives'
import { ICON } from '@/components/members/app/ui'
import { useOptionalMembers } from '@/components/members/membersContext'
import { EditProfileDialog } from '@/components/members/ProfileSettings'
import { Card, FeedOnlyNote, Skeleton } from '@/components/members/settings/ui'
import { usePreferences } from '@/components/members/settings/usePreferences'
import { FormField, Input, useToast } from '@/components/ui'
import { api, ApiError, type Appearance } from '@/lib/api'
import { chooseAppearance } from '@/lib/appearance'
import { cn } from '@/lib/cn'
import { displayNameError } from '@/pages/account/validation'

function DisplayNameForm({ current }: { current: string }) {
  const auth = useAuth()
  const toast = useToast()
  const [value, setValue] = useState(current)
  const [error, setError] = useState<string>()
  const [saving, setSaving] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const found = displayNameError(value)
    setError(found)
    if (found) return
    setSaving(true)
    try {
      auth.applySession(await api.changeDisplayName(value.trim()))
      toast.show({ tone: 'success', title: 'Display name updated' })
    } catch (err) {
      setError(err instanceof ApiError && err.fieldErrors.display_name ? err.fieldErrors.display_name : 'Please try again.')
    } finally {
      setSaving(false)
    }
  }

  return (
    <form noValidate onSubmit={submit} aria-label="Change display name" className="flex flex-col gap-3">
      <FormField label="Display name" hint="The only name anyone else sees. Please avoid your real name." error={error} required>
        {(field) => <Input {...field} name="display_name" autoComplete="off" value={value} onChange={(e) => setValue(e.target.value)} />}
      </FormField>
      <AppButton type="submit" className="self-start" disabled={saving || value.trim() === current}>
        {saving ? 'Saving' : 'Save name'}
      </AppButton>
    </form>
  )
}

/** Pronouns: optional, shown on your feed profile only when filled in. */
function PronounsForm() {
  const members = useOptionalMembers()
  const { preferences, save, saving } = usePreferences()
  const [value, setValue] = useState<string | null>(null)
  if (!preferences) return <Skeleton lines={2} />
  const shown = value ?? preferences.pronouns
  return (
    <form
      noValidate
      aria-label="Pronouns"
      className="flex flex-col gap-3"
      onSubmit={(event) => {
        event.preventDefault()
        void save({ pronouns: shown.trim() }, shown.trim() ? 'Pronouns saved' : 'Pronouns removed').then((ok) => {
          if (!ok) return
          setValue(null)
          void members?.refreshMe()
        })
      }}
    >
      <FormField label="Pronouns" hint="Optional. Shown on your profile only if you fill this in." optionalLabel="">
        {(field) => (
          <Input
            {...field}
            name="pronouns"
            maxLength={40}
            autoComplete="off"
            placeholder="she/her, they/them…"
            value={shown}
            onChange={(e) => setValue(e.target.value)}
          />
        )}
      </FormField>
      <AppButton type="submit" variant="secondary" className="self-start" disabled={saving || shown.trim() === preferences.pronouns}>
        Save pronouns
      </AppButton>
    </form>
  )
}

/** Light or dark, for the website and the member app; saved on the account. */
function AppearanceChoice({ current }: { current: Appearance }) {
  const auth = useAuth()
  const toast = useToast()
  async function choose(next: Appearance) {
    try {
      const session = await chooseAppearance(next, true)
      if (session) auth.applySession(session)
    } catch {
      toast.show({
        tone: 'error',
        title: 'Your choice was not saved',
        message: 'It applies in this browser for now.',
      })
    }
  }
  return (
    <div role="radiogroup" aria-label="Appearance" className="grid grid-cols-2 gap-2">
      {(['light', 'dark'] as const).map((value) => {
        const Icon = value === 'light' ? Sun : Moon
        const on = current === value
        return (
          <button
            key={value}
            type="button"
            role="radio"
            aria-checked={on}
            onClick={() => void choose(value)}
            className={cn(
              'flex min-h-12 items-center gap-3 rounded-app border px-3 text-left font-semibold',
              on ? 'border-fg text-fg' : 'border-border text-fg-muted hover:text-fg',
            )}
          >
            <Icon aria-hidden="true" size={20} strokeWidth={ICON.stroke} />
            <span className="flex-1">{value === 'light' ? 'Light' : 'Dark'}</span>
            {on && <Check aria-hidden="true" size={18} strokeWidth={ICON.activeStroke} className="text-link" />}
          </button>
        )
      })}
    </div>
  )
}

/** The feed profile: picture and bio, edited in the existing dialog. */
function FeedProfile() {
  const members = useOptionalMembers()
  const [editing, setEditing] = useState(false)
  if (!members) {
    return (
      <FeedOnlyNote icon={ImageIcon} title="Picture and bio">
        Your picture and bio belong to your member feed profile. Add them when you join.
      </FeedOnlyNote>
    )
  }
  const { me } = members
  return (
    <>
      <div className="flex items-center gap-4">
        <Avatar member={me} size="md" className="size-16" />
        <div className="min-w-0 flex-1">
          <p className="font-semibold text-fg">{me.handle}</p>
          <p className={cn('text-sm', me.bio ? 'text-fg' : 'text-fg-muted')}>{me.bio || 'No bio yet.'}</p>
        </div>
      </div>
      <AppButton variant="secondary" className="mt-4" onClick={() => setEditing(true)}>
        Edit picture and bio
      </AppButton>
      <EditProfileDialog open={editing} onClose={() => setEditing(false)} />
    </>
  )
}

/** Settings · Profile: display name, picture and bio, pronouns, appearance. */
export function ProfileSection() {
  const auth = useAuth()
  const user = auth.user
  if (!user) return null
  return (
    <div className="flex flex-col gap-4">
      <Card title="About you">
        <DisplayNameForm key={user.display_name} current={user.display_name} />
        <div className="mt-5 border-t border-border pt-5">
          <PronounsForm />
        </div>
      </Card>
      <Card title="Picture and bio">
        <FeedProfile />
      </Card>
      <Card title="Appearance">
        <AppearanceChoice current={user.appearance} />
        <p className="mt-3 text-meta text-fg-muted">Light is the default. Your choice follows you to every device you sign in on.</p>
      </Card>
    </div>
  )
}
