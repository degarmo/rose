import { useState } from 'react'
import { useToast } from '@/components/ui'
import { api, type Preferences } from '@/lib/api'
import { useAsync } from '@/lib/useAsync'

type Changes = Partial<Omit<Preferences, 'discreet_subjects'>>

/** Your preferences, with a save that shows the change at once and puts it back if it fails. */
export function usePreferences() {
  const toast = useToast()
  const state = useAsync(() => api.preferences(), 'preferences')
  const [local, setLocal] = useState<Preferences | null>(null)
  const [saving, setSaving] = useState(false)
  const preferences = local ?? (state.status === 'success' ? state.data : null)

  async function save(changes: Changes, success?: string): Promise<boolean> {
    const before = preferences
    if (before) setLocal({ ...before, ...changes })
    setSaving(true)
    try {
      setLocal(await api.updatePreferences(changes))
      if (success) toast.show({ tone: 'success', title: success })
      return true
    } catch {
      setLocal(before)
      toast.show({
        tone: 'error',
        title: 'Your change was not saved',
        message: 'Please try again.',
      })
      return false
    } finally {
      setSaving(false)
    }
  }

  return { state, preferences, saving, save }
}
