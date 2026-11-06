import { useMemo, useRef, useState } from 'react'
import type { ChapterMap } from '../data/maps/types'
import { FE16_BATTALIONS, FE16_BATTALION_SOURCES, FE16_GAMBITS } from '../data/fe16/fe16Battalions'
import type { Fe16Battalion, Fe16BattalionSource, Fe16BattalionStat } from '../data/fe16/fe16BattalionTypes'
import { FE16_STORY } from '../data/fe16/fe16MapSet'
import { PixelIcon } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import { ARMOR_HELM, HORSE_HEAD, MAGIC, NOT_FOR_PLAYER, SWORD_ICON, WING } from '../icons/sprites'
import { turnsUpAt } from '../logic/spoiler'
import { onDifficulty, useDifficulty } from './Difficulty'
import { GambitArea, GambitAreaLegend } from './GambitArea'
import { useReach } from './Reach'

const KIND_ICON: Record<Fe16Battalion['kind'], Sprite> = { Infantry: SWORD_ICON, Armored: ARMOR_HELM, Cavalry: HORSE_HEAD, Flying: WING }
const STATS: Fe16BattalionStat[] = ['Phys', 'Mag', 'Hit', 'Crit', 'Avo', 'Prot', 'Res', 'Cha']
const RANKS = ['E', 'D', 'C', 'B', 'A'] as const
const GAMBIT_KIND = { physical: 'Attack (against Prt)', magic: 'Magic attack (against Rsl)', support: 'Support (for allies)' }
/** The houses whose White Clouds guild lines a route list covers, by the routes they lead to. */
const HOUSE_OF: Record<string, string> = { cf: 'Black Eagles', ss: 'Black Eagles', am: 'Blue Lions', vw: 'Golden Deer' }
/** The routes still open on the route the spoiler block is walking (its choices so far: 'be', 'be/cf', 'bl'...). */
const OPEN_ROUTES: Record<string, string[]> = { be: ['cf', 'ss'], 'be/cf': ['cf'], 'be/ss': ['ss'], bl: ['am'], gd: ['vw'] }
const NUM = 'w-0 py-1 pr-2 sm:pr-3'
const signed = (v: number) => (v > 0 ? `+${v}` : `${v}`)

/**
 * Three Houses' battalions: a tab of their own (the user's call), each with its stats by level, the Authority it needs, what can equip
 * it, its gambit with the gambit's area drawn, and where it turns up (the Battalion Guild by house and route, the battles that give it,
 * quests). Read from the game's battalion, gambit and guild tables and program (scripts/build-fe16-battalions.py).
 */
export function Fe16Battalions({ routeName }: { routeName: (m: ChapterMap) => string | undefined }) {
  const reach = useReach()
  const difficulty = useDifficulty()
  const story = reach.story ?? FE16_STORY
  const open = reach.on && reach.route ? OPEN_ROUTES[reach.route] : undefined
  const sourceAt = (s: Fe16BattalionSource) => turnsUpAt(story, s.mapId, s.kind.endsWith('-later'))
  const sourcesOf = (b: Fe16Battalion) =>
    (FE16_BATTALION_SOURCES[b.name] ?? []).filter(
      (s) => onDifficulty(difficulty, s.difficulties) && (!open || !s.routes || s.routes.some((r) => open.includes(r))),
    )
  /** The first chapter a battalion turns up in (its story index); a guild line that stops offering it doesn't count. */
  const firstAt = (b: Fe16Battalion) => Math.min(Infinity, ...sourcesOf(b).filter((s) => s.kind !== 'guild-gone').map(sourceAt))

  // With the spoiler block on, a battalion is listed from the first chapter it turns up in and stays listed; new ones get a mark.
  const { battalions, fresh } = useMemo(() => {
    const listed = FE16_BATTALIONS.filter((b) => sourcesOf(b).length)
    if (!reach.on) return { battalions: listed, fresh: new Set<number>() }
    const shown = listed.filter((b) => firstAt(b) <= reach.at)
    return { battalions: shown, fresh: new Set(shown.filter((b) => reach.at > 0 && firstAt(b) === reach.at).map((b) => b.id)) }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [reach, difficulty])
  const [kind, setKind] = useState('all')
  const [rank, setRank] = useState('all')
  const [search, setSearch] = useState('')
  const [hideFoeOnly, setHideFoeOnly] = useState(false)
  const [selectedId, setSelectedId] = useState(FE16_BATTALIONS[0].id)
  const detailRef = useRef<HTMLDivElement>(null)
  const hasFoeOnly = battalions.some((b) => b.foeOnly)
  const filtered = battalions.filter(
    (b) =>
      (kind === 'all' || b.kind === kind) &&
      (rank === 'all' || b.rank === rank) &&
      !(hideFoeOnly && b.foeOnly) &&
      (!search ||
        b.name.toLowerCase().includes(search.toLowerCase()) ||
        FE16_GAMBITS[b.gambit].name.toLowerCase().includes(search.toLowerCase())),
  )
  const selected = battalions.find((b) => b.id === selectedId) ?? battalions[0] ?? null

  function select(id: number) {
    setSelectedId(id)
    const panel = detailRef.current
    if (!panel) return
    const top = panel.getBoundingClientRect().top
    if (top < 0 || top > window.innerHeight * 0.5) panel.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  return (
    <>
      <p className="max-w-3xl text-sm text-neutral-400">
        A battalion adds its stats to the unit leading it and gives it a gambit. A unit can equip one whose rank its Authority has
        reached, and a unit whose class flies only a flying one. The Battalion Guild offers each of its battalions once. Stats rise with
        the battalion's level, 1 to 5 (not Cha or endurance).
      </p>
      <div className="flex flex-wrap gap-3">
        <select value={kind} onChange={(e) => setKind(e.target.value)} aria-label="Kind" className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1">
          <option value="all">All kinds</option>
          {Object.keys(KIND_ICON).map((k) => (
            <option key={k} value={k}>
              {k}
            </option>
          ))}
        </select>
        <select value={rank} onChange={(e) => setRank(e.target.value)} aria-label="Authority rank" className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1">
          <option value="all">Any Authority</option>
          {RANKS.map((r) => (
            <option key={r} value={r}>
              Authority {r}
            </option>
          ))}
        </select>
        {hasFoeOnly && (
          <label className="flex items-center gap-1 text-sm text-neutral-300">
            <input type="checkbox" checked={hideFoeOnly} onChange={(e) => setHideFoeOnly(e.target.checked)} />
            Hide foe-only
          </label>
        )}
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search battalion or gambit..."
          className="flex-1 rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        />
      </div>
      {hasFoeOnly && !hideFoeOnly && (
        <p className="text-xs text-neutral-500">
          <PixelIcon sprite={NOT_FOR_PLAYER} size={12} /> marks battalions only foes lead; nothing gives them to you.
        </p>
      )}
      <div className="grid flex-1 grid-cols-1 gap-4 lg:grid-cols-2">
        <div className="overflow-x-auto rounded border border-neutral-800">
          <table className="w-full border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-700 text-left text-neutral-400">
                <th className="py-1 pl-2 pr-1 sm:pr-3">Name</th>
                <th className={NUM}>Auth.</th>
                <th className="py-1 pr-2 sm:pr-3">Gambit</th>
                <th className={NUM}>End.</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((b) => (
                <tr
                  key={b.id}
                  onClick={() => select(b.id)}
                  className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${selected?.id === b.id ? 'bg-neutral-800' : ''}`}
                >
                  <td className="py-1 pl-2 pr-1 text-neutral-100 sm:pr-3">
                    <PixelIcon sprite={KIND_ICON[b.kind]} size={14} title={b.kind} /> {b.name}
                    {b.foeOnly && (
                      <span className="ml-1 inline-flex" title="Foe only: led by enemy units, not available to the player">
                        <PixelIcon sprite={NOT_FOR_PLAYER} size={14} title="Foe only" />
                      </span>
                    )}
                    {fresh.has(b.id) && <span className="ml-1 rounded bg-emerald-900 px-1 text-[10px] text-emerald-200">new</span>}
                  </td>
                  <td className={`${NUM} text-neutral-400`}>{b.rank}</td>
                  <td className="py-1 pr-2 text-neutral-300 sm:pr-3">{FE16_GAMBITS[b.gambit].name}</td>
                  <td className={NUM}>{b.endurance}</td>
                </tr>
              ))}
              {filtered.length === 0 && (
                <tr>
                  <td colSpan={4} className="py-4 text-center text-neutral-500">
                    No battalions match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        <div
          ref={detailRef}
          className="scroll-mt-4 rounded border border-neutral-800 lg:sticky lg:top-4 lg:max-h-[calc(100vh-2rem)] lg:self-start lg:overflow-y-auto"
        >
          {selected ? (
            <Detail
              key={selected.id}
              battalion={selected}
              routeName={routeName}
              sources={sourcesOf(selected)
                .filter((s) => !reach.on || sourceAt(s) <= reach.at)
                .sort((a, b) => sourceAt(a) - sourceAt(b))}
            />
          ) : (
            <p className="p-4 text-neutral-500">Nothing to show yet.</p>
          )}
        </div>
      </div>
    </>
  )
}

function Detail({
  battalion: b,
  sources,
  routeName,
}: {
  battalion: Fe16Battalion
  sources: Fe16BattalionSource[]
  routeName: (m: ChapterMap) => string | undefined
}) {
  const reach = useReach()
  const g = FE16_GAMBITS[b.gambit]
  const mapOf = (id: string) => FE16_STORY.maps.find((m) => m.id === id)
  // Under the spoiler block the guild's price is only said while the guild offers it.
  const offered = !reach.on || (sources.some((s) => s.kind === 'guild') && !sources.some((s) => s.kind === 'guild-gone'))
  const rows = useMemo(() => {
    const out = new Map<string, { text: string; later: boolean; label?: string; chapters: string[] }>()
    for (const s of sources) {
      const m = mapOf(s.mapId)
      // A White Clouds guild line names the houses it holds for, where not all three; any other line its map's route.
      const houses = s.routes ? [...new Set(s.routes.map((r) => HOUSE_OF[r]))] : []
      const label = s.routes ? (houses.length < 3 ? houses.join(', ') : undefined) : m ? routeName(m) : undefined
      const later = s.kind.endsWith('-later')
      const key = JSON.stringify([s.text, later, label])
      const row = out.get(key) ?? { text: s.text, later, label, chapters: [] }
      const chapter = m ? FE16_STORY.short(m) : s.mapId
      if (!row.chapters.includes(chapter)) row.chapters.push(chapter)
      out.set(key, row)
    }
    return [...out.values()]
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sources])
  const shown = STATS.filter((s) => b.stats[s].some((v) => v !== 0))
  const chip = (label: string, value: string | number) => (
    <div className="rounded bg-neutral-900 px-2 py-1 text-center">
      <p className="text-xs text-neutral-500">{label}</p>
      <p className="text-neutral-100">{value}</p>
    </div>
  )
  return (
    <div className="flex flex-col gap-3 p-4 text-sm">
      <div>
        <h2 className="text-xl font-semibold text-neutral-100">{b.name}</h2>
        <p className="text-neutral-500">
          <PixelIcon sprite={KIND_ICON[b.kind]} size={14} /> {b.kind} battalion · Authority {b.rank}
        </p>
      </div>
      {b.foeOnly && (
        <p className="flex items-center gap-1 text-red-300">
          <PixelIcon sprite={NOT_FOR_PLAYER} size={14} /> Led only by foes; you can't get it.
        </p>
      )}
      <div className="grid grid-cols-3 gap-2 sm:grid-cols-4">
        {chip('Authority', b.rank)}
        {chip('Endurance', b.endurance)}
        {b.price !== undefined && offered && chip('Price', b.price.toLocaleString())}
      </div>
      <p className="text-neutral-300">
        Needs Authority {b.rank} or higher.{' '}
        {b.kind === 'Flying'
          ? 'A flying battalion: any unit can lead it, and it is the only kind a unit whose class flies can.'
          : 'A unit whose class flies can’t lead it: fliers take only flying battalions.'}
      </p>
      {shown.length > 0 && (
        <div className="overflow-x-auto">
          <table className="border-collapse text-xs sm:text-sm">
            <thead>
              <tr className="border-b border-neutral-800 text-neutral-500">
                <th className="py-1 pr-4 text-left font-normal">Level</th>
                {[1, 2, 3, 4, 5].map((lv) => (
                  <th key={lv} className="py-1 pr-3 text-right font-normal">
                    {lv}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {shown.map((s) => (
                <tr key={s} className="border-b border-neutral-800">
                  <td className="py-1 pr-4 text-neutral-400">{s}</td>
                  {b.stats[s].map((v, i) => (
                    <td key={i} className={`py-1 pr-3 text-right ${v < 0 ? 'text-red-300' : 'text-neutral-100'}`}>
                      {signed(v)}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <div className="flex flex-col gap-2 rounded border border-neutral-800 p-3">
        <div>
          <h3 className="font-semibold text-neutral-100">
            {g.kind === 'magic' && <PixelIcon sprite={MAGIC} size={14} />} Gambit: {g.name}
          </h3>
          <p className="text-neutral-500">{GAMBIT_KIND[g.kind]}</p>
        </div>
        <div className="grid grid-cols-4 gap-2">
          {g.mt !== undefined && chip(g.heals ? 'Heals (Mt)' : 'Mt', g.mt)}
          {chip('Hit', g.hit)}
          {chip('Rng', g.range[0] === g.range[1] ? g.range[0] : `${g.range[0]}-${g.range[1]}`)}
          {chip('Uses', g.uses)}
        </div>
        <p className="text-neutral-300">{g.help}</p>
        {g.effective && <p className="text-amber-200">Effective against {g.effective.join(' and ')}.</p>}
        <div className="flex flex-wrap items-end gap-3">
          <GambitArea gambit={g} />
          <div className="min-w-[12rem] flex-1">
            <GambitAreaLegend />
          </div>
        </div>
      </div>
      {rows.length > 0 && (
        <div>
          <p className="text-neutral-500">Where it turns up</p>
          <ul className="list-disc space-y-0.5 pl-5 text-neutral-300">
            {rows.map((r, i) => (
              <li key={i}>
                {r.text}
                {r.label && ` (${r.label})`}
                {r.later && ', counted from the next chapter'}: <span className="text-neutral-400">{r.chapters.join(', ')}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
