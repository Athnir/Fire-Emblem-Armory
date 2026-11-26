/** A weapon's range as the app writes it, a hyphen between its ends ("1-2", the user's call, 2026-11-26), however its source writes
 * it: Fates' Serenes Forest data "1~2", the DS and 3DS games' generators "1–2". Anything else ("—", "Mag/2") stays as it is. */
export const rangeText = (range: string) => range.replace(/(\d)\s*[–~]\s*(\d)/g, '$1-$2')
