import { useEffect } from 'react'
import { DOUBLE_ESCAPE_WINDOW_MS, leaveNow } from './quickExit'

/** Listens for Escape pressed twice in quick succession, anywhere on the page. */
export function useDoubleEscapeExit() {
  useEffect(() => {
    let lastPress = Number.NEGATIVE_INFINITY
    function onKeyDown(event: KeyboardEvent) {
      if (event.key !== 'Escape' || event.repeat) return
      const now = performance.now()
      if (now - lastPress <= DOUBLE_ESCAPE_WINDOW_MS) {
        leaveNow()
        return
      }
      lastPress = now
    }
    // Capture phase, so dialogs that handle Escape cannot swallow it first.
    window.addEventListener('keydown', onKeyDown, true)
    return () => window.removeEventListener('keydown', onKeyDown, true)
  }, [])
}
