import { useEffect, useState } from 'react'
import { request, type RemoteImage } from './api'

/** The point that must stay in view when a picture is cropped, from 0 to 1 each way. */
export interface FocalPoint {
  x: number
  y: number
}

/** A page image (a slot) as /api/site-images/ gives it: public data only. */
export interface SiteImageData extends RemoteImage {
  focal: FocalPoint
}

/** Slot key ("home.hero") to picture. A slot left out shows the page's texture. */
export type SiteImages = Record<string, SiteImageData>

/**
 * The server writes the page images into the page (apps.core.spa), so a page's pictures
 * start loading without waiting for a request. The Vite dev server, which serves the page
 * itself, has none, so they are fetched once instead.
 */
function fromPage(): SiteImages | null {
  const element = typeof document === 'undefined' ? null : document.getElementById('rose-site-images')
  if (!element?.textContent) return null
  try {
    return JSON.parse(element.textContent) as SiteImages
  } catch {
    return null
  }
}

let known: SiteImages | null = fromPage()
let loading: Promise<SiteImages> | null = null

export function loadSiteImages(): Promise<SiteImages> {
  if (known) return Promise.resolve(known)
  loading ??= request<{ images: SiteImages }>('/site-images/').then(
    (data) => {
      known = data.images
      return known
    },
    (error: unknown) => {
      loading = null
      throw error
    },
  )
  return loading
}

/** One slot's picture: undefined while loading, null when the slot shows its fallback. */
export function useSiteImage(slot: string): SiteImageData | null | undefined {
  const [images, setImages] = useState<SiteImages | null>(known)
  useEffect(() => {
    if (images) return
    let live = true
    loadSiteImages().then(
      (loaded) => live && setImages(loaded),
      // Unreachable: the slot keeps its texture rather than showing an error.
      () => live && setImages({}),
    )
    return () => {
      live = false
    }
  }, [images])
  if (!images) return undefined
  return images[slot] ?? null
}
