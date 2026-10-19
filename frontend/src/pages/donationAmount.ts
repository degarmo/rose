/** "$25", "25.50" or "1,000" as cents, or null when it is not an amount. */
export function parseAmount(text: string): number | null {
  const cleaned = text.replace(/[$,\s]/g, '')
  if (!/^\d+(\.\d{1,2})?$/.test(cleaned)) return null
  return Math.round(Number(cleaned) * 100)
}

export function amountError(cents: number | null, minimumCents: number, maximumCents: number): string | undefined {
  if (cents === null) return 'Enter an amount in dollars, like 30 or 30.00.'
  if (cents < minimumCents) return `The smallest gift we can take online is $${minimumCents / 100}.`
  if (cents > maximumCents)
    return `For gifts over $${(maximumCents / 100).toLocaleString('en-US')}, please get in touch so we can thank you properly.`
  return undefined
}
