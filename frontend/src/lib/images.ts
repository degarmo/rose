import rawManifest from '@image-manifest'

export interface ImageVariant {
  width: number
  height: number
  filename: string
}

export interface ManifestImage {
  filename: string
  width: number
  height: number
  variants: ImageVariant[]
  source: string
  original_url: string
  license: string
  credit: string
  /** Describes the picture; pages that pass no alt text of their own use it. */
  alt?: string
  faces_visible: boolean
  consent_confirmed: boolean
}

interface ImageManifest {
  images: ManifestImage[]
}

const manifest = rawManifest as unknown as ImageManifest
const byFilename = new Map(manifest.images.map((image) => [image.filename, image]))

/**
 * Where site imagery lives: the public bucket in production (the server puts
 * its address in a meta tag when it serves index.html), /images in development.
 */
function siteImagesBase(): string {
  const meta = typeof document === 'undefined' ? null : document.querySelector('meta[name="rose-site-images"]')
  const value = meta?.getAttribute('content')?.trim()
  return (value || '/images/').replace(/\/$/, '')
}

export const IMAGE_BASE_PATH = siteImagesBase()

/** An image may render only when it shows no faces, or everyone visible consented. */
export function isDisplayable(image: Pick<ManifestImage, 'faces_visible' | 'consent_confirmed'>) {
  return !image.faces_visible || image.consent_confirmed
}

/** Look up a local image. Returns null when missing or not cleared to display. */
export function resolveImage(filename: string): ManifestImage | null {
  const image = byFilename.get(filename)
  if (!image || !isDisplayable(image)) return null
  return image
}

export function srcSetFor(image: ManifestImage): string {
  return image.variants
    .map((variant) => `${IMAGE_BASE_PATH}/${variant.filename} ${variant.width}w`)
    .join(', ')
}
