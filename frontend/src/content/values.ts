import type { PageCopy } from '@/lib/pageContent'

/** How many values the skeleton shows while the copy loads. */
const VALUES_WHILE_LOADING = [1, 2, 3, 4]

/**
 * The values are staff-editable copy on the "values" page (values.1.title,
 * values.1.short, values.1.long, ...). Returns the value numbers, in order.
 */
export function valueNumbers(copy: PageCopy): number[] {
  return copy.status === 'loading' ? VALUES_WHILE_LOADING : copy.items('values')
}
