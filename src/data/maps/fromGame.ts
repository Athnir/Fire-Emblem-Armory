import type { ChapterMap, MapObjective } from './types'
import { GAME_CHAPTERS } from './gameChapters'
import { GAME_TERRAIN } from './gameTerrain'
import { GAME_UNITS } from './gameUnits'

const OBJECTIVE_LABEL: Record<MapObjective['type'], string> = {
  seize: 'Seize point',
  defend: 'Defend point',
  escape: 'Escape point',
  arrive: 'Arrival point',
}

/** The game's victory rule as a sentence, naming the boss where there's only one. */
function victory(rule: string, id: string): string {
  const bosses = [...new Set((GAME_UNITS[id]?.units ?? []).filter((u) => u.type === 'boss' && !u.generic).map((u) => u.name))]
  if (rule === 'Defeat the boss' && bosses.length === 1) return `Defeat ${bosses[0]}.`
  if (rule === 'Seize') return 'Seize the marked tile.'
  return `${rule}.`
}

function defeat(rule: string): string {
  const turns = rule.match(/(?:within|in) (\d+) turns/)
  return turns ? `Corrin dies, your army is routed, or ${turns[1]} turns pass.` : 'Corrin dies, or your army is routed.'
}

/**
 * A chapter built wholly from the game's own files: terrain, objective, chests and villages, Dragon
 * Veins, and (through the units pass in index.ts) every unit. `extra` adds what the files don't say,
 * like notes on who joins.
 */
export function gameMap(id: string, extra: Partial<ChapterMap> = {}): ChapterMap {
  const ch = GAME_CHAPTERS[id]
  const terrain = GAME_TERRAIN[id]
  const effect = ch.veinEffect
    ? ch.veinEffectNormal
      ? `${ch.veinEffect} (On Normal: ${ch.veinEffectNormal})`
      : ch.veinEffect
    : 'A Dragon Vein.'
  return {
    id,
    route: ch.route,
    chapter: ch.chapter,
    ...(ch.availableIn ? { availableIn: ch.availableIn } : {}),
    ...(ch.route === 'DLC' ? { heading: ch.prefix } : {}),
    title: ch.title,
    location: ch.location,
    width: terrain.width,
    height: terrain.height,
    grid: terrain.grid,
    ...(terrain.dark ? { dark: terrain.dark } : {}),
    terrainOverrides: terrain.terrain,
    victory: victory(ch.rule, id),
    defeat: defeat(ch.rule),
    objectives: Object.entries(ch.objectives).map(([type, tiles]) => ({
      type: type as MapObjective['type'],
      tiles,
      label: OBJECTIVE_LABEL[type as MapObjective['type']],
    })),
    units: [],
    starts: [],
    objects: ch.objects,
    changes: terrain.veins.map((v) => ({
      id: `vein-${v.tile[0]}-${v.tile[1]}`,
      trigger: 'dragonVein' as const,
      tile: { default: v.tile },
      usableBy: 'Royals',
      effect,
      ...(v.patch.length ? { patch: v.patch } : {}),
    })),
    notes: [],
    sources: [{ label: 'Fire Emblem Fates game files' }],
    ...extra,
  }
}
