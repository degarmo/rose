import { useSiteImage } from '@/lib/siteImages'
import { type AspectRatio, ImageFrame, type PlaceholderTexture } from './ImageFrame'

interface SiteImageProps {
  /** The page image's key, as Admin > Page images lists it: "home.hero". */
  slot: string
  ratio?: AspectRatio
  placeholder?: PlaceholderTexture
  sizes?: string
  /** Above the fold: load at once rather than lazily. */
  priority?: boolean
  className?: string
}

/**
 * A fixed picture on a public page, chosen by staff in Admin > Page images. It carries
 * its own description and focal point; an empty slot shows the page's texture.
 */
export function SiteImage({ slot, ...frame }: SiteImageProps) {
  const image = useSiteImage(slot)
  return <ImageFrame remote={image} focal={image?.focal} alt="" {...frame} />
}
