import type { ChapterMap, Difficulty, DifficultyTile, MapObject, PotEffect, StatKey, Tile } from '../data/maps/types'
import type { TerrainCode } from '../data/maps/terrainCodes'
import { FATES_TERRAIN } from '../data/maps/fatesTerrain'
import type { TerrainInfo } from '../data/maps/fatesTerrain'

export const tileKey = ([x, y]: Tile) => `${x},${y}`
export const sameTile = (a: Tile, b: Tile) => a[0] === b[0] && a[1] === b[1]

/** A grid row's tiles: two characters each. */
export function rowCodes(row: string): TerrainCode[] {
  const out: TerrainCode[] = []
  for (let i = 0; i < row.length; i += 2) out.push(row.slice(i, i + 2) as TerrainCode)
  return out
}

/** Terrain code at (x, y), bottom-left (1, 1). The grid is stored top row first, two characters a tile. */
export function terrainAt(map: ChapterMap, [x, y]: Tile): TerrainCode {
  return map.grid[map.height - y].slice(2 * (x - 1), 2 * x) as TerrainCode
}

export function resolveTile(tile: DifficultyTile, difficulty: Difficulty): Tile {
  return tile[difficulty] ?? tile.default
}

/** Every on-map tile within `radius` steps (Fire Emblem's range: |dx| + |dy|), the centre included. */
export function tilesInRadius(map: ChapterMap, [cx, cy]: Tile, radius: number): Tile[] {
  const out: Tile[] = []
  for (let dx = -radius; dx <= radius; dx++) {
    for (let dy = -radius; dy <= radius; dy++) {
      const x = cx + dx
      const y = cy + dy
      if (Math.abs(dx) + Math.abs(dy) <= radius && x >= 1 && x <= map.width && y >= 1 && y <= map.height) out.push([x, y])
    }
  }
  return out
}

/** The map as it looks with the given changes applied (each one's terrain patch laid over the base grid). */
export function applyChanges(map: ChapterMap, active: Set<string>): ChapterMap {
  const patches = map.changes.filter((c) => active.has(c.id)).flatMap((c) => c.patch ?? [])
  if (patches.length === 0) return map
  const rows = map.grid.map(rowCodes)
  for (const { tile: [x, y], becomes } of patches) rows[map.height - y][x - 1] = becomes
  return { ...map, grid: rows.map((r) => r.join('')) }
}

/** Terrain stats for a code on this map, with the map's own overrides applied. */
export function terrainInfo(map: ChapterMap, code: TerrainCode): TerrainInfo {
  const base = (map.terrain?.[code] ?? FATES_TERRAIN[code]) as TerrainInfo
  const o = map.terrainOverrides?.[code]
  return o ? { ...base, ...o } : base
}

/** What's on a tile; a hidden item, or a house that can burn, counts on every tile of its area. */
export function objectsAt(map: ChapterMap, tile: Tile): MapObject[] {
  return map.objects.filter((o) =>
    o.type === 'hidden' || o.type === 'fire'
      ? tile[0] >= o.area[0] && tile[0] <= o.area[2] && tile[1] >= o.area[1] && tile[1] <= o.area[3]
      : sameTile(o.tile, tile),
  )
}

const STAT_LABEL: Record<StatKey, string> = { str: 'Str', mag: 'Mag', skl: 'Skl', spd: 'Spd', lck: 'Lck', def: 'Def', res: 'Res' }

export function describePotEffect(effect: PotEffect): string {
  switch (effect.type) {
    case 'heal':
      return `Heals ${effect.percent}% of max HP`
    case 'damage':
      return `Deals ${effect.percent}% of max HP as damage`
    case 'silence':
      return 'Silence for one turn (no staves or tomes)'
    case 'freeze':
      return 'Freeze for one turn (can\'t move)'
    case 'hex':
      return 'Hex: halves HP until the chapter ends'
    case 'stats': {
      const parts = Object.entries(effect.changes).map(([k, v]) => `${v > 0 ? '+' : ''}${v} ${STAT_LABEL[k as StatKey]}`)
      const kind = effect.kind === 'tonic' ? ' (tonic)' : effect.kind === 'status' ? ' (status)' : ''
      return parts.join(', ') + kind
    }
  }
}
