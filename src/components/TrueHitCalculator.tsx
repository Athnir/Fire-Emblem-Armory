import { useState } from 'react'
import { formatBasisPoints, trueHit } from '../logic/trueHit'
import type { HitSystem } from '../logic/trueHit'

const ADJUSTED_NOTE = {
  high: 'Capped at 100%.',
  low: 'Raised to 0%.',
  fraction: 'Displayed hit is always a whole number, so the decimals were dropped.',
} as const

// Chart geometry: 0–100 displayed on x, 0–100 true on y, in a 100×100 plot box with room for labels.
const PAD = { left: 30, right: 8, top: 8, bottom: 26 }
const W = 320
const H = 240
const plotW = W - PAD.left - PAD.right
const plotH = H - PAD.top - PAD.bottom
const x = (v: number) => PAD.left + (v / 100) * plotW
const y = (v: number) => PAD.top + plotH - (v / 100) * plotH

const curve = (system: HitSystem) =>
  Array.from({ length: 101 }, (_, d) => `${x(d)},${y(trueHit(system, d).trueHitBasisPoints / 100)}`).join(' ')

/** How each system rolls, in a sentence or two. */
const EXPLAIN: Record<HitSystem, (game: string) => string> = {
  'hybrid-fates': (game) =>
    `Below 50, ${game} rolls once and the displayed hit is exact. From 50 up, the real chance is higher than shown, by the most around a displayed 78 (+10.21). The same formula applies to enemy attacks, so a displayed 30 against you really is 30.`,
  '1rn': (game) =>
    `${game} rolls a single number, so the displayed hit is exactly the chance to hit, for your attacks and the enemy's alike. Read in the game's own code: one draw of 0-99, a hit when it's below the displayed hit.`,
  '2rn': (game) =>
    `${game} rolls two numbers and averages them, so high hit rates land more often than shown and low ones less often: a displayed 80 is really 92.20%, a displayed 30 only 18.30%. The same goes for enemy attacks against you. Crits roll a single number, so the displayed crit is exact.`,
}

export function TrueHitCalculator({ system, gameName }: { system: HitSystem; gameName: string }) {
  const [raw, setRaw] = useState('80')
  const parsed = raw.trim() === '' ? null : Number(raw)
  const result = parsed === null || Number.isNaN(parsed) ? null : trueHit(system, parsed)
  const truePct = result ? result.trueHitBasisPoints / 100 : null
  const gain = result && truePct !== null ? truePct - result.displayed : 0

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <section className="flex flex-col gap-4 rounded border border-neutral-800 p-4">
        <label className="flex flex-col gap-1 text-sm text-neutral-400">
          Displayed hit
          <input
            type="number"
            inputMode="numeric"
            min={0}
            max={100}
            value={raw}
            onChange={(e) => setRaw(e.target.value)}
            className="w-32 rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-2xl text-neutral-100"
          />
        </label>

        {result ? (
          <div>
            <p className="text-sm text-neutral-400">True chance to hit</p>
            <p className="text-5xl font-bold text-emerald-400">{formatBasisPoints(result.trueHitBasisPoints)}%</p>
            <p className="mt-1 text-sm text-neutral-400">
              Displayed {result.displayed} → true {formatBasisPoints(result.trueHitBasisPoints)}%
              {gain > 0 && <span className="text-emerald-500"> (+{gain.toFixed(2)})</span>}
            </p>
            {result.adjusted && <p className="mt-1 text-sm text-amber-400">{ADJUSTED_NOTE[result.adjusted]}</p>}
          </div>
        ) : (
          <p className="text-neutral-500">Enter the hit shown on the battle forecast.</p>
        )}

        <div className="text-sm text-neutral-400">
          <p>{EXPLAIN[system](gameName)}</p>
          <p className="mt-2 text-neutral-500">
            Formula and values:{' '}
            <a
              href="https://fireemblemwiki.org/wiki/True_hit"
              target="_blank"
              rel="noreferrer"
              className="underline hover:text-neutral-300"
            >
              Fire Emblem Wiki
            </a>
            .
          </p>
        </div>
      </section>

      <section className="rounded border border-neutral-800 p-4">
        <p className="mb-2 text-sm text-neutral-400">Displayed vs. true hit</p>
        <svg viewBox={`0 0 ${W} ${H}`} className="w-full max-w-md" role="img" aria-label={`Chart of displayed hit against true hit in ${gameName}`}>
          {[0, 25, 50, 75, 100].map((t) => (
            <g key={t}>
              <line x1={x(0)} x2={x(100)} y1={y(t)} y2={y(t)} className="stroke-neutral-800" />
              <text x={PAD.left - 6} y={y(t) + 3} textAnchor="end" className="fill-neutral-500 text-[9px]">
                {t}
              </text>
              <text x={x(t)} y={H - PAD.bottom + 12} textAnchor="middle" className="fill-neutral-500 text-[9px]">
                {t}
              </text>
            </g>
          ))}
          <text x={x(50)} y={H - 4} textAnchor="middle" className="fill-neutral-500 text-[9px]">
            Displayed hit
          </text>
          {/* Dashed diagonal = "what you see is what you get", for reference against the real curve. */}
          <line x1={x(0)} y1={y(0)} x2={x(100)} y2={y(100)} strokeDasharray="3 3" className="stroke-neutral-600" />
          <polyline points={curve(system)} fill="none" strokeWidth={2} className="stroke-emerald-400" />
          {result && truePct !== null && (
            <circle cx={x(result.displayed)} cy={y(truePct)} r={4} className="fill-emerald-300 stroke-neutral-950" strokeWidth={1.5} />
          )}
        </svg>
        <p className="mt-1 text-xs text-neutral-500">Dashed line: displayed = true. Green: what {gameName} actually rolls.</p>
      </section>
    </div>
  )
}
