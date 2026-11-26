export function parseMinorUnits(value: string | number): number {
  const text = String(value).trim()
  const match = /^(\d+)(?:\.(\d{1,2}))?$/.exec(text)
  if (!match) {
    throw new Error(`Invalid monetary amount: ${text}`)
  }
  const fractional = (match[2] ?? '').padEnd(2, '0')
  const minorUnits = BigInt(match[1]) * 100n + BigInt(fractional || '0')
  if (minorUnits > 999_999_999_999n) {
    throw new Error('Monetary amount exceeds the supported 12-digit precision')
  }
  return Number(minorUnits)
}

export function formatMinorUnits(value: number): string {
  return `${Math.floor(value / 100)}.${String(value % 100).padStart(2, '0')}`
}

export function calculateTaxMinorUnits(
  amount: number,
  ratePercent: string | number | null,
  inclusive: boolean,
): number {
  if (!ratePercent) return 0
  const match = /^(0|[1-9]\d*)(?:\.(\d{1,2}))?$/.exec(String(ratePercent))
  if (!match) throw new Error(`Invalid tax rate: ${ratePercent}`)

  const rateHundredths = Number(match[1]) * 100 + Number((match[2] ?? '').padEnd(2, '0') || '0')
  const denominator = BigInt(inclusive ? 10_000 + rateHundredths : 10_000)
  const numerator = BigInt(amount) * BigInt(rateHundredths)
  return Number((2n * numerator + denominator) / (2n * denominator))
}
