import type { ChapterMap } from './types'
import { SHARED_MAPS } from './shared'
import { CONQUEST_12 } from './conquest12'
import { CONQUEST_6_TO_11 } from './conquest'

/** Every transcribed map: the shared chapters first, then each route in chapter order. */
export const ALL_MAPS: ChapterMap[] = [...SHARED_MAPS, ...CONQUEST_6_TO_11, CONQUEST_12]

export function mapLabel(map: ChapterMap): string {
  if (map.route === 'Shared') return `${map.chapter === 0 ? 'Prologue' : `Chapter ${map.chapter}`}: ${map.title}`
  return `${map.route} ${map.chapter}: ${map.title}`
}
