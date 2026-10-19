import { HandHeart, KeyRound, ShieldCheck, UsersRound, type LucideIcon } from 'lucide-react'

/**
 * Icons for the values, in order. The words are staff-editable copy on the
 * "values" page (values.1.title, values.1.short, values.1.long, ...).
 */
export const VALUE_ICONS: LucideIcon[] = [KeyRound, UsersRound, ShieldCheck, HandHeart]

export function valueIcon(index: number): LucideIcon {
  return VALUE_ICONS[(index - 1) % VALUE_ICONS.length]
}
