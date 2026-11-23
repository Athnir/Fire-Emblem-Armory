/**
 * Frozen games: once the user has marked every map of a game good in the map review, its maps are frozen (the user's call,
 * 2026-11-23: tiles, textures and icons are shared by many maps and several games, so a change made for one game can quietly alter
 * another that was finished). Each frozen map is drawn here as the map page draws it (MapGrid at the start of the battle, on the
 * game's first difficulty), every icon's pixels inline, and the drawing's fingerprint must match the one taken when the game was
 * frozen (frozenMaps.json). A mismatch names the maps; `node scripts/frozen-maps.mjs check <game>` then compares their pictures with
 * the approved ones to show which look different.
 *
 *   FROZEN_FREEZE=fe4 npx vitest run frozenMaps     freeze a game (or take a changed one's fingerprints again once the user approves)
 *   FROZEN_SVG=current npx vitest run frozenMaps    write the frozen maps' drawings to data-raw/frozen-maps/<game>/current/ (the script)
 */
import { createHash } from 'node:crypto'
import { mkdirSync, readFileSync, writeFileSync } from 'node:fs'
import { dirname, join } from 'node:path'
import { env } from 'node:process'
import { fileURLToPath } from 'node:url'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { MapGrid } from '../../components/MapViewer'
import type { MapSet } from '../../data/maps/mapSet'
import type { ChapterMap } from '../../data/maps/types'

const HERE = dirname(fileURLToPath(import.meta.url))
const MANIFEST = join(HERE, 'frozenMaps.json')
const OUT = join(HERE, '..', '..', '..', 'data-raw', 'frozen-maps')

type Manifest = Record<string, { frozen: string; maps: Record<string, string> }>

const SETS: Record<string, () => Promise<MapSet>> = {
  fe1: async () => (await import('../../data/fe1/fe1MapSet')).FE1_MAP_SET,
  fe2: async () => (await import('../../data/fe2/fe2MapSet')).FE2_MAP_SET,
  fe3: async () => (await import('../../data/fe3/fe3MapSet')).FE3_MAP_SET,
  fe4: async () => (await import('../../data/fe4/fe4MapSet')).FE4_MAP_SET,
  fe5: async () => (await import('../../data/fe5/fe5MapSet')).FE5_MAP_SET,
  fe6: async () => (await import('../../data/fe6/fe6MapSet')).FE6_MAP_SET,
  fe7: async () => (await import('../../data/fe7/fe7MapSet')).FE7_MAP_SET,
  fe8: async () => (await import('../../data/fe8/fe8MapSet')).FE8_MAP_SET,
  fe9: async () => (await import('../../data/fe9/fe9MapSet')).FE9_MAP_SET,
  fe10: async () => (await import('../../data/fe10/fe10MapSet')).FE10_MAP_SET,
  fe11: async () => (await import('../../data/fe11/fe11MapSet')).FE11_MAP_SET,
  fe12: async () => (await import('../../data/fe12/fe12MapSet')).FE12_MAP_SET,
  fe13: async () => (await import('../../data/fe13/fe13MapSet')).FE13_MAP_SET,
  fates: async () => (await import('../../data/maps')).FATES_MAP_SET,
  fe15: async () => (await import('../../data/fe15/fe15MapSet')).FE15_MAP_SET,
  fe16: async () => (await import('../../data/fe16/fe16MapSet')).FE16_MAP_SET,
  fe17: async () => (await import('../../data/fe17/fe17MapSet')).FE17_MAP_SET,
}

/** Every map a game's page can show: its chapters, side maps and every route's lists. */
export function everyMap(set: MapSet): ChapterMap[] {
  const out = new Map<string, ChapterMap>()
  const add = (ms: ChapterMap[] | undefined) => ms?.forEach((m) => out.has(m.id) || out.set(m.id, m))
  add(set.maps)
  add(set.extras?.maps)
  add(set.third?.maps)
  for (const r of set.routes?.list ?? []) {
    add(set.routes!.maps(r))
    add(set.routes!.side(r))
    add(set.routes!.third?.maps(r))
    add(set.routes!.fourth?.maps(r))
  }
  return [...out.values()]
}

/** A map as the map page first draws it. */
export function drawing(set: MapSet, map: ChapterMap): string {
  return renderToStaticMarkup(
    <MapGrid map={map} difficulty={set.difficulties[0].value} selected={null} radius={new Set()} potsBroken={false}
      previewing={new Set()} arrivals={[]} triggers={[]} onSelect={() => {}} />,
  )
}

const fingerprint = (svg: string) => createHash('sha256').update(svg).digest('hex').slice(0, 20)

function save(game: string, kind: string, id: string, svg: string) {
  const dir = join(OUT, game, kind)
  mkdirSync(dir, { recursive: true })
  writeFileSync(join(dir, `${id}.svg`), svg.replace('<svg ', '<svg xmlns="http://www.w3.org/2000/svg" '))
}

const manifest: Manifest = JSON.parse(readFileSync(MANIFEST, 'utf8'))

describe('frozen games (every map marked good in the review)', () => {
  const freeze = env.FROZEN_FREEZE
  if (freeze) {
    it(`freezes ${freeze}`, async () => {
      const set = await SETS[freeze]()
      const maps: Record<string, string> = {}
      for (const m of everyMap(set)) {
        const svg = drawing(set, m)
        maps[m.id] = fingerprint(svg)
        save(freeze, 'baseline', m.id, svg)
      }
      manifest[freeze] = { frozen: new Date().toISOString().slice(0, 10), maps }
      writeFileSync(MANIFEST, JSON.stringify(manifest, null, 1) + '\n')
      expect(Object.keys(maps).length).toBeGreaterThan(0)
    }, 600_000)
  }
  for (const [game, entry] of Object.entries(manifest)) {
    if (game === freeze) continue
    it(`${game}: every map draws as it did when it was frozen (${entry.frozen})`, async () => {
      const set = await SETS[game]()
      const byId = new Map(everyMap(set).map((m) => [m.id, m]))
      const changed: string[] = []
      const gone: string[] = []
      for (const [id, print] of Object.entries(entry.maps)) {
        const m = byId.get(id)
        if (!m) {
          gone.push(id)
          continue
        }
        const svg = drawing(set, m)
        if (env.FROZEN_SVG) save(game, env.FROZEN_SVG, id, svg)
        if (fingerprint(svg) !== print) changed.push(id)
      }
      expect(gone, `${game}: frozen maps no longer in the game`).toEqual([])
      expect(changed, `${game}: frozen maps changed; run \`node scripts/frozen-maps.mjs check ${game}\` to see which look different`).toEqual([])
    }, 600_000)
  }
})
