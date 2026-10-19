import { Navigate, useLocation, useParams } from 'react-router'

/**
 * The old account pages now live in the member app's Settings. The server answers these
 * addresses with a 301; this covers links followed inside the app. Anchors carry over, and
 * Settings maps the old ones (#password, #delete…) to their sections.
 */
export function AccountMoved({ to }: { to: 'settings' | 'notices' | 'export' | 'receipt' }) {
  const { hash } = useLocation()
  const { id = '' } = useParams()
  const pathname = {
    settings: '/members/settings',
    notices: '/members/settings/notices',
    export: '/members/settings/privacy/export',
    receipt: `/members/settings/membership/receipts/${encodeURIComponent(id)}`,
  }[to]
  return <Navigate to={{ pathname, hash }} replace />
}
