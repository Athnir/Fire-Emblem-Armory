import type { StoryOrder } from '../data/maps/mapSet'
import type { ChapterMap } from '../data/maps/types'

/**
 * The spoiler block: with it on, a game opens at its first chapter and "Proceed" reveals the next one, so nothing
 * from a chapter you haven't reached shows up (a weapon you won't get for ten chapters, a map, a shop).
 */
export interface Reach {
  /** Whether the block is on for the game being shown. */
  on: boolean
  /** The index in the game's story of the chapter you're on (Infinity with the block off). */
  at: number
  /** Whether a map has been reached. A side map outside the story (the trial maps) counts once the story is cleared. */
  has: (mapId: string) => boolean
}

/** No block: everything counts as reached. */
export const SEES_ALL: Reach = { on: false, at: Infinity, has: () => true }

export function reachOf(story: StoryOrder, at: number): Reach {
  const index = new Map(story.maps.map((m, i) => [m.id, i]))
  const last = story.maps.length - 1
  return { on: true, at, has: (id) => (index.has(id) ? index.get(id)! <= at : at >= last) }
}

/** A game's story from its main chapters, naming each one the way the game numbers it. */
export function storyOrder(
  maps: ChapterMap[],
  words: Pick<StoryOrder, 'name' | 'short' | 'part'>,
): StoryOrder {
  const plain = maps.map(words.name)
  const shared = new Map<string, number>()
  for (const n of plain) shared.set(n, (shared.get(n) ?? 0) + 1)
  const placed = new Map<string, number>()
  const names = new Map(
    maps.map((m, i) => {
      const n = plain[i]
      if (shared.get(n) === 1) return [m.id, n] as const
      const k = (placed.get(n) ?? 0) + 1
      placed.set(n, k)
      return [m.id, `${n} (part ${k})`] as const
    }),
  )
  return { maps, ...words, name: (m) => names.get(m.id) ?? words.name(m) }
}

/**
 * Chapters as a shop list words them, up to the chapter you've reached: 'Ch.8–11, 13' (Path of Radiance), or
 * 'Part 3: Ch.2, Ch.4, Ch.6–7 · Part 4: Prologue' (Radiant Dawn). `ids` are the chapters whose base has the item
 * and `bases` every chapter with a base, in order: a run is consecutive bases, not consecutive chapters.
 * Path of Radiance ends a list that reaches the last base with "onward"; Radiant Dawn doesn't.
 */
export function chapterText(
  ids: string[],
  bases: string[],
  story: StoryOrder,
  reach: Reach,
  style: { parts: boolean; onward: boolean },
): string {
  const byId = new Map(story.maps.map((m) => [m.id, m]))
  const label = (id: string) => story.short(byId.get(id)!)
  const reached = ids.filter(reach.has)
  const groups: string[][] = []
  if (style.parts) {
    const part = (id: string) => story.part!(byId.get(id)!)
    for (const id of reached) {
      const last = groups[groups.length - 1]
      if (last && part(last[0]) === part(id)) last.push(id)
      else groups.push([id])
    }
  } else if (reached.length) groups.push(reached)

  const lastBase = bases[bases.length - 1]
  const runsOf = (group: string[]) => {
    // Consecutive among the bases of the same part (all of them, for a game without parts).
    const own = style.parts ? bases.filter((b) => story.part!(byId.get(b)!) === story.part!(byId.get(group[0])!)) : bases
    const runs: string[][] = []
    for (const id of group) {
      const run = runs[runs.length - 1]
      if (run && own.indexOf(id) === own.indexOf(run[run.length - 1]) + 1) run.push(id)
      else runs.push([id])
    }
    return runs.map((run) => {
      const first = run[0]
      const last = run[run.length - 1]
      const a = label(first)
      const b = label(last)
      if (first === last) return a
      if (style.onward && last === lastBase) return `${a} onward`
      return `${a}–${a.startsWith('Ch.') && b.startsWith('Ch.') ? b.slice(3) : b}`
    })
  }
  return groups
    .map((group) => {
      const runs = runsOf(group)
      const text = style.parts
        ? runs.join(', ')
        : // 'Ch.' once, at the front of the list.
          runs.map((r, k) => (k === 0 ? r : r.replace(/^Ch\./, ''))).join(', ')
      return style.parts ? `Part ${story.part!(byId.get(group[0])!)}: ${text}` : text
    })
    .join(' · ')
}
