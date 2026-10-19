import { GUTTER } from '@/components/ui'
import { cn } from '@/lib/cn'

/** The quiet "Back" beside a step's main button (design: Join step 2). */
export const BACK_BUTTON = 'inline-flex h-12 items-center self-start px-3 font-semibold text-fg-muted transition-colors hover:text-fg disabled:cursor-not-allowed'

/** The join flow's page frame: the site gutter, 64px from the top on desktop. */
export const JOIN_FRAME = cn('mx-auto w-full max-w-[1440px] pb-12 pt-6 lg:pb-16 lg:pt-16', GUTTER)
