import { useState } from 'react'
import type { Weapon } from '../data/types'
import type { ItemSource } from '../logic/itemSources'
import { cumulativeForgeBonus } from '../logic/forge'
import { ForgeTable } from './ForgeTable'
import { PixelIcon } from '../icons/PixelSprite'
import { BRAVE, MAGIC, MIGHT_UP, NO_CRIT, NO_FOLLOW_UP, NOT_FOR_PLAYER, REVERSED_TRIANGLE } from '../icons/sprites'
import { effectivenessIcons } from '../icons/weaponIcons'

const STAT_NAME: Record<string, string> = { hp: 'HP', str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res' }

const ROUTE_COLORS: Record<string, string> = {
  Birthright: 'bg-sky-900 text-sky-200',
  Conquest: 'bg-rose-900 text-rose-200',
  Revelation: 'bg-violet-900 text-violet-200',
  all: 'bg-neutral-700 text-neutral-200',
}

/** What the spoiler block lets the panel say: where to get the weapon as far as this chapter goes, and how far the Smithy forges. */
export interface BlockView {
  lines: string[]
  mapSources: ItemSource[]
  /** The Smithy's level (0: not built yet, so no forging notes at all) and the highest forge rank it reaches. */
  smithy: { level: number; maxRank: number }
}

export function WeaponDetailPanel({ weapon, block }: { weapon: Weapon; block?: BlockView }) {
  const [picked, setForgeLevel] = useState(0)
  const maxRank = block ? block.smithy.maxRank : 7
  const forgeLevel = Math.min(picked, maxRank)
  const showForge = !block || block.smithy.level > 0
  const mapSources = block ? block.mapSources : weapon.mapSources

  const bonus = cumulativeForgeBonus(weapon.canCrit, weapon.forgeable ? forgeLevel : 0)
  const mt = weapon.stats.mt + bonus.mt
  const hit = weapon.stats.hit + bonus.hit
  const crit = weapon.stats.crit + bonus.crit

  return (
    <div className="flex h-full flex-col gap-4 overflow-y-auto p-4">
      <div>
        <div className="flex flex-wrap items-center gap-2">
          <h2 className="text-xl font-semibold text-neutral-100">{weapon.name}</h2>
          {weapon.foeOnly && (
            <span className="rounded bg-red-950 px-2 py-0.5 text-xs text-red-300">
              <PixelIcon sprite={NOT_FOR_PLAYER} size={14} /> Foe only: enemy units carry it. It isn't available to the player.
            </span>
          )}
          {weapon.isMagic && (
            <span className="rounded bg-indigo-900 px-2 py-0.5 text-xs text-indigo-200">
              <PixelIcon sprite={MAGIC} size={14} /> Uses Magic for damage, not Strength
            </span>
          )}
          {weapon.effectiveness && (
            <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">
              {effectivenessIcons(weapon.effectiveness.vs).map((t) => (
                <PixelIcon key={t.label} sprite={t.sprite} size={14} />
              ))}{' '}
              Effective vs. {weapon.effectiveness.vs}
            </span>
          )}
          {weapon.strikesTwice && (
            <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">
              <PixelIcon sprite={BRAVE} size={14} /> Strikes twice when it starts the fight
            </span>
          )}
          {weapon.mightBoost && (
            <span className="rounded bg-red-950 px-2 py-0.5 text-xs text-red-200">
              <PixelIcon sprite={MIGHT_UP} size={14} /> Mt boost
            </span>
          )}
          {weapon.reversesTriangle && (
            <span className="rounded bg-cyan-900 px-2 py-0.5 text-xs text-cyan-200">
              <PixelIcon sprite={REVERSED_TRIANGLE} size={14} /> Reverses the weapon triangle
            </span>
          )}
          {weapon.canCrit === false && weapon.category !== 'Staff' && weapon.category !== 'Rod' && (
            <span className="rounded bg-rose-900 px-2 py-0.5 text-xs text-rose-200">
              <PixelIcon sprite={NO_CRIT} size={14} /> Can't crit or trigger offensive skills
            </span>
          )}
          {weapon.canFollowUp === false && (
            <span className="rounded bg-neutral-700 px-2 py-0.5 text-xs text-neutral-200">
              <PixelIcon sprite={NO_FOLLOW_UP} size={14} /> Cannot follow up
            </span>
          )}
        </div>
        <p className="text-sm text-neutral-500">
          {weapon.category} · Rank {weapon.rank} · {weapon.faction}
        </p>
      </div>

      {weapon.forgeable && showForge && (
        <label className="flex items-center gap-2 text-sm text-neutral-300">
          Level:
          <select
            value={forgeLevel}
            onChange={(e) => setForgeLevel(Number(e.target.value))}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            {[0, 1, 2, 3, 4, 5, 6, 7].filter((r) => r <= maxRank).map((r) => (
              <option key={r} value={r}>
                {r === 0 ? 'Base' : `+${r}`}
              </option>
            ))}
          </select>
          {forgeLevel > 0 && <span className="text-xs text-neutral-500">stats below reflect this forge level</span>}
        </label>
      )}

      <div className="grid grid-cols-3 gap-2 text-sm sm:grid-cols-6">
        {(
          [
            ['Mt', mt],
            ['Hit', hit],
            ['Crit', crit],
            ['Avoid', weapon.stats.avoid],
            ['Dodge', weapon.stats.dodge],
            ['Rng', weapon.stats.range],
            ...(weapon.stats.uses !== undefined ? ([['Uses', weapon.stats.uses]] as const) : []),
          ] as const
        ).map(([label, value]) => (
          <div key={label} className="rounded bg-neutral-800 px-2 py-1 text-center">
            <div className="text-neutral-500">{label}</div>
            <div className="text-neutral-100">{value}</div>
          </div>
        ))}
      </div>
      <p className="-mt-2 text-xs text-neutral-600">Avoid: chance to be missed entirely · Dodge: chance to avoid being critically hit</p>

      {weapon.effects && <p className="text-sm text-neutral-300">{weapon.effects}</p>}
      {weapon.game && Object.keys(weapon.game.stats).length > 0 && (
        <p className="text-sm text-neutral-300">
          <span className="text-neutral-500">While equipped: </span>
          {Object.entries(weapon.game.stats)
            .map(([k, v]) => `${STAT_NAME[k] ?? k} ${v! > 0 ? '+' : '−'}${Math.abs(v!)}`)
            .join(', ')}
        </p>
      )}
      {weapon.game && (weapon.category === 'Staff' || weapon.category === 'Rod') && weapon.game.mt > 0 && (
        <p className="text-sm text-neutral-300">
          <span className="text-neutral-500">Healing power: </span>
          {weapon.game.mt} <span className="text-neutral-500">(the game's Mt figure for staves)</span>
        </p>
      )}

      {weapon.effectiveness && (
        <div className="rounded bg-neutral-800 px-3 py-2 text-sm">
          <div className="text-neutral-200">
            Effective vs. {weapon.effectiveness.vs}: Might ×{weapon.effectiveness.multiplier} (
            {mt} → {mt * weapon.effectiveness.multiplier})
          </div>
          <div className="text-neutral-500">
            {weapon.effectiveness.nonEffectivePenalty ? (
              <>
                Otherwise: Might {weapon.effectiveness.nonEffectivePenalty.mt}, Hit{' '}
                {weapon.effectiveness.nonEffectivePenalty.hit} ({mt} →{' '}
                {mt + weapon.effectiveness.nonEffectivePenalty.mt}, {hit} →{' '}
                {hit + weapon.effectiveness.nonEffectivePenalty.hit})
              </>
            ) : (
              'Otherwise: no penalty — keeps its listed stats, just without the bonus'
            )}
          </div>
        </div>
      )}

      <div className="flex flex-wrap gap-1">
        {!block && !weapon.foeOnly && weapon.availability.routes.length === 0 && !weapon.isAmiibo && !weapon.isDlc && (
          <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">Not player-obtainable</span>
        )}
        {/* Amiibo-scan/DLC items with no routes aren't unobtainable — they're just not gated by story
            route at all (any save works), which is a different thing from the route-tally feature
            this badge set otherwise reports on. */}
        {!block && weapon.availability.routes.length === 0 && (weapon.isAmiibo || weapon.isDlc) && (
          <span className="rounded bg-neutral-800 px-2 py-0.5 text-xs text-neutral-500">Not route-gated</span>
        )}
        {(block ? [] : weapon.availability.routes).map((route) => (
          <span key={route} className={`rounded px-2 py-0.5 text-xs ${ROUTE_COLORS[route]}`}>
            {route === 'all' ? 'All routes' : route}
          </span>
        ))}
        {weapon.isDlc && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">DLC</span>}
        {weapon.isAmiibo && <span className="rounded bg-amber-900 px-2 py-0.5 text-xs text-amber-200">Amiibo</span>}
        {weapon.isMyCastle && (
          <span className="rounded bg-cyan-900 px-2 py-0.5 text-xs text-cyan-200">My Castle</span>
        )}
        {weapon.isPersonal && (
          <span className="rounded bg-emerald-900 px-2 py-0.5 text-xs text-emerald-200">
            Personal{weapon.personalTo ? ` · ${weapon.personalTo}` : ''}
          </span>
        )}
      </div>
      {/* Under the block the hand-written source (it names later chapters) gives way to what this chapter allows. */}
      {block ? (
        block.lines.map((line) => (
          <p key={line} className="text-sm text-neutral-400">
            {line}
          </p>
        ))
      ) : (
        <p className="text-sm text-neutral-500">{weapon.availability.source}</p>
      )}
      {weapon.rankRewards?.map((r) => (
        <p key={r.track} className="text-sm text-cyan-200">
          My Castle rank reward: {r.points.toLocaleString()} {r.track}
        </p>
      ))}

      {mapSources && mapSources.length > 0 && (
        <div className="text-sm">
          <p className="text-neutral-400">On the maps (from the game's files)</p>
          <ul className="mt-1 space-y-0.5">
            {mapSources.map((s) => {
              const cross = s.routes.some((r) => weapon.availability.crossRoutes?.includes(r))
              return (
                <li key={`${s.mapId}${s.how}`} className="text-neutral-300">
                  <span className="text-neutral-100">{s.map}</span>
                  <span className="text-neutral-500"> · {s.how}</span>
                  {s.dlc && <span className="ml-1 rounded bg-amber-900 px-1 text-xs text-amber-200">DLC</span>}
                  {cross && !s.dlc && <span className="ml-1 rounded bg-neutral-700 px-1 text-xs text-neutral-200">Cross-route</span>}
                </li>
              )
            })}
          </ul>
        </div>
      )}

      <div className="text-sm">
        <span className="text-neutral-500">Shop price: </span>
        {weapon.purchase ? (
          <span className="text-neutral-200">
            Buy {weapon.purchase.buy}
            {weapon.purchase.sell !== undefined ? ` · Sell ${weapon.purchase.sell}` : ' · sell price not verified'}
          </span>
        ) : (
          <span className="text-neutral-500">
            Not sold in any shop{weapon.game?.sell ? ` · sells for ${weapon.game.sell.toLocaleString()}` : ''}
          </span>
        )}
      </div>

      {showForge && (
        <div>
          <h3 className="mb-2 text-sm font-semibold text-neutral-300">Smithy forging</h3>
          {block && (
            <p className="mb-2 text-sm text-neutral-400">
              Your Smithy is level {block.smithy.level}: it forges up to +{block.smithy.maxRank}.
            </p>
          )}
          <ForgeTable weapon={weapon} highlightRank={forgeLevel} maxRank={maxRank} />
        </div>
      )}
    </div>
  )
}
