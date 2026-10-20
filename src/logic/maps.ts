import type { ChapterMap, Difficulty, DifficultyTile, MapObject, PotEffect, StatKey, TerrainLetter, Tile } from '../data/maps/types'
import { FATES_TERRAIN } from '../data/maps/fatesTerrain'
import type { TerrainInfo } from '../data/maps/fatesTerrain'

export const tileKey = ([x, y]: Tile) => `${x},${y}`
export const sameTile = (a: Tile, b: Tile) => a[0] === b[0] && a[1] === b[1]

/** Terrain letter at (x, y), bottom-left (1, 1). The grid is stored top row first. */
export function terrainAt(map: ChapterMap, [x, y]: Tile): TerrainLetter {
  return map.grid[map.height - y][x - 1] as TerrainLetter
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
  const rows = map.grid.map((r) => r.split(''))
  for (const { tile: [x, y], becomes } of patches) rows[map.height - y][x - 1] = becomes
  return { ...map, grid: rows.map((r) => r.join('')) }
}

/** Terrain stats for a letter on this map, with the map's own overrides applied. */
export function terrainInfo(map: ChapterMap, letter: TerrainLetter): TerrainInfo {
  const base = map.terrain?.[letter] ?? FATES_TERRAIN[letter]
  const o = map.terrainOverrides?.[letter]
  return o ? { ...base, ...o } : base
}

export function objectsAt(map: ChapterMap, tile: Tile): MapObject[] {
  return map.objects.filter((o) => sameTile(o.tile, tile))
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
