import type { ChapterMap, MapObjective, SwitchWalls, Tile } from './types'
import { GAME_CHAPTERS } from './gameChapters'
import { GAME_TERRAIN } from './gameTerrain'
import { GAME_UNITS } from './gameUnits'

const OBJECTIVE_LABEL: Record<MapObjective['type'], string> = {
  seize: 'Seize point',
  defend: 'Defend point',
  escape: 'Escape point',
  arrive: 'Arrival point',
  burn: 'Supplies to burn',
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
    changes: [
      ...terrain.veins.map((v) => ({
        id: `vein-${v.tile[0]}-${v.tile[1]}`,
        trigger: 'dragonVein' as const,
        tile: { default: v.tile },
        usableBy: 'Royals',
        effect,
        ...(v.patch.length ? { patch: v.patch } : {}),
        ...(v.flips !== undefined ? { flips: v.flips } : {}),
      })),
      // Traps the chapter script springs when one of your units stops in their zone (Birthright 10's and Revelation 11's spikes).
      ...(terrain.traps ?? []).map((t) => ({
        id: `trap-${t.zone.join('-')}`,
        trigger: 'trap' as const,
        tile: { default: [t.zone[0], t.zone[3]] as Tile },
        usableBy: 'Your units',
        effect: `Springs when one of your units stops in the outlined area: these tiles become ${[...new Set(t.patch.map((p) => terrain.terrain[p.becomes]?.name ?? p.becomes))].join(' / ')}.`,
        wide: true as const,
        zone: t.zone,
        patch: t.patch,
      })),
    ],
    ...(terrain.switchWalls ? { switchWalls: terrain.switchWalls } : {}),
    ...extra,
    notes: [
      ...(ch.amiibo ? [amiiboNote(ch.amiibo)] : []),
      ...(terrain.switchWalls ? [wallsNote(terrain.switchWalls)] : []),
      ...(extra.notes ?? []),
    ],
  }
}

/** How an amiibo Hero Battle opens, from its hero's amiibo script. */
function amiiboNote({ hero, talk }: { hero: string; talk: number }): string {
  const nth = ['first', 'second', 'third', 'fourth', 'fifth'][talk - 1] ?? `${talk}th`
  return `Opens through ${hero}'s amiibo, scanned in My Castle: the ${nth} talk with ${hero} there offers this battle, and winning it recruits ${hero}.`
}

/** What the chapter script does with its switching walls (Revelation 16's flame walls), in a sentence or two. */
function wallsNote(sw: SwitchWalls): string {
  const list = (ns: number[]) => `${ns.slice(0, -1).join(', ')} and ${ns[ns.length - 1]}`
  const words = ['no', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten']
  const turns = sw.turns.map((t) => `walls ${list(t.walls)} flip on every turn that divides by ${t.every}`)
  return (
    `The battle starts with one of ${words[sw.starts.length] ?? sw.starts.length} sets of walls down, picked at random. ` +
    `From turn ${Math.min(...sw.turns.map((t) => t.from))}, ` +
    `${turns.join(', and ')}. Each Dragon Vein flips its own wall, up or down, and stays usable: it can be used again every turn.`
  )
}
