import { Navigate } from 'react-router'
import { profilePath } from '@/components/members/app/postUtils'
import { useMembers } from '@/components/members/membersContext'

/** /members/saved: your saved posts live on your own profile's Saved tab. */
export function SavedPage() {
  const { me } = useMembers()
  return <Navigate to={`${profilePath(me.handle)}/saved`} replace />
}
