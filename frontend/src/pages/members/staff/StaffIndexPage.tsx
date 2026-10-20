import { useEffect } from 'react'
import { Navigate } from 'react-router'
import { LoadingState } from '@/components/content/States'
import { useAuth } from '@/components/layout/authContext'
import { NotFoundPage } from '@/pages/NotFoundPage'

/**
 * /members/staff: the staff section has no home page of its own (the dashboard is the
 * admin's). The team go to the reports inbox; a door volunteer to the door desk, with a
 * full page load so its camera permission applies.
 */
export function StaffIndexPage() {
  const auth = useAuth()
  const staff = auth.user?.staff
  const toDoor = Boolean(staff && !staff.role && staff.door_desk)
  useEffect(() => {
    if (toDoor) window.location.replace('/members/staff/door')
  }, [toDoor])
  if (auth.status === 'loading' || toDoor) return <LoadingState label="Loading" />
  if (!staff?.role) return <NotFoundPage />
  return <Navigate to="/members/staff/reports" replace />
}
