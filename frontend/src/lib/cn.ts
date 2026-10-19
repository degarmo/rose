import { extendTailwindMerge } from 'tailwind-merge'

/**
 * Joins class names, and when two set the same thing (a size, a padding, display) the last
 * one wins, so a `className` passed to a component reliably overrides its defaults. The
 * design's own text sizes, corners and shadows (index.css) are registered so they are not
 * mistaken for colours.
 */
const merge = extendTailwindMerge({
  extend: {
    theme: {
      text: ['display', 'h1', 'h2-lg', 'h2', 'card-title', 'lead', 'body', 'label', 'meta', 'app'],
      radius: ['app', 'field', 'sheet', 'card', 'panel'],
      shadow: ['modal', 'sheet', 'panel'],
    },
  },
})

export function cn(...classes: Array<string | false | null | undefined>): string {
  return merge(classes)
}
