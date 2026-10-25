import { describe, expect, it } from 'vitest'
import { fatesTrueHit, formatBasisPoints, oneRnTrueHit, trueHit } from '../trueHit'

// Fire Emblem Wiki's Fates true hit table, displayed 50–99: https://fireemblemwiki.org/wiki/True_hit
const WIKI_TABLE: Record<number, string> = {
  50: '50.00', 51: '51.42', 52: '52.86', 53: '54.32', 54: '55.79',
  55: '57.26', 56: '58.74', 57: '60.23', 58: '61.72', 59: '63.21',
  60: '64.70', 61: '66.18', 62: '67.65', 63: '69.12', 64: '70.57',
  65: '72.01', 66: '73.43', 67: '74.82', 68: '76.20', 69: '77.55',
  70: '78.87', 71: '80.16', 72: '81.42', 73: '82.65', 74: '83.84',
  75: '85.00', 76: '86.11', 77: '87.18', 78: '88.21', 79: '89.20',
  80: '90.14', 81: '91.04', 82: '91.89', 83: '92.69', 84: '93.45',
  85: '94.16', 86: '94.83', 87: '95.45', 88: '96.03', 89: '96.56',
  90: '97.05', 91: '97.50', 92: '97.90', 93: '98.27', 94: '98.61',
  95: '98.91', 96: '99.18', 97: '99.42', 98: '99.63', 99: '99.82',
}

describe('fatesTrueHit', () => {
  it('matches every row of the Fire Emblem Wiki table (50–99)', () => {
    for (const [displayed, expected] of Object.entries(WIKI_TABLE)) {
      expect(formatBasisPoints(fatesTrueHit(Number(displayed)).trueHitBasisPoints), `displayed ${displayed}`).toBe(expected)
    }
  })

  it('is a straight single roll below 50', () => {
    expect(fatesTrueHit(0).trueHitBasisPoints).toBe(0)
    expect(fatesTrueHit(30).trueHitBasisPoints).toBe(3000)
    expect(fatesTrueHit(49).trueHitBasisPoints).toBe(4900)
  })

  it('treats 100 as a guaranteed hit', () => {
    expect(fatesTrueHit(100).trueHitBasisPoints).toBe(10000)
  })

  it('caps input above 100 and below 0, and drops decimals', () => {
    expect(fatesTrueHit(244)).toEqual({ displayed: 100, trueHitBasisPoints: 10000, adjusted: 'high' })
    expect(fatesTrueHit(-5)).toEqual({ displayed: 0, trueHitBasisPoints: 0, adjusted: 'low' })
    expect(fatesTrueHit(80.7)).toEqual({ displayed: 80, trueHitBasisPoints: 9014, adjusted: 'fraction' })
    expect(fatesTrueHit(80).adjusted).toBeUndefined()
  })
})

describe('twoRnTrueHit (FE9 and the other 2RN games)', () => {
  it('matches the wiki: displayed 80 is really 92.20%', async () => {
    const { twoRnTrueHit } = await import('../trueHit')
    expect(formatBasisPoints(twoRnTrueHit(80).trueHitBasisPoints)).toBe('92.20')
    expect(formatBasisPoints(twoRnTrueHit(30).trueHitBasisPoints)).toBe('18.30')
    expect(formatBasisPoints(twoRnTrueHit(50).trueHitBasisPoints)).toBe('50.50')
    expect(twoRnTrueHit(0).trueHitBasisPoints).toBe(0)
    expect(twoRnTrueHit(100).trueHitBasisPoints).toBe(10000)
    expect(twoRnTrueHit(244)).toEqual({ displayed: 100, trueHitBasisPoints: 10000, adjusted: 'high' })
  })
})

describe('oneRnTrueHit (Genealogy of the Holy War)', () => {
  it('is the displayed hit exactly, clamped to 0-100', () => {
    expect(oneRnTrueHit(80).trueHitBasisPoints).toBe(8000)
    expect(oneRnTrueHit(0).trueHitBasisPoints).toBe(0)
    expect(oneRnTrueHit(130)).toMatchObject({ displayed: 100, trueHitBasisPoints: 10000, adjusted: 'high' })
    expect(trueHit('1rn', 55).trueHitBasisPoints).toBe(5500)
  })
})
