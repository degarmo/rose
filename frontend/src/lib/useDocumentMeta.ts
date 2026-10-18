import { useEffect } from 'react'
import { config } from './config'

interface DocumentMeta {
  title?: string
  description?: string
  noindex?: boolean
}

function setMeta(name: string, content: string) {
  let element = document.head.querySelector<HTMLMetaElement>(`meta[name="${name}"]`)
  if (!element) {
    element = document.createElement('meta')
    element.name = name
    document.head.appendChild(element)
  }
  element.content = content
}

export function useDocumentMeta({ title, description, noindex = false }: DocumentMeta) {
  useEffect(() => {
    document.title = title ? `${title} | ${config.siteName}` : config.siteName
    if (description) setMeta('description', description)
    setMeta('robots', noindex ? 'noindex, nofollow' : 'index, follow')
  }, [title, description, noindex])
}

const PRIVATE_PREFIXES = ['/members', '/account', '/api']

export function isPrivatePath(pathname: string): boolean {
  return PRIVATE_PREFIXES.some(
    (prefix) => pathname === prefix || pathname.startsWith(`${prefix}/`),
  )
}
