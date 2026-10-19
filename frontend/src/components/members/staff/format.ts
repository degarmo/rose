import { formatMoney } from '@/lib/format'
import type { Count, Money } from '@/lib/safetyApi'

/** A count, or "Fewer than 5" where the server withheld it. */
export function countText(count: Count | null | undefined) {
  if (!count) return '–'
  return count.value === null ? `Fewer than ${count.fewer_than ?? 5}` : count.value.toLocaleString('en-US')
}

/** A sum of money, or a note that it came from too few payments to show. */
export function moneyText(money: Money) {
  return money.cents === null ? `Fewer than ${money.fewer_than ?? 5} payments` : formatMoney(money.cents)
}
