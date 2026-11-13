import { useMemo, useState } from 'react'
import { useReach } from './Reach'
import { useDifficulty } from './Difficulty'
import { POT_TERRAIN_NOTE } from '../data/maps/fatesTerrain'
import type { MapSet } from '../data/maps/mapSet'
import type { Arrival, ChapterMap, Difficulty, Joiner, MapChange, MapObject, MapUnit, StandIn, Tile } from '../data/maps/types'
import { TERRAIN_CODES, type TerrainCode } from '../data/maps/terrainCodes'
import { PixelIcon, SpriteG } from '../icons/PixelSprite'
import type { Sprite } from '../icons/sprites'
import {
  ACID_BOG, ALLY, ARROW_TRAP, BALLISTA, GAS_VENT, BOULDER, CALTROPS, COAST, COMMON_PARTNER, FISSURE, MUCK, PARTNER, SIGIL, TRAIL, WARD, BURIED, EVENT_TILE, CAPTURE_BADGE, STEAL_BADGE, CASTLE, CHEST, COMMON_ALLY, COMMON_ENEMY, COMMON_PAIR, CRACK, DOOR, DROP_BADGE, DRAGON_VEIN, FORT, GATE, HEAL, HOUSE, JOINER, LEDGE, NAMED_ENEMY, PILLAR, PIT,
  REINFORCEMENT, NAMED_REINFORCEMENT, BOSS_REINFORCEMENT, RUBBLE, SKULL, SNOW_PEAK, STAIRS, SUPPLIES, TORCH, FLAME, HEAL_FLOOR, DEF_FLOOR, RES_FLOOR, SPIKES, TREE, THICK_WOOD, THICKET, CHURCH, OLD_GATE, GATEWAY, RUBBLE_WALL, ICE_BLOCK, VASE_MEDICINE, VASE_POISON, ARMORY, VENDOR, SECRET_SHOP, ARENA, PEAK,
  BULWARK, GRAVE, FELL_FLOOR, SHINY, COTTAGE, SNAG, NO_LORD, CREST_STONE, HEALTH_PIPS, FLOOR_TRAP, CRATER, ONAGER, FIRE_ORB,
  FOG, PUDDLE, STONE_PILLARS, MIASMA, FROST, TUNNEL, VILLAGE_PIECES, VILLAGE_VARIANTS, CASTLE_PIECES, TOWN_HOUSE, MOUNTAIN, LAVA_CRACK, BARREL, BONES,
  HOUSE_PIECES, HOUSE_SIDE_PIECES, FOUNTAIN_PIECES, ROOFTOP_PIECES, ROOFTOP_DOORS, CHIMNEY, HOUSE_VARIANTS, HOUSE_FRONT, MARKET_STALL, CRATES, ODDS_AND_ENDS, CANDLESTICK, PROP_SPRITES, FLOOR_PATTERNS, COAST_VARIANTS, SNOW_TREE, SNOW_THICK_WOOD, DEF_SIGIL, DEF2_SIGIL, RES_SIGIL, LAVA_POOL, CHURCH_PIECES, CAMP_PIECES, WATCHTOWER,
  CHURCH_FRONT_PLAIN, CAMP_FRONT_PLAIN, DOOR_MAT, VILLAGE_HOUSE, RUINED_VILLAGE_TOP, RUINED_VILLAGE_FRONT,
  SEALED_DOOR, STAIR_FORT_PIECES, BRIDGE_SIDE, OPEN_DOOR,
} from '../icons/sprites'
import { applyChanges, arrivalTurn, doorMat, sceneryHouse, visitable, atStart, closedRooms, covers, describePotEffect, digAt, inTheFog, mapSteps, noteOn, notesOn, objectsAt, resolveTile, rowCodes, sameTile, terrainAt, terrainInfo, terrainName, tileKey, tilesInRadius, withStandIns, withSwitchWalls } from '../logic/maps'
import { visibleFills } from '../logic/mapFills'

const CELL = 10
const GUTTER = 7 // room for the axis numbers
/** The dev server's review captures (`?reveal`): every map shown whole, with no fog and each closed room's contents in view. */
const REVEAL = import.meta.env.DEV && typeof location !== 'undefined' && new URLSearchParams(location.search).has('reveal')

/** A fence along a tile side. */
const FENCE = '#7c4a1e'
/** A railing along a step between two heights: a rail on posts, light against the fence's brown (the user: like the fence). */
const RAIL = '#e7d3a8'

/** A step between two heights along a tile side (Path of Radiance's ship decks and terraces): a rail with three posts. */
function Railing({ x1, y1, x2, y2 }: { x1: number; y1: number; x2: number; y2: number }) {
  const posts = [0.15, 0.5, 0.85].map((t) => [x1 + (x2 - x1) * t, y1 + (y2 - y1) * t])
  return (
    <g pointerEvents="none">
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke="#3b2a14" strokeWidth={1.9} strokeLinecap="round" />
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={RAIL} strokeWidth={0.9} strokeLinecap="round" />
      {posts.map(([px_, py_], i) => (
        <rect key={i} x={px_ - 0.75} y={py_ - 0.75} width={1.5} height={1.5} fill={RAIL} stroke="#3b2a14" strokeWidth={0.35} />
      ))}
    </g>
  )
}

/** The corner marks on a tile the game deploys one of your units to itself. */
const FORCED = '#f472b6'

/** The outline round supplies to burn. */
const BURN = '#ea580c'

/** Where a tapped unit is headed. */
const GOES_TO = '#4ade80'
/** Revelation 21's room colours, as the game's floors show them. */
const ROOM = { red: '#ef4444', blue: '#3b82f6' }
/** Blue over the tan floor reads as grey unless it's laid on thicker. */
const ROOM_TINT = { red: 0.25, blue: 0.45 }
/** A trap's zone: the red of the spikes it raises. */
const TRAP_ZONE = '#e11d48'

/** A challenge battle's foe groups (Fates), outlined and numbered each in its own colour. */
const FOE_GROUP = ['#fbbf24', '#a78bfa']

/** A trap that goes off on its own (the GBA games' fire tiles, gas vents and arrow launchers). */
const TRAP_SPRITE = { fire: LAVA_CRACK, gas: GAS_VENT, arrow: ARROW_TRAP } as const
const TRAP_LABEL = { fire: 'Fire trap', gas: 'Gas vent', arrow: 'Arrow launcher' } as const

/** Steps between two tiles. */
const distance = (a: Tile, b: Tile) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1])

const TERRAIN_FILL: Record<TerrainCode, string> = {
  ta: '#b89a6a',
  // The ground as itself (the GBA games'): each map gives its own colours (`fills`); these are the defaults.
  t0: '#86a35c',
  t1: '#8a8794',
  t2: '#dfe7ec',
  t5: '#a87a18',
  // Ground a game calls plain: a dirt path or yard, paving (a town's flagstones, a stone bridge's ends), mossy cobbles.
  ga: '#9a8a66',
  gb: '#b3a488',
  gc: '#a8a68c',
  gd: '#8a7f6e',
  ge: '#a8a4a0',
  t4: '#a39d90',
  t3: '#9c7d4e',
  t6: '#d6ecf2',
  t7: '#a08a76',
  tv: '#b89a6a',
  tb: '#8a6a44',
  wu: '#5f8fd6',
  t8: '#9d978c',
  t9: '#7d2e2a',
  ty: '#9b7447',
  ts: '#8a6a44',
  tc: '#a08a64',
  td: '#e0c88a',
  te: '#8a6d45',
  tf: '#5fa3bd',
  tg: '#5fa3bd',
  th: '#6f7a3a',
  ti: '#5b4a3a',
  tj: '#a8d4de',
  tk: '#d9c9a0',
  tm: '#8f8676',
  tn: '#a89474',
  tl: '#b08c56',
  ba: '#b89a6a',
  bb: '#b89a6a',
  bc: '#8b4a8b',
  bd: '#b89a6a',
  be: '#b89a6a',
  bv: '#b89a6a',
  bw: '#9a8fb0',
  bx: '#9a8fb0',
  by: '#9a9488',
  bz: '#a08a64',
  bf: '#c4a874',
  bg: '#c8b088',
  bh: '#b89a6a',
  bi: '#c99a6a',
  bj: '#c9b0e0',
  bk: '#c9b0e0',
  bl: '#8a6d45',
  b4: '#b59a6b',
  ws: '#2a2633',
  // Mountains stand on the ground around them (rocky, or snowy on a snowy map: spriteOf).
  bm: '#b89a6a',
  bn: '#f4f7fb',
  bo: '#9a9488',
  bp: '#9a9488',
  bq: '#9a9488',
  br: '#9a9488',
  bs: '#7a5040',
  bt: '#2f5a2c',
  bu: '#9a8f86',
  ha: '#3fbfa8',
  hh: '#3f9fbf',
  hb: '#3fbfa8',
  hc: '#c0a070',
  hd: '#b89a6a',
  he: '#b89a6a',
  hf: '#9a9488',
  da: '#6f7a3a',
  db: '#5b4a3a',
  dc: '#a08060',
  de: '#8a7a4a',
  dd: '#5a2a14',
  wa: '#4a443e',
  wb: '#6b5a4a',
  wc: '#e8eef2',
  wd: '#2b2f38',
  we: '#2f6f9f',
  wf: '#7cb6ea',
  wg: '#7a6a58',
  wh: '#3f5a2c',
  wi: '#5a6f80',
  wj: '#6e5a48',
  wk: '#a8d4de',
  wl: '#5fa3bd',
  wm: '#3a3550',
  wn: '#4f4236',
  wo: '#5a4632',
  wt: '#7d7468',
  wv: '#1f3a52',
  // Awakening's Ire, Grima's tile: colour only, as a throne under its boss.
  ww: '#6a2a3a',
  oa: '#b89a6a',
  ob: '#b89a6a',
  oc: '#b89a6a',
  od: '#bfa77e',
  oe: '#d9c7a3',
  ot: '#d9c7a3',
  // Barrels and bones stand on the ground around them.
  o1: '#b89a6a',
  o2: '#b89a6a',
  of: '#9a6b3a',
  og: '#8a4f8f',
  oh: '#6a6a7a',
  oi: '#a070c0',
  oj: '#cbbfd9',
  ok: '#d9c7a3',
  ol: '#8a8378',
  o0: '#b89a6a',
  om: '#d9c7a3',
  on: '#d9c7a3',
  oo: '#c9b48a',
  op: '#d9c7a3',
  oq: '#d9c7a3',
  or: '#b89a6a',
  os: '#d9c7a3',
  ou: '#9a9286',
  to: '#8cc4d4',
  tp: '#7a6a58',
  wp: '#b0441e',
  sa: '#cfe3ea',
  sb: '#15121c',
  sc: '#8a5a44',
  // Effects laid over a tile (Engage): the ground's colour under them, woods' and sand's where they lie on those.
  ea: '#b89a6a',
  eb: '#b89a6a',
  ec: '#b89a6a',
  ed: '#b89a6a',
  ee: '#e0c88a',
  ef: '#b89a6a',
  eg: '#b89a6a',
  eh: '#b89a6a',
  ei: '#b89a6a',
  b0: '#9a9488',
  b1: '#8a6a44',
  b2: '#8f8a7a',
  b3: '#7a8a5a',
  tq: '#5a4a6a',
  tr: '#bfe3ef',
  tx: '#6a3a5a',
  wq: '#4a443e',
  wr: '#e3f0f6',
  // Shadow Dragon: a ledge climbed at a cost, a castle only fliers cross, and the tiles the lord can't enter (their base's colour).
  tt: '#a48c64',
  wx: '#6f675d',
  tu: '#b89a6a',
  b5: '#b89a6a',
  b6: '#b89a6a',
  b7: '#b89a6a',
  // Three Houses: indoor floors that slow some monsters, its lighter thicket, its Avoid floors, the prayer stone, breakable walls, levers,
  // the Holy Tomb's Crest Stones (a wall's colour).
  tw: '#9a9488',
  b8: '#3f6b38',
  b9: '#9a9488',
  hg: '#3fbfa8',
  wz: '#6b5a4a',
  ov: '#b89a6a',
  ow: '#4a443e',
  // Its swamp, floor traps and craters (they hurt), and the onagers units fire (standing on ground).
  df: '#4a5a32',
  dg: '#9a9488',
  dh: '#5a3a28',
  ox: '#b89a6a',
  oy: '#6a5a9a',
  oz: '#9a5a3a',
  // Walls by what they are on the map (the GBA games'), coloured from the games' own art: castle stone, mossy ruins, a village's red
  // roofs, a temple's dark stone, wood, sandstone, snow, a roof, a village's low walls, a ship's sides, and the black beyond a map.
  w0: '#9a9282',
  w1: '#7f8a70',
  w2: '#b2654c',
  w3: '#5a4f78',
  w4: '#7d5a36',
  w5: '#c4a066',
  w6: '#c9d8e0',
  w7: '#9a5a44',
  w8: '#7f9a52',
  // A village's pieces stand in its yard (its map's plains a shade darker: villageYard); a castle's on the ground around it (the
  // plain ground's colour, so groundUnder gives each its map's).
  va: '#7f9a52', vb: '#7f9a52', vc: '#7f9a52', vd: '#7f9a52', ve: '#7f9a52', vf: '#7f9a52', vg: '#7f9a52', vh: '#7f9a52', vi: '#7f9a52',
  ca: '#b89a6a', cb: '#b89a6a', cc: '#b89a6a', cd: '#b89a6a', ce: '#b89a6a', cf: '#b89a6a', cg: '#b89a6a', ch: '#b89a6a', ci: '#b89a6a',
  // A town house's pieces, a market's stalls, crates and odds and ends stand on the ground around them.
  ra: '#b89a6a', rb: '#b89a6a', rc: '#b89a6a', rd: '#b89a6a', re: '#b89a6a', rf: '#b89a6a', rg: '#b89a6a', rh: '#b89a6a', ri: '#b89a6a',
  fa: '#4f97cc', fb: '#4f97cc', fc: '#4f97cc', fd: '#4f97cc', fe: '#4f97cc', ff: '#4f97cc', fg: '#4f97cc', fh: '#4f97cc', fi: '#4f97cc',
  rj: '#b89a6a', rk: '#b89a6a', rl: '#b89a6a', rm: '#b89a6a', rn: '#b89a6a', ro: '#b89a6a', rp: '#b89a6a', rq: '#b89a6a', rr: '#b89a6a',
  o3: '#b89a6a', o4: '#b89a6a', o5: '#b89a6a', o6: '#b89a6a', o7: '#b89a6a', o8: '#b89a6a', o9: '#b89a6a',
  ka: '#b89a6a', kb: '#b89a6a', kc: '#b89a6a', kd: '#b89a6a', ke: '#b89a6a', kf: '#b89a6a', kg: '#b89a6a', kh: '#b89a6a', ki: '#b89a6a',
  pa: '#b89a6a', pb: '#b89a6a', pc: '#b89a6a', pd: '#b89a6a', pe: '#b89a6a', pf: '#b89a6a', pg: '#b89a6a', ph: '#b89a6a', pi: '#b89a6a',
  w9: '#6e4e2e',
  wy: '#08080a',
}

/** A wall kind's lines over its colour, in a tile's own 10 x 10 units: bricks, broken bricks, roof tiles, a temple's carving, planks. */
const BRICKS: [number, number, number, number][] = [
  [0, 3.33, 10, 3.33], [0, 6.67, 10, 6.67], [5, 0, 5, 3.33], [2.5, 3.33, 2.5, 6.67], [7.5, 3.33, 7.5, 6.67], [5, 6.67, 5, 10],
]
/** Big stone blocks in two staggered courses (Gaiden's castles, which only fliers cross). */
const BLOCKS: [number, number, number, number][] = [[0, 5, 10, 5], [5, 0, 5, 5], [2.5, 5, 2.5, 10], [7.5, 5, 7.5, 10]]
/** A pattern's stroke: a colour, or a shade of the tile's own colour (shade's amount) where the map gives the wall its colour. */
const WALL_PATTERN: Partial<Record<TerrainCode, { stroke: string | number; lines: [number, number, number, number][] }>> = {
  w0: { stroke: '#6b6457', lines: BRICKS },
  wx: { stroke: -0.32, lines: BLOCKS },
  w1: { stroke: '#55604a', lines: [[0, 4, 4, 4], [6, 6, 10, 6], [4, 4, 4, 7], [6, 2, 6, 6], [2, 7.5, 3.5, 9.5], [7.5, 0.5, 9, 2.5]] },
  w2: {
    stroke: '#7a3c2a',
    lines: [[0, 2.5, 10, 2.5], [0, 5, 10, 5], [0, 7.5, 10, 7.5], [2.5, 0, 2.5, 2.5], [7.5, 0, 7.5, 2.5], [5, 2.5, 5, 5], [2.5, 5, 2.5, 7.5], [7.5, 5, 7.5, 7.5], [5, 7.5, 5, 10]],
  },
  w3: { stroke: '#3a3354', lines: [[2, 2, 8, 2], [2, 8, 8, 8], [5, 2, 5, 8], [2, 2, 2, 8], [8, 2, 8, 8]] },
  w4: { stroke: '#523a22', lines: [[3.33, 0, 3.33, 10], [6.67, 0, 6.67, 10]] },
  w5: { stroke: '#86683a', lines: BRICKS },
  w6: { stroke: '#93a8b4', lines: BRICKS },
  w9: { stroke: '#4a331d', lines: [[0, 2.5, 10, 2.5], [0, 5, 10, 5], [0, 7.5, 10, 7.5]] },
  // A barrier of light: bright streaks rising through it.
  wu: { stroke: '#cfe2ff', lines: [[1.5, 1, 1.5, 6], [4, 3.5, 4, 9], [6.5, 0.5, 6.5, 5], [8.8, 4, 8.8, 9.5]] },
}

/** A tile's colour: its map's own where the map gives one (the GBA games' ground and water, from their art), else its code's. */
/** The Tower's Defense and Resistance floors: the hall's flagstone (the map's floor colour and slabs) with an emblem inlaid; and the
 * same for the castle floors that give Avoid (Gaiden's and Echoes', Mystery of the Emblem's): a pattern laid in the floor, not a
 * shield on every tile (the user's call, as the Tower's). */
const FLOOR_BONUS = new Set<TerrainCode>(['bo', 'bp', 'bq', 'br', 'b0', 'by'])
const fillOf = (map: ChapterMap, code: TerrainCode): string =>
  visibleFills(map.fills)[code] ?? (FLOOR_BONUS.has(code) ? fillOf(map, 't1') : TERRAIN_FILL[code])

/** A colour mixed toward white (amount > 0) or black (< 0). */
function shade(hex: string, amount: number): string {
  const to = amount > 0 ? 255 : 0
  const a = Math.abs(amount)
  const mix = (i: number) => Math.round(parseInt(hex.slice(i, i + 2), 16) * (1 - a) + to * a)
  return `#${[1, 3, 5].map((i) => mix(i).toString(16).padStart(2, '0')).join('')}`
}

/** Water's ripples and sand's grains, in a tile's own 10 x 10 units, drawn in a lighter or darker shade of its colour. */
const WATER_CODES = new Set<TerrainCode>(['we', 'wk', 'tg', 'wm', 'tf', 'tj', 'to', 'wl'])
const WAVES = ['M1 3.2 q1.2 -1.1 2.4 0 t2.4 0', 'M5 7.2 q1.2 -1.1 2.4 0 t2.4 0']
const SAND_CODES = new Set<TerrainCode>(['tk', 'td'])
const GRAINS: [number, number][] = [[1.5, 2], [5.5, 1.2], [8.2, 3.6], [3.2, 5.4], [6.8, 6.6], [1.2, 8.4], [4.6, 8.8], [8.6, 8.2]]

/** The code a map's plains are drawn with where its art gives them a colour: the plain, or the plain with Avo +5 (Shadow Dragon and
 * the Blade of Light's and Mystery of the Emblem's grassland). */
const plainOf = (map: ChapterMap): TerrainCode | undefined => (map.fills?.t0 ? 't0' : map.fills?.tv ? 'tv' : undefined)

/** A map whose plains are snow (Ilia's: light and nearly colourless, from its art). */
function snowy(map: ChapterMap): boolean {
  const plain = plainOf(map)
  const t0 = plain && map.fills?.[plain]
  if (!t0) return mostlySnow(map)
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(t0.slice(i, i + 2), 16))
  if (Math.min(r, g, b) > 160 && Math.max(r, g, b) - Math.min(r, g, b) < 45) return true
  // Snow drawn pale blue (Mystery of the Emblem's): light, and bluer than anything else in it.
  return (Math.max(r, g, b) + Math.min(r, g, b)) / 510 >= 0.72 && b > r && b >= g
}

/** Odds and ends in a castle's halls: the ground around them (two tiles out) mostly floor. */
function onFloor(map: ChapterMap, [x, y]: Tile): boolean {
  let floor = 0
  let other = 0
  for (let dy = -2; dy <= 2; dy++)
    for (let dx = -2; dx <= 2; dx++) {
      const n: Tile = [x + dx, y + dy]
      if (n[0] < 1 || n[1] < 1 || n[0] > map.width || n[1] > map.height) continue
      const c = terrainAt(map, n)
      if (c === 't1') floor++
      else if (GROUND_CODES.has(c)) other++
    }
  return floor > 0 && floor >= other
}

/** The Tower's floors' patterns: each map a design of its own for each kind (Defense, strong Defense, Resistance), from its id. */
function floorPattern(map: ChapterMap, code: TerrainCode) {
  const kind = code === 'bp' ? 'def2' : code === 'bq' ? 'res' : 'def'
  const base = [...map.id].reduce((n, ch) => n + ch.charCodeAt(0), 0)
  const step = { def: 0, def2: 2, res: 4 }[kind]
  return FLOOR_PATTERNS[kind][(base + step) % FLOOR_PATTERNS[kind].length]
}

/** On a map of rooftops (`rooftops`), whether a tile is roof: one its houses name (a house's number; 0, the user's, is none), else a
 * house's, a prison camp's, a church's but its front row, or a prop under a house's model. */
function roofAt(map: ChapterMap, [x, y]: Tile): boolean {
  if (x < 1 || y < 1 || x > map.width || y > map.height) return false
  const house = map.rooftops?.houses?.[tileKey([x, y])]
  if (house !== undefined) return house > 0
  const c = terrainAt(map, [x, y])
  if (/^[rp][a-r]$/.test(c)) return true
  if (/^k[a-f]$/.test(c)) return true
  return c === 'o4' && map.props?.[tileKey([x, y])] === 'roof'
}

/** A rooftop's piece: its place from which of its neighbours are roof too, so packed buildings' roofs join; a door under the eave where
 * a place to visit stands below it. */
function rooftopOf(map: ChapterMap, [x, y]: Tile) {
  // Two roofs join only within one house, where the user has marked the houses (an edge where two meet).
  const houses = map.rooftops?.houses
  const same = (n: Tile) => roofAt(map, n) && (!houses || houses[tileKey(n)] === houses[tileKey([x, y])])
  const up = same([x, y + 1]), down = same([x, y - 1]), left = same([x - 1, y]), right = same([x + 1, y])
  const row = !down ? 2 : !up ? 0 : 1
  const col = !left && right ? 0 : !right && left ? 2 : 1
  const place = 'abcdefghi'[row * 3 + col] as keyof typeof ROOFTOP_PIECES
  if (row === 2 && y > 1 && doorMat(map, [x, y - 1])) return ROOFTOP_DOORS[place as 'g' | 'h' | 'i']
  return ROOFTOP_PIECES[place]
}

const codeAt = (map: ChapterMap, [x, y]: Tile): TerrainCode | undefined =>
  x >= 1 && y >= 1 && x <= map.width && y <= map.height ? terrainAt(map, [x, y]) : undefined

/** A village of two tiles (Shadow Dragon and the Blade of Light's and Mystery of the Emblem's: a wall over the village you visit), drawn
 * as one building (the user's call), and the same razed (two closed-village tiles, one over the other): its piece for a tile. */
function twoTileVillage(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  if (code === 'w2' && codeAt(map, [x, y - 1]) === 'oc') return VILLAGE_HOUSE.middleTop
  if (code === 'oc' && codeAt(map, [x, y + 1]) === 'w2') return VILLAGE_HOUSE.middleFront
  if (code === 'od' && codeAt(map, [x, y - 1]) === 'od') return RUINED_VILLAGE_TOP
  if (code === 'od' && codeAt(map, [x, y + 1]) === 'od') return RUINED_VILLAGE_FRONT
  return undefined
}

/** The wings a village of two tiles has on the grass either side (the game draws the village three tiles wide: the user's call), for
 * a tile of that grass, which stays grassland. */
function villageYardPiece(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  if (code !== 'tv' && code !== 't0') return undefined
  const right = twoTileVillage(map, [x + 1, y])
  if (right === VILLAGE_HOUSE.middleTop) return VILLAGE_HOUSE.leftTop
  if (right === VILLAGE_HOUSE.middleFront) return VILLAGE_HOUSE.leftFront
  const left = twoTileVillage(map, [x - 1, y])
  if (left === VILLAGE_HOUSE.middleTop) return VILLAGE_HOUSE.rightTop
  if (left === VILLAGE_HOUSE.middleFront) return VILLAGE_HOUSE.rightFront
  return undefined
}

/** A castle's gate row under its pieces (Mystery of the Emblem's: the castle tile you seize between its flanks, which keep their own
 * stats): drawn as the castle's front, so the castle stands whole (the user: it was missing tiles). */
const GATE_ROW = new Set<TerrainCode>(['ou', 'ol'])
const isPiece = (c: TerrainCode | undefined) => !!c && /^c[a-i]$/.test(c)
function castleFront(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  if (!code || !GATE_ROW.has(code) || !isPiece(codeAt(map, [x, y + 1]))) return undefined
  if (code === 'ol') return CASTLE_PIECES.h
  const inRow = (dx: number) => GATE_ROW.has(codeAt(map, [x + dx, y]) as TerrainCode) && isPiece(codeAt(map, [x + dx, y + 1]))
  return !inRow(-1) ? CASTLE_PIECES.g : !inRow(1) ? CASTLE_PIECES.i : CASTLE_PIECES.h
}

/** A fort drawn whole with stairs up its front (Gaiden's small forts): its middle row's part ('d' and 'f' its sides, 'e' the fort in
 * the middle), which is the raised platform the stairs climb to, not a castle's walls (the user's call). */
function stairFortPart(map: ChapterMap, [x, y]: Tile): 'd' | 'e' | 'f' | undefined {
  const code = codeAt(map, [x, y])
  const middle = (cx: number) => {
    const c = codeAt(map, [cx, y])
    return (c === 'bb' || c === 'ce') && codeAt(map, [cx, y - 1]) === 'tc' && codeAt(map, [cx - 1, y]) === 'cd' && codeAt(map, [cx + 1, y]) === 'cf'
  }
  if (code === 'cd' && middle(x + 1)) return 'd'
  if (code === 'cf' && middle(x - 1)) return 'f'
  if ((code === 'bb' || code === 'ce') && middle(x)) return 'e'
  return undefined
}

/** A tile's icon: its code's, but a mountain is the snowy peak on a snowy map (the user's call: rocky elsewhere), and a village
 * piece in a building wider or taller than 3 one of its place's variants, tile by tile (`at`: the tile, to pick by). */
function spriteOf(map: ChapterMap, code: TerrainCode, at?: Tile) {
  if ((code === 'bm' || code === 'b7') && snowy(map)) return SNOW_PEAK
  if (at) {
    const village = twoTileVillage(map, at)
    if (village) return village
    const front = castleFront(map, at)
    if (front) return front
    const fort = stairFortPart(map, at)
    if (fort === 'd' || fort === 'f') return STAIR_FORT_PIECES[fort]
  }
  // A snowy map's trees (Mystery of the Emblem's, its grassland snow) are snowy, as its art draws them.
  if (code === 'ba' && map.fills?.tv && snowy(map)) return SNOW_TREE
  if (at && map.rooftops && roofAt(map, at)) return rooftopOf(map, at)
  // A tile the user marked as no house is odds and ends (the user: the packed towns' odd tiles are small objects), its own terrain kept.
  if (at && map.rooftops?.houses?.[tileKey(at)] === 0) return TERRAIN_SPRITE.o4
  if (at && map.rooftops?.stalls?.includes(tileKey(at))) return TERRAIN_SPRITE.o8
  if (at && code === 'o4' && map.props?.[tileKey(at)] === 'roof') return rooftopOf(map, at)
  if (map.snowyTrees && code === 'ba') return SNOW_TREE
  if (map.snowyTrees && code === 'wh') return SNOW_THICK_WOOD
  if (at && code === 'oc' && doorMat(map, at)) return DOOR_MAT
  if (at && code === 'o4') {
    // The prop the game's model puts there; a map that names none: a castle's halls hold its lights.
    const kind = map.props?.[tileKey(at)]
    if (kind === 'roof') return rooftopOf(map, at)
    if (kind) return kind === 'candle' ? CANDLESTICK : kind === 'barrel' ? BARREL : PROP_SPRITES[kind]
    if (!map.props && onFloor(map, at)) return CANDLESTICK
  }
  // A shore's look: the pebbles (the user's pick of the shore's looks).
  if (code === 'b4') return COAST_VARIANTS[3]
  if (FLOOR_BONUS.has(code)) return floorPattern(map, code)
  // A town house with a door mat before it has its door over each mat (windows or a blank wall past them), not where it would be.
  if (at && /^r[ghi]$/.test(code)) {
    const [x, y] = at
    const front = (fx: number) => fx >= 1 && fx <= map.width && /^r[ghi]$/.test(terrainAt(map, [fx, y]))
    let x0 = x
    while (front(x0 - 1)) x0--
    let x1 = x
    while (front(x1 + 1)) x1++
    const mats: number[] = []
    for (let fx = x0; fx <= x1; fx++) if (y > 1 && doorMat(map, [fx, y - 1])) mats.push(fx)
    if (mats.length) {
      const place = code[1] as 'g' | 'h' | 'i'
      if (mats.includes(x)) return place === 'g' ? HOUSE_FRONT['door-left'] : place === 'i' ? HOUSE_FRONT['door-right'] : HOUSE_PIECES.h
      return place === 'h' ? [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(x, y) % 2] : HOUSE_PIECES[place]
    }
  }
  if (at && /^[rkp][dfghie]$/.test(code)) {
    const [x, y] = at
    const beside = (dx: number) => (x + dx >= 1 && x + dx <= map.width ? terrainAt(map, [x + dx, y]) : undefined)
    const [group, place] = code
    if (place === 'h' && beside(-1) === code)
      return group === 'r' ? [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(x, y) % 2] : group === 'k' ? CHURCH_FRONT_PLAIN : CAMP_FRONT_PLAIN
    if (group === 'r' && place === 'g' && beside(1) === 'ri') return HOUSE_FRONT['door-left']
    if (group === 'r' && place in HOUSE_VARIANTS) {
      const options = [HOUSE_PIECES[place as 'd'], ...HOUSE_VARIANTS[place as keyof typeof HOUSE_VARIANTS]]
      return options[variety(x, y) % options.length]
    }
  }
  const place = code[1] as 'b' | 'd' | 'e' | 'f' | 'h'
  if (at && code[0] === 'v' && place in VILLAGE_VARIANTS) {
    const [x, y] = at
    const c = (dx: number, dy: number) => {
      const n: Tile = [x + dx, y + dy]
      return n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height ? terrainAt(map, n) : undefined
    }
    // A 3-wide (or 3-tall) building's middle keeps its own piece: its ends on both sides of it.
    const across = place === 'd' || place === 'f' ? [c(0, 1), c(0, -1)] : [c(-1, 0), c(1, 0)]
    const ends = { b: ['va', 'vc'], h: ['vg', 'vi', 'oc'], d: ['va', 'vg'], f: ['vc', 'vi'], e: ['vd', 'vf'] }[place]
    if (!across.every((n) => !!n && ends.includes(n))) {
      const options = [VILLAGE_PIECES[place], ...VILLAGE_VARIANTS[place]]
      return options[variety(x, y) % options.length]
    }
  }
  return TERRAIN_SPRITE[code]
}

/** The ground drawn as itself (plain, floor, snowfield, deck, paving, glacier, rocky ground, road, sand): what an icon stands on. */
const GROUND_CODES = new Set<TerrainCode>(['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't9', 'ty', 'ge', 'ga', 'gb', 'gc', 'gd', 'tl', 'tk', 'td',
  'tv', 'tn'])
/** Floors indoors: a tree stands on them only where no ground outdoors is near (the user: Shadow Dragon and the Blade of Light's trees
 * by a town's paving came out on the paving). */
const INDOOR_GROUND = new Set<TerrainCode>(['t1', 'tn', 'ge', 't5', 't9', 'b0', 'by', 'bo', 'bp', 'bq', 'br'])
/** Trees and thickets, which the games draw on grass. */
const TREE_CODES = new Set<TerrainCode>(['ba', 'bt', 'wh', 'b5', 'b8'])
/** Buildings and markers drawn over the ground around them (the user: a house, an arena or a grave on its own tan block read as
 * wrong): shops, houses, castles, a closed village, graves. */
const ON_THE_GROUND = new Set<TerrainCode>(['om', 'on', 'oo', 'op', 'os', 'ot', 'ol', 'ou', 'od', 'b2'])

/** Whether a map's open ground is mostly snowfield (the Tellius games name it: Radiant Dawn's Part 1 and 4 in the north). */
const SNOWFIELD = new WeakMap<ChapterMap, boolean>()
function mostlySnow(map: ChapterMap): boolean {
  if (!SNOWFIELD.has(map)) {
    const codes = map.grid.flatMap(rowCodes)
    SNOWFIELD.set(map, codes.filter((c) => c === 't2').length > codes.filter((c) => c === 't0').length)
  }
  return SNOWFIELD.get(map)!
}

/** A village's yard: its map's plains a shade darker (Ilia's snow, Sacae's dry grass), snow on a map of snowfields, else the
 * village's own colour. */
const villageYard = (map: ChapterMap) => {
  const plain = plainOf(map)
  return plain ? shade(visibleFills(map.fills)[plain]!, -0.08) : mostlySnow(map) ? shade(TERRAIN_FILL.t2, -0.06) : TERRAIN_FILL.w8
}

/** A tile's variety (0-3), so details don't repeat from one tile to the next. */
const variety = (x: number, y: number) => (x * 7 + y * 13 + ((x * y) % 5)) % 4

const TUFTS: [number, number][][] = [
  [[2.2, 3.4], [6.6, 7.6]],
  [[6.8, 2.8], [3.0, 7.0], [8.2, 8.6]],
  [[4.4, 5.2]],
  [[1.8, 8.0], [7.4, 4.2]],
]
const SPECKS: [number, number][][] = [[[3, 6.5], [7, 3]], [[6, 7.5]], [[2.5, 3.5], [6.5, 6]], [[4.5, 2.5], [7.5, 7.5]]]
const PEBBLES: [number, number][][] = [[[2, 3], [7, 6.5]], [[5, 2.5], [3, 7.5], [8, 8]], [[6.5, 4]], [[2.5, 6], [7.5, 2.5]]]
const COBBLES: [number, number, number][] = [
  [0.4, 0.5, 4.2], [5.2, 0.5, 4.4], [0.4, 3.6, 2.2], [3, 3.6, 4.2], [7.6, 3.6, 2], [0.4, 6.7, 4.2], [5.2, 6.7, 4.4],
]
// Coins on a treasure tile: staggered rows that repeat every 10, so neighbouring tiles' coins meet across the edge.
const COINS: [number, number][] = [0, 1, 2, 3, 4].flatMap((r) =>
  [0, 1, 2, 3, 4].map((c): [number, number] => [c * 2.5 + (r % 2 ? 1.25 : 0), r * 2.5 + 0.6]),
)
// Moss along the joints between the cobbles' rows: [x, y, length], varied from tile to tile.
const MOSS: [number, number, number][][] = [
  [[1.2, 3.35, 2], [5.8, 6.45, 2.4]],
  [[4.6, 3.35, 2.6], [1.4, 6.45, 1.6]],
  [[3.2, 6.45, 2.6], [7.4, 3.35, 1.4]],
  [[6.6, 3.35, 2], [0.8, 6.45, 2.2], [5.4, 9.55, 1.6]],
]
const SHINGLES = 'q1.25 -2.2 2.5 0 q1.25 -2.2 2.5 0 q1.25 -2.2 2.5 0 q1.25 -2.2 2.5 0'
// A cliff's rock layers: ledges across it, each lit along its lower edge, varied from tile to tile.
const STRATA: [number, number, number][][] = [
  [[0, 3, 6], [3, 6.5, 7]],
  [[2, 2.5, 8], [0, 7, 5]],
  [[0, 4, 10], [5, 7.5, 5]],
  [[1, 2, 5], [4, 5, 6], [0, 8, 4]],
]
const BOG: { puddle: [number, number, number, number]; bubbles: [number, number][]; reeds: [number, number][] }[] = [
  { puddle: [3.2, 4, 2.2, 1.1], bubbles: [[7, 7.2]], reeds: [[7.6, 3.4]] },
  { puddle: [6.4, 6.6, 2.4, 1.2], bubbles: [[2.6, 3]], reeds: [[2.2, 8.4]] },
  { puddle: [4.6, 7.2, 2, 1], bubbles: [[7.4, 3], [2.2, 4.8]], reeds: [] },
  { puddle: [5.6, 3.2, 2.6, 1.2], bubbles: [[3, 7.4]], reeds: [[8.2, 7.8]] },
]
const CRACKS = ['M2 2 l2 2 l-0.5 2', 'M7 1.5 l-1.5 2.5 l1.5 1.5', 'M3 7 l2.5 -1 l1.5 2', 'M6.5 5.5 l2 1.5']
// Rubble's stones: [x, y, width], varied from tile to tile.
const RUBBLE_STONES: [number, number, number][][] = [
  [[1, 1.5, 2.6], [5.5, 3, 2.2], [2.2, 6.2, 2], [6.6, 7, 2.6]],
  [[3, 1, 2.2], [7, 2.4, 2], [1, 4.6, 2.6], [5, 6.4, 2.4], [2.4, 8, 1.6]],
  [[1.4, 2.2, 2], [4.8, 1.2, 2.6], [6.8, 5, 2.2], [1.8, 6.8, 2.6]],
  [[2.4, 1.6, 2.4], [6.2, 2.8, 2.2], [3.6, 5.4, 2.6], [7.2, 7.2, 2], [1, 8, 1.6]],
]

/**
 * Small details on the ground (the user's call), in a shade of the tile's own colour and varied from tile to tile so a field doesn't
 * repeat: grass tufts, a floor's slab (lit on its top and left, shaded on its bottom and right, a speck or two: never a wall's bricks),
 * a road's pebbles, a deck's planks, rocky ground's cracks.
 */
function GroundDetail({ code, fill, X, Y, x, y }: { code: TerrainCode; fill: string; X: number; Y: number; x: number; y: number }) {
  const v = variety(x, y)
  const dark = shade(fill, -0.2)
  if (code === 't0' || code === 'tv')
    return (
      <>
        {TUFTS[v].map(([tx, ty]) => (
          // Three blades side by side, leaning out: a tuft, not an arrow.
          <path key={`${tx}${ty}`} d={`M${X + tx - 0.6} ${Y + ty} l-0.3 -1 M${X + tx} ${Y + ty} v-1.4 M${X + tx + 0.6} ${Y + ty} l0.3 -1`}
            fill="none" stroke={dark} strokeWidth={0.4} strokeLinecap="round" />
        ))}
      </>
    )
  if (code === 't1' || code === 'ge' || code === 'tn')
    return (
      <>
        <path d={`M${X + 0.4} ${Y + 9.6} V${Y + 0.4} H${X + 9.6}`} fill="none" stroke={shade(fill, 0.16)} strokeWidth={0.5} />
        <path d={`M${X + 0.4} ${Y + 9.6} H${X + 9.6} V${Y + 0.4}`} fill="none" stroke={shade(fill, -0.18)} strokeWidth={0.5} />
        {SPECKS[v].map(([sx, sy]) => <rect key={`${sx}${sy}`} x={X + sx} y={Y + sy} width={0.6} height={0.6} fill={shade(fill, -0.14)} />)}
      </>
    )
  if (code === 't2')
    // Snow: a drift's soft shadow or two.
    return (
      <>
        {TUFTS[v].map(([tx, ty]) => (
          <path key={`${tx}${ty}`} d={`M${X + tx - 1.2} ${Y + ty} q1.2 -0.9 2.4 0`} fill="none" stroke={shade(fill, -0.12)} strokeWidth={0.4} strokeLinecap="round" />
        ))}
      </>
    )
  if (code === 't4' || code === 'gb')
    // Paving: cobblestones in staggered rows (a town's paved plain too).
    return (
      <>
        {COBBLES.map(([cx, cy, cw]) => (
          <rect key={`${cx}${cy}`} x={X + cx} y={Y + cy} width={cw} height={2.6} rx={0.8} fill="none" stroke={shade(fill, -0.22)} strokeWidth={0.4} />
        ))}
      </>
    )
  if (code === 't5')
    // Treasure (the game's 財宝: the 3D map's gold heaped on the floor): coins lying edge to edge in staggered rows, so a hoard of
    // tiles reads as one (the user's call), a glint here and there.
    return (
      <>
        {COINS.map(([cx, cy], i) => (
          <g key={i}>
            <ellipse cx={X + cx} cy={Y + cy} rx={1.15} ry={0.75} fill="#e3b02e" stroke="#8a6414" strokeWidth={0.25} />
            {(i + v) % 4 === 0 && <ellipse cx={X + cx - 0.3} cy={Y + cy - 0.2} rx={0.4} ry={0.22} fill="#ffe489" />}
          </g>
        ))}
      </>
    )
  if (code === 't9')
    // A carpet: a woven lozenge on each tile, a gold knot at its heart.
    return (
      <>
        <rect x={X + 4.6} y={Y + 4.6} width={0.8} height={0.8} fill="#c9a24a" />
        <path d={`M${X + 5} ${Y + 2} L${X + 7} ${Y + 5} L${X + 5} ${Y + 8} L${X + 3} ${Y + 5} Z`} fill="none" stroke={shade(fill, 0.22)} strokeWidth={0.5} />
      </>
    )
  if (code === 'gc')
    // Mossy cobbles (a town of grass and stone): the cobbles, and moss in the joints between them, varied tile to tile.
    return (
      <>
        {COBBLES.map(([cx, cy, cw]) => (
          <rect key={`${cx}${cy}`} x={X + cx} y={Y + cy} width={cw} height={2.6} rx={0.8} fill="none" stroke={shade(fill, -0.22)} strokeWidth={0.4} />
        ))}
        {MOSS[v].map(([mx, my, ml]) => (
          <path key={`m${mx}${my}`} d={`M${X + mx} ${Y + my} h${ml}`} stroke="#6f8f3e" strokeWidth={0.6} strokeLinecap="round" />
        ))}
      </>
    )
  if (code === 'gd')
    // Bare ground in a snowfield: a pebble or two and the last flecks of snow.
    return (
      <>
        {PEBBLES[v].slice(0, 2).map(([px, py]) => <rect key={`${px}${py}`} x={X + px} y={Y + py} width={0.8} height={0.6} rx={0.2} fill={dark} />)}
        {TUFTS[v].map(([tx, ty]) => <rect key={`s${tx}${ty}`} x={X + tx - 0.6} y={Y + ty - 0.4} width={1.3} height={0.7} rx={0.3} fill="#eef3f7" opacity={0.85} />)}
      </>
    )
  if (code === 'tl' || code === 'ga')
    // A road's or a dirt yard's pebbles.
    return (
      <>
        {PEBBLES[v].map(([px, py]) => <rect key={`${px}${py}`} x={X + px} y={Y + py} width={0.8} height={0.6} rx={0.2} fill={dark} />)}
      </>
    )
  if (code === 't3' || code === 'ty')
    return (
      <>
        {[3.33, 6.67].map((o) => <line key={o} x1={X} x2={X + 10} y1={Y + o} y2={Y + o} stroke={dark} strokeWidth={0.45} />)}
        <line x1={X + 2 + v * 2} x2={X + 2 + v * 2} y1={Y} y2={Y + 3.33} stroke={dark} strokeWidth={0.35} />
      </>
    )
  if (code === 'ti' || code === 'db' || code === 'df') {
    // A bog: dark puddles in the mud, a glint on each, a bubble or two, reeds here and there (Gaiden's swamp too: the user's call).
    const { puddle: [cx, cy, rx, ry], bubbles, reeds } = BOG[v]
    return (
      <>
        <ellipse cx={X + cx} cy={Y + cy} rx={rx} ry={ry} fill={shade(fill, -0.3)} />
        <path d={`M${X + cx - rx * 0.5} ${Y + cy - ry * 0.35} h${rx * 0.7}`} stroke={shade(fill, 0.28)} strokeWidth={0.35} strokeLinecap="round" />
        <path d={`M${X + 1} ${Y + 9.2} q0.6 -0.5 1.2 0 t1.2 0`} fill="none" stroke={dark} strokeWidth={0.35} />
        {bubbles.map(([bx, by]) => (
          <circle key={`${bx}${by}`} cx={X + bx} cy={Y + by} r={0.45} fill="none" stroke={shade(fill, 0.22)} strokeWidth={0.3} />
        ))}
        {reeds.map(([rx_, ry_]) => (
          <path key={`${rx_}${ry_}`} d={`M${X + rx_ - 0.5} ${Y + ry_} l-0.3 -1.6 M${X + rx_} ${Y + ry_} v-2.1 M${X + rx_ + 0.5} ${Y + ry_} l0.3 -1.4`}
            fill="none" stroke="#7d8f45" strokeWidth={0.35} strokeLinecap="round" />
        ))}
      </>
    )
  }
  if (code === 't7') return <path d={`M${X} ${Y} ${CRACKS[v].replace(/^M/, 'm')}`} fill="none" stroke={shade(fill, -0.28)} strokeWidth={0.4} />
  if (code === 'wb' || code === 'wt')
    // A cliff's rock layers: a dark ledge with a lit edge under it, and a crack down the face (a rock wall's too).
    return (
      <>
        {STRATA[v].map(([sx, sy, len]) => (
          <g key={`${sx}${sy}`}>
            <line x1={X + sx} x2={X + sx + len} y1={Y + sy} y2={Y + sy} stroke={shade(fill, -0.35)} strokeWidth={0.6} />
            <line x1={X + sx} x2={X + sx + len} y1={Y + sy + 0.6} y2={Y + sy + 0.6} stroke={shade(fill, 0.22)} strokeWidth={0.4} />
          </g>
        ))}
        <path d={`M${X + 2 + v * 2} ${Y + 0.5} l-0.8 1.6 l0.6 1.4`} fill="none" stroke={shade(fill, -0.35)} strokeWidth={0.4} />
      </>
    )
  if (code === 'tm')
    // Rubble: broken stones lying about, each lit along its top, and a crack between.
    return (
      <>
        {RUBBLE_STONES[v].map(([sx, sy, sw]) => (
          <g key={`${sx}${sy}`}>
            <rect x={X + sx} y={Y + sy} width={sw} height={sw * 0.7} rx={0.4} fill={shade(fill, -0.18)} />
            <path d={`M${X + sx + 0.3} ${Y + sy + 0.3} h${sw - 0.6}`} stroke={shade(fill, 0.22)} strokeWidth={0.35} strokeLinecap="round" />
          </g>
        ))}
        <path d={`M${X} ${Y} ${CRACKS[(v + 2) % 4].replace(/^M/, 'm')}`} fill="none" stroke={shade(fill, -0.3)} strokeWidth={0.35} />
      </>
    )
  if (code === 'w7')
    // A roof's shingles: rows of curved tiles, each row's edge shaded.
    return (
      <>
        {[3.2, 6.6, 10].map((o) => (
          <path key={o} d={`M${X} ${Y + o} ${SHINGLES}`} fill="none" stroke="#6e3a2a" strokeWidth={0.5} />
        ))}
      </>
    )
  return null
}

/** A chest or a door on a tile: the mark of a change it sets off (opening it), so no other mark is drawn there. */
const ownMark = (map: ChapterMap, t: Tile) =>
  ['oa', 'or', 'ob'].includes(codeAt(map, t) ?? '') || map.objects.some((o) => o.type === 'chest' && sameTile(o.tile, t))
/** A change's tile (the legend's: any difficulty's will do, the kind of mark is the same). */
const changeTile = (c: MapChange): Tile => c.tile.default
/** A change that shuts the door on its own tile (a doorway open at the start). */
const shutsDoor = (c: MapChange, t: Tile) => (c.patch ?? []).some((p) => p.becomes === 'ob' && sameTile(p.tile, t))

/** What the game draws on a tile that its terrain doesn't say (`decor`): a door nothing opens in a wall and a stone bridge's side
 * (Gaiden's), bones on the ground (Mystery of the Emblem's deserts). */
const DECOR_SPRITE: Record<NonNullable<ChapterMap['decor']>[string], Sprite> = { door: SEALED_DOOR, bones: BONES, bridge: BRIDGE_SIDE }

/**
 * What a tile with an icon on the plain ground's colour (woods, forts, villages, chests) stands on, on a map that gives its ground's
 * colours: the ground most common around it (a road only where nothing else is), out to three tiles.
 */
function groundUnder(map: ChapterMap): Map<string, TerrainCode> {
  const out = new Map<string, TerrainCode>()
  const fills = map.fills ?? {}
  const rows = map.grid.map(rowCodes)
  if (!map.fills && !rows.some((r) => r.some((c) => GROUND_CODES.has(c)))) return out
  const at = (x: number, y: number) => (x >= 1 && y >= 1 && x <= map.width && y <= map.height ? rows[map.height - y][x - 1] : undefined)
  // Walls take a map's colours too (the Tellius minimaps'), but an icon never stands on a wall (the user: chests and candlesticks in
  // a castle came out wall-coloured).
  const ground = (c: TerrainCode | undefined): c is TerrainCode =>
    !!c && (GROUND_CODES.has(c) || (c in fills && !WATER_CODES.has(c) && c[0] !== 'w' && c !== 'tb' && c !== 't8'))
  let common: TerrainCode | null | undefined
  for (let y = 1; y <= map.height; y++) {
    for (let x = 1; x <= map.width; x++) {
      const c = at(x, y)!
      // A rooftop town's stalls on a wall stand on its ground too, and its bare walls drawn as ground are that ground.
      const walledGround = !!map.rooftops?.stalls?.includes(tileKey([x, y])) || !!map.rooftops?.ground?.includes(tileKey([x, y]))
      if (!walledGround && (c in fills || (TERRAIN_FILL[c] !== TERRAIN_FILL.ta && !ON_THE_GROUND.has(c)))) continue
      // A tree stands on the ground outdoors where there's any near, never a castle's floor by it.
      for (const outdoors of TREE_CODES.has(c) ? [true, false] : [false]) {
        for (let r = 1; r <= 3 && !out.has(tileKey([x, y])); r++) {
          const count = new Map<TerrainCode, number>()
          for (let dy = -r; dy <= r; dy++) for (let dx = -r; dx <= r; dx++) {
            const n = at(x + dx, y + dy)
            if (ground(n) && !(outdoors && INDOOR_GROUND.has(n))) count.set(n, (count.get(n) ?? 0) + (n === 'tl' ? 0.01 : 1))
          }
          if (count.size) out.set(tileKey([x, y]), [...count.entries()].sort((a, b) => b[1] - a[1])[0][0])
        }
        if (out.has(tileKey([x, y]))) break
      }
      // Deep in a wood with no ground for three tiles: the map's most common ground (the user: Ch.6's trees came out tan).
      if (!out.has(tileKey([x, y]))) {
        if (!common) {
          const all = new Map<TerrainCode, number>()
          for (const row of rows) for (const n of row) if (ground(n)) all.set(n, (all.get(n) ?? 0) + 1)
          common = [...all.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? null
        }
        if (common) out.set(tileKey([x, y]), common)
      }
    }
  }
  return out
}

/** A village's houses and walls (the GBA games', fliers cross them), as the game draws them: a little red-roofed house on a green
 * yard, the yard fenced along its outer sides (the user's pick). `sides`: the tile's sides that face out of the village. */
function VillageTile({ X, Y, yard, sides }: { X: number; Y: number; yard: string; sides: ('n' | 's' | 'w' | 'e')[] }) {
  const seg = { n: [0, 0.6, 10, 0.6], s: [0, 9.4, 10, 9.4], w: [0.6, 0, 0.6, 10], e: [9.4, 0, 9.4, 10] }
  return (
    <>
      <rect x={X} y={Y} width={CELL} height={CELL} fill={yard} />
      <rect x={X + 2.2} y={Y + 4.6} width={5.6} height={3.8} fill="#efe6cf" stroke="#5c4a36" strokeWidth={0.35} />
      <rect x={X + 4.3} y={Y + 6.2} width={1.4} height={2.2} fill="#5c4a36" />
      <polygon points={`${X + 1.2},${Y + 5} ${X + 5},${Y + 1.4} ${X + 8.8},${Y + 5}`} fill="#c4462f" stroke="#6e2416" strokeWidth={0.4} />
      {sides.map((side) => {
        const [x1, y1, x2, y2] = seg[side]
        return (
          <g key={side}>
            <line x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke="#4d3d27" strokeWidth={1.2} />
            <line x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke="#f2ecdc" strokeWidth={0.5} strokeDasharray="0.5 1.2" />
          </g>
        )
      })}
    </>
  )
}
/** The step to the tile beside one, by side (map y counts up). */
const SIDE_STEP = { n: [0, 1], s: [0, -1], w: [-1, 0], e: [1, 0] } as const

/** A rooftop town's buildings the game makes walls (no unit enters them, fliers included), drawn as the roofs and stalls the 3D map
 * shows: a railing along each side they meet a tile that isn't a wall (the user's call: a railing, not a fliers' mark). */
function railedSides(map: ChapterMap): { tile: Tile; side: keyof typeof SIDE_STEP }[] {
  if (!map.rooftops) return []
  const walled = (t: Tile) =>
    terrainAt(map, t)[0] === 'w' &&
    (roofAt(map, t) || !!map.rooftops?.stalls?.includes(tileKey(t)) || !!map.rooftops?.ground?.includes(tileKey(t)))
  const out: { tile: Tile; side: keyof typeof SIDE_STEP }[] = []
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      if (!walled([x, y])) continue
      for (const side of ['n', 's', 'w', 'e'] as const) {
        const n: Tile = [x + SIDE_STEP[side][0], y + SIDE_STEP[side][1]]
        if (n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height && terrainAt(map, n)[0] !== 'w') out.push({ tile: [x, y], side })
      }
    }
  return out
}
/** What counts as inside a village's fence: its houses and walls, and its entrance (the village, house or shop). */
const VILLAGE_INSIDE = new Set<TerrainCode>([
  'w8', 'oc', 'od', 'ot', 'om', 'on', 'oo', 'op', 'va', 'vb', 'vc', 'vd', 've', 'vf', 'vg', 'vh', 'vi',
])

/** A building's piece (its group, v a village's, c a castle's, r a town house's, k a church's or p a prison camp's, then its place
 * a-i). */
const PIECE = /^[vcrkp][a-i]$/
/** The pieces that make up one kind of thing (a building, a market's stalls): one line in the legend. */
const family = (code: TerrainCode) => (PIECE.test(code) ? code[0] : /^o[5-8]$/.test(code) ? 'stall' : null)

/** Terrain that gets a pixel-art icon on top of its fill; the rest (floor, wall, water, chasm,
 * bridge, building) reads fine as colour alone. */
const TERRAIN_SPRITE: Partial<Record<TerrainCode, Sprite>> = {
  tc: STAIRS, ba: TREE, bb: FORT, bd: GATE, be: OLD_GATE, bf: GATEWAY, bv: GATE, bg: LEDGE, bh: PILLAR, bm: MOUNTAIN, bo: DEF_SIGIL,
  bp: DEF2_SIGIL, bq: RES_SIGIL, br: DEF_SIGIL, ha: HEAL, hb: HEAL, hh: DEF_FLOOR, hd: VASE_MEDICINE, he: HEAL, hf: HEAL_FLOOR,
  dd: LAVA_CRACK, de: SPIKES, wc: SNOW_PEAK, wh: THICK_WOOD, wj: RUBBLE, wq: RUBBLE_WALL, wr: ICE_BLOCK, oa: CHEST, ob: DOOR, oc: HOUSE, of: BALLISTA, oy: BALLISTA, oz: FIRE_ORB, ol: CASTLE,
  bu: PEAK, om: ARMORY, on: VENDOR, oo: ARENA, op: SECRET_SHOP, or: CHEST, bw: RES_FLOOR, bx: RES_FLOOR, os: VENDOR, by: DEF_FLOOR, bz: STAIRS,
  b0: DEF_FLOOR, b1: BULWARK, b2: GRAVE, b3: PILLAR, tq: FELL_FLOOR,
  // Fates: a cushion is a fort in all but looks; Ryoma's hall floor heals 5%, a badge as it covers the room.
  bi: FORT, hc: HEAL_FLOOR, bj: WARD, oi: SIGIL, bs: FISSURE, da: ACID_BOG, db: MUCK, dc: CALTROPS,
  // Path of Radiance's trail and coast give Def +1 and Avo +10, so they get a little detail.
  bl: TRAIL, b4: COAST,
  // The GBA games' houses and inns: Avo like a village's, but no looter goes for them.
  ot: COTTAGE,
  o1: BARREL,
  o3: CRATES,
  o4: ODDS_AND_ENDS,
  o5: MARKET_STALL.left,
  o6: MARKET_STALL.mid,
  o7: MARKET_STALL.right,
  o8: MARKET_STALL.alone,
  ...Object.fromEntries(Object.entries(HOUSE_PIECES).map(([p, sprite]) => [`r${p}`, sprite])),
  ...Object.fromEntries(Object.entries(HOUSE_SIDE_PIECES).map(([p, sprite]) => [`r${p}`, sprite])),
  ...Object.fromEntries(Object.entries(FOUNTAIN_PIECES).map(([p, sprite]) => [`f${p}`, sprite])),
  ...Object.fromEntries(Object.entries(CHURCH_PIECES).map(([p, sprite]) => [`k${p}`, sprite])),
  ...Object.fromEntries(Object.entries(CAMP_PIECES).map(([p, sprite]) => [`p${p}`, sprite])),
  o9: WATCHTOWER,
  // Lava no one crosses is molten; burning ground (and the GBA games' fire traps) cracked lava, as the games draw them.
  wp: LAVA_POOL,
  o2: BONES,
  // A village's and a castle's pieces, a sprite for each place in the building (a-c its top, d-f its middle, g-i its front).
  ...Object.fromEntries(Object.entries(VILLAGE_PIECES).map(([p, sprite]) => [`v${p}`, sprite])),
  ...Object.fromEntries(Object.entries(CASTLE_PIECES).map(([p, sprite]) => [`c${p}`, sprite])),
  // Mystery of the Emblem's tunnels: Avo 25 at a mountain's costs.
  tp: TUNNEL,
  // Genealogy of the Holy War's thickets (Avo 40, barbarians, hunters and fliers only), churches (they heal) and castle gates (where a
  // castle is entered).
  bt: THICKET, oj: CHURCH, o0: GATE,
  // Mystery of the Emblem's castle tiles that don't heal (a gate's flanks): a castle where they stand alone (castleFront otherwise).
  ou: CASTLE,
  // A village or house that can't be visited (Thracia's and The Binding Blade's closed ones): a house with no door on its ground (two
  // tiles of it, one over the other, a razed village: twoTileVillage).
  od: TOWN_HOUSE,
  // Shadow Dragon's tiles the lord can't enter keep their base's icon; the lord badge marks them (below).
  b5: TREE, b6: FORT, b7: MOUNTAIN,
  // Three Houses: its lighter thicket is woods to look at; its Avoid floor is a floor bonus like the others; the prayer stone heals;
  // the Holy Tomb's Crest Stones sit in its walls.
  b8: TREE, b9: DEF_FLOOR, hg: HEAL, ow: CREST_STONE,
  // Its floor traps and craters, and the siege engines a unit fires: onagers and fire orbs (Fates' fire orbs too). (Its swamp is mud,
  // drawn as Radiant Dawn's bog: GroundDetail.)
  dg: FLOOR_TRAP, dh: CRATER, ox: ONAGER, og: FIRE_ORB,
  // Engage's effects laid over a tile (Dragon Vein terrain, miasma), each a badge over the tile's own icon.
  ea: FOG, eb: FOG, ec: PUDDLE, ed: PUDDLE, ee: STONE_PILLARS, ef: FLAME, eg: MIASMA, eh: MIASMA, ei: FROST,
}

/** An effect laid over woods or pillars keeps their icon under its badge. */
const UNDER_SPRITE: Partial<Record<TerrainCode, Sprite>> = { eb: TREE, ed: TREE, eh: PILLAR }

/** Tiles the lord alone can't enter (Shadow Dragon's categories 25-29): a corner badge on top of the tile's own icon. */
const LORD_BLOCKED = new Set<TerrainCode>(['tu', 'b5', 'b6', 'b7'])

/** Terrain whose own icon is a building you visit (a village, the GBA games' houses): a village or house standing on it needs no
 * house drawn on top. */
const marksBuilding = (code: TerrainCode) => TERRAIN_SPRITE[code] === HOUSE || TERRAIN_SPRITE[code] === COTTAGE

/** A shop's icon by kind: drawn over a shop that sits on terrain without one (Mystery of the Emblem's secret shops are ordinary tiles). */
const SHOP_SPRITE: Record<string, Sprite> = { Armory: ARMORY, Vendor: VENDOR, 'Secret shop': SECRET_SHOP }

/** Terrain whose icon is a small top-left badge instead (the drop badge is top-right): the Tower's floors cover
 * most of the Endgame's maps, and Echoes' castle floors most of its castles, so full-size icons would hide the map. */
const BADGE_TERRAIN = new Set<TerrainCode>(['hf', 'bw', 'bx', 'hc', 'b9', 'ea', 'eb', 'ec', 'ed', 'ee',
  'ef', 'eg', 'eh', 'ei'])

/** The map's terrain at one phase of a cloud map: the clouds drift one tile left each phase, wrapping round. */
function withClouds(map: ChapterMap, phase: number): ChapterMap {
  const c = map.clouds
  if (!c) return map
  const grid = map.grid.map((row, r) =>
    rowCodes(row)
      .map((code, x) => {
        if (code !== 'bn' && code !== 'wf') return code
        const pattern = c.pattern[r]
        return pattern[(c.left + x + phase) % pattern.length] === '#' ? 'bn' : 'wf'
      })
      .join(''),
  )
  return { ...map, grid }
}

/** How many turns the switching walls take to come round again: each set is back after two of its flips. */
function wallCycle(sw: NonNullable<ChapterMap['switchWalls']>): number {
  const gcd = (a: number, b: number): number => (b ? gcd(b, a % b) : a)
  return sw.turns.reduce((n, t) => (n * 2 * t.every) / gcd(n, 2 * t.every), 1)
}

/** The first three turns from `from` that divide by `every`. */
const firstMultiples = (every: number, from: number) => [0, 1, 2].map((k) => (Math.ceil(from / every) + k) * every)

/** A torch is lit when it starts lit and isn't being previewed as put out, or the other way round. */
const torchLit = (c: ChapterMap['changes'][number], previewing: Set<string>) => Boolean(c.lit) !== previewing.has(c.id)

/** Every tile the lit torches light (within each one's radius, counted in steps as Fire Emblem counts range). */
function torchLight(map: ChapterMap, previewing: Set<string>): Set<string> {
  const out = new Set<string>()
  for (const c of map.changes)
    if (c.trigger === 'torch' && torchLit(c, previewing)) for (const t of tilesInRadius(map, c.tile.default, c.radius ?? 0)) out.add(tileKey(t))
  return out
}

/** Boss, named foes, allies and pairs get their own sprite; everyone else is a plain red marker. Drops are a badge on top. */
function unitSprite(u: MapUnit): Sprite {
  if (u.type === 'boss') return SKULL
  if (u.type === 'named') return NAMED_ENEMY
  // The person icon is for named green units; generic ones are a plain green dot. A partner unit, or a neutral one (no game has
  // both), is the same in yellow.
  if (u.type === 'ally' && (u.yellow || u.neutral)) return u.generic ? COMMON_PARTNER : PARTNER
  if (u.type === 'ally') return u.generic ? COMMON_ALLY : ALLY
  if (u.paired) return COMMON_PAIR
  return COMMON_ENEMY
}
const UNIT_NAME: Record<MapUnit['type'], string> = { boss: 'Boss', named: 'Named enemy', enemy: 'Enemy', ally: 'Ally' }

/** A reinforcement's marker: the orange ring, or a named foe's figure or a boss's skull in the ring's orange. */
const reinforcementSprite = (u: MapUnit) => (u.type === 'boss' ? BOSS_REINFORCEMENT : u.type === 'named' ? NAMED_REINFORCEMENT : REINFORCEMENT)

/** A green joiner's marker: the person icon if it's named, a plain green dot if not; a partner's the same in yellow. */
const joinerSprite = (j: Joiner) =>
  !j.ally ? JOINER : j.yellow || j.neutral ? (j.generic ? COMMON_PARTNER : PARTNER) : j.generic ? COMMON_ALLY : ALLY


type Pot = Extract<MapObject, { type: 'pot' }>

/** A reinforcement or joiner currently drawn on the map. */
type ShownArrival =
  | { kind: 'reinforcement'; group: string; when?: string; unit: MapUnit & { from?: Tile } }
  | { kind: 'joiner'; joiner: Joiner }

const onDifficulty = (d: Difficulty) => (u: MapUnit) => !u.difficulties || u.difficulties.includes(d)
const headcount = (units: MapUnit[]) => units.reduce((n, u) => n + (u.paired ? 2 : 1), 0)
const arrivalTile = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.tile : a.unit.tile)

/** A monster's health bars as pips along the bottom of its marker (`span` units square, its top-left at x, y), centred, one per bar. */
function HealthPips({ bars, x, y, span }: { bars: number; x: number; y: number; span: number }) {
  const gap = 0.8
  const w = Math.min(2.6, (span - 2 - (bars - 1) * gap) / bars)
  const left = x + (span - (bars * w + (bars - 1) * gap)) / 2
  return (
    <g pointerEvents="none">
      {Array.from({ length: bars }, (_, i) => (
        <rect key={i} x={left + i * (w + gap)} y={y + span - 2.8} width={w} height={1.7} rx={0.3} fill="#4ade80" stroke="#0a0a0a" strokeWidth={0.45} />
      ))}
    </g>
  )
}
const arrivalFrom = (a: ShownArrival) => (a.kind === 'joiner' ? a.joiner.from : a.unit.from)

const INFO_BELOW_KEY = 'fe-armory-map-info-below'

/** Whether this device last put the map's info panels below it. */
function savedInfoBelow() {
  try {
    return localStorage.getItem(INFO_BELOW_KEY) === '1'
  } catch {
    return false
  }
}

/** A game's maps: its route buttons (Fates) and chapter list, a grid per chapter, and the tile, arrival and chapter panels. */
export function MapViewer({ set }: { set: MapSet }) {
  const all = set.maps
  // Under the spoiler block only the chapters you've reached are listed, and the page opens on the newest.
  const reach = useReach()
  const newest = reach.now ? all.find((m) => m.id === reach.now) : undefined
  const [mapId, setMapId] = useState((newest ?? all[0]).id)
  const picked = all.find((m) => m.id === mapId && reach.has(m.id)) ?? newest ?? all[0]
  // The difficulty picked in the bar; changing it keeps this map and redraws it as that difficulty lays it out. A map played on
  // fewer difficulties than the game has (The Blazing Blade's Lyn's story: Normal only) shows its own.
  const pickedDifficulty = useDifficulty()
  const difficulties = picked.difficulties ? set.difficulties.filter((d) => picked.difficulties!.includes(d.value)) : set.difficulties
  const difficulty = difficulties.some((d) => d.value === pickedDifficulty) ? pickedDifficulty : difficulties[0].value
  // The block shows a map as it starts: nobody arrives later, on either side. A change some difficulties lack (Fell Xenologue 6's
  // islands sinking on Hard and Maddening) is left off the others.
  const map = useMemo(() => {
    const m = reach.on ? atStart(picked) : picked
    return m.changes.some((c) => c.difficulties)
      ? { ...m, changes: m.changes.filter((c) => !c.difficulties || c.difficulties.includes(difficulty)) }
      : m
  }, [picked, reach.on, difficulty])
  const [route, setRoute] = useState(set.routes ? set.routes.of(map) : '')
  // The second dropdown: a route's paralogues (Fates), or the game's side maps (trial maps).
  const paralogues = (set.routes ? set.routes.side(route) : (set.extras?.maps ?? [])).filter((m) => reach.has(m.id))
  const offMain = [...(set.extras?.maps ?? []), ...(set.third?.maps ?? [])]
  const mainMaps = (set.routes ? set.routes.maps(route) : all.filter((m) => !offMain.includes(m))).filter((m) => reach.has(m.id))
  const sideLabel = set.extras?.label ?? set.routes?.sideLabel ?? 'Paralogues'
  // The third dropdown: the route's challenge battles (Fates), or a game's own third list (Awakening's skirmishes).
  const third = set.routes?.third ?? (set.third ? { label: set.third.label, maps: () => set.third!.maps } : undefined)
  const challenges = (third ? third.maps(route) : []).filter((m) => reach.has(m.id))
  // The fourth: a route's own fourth list (Engage's skirmishes).
  const fourth = set.routes?.fourth
  const fourthMaps = (fourth ? fourth.maps(route) : []).filter((m) => reach.has(m.id))
  const [selected, setSelected] = useState<Tile | null>(null)
  // Each change previews on its own toggle, never all at once.
  const [previewing, setPreviewing] = useState<Set<string>>(new Set())
  // A map its script changes on set turns (the Phantom Ship's ships): how many of its turns' changes are made (0: the start).
  const [step, setStep] = useState(0)
  // Digging (Revelation 10's snow): the tiles cleared so far, and whether a tap on the map digs.
  const [dug, setDug] = useState<Set<string>>(new Set())
  const [digging, setDigging] = useState(false)
  // Reinforcement groups and joiners stay hidden until asked for, so the starting layout reads cleanly.
  const [groups, setGroups] = useState<Set<string>>(new Set())
  const [showJoiners, setShowJoiners] = useState(false)
  // A cloud map's phase: 0 is turn 1's player phase, 1 its enemy phase, and so on.
  const [phase, setPhase] = useState(0)
  // A map whose script raises and lowers walls (Revelation 16): the set the battle started with down, and the turn shown.
  const [wallStart, setWallStart] = useState(0)
  const [wallTurn, setWallTurn] = useState(1)
  // Everyone a stand-in can replace (a character who died or left earlier), swapped all at once.
  const [standIns, setStandIns] = useState(false)
  // The tile, arrival and chapter panels sit beside the map, or below it so a wide map (RD's bridges, FE4) gets the full width.
  const [infoBelow, setInfoBelow] = useState(savedInfoBelow)
  function toggleInfoBelow() {
    setInfoBelow((v) => {
      try {
        localStorage.setItem(INFO_BELOW_KEY, v ? '0' : '1')
      } catch {
        // Not remembered this time.
      }
      return !v
    })
  }
  const hasStandIns = [...map.units, ...(map.reinforcements ?? []).flatMap((g) => g.units), ...(map.joiners ?? []), ...(map.forced ?? [])].some(
    (u) => u.standIn,
  )
  const cast = useMemo(() => (standIns ? withStandIns(map) : map), [map, standIns])
  // The map's states through its turns, and every change made in the one shown: the previewed ones, and its turns' up to `step`.
  const steps = useMemo(() => mapSteps(map), [map])
  const active = useMemo(
    () => (step ? new Set([...previewing, ...steps.slice(0, step).flatMap((s) => s.ids)]) : previewing),
    [previewing, steps, step],
  )

  const potsBroken = map.changes.some((c) => c.breaksAllPots && active.has(c.id))
  // The map with every previewed change's terrain patch applied.
  // ...and with only the units present on the chosen difficulty.
  // ...the tiles dug so far, and the foes hidden under them.
  const seen = useMemo(() => {
    const digs = cast.changes.filter((c) => c.dig)
    const digPatch = digs.filter((c) => !active.has(c.id)).flatMap((c) => (c.patch ?? []).filter((p) => dug.has(tileKey(p.tile))))
    // The review captures show each closed room as it actually is: its floor as the door that opens it lays it (the user's call).
    const roomPatch = REVEAL ? cast.changes.flatMap((c) => (c.patch ?? []).filter((p) => terrainAt(cast, p.tile) === 'ws')) : []
    const patched = withSwitchWalls(withClouds(applyChanges(cast, active, [...digPatch, ...roomPatch]), phase), wallStart, wallTurn, active)
    const cleared = (t: Tile) =>
      dug.has(tileKey(t)) || digs.some((c) => active.has(c.id) && (c.patch ?? []).some((p) => sameTile(p.tile, t)))
    return {
      ...patched,
      fog: patched.fog || !!patched.fogOn?.includes(difficulty),
      units: patched.units.filter((u) => (!u.difficulties || u.difficulties.includes(difficulty)) && (!u.buried || cleared(u.tile))),
      objects: patched.objects.filter((o) => !('difficulties' in o) || !o.difficulties || o.difficulties.includes(difficulty)),
    }
  }, [cast, active, difficulty, phase, dug, wallStart, wallTurn])
  // A map fogged at the start hides the foes your army can't see from its starting tiles or by a lit torch, and, under the spoiler
  // block, Thracia's the ground beyond your units' sight.
  const fogged = useMemo(
    () => (seen.fog && !REVEAL ? inTheFog(seen, torchLight(seen, active), reach.on) : null),
    [reach.on, seen, active],
  )
  const unseen = fogged?.unseen
  const sight = fogged?.seen
  // A closed room under its roof hides what's in it, as the game draws it, until a door into it opens (previewed).
  const closed = useMemo(() => (REVEAL ? new Set<string>() : closedRooms(seen)), [seen])
  const shown = useMemo(() => {
    if (!fogged && closed.size === 0) return seen
    const units = fogged ? fogged.units : seen.units
    const hidden = (t: Tile) => closed.has(tileKey(t)) || !!unseen?.has(tileKey(t))
    // A room's steps and fences are under its roof too, until a door into it opens (the user: Ch.27's showed through).
    const walls = seen.walls?.filter(
      ({ tile: [x, y], side }) => !closed.has(tileKey([x, y])) && !closed.has(tileKey(side === 'e' ? [x + 1, y] : [x, y - 1])),
    )
    return {
      ...seen,
      units: units.filter((u) => !closed.has(tileKey(u.tile))),
      objects: seen.objects.filter((o) => !hidden(o.tile)),
      ...(seen.walls ? { walls } : {}),
    }
  }, [seen, fogged, unseen, closed])
  const arrivals = useMemo((): ShownArrival[] => {
    const out: ShownArrival[] = []
    for (const g of cast.reinforcements ?? []) {
      if (!groups.has(g.id)) continue
      const when = whenText(g, difficulty)
      for (const unit of g.units.filter(onDifficulty(difficulty))) out.push({ kind: 'reinforcement', group: g.label, when, unit })
    }
    if (showJoiners) for (const joiner of (cast.joiners ?? []).filter(joinsOn(difficulty))) out.push({ kind: 'joiner', joiner })
    // Who arrives inside a closed room isn't seen until it opens.
    return closed.size ? out.filter((a) => !closed.has(tileKey(arrivalTile(a)))) : out
  }, [cast, groups, showJoiners, difficulty, closed])
  // The map areas whose entry brings in (or stops) a group or joiner that's being shown.
  const triggers = useMemo(() => {
    const seen = new Map<string, NonNullable<Arrival['areas']>[number]>()
    const add = (areas: Arrival['areas']) => {
      for (const a of areas ?? []) seen.set(`${a.who}${a.rect.join(',')}${a.step ?? ''}`, a)
    }
    for (const g of map.reinforcements ?? []) if (groups.has(g.id)) add(g.areas)
    if (showJoiners) for (const j of (map.joiners ?? []).filter(joinsOn(difficulty))) add(j.areas)
    return [...seen.values()]
  }, [map, groups, showJoiners, difficulty])
  const selectedPot = selected
    ?(objectsAt(map, selected).find((o) => o.type === 'pot') as Pot | undefined)
    : undefined
  const radius = useMemo(
    () => new Set(selectedPot && !potsBroken ? tilesInRadius(map, selectedPot.tile, selectedPot.radius).map(tileKey) : []),
    [map, selectedPot, potsBroken],
  )

  function togglePreview(id: string) {
    // A turn's change shows the map as that turn leaves it, the turns before it made too; previewed again, as the turn before.
    const at = steps.findIndex((s) => s.ids.includes(id)) + 1
    if (at > 0) {
      setStep((s) => (s >= at ? at - 1 : at))
      return
    }
    setPreviewing((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  // Proceeding to the next chapter takes the page to its map.
  const [openedTo, setOpenedTo] = useState(reach.at)
  if (newest && openedTo !== reach.at) {
    setOpenedTo(reach.at)
    choose(newest.id)
  }

  // Showing who arrives on a turn shows the map as it stands by then (the Phantom Ship's joiners come on the ship of turn 5).
  function stepFor(when: string | undefined) {
    const turn = arrivalTurn(when)
    return turn === undefined ? 0 : steps.filter((s) => s.turn <= turn).length
  }
  function reachStep(whens: (string | undefined)[]) {
    if (steps.length) setStep((s) => Math.max(s, ...whens.map(stepFor)))
  }

  function choose(id: string) {
    setMapId(id)
    setSelected(null)
    setPreviewing(new Set())
    setStep(0)
    setDug(new Set())
    setDigging(false)
    setGroups(new Set())
    setShowJoiners(false)
    setPhase(0)
    setWallStart(0)
    setWallTurn(1)
  }

  function chooseRoute(next: string) {
    setRoute(next)
    // A chapter the new route plays too (Three Houses' White Clouds, shared by the routes of a house), or a paralogue or challenge it
    // can also reach, stays open; anything else gives way to the route's first map.
    const shared =
      set.routes!.maps(next).some((m) => m.id === map.id) ||
      ((map.route === 'Paralogue' || map.route === 'Challenge') && map.availableIn?.some((r) => r === next))
    if (!shared) choose(set.routes!.maps(next)[0].id)
  }

  const onParalogue = paralogues.includes(picked)
  const onChallenge = challenges.includes(picked)
  const onFourth = fourthMaps.includes(picked)
  const offStory = onParalogue || onChallenge || onFourth
  const dlcGroups = [...new Set(mainMaps.map((m) => m.heading ?? ''))]
  const select = 'rounded border border-neutral-700 bg-neutral-900 px-2 py-1'

  return (
    <div className="flex flex-col gap-4">
      {set.routes && (
      <div className="flex flex-wrap gap-1" role="group" aria-label="Route">
        {set.routes.list.filter((r) => !reach.on || set.routes!.maps(r).some((m) => reach.has(m.id))).map((r) => (
          <button
            key={r}
            onClick={() => chooseRoute(r)}
            aria-pressed={route === r}
            className={`rounded border px-3 py-1 text-sm ${
              route === r ? 'border-emerald-500 bg-emerald-950/60 text-emerald-100' : 'border-neutral-700 text-neutral-300 hover:bg-neutral-800'
            }`}
          >
            {r}
          </button>
        ))}
      </div>
      )}
      <div className="flex flex-wrap items-center gap-3">
        <select value={offStory ? '' : map.id} onChange={(e) => choose(e.target.value)} className={select} aria-label="Chapter">
          {offStory && (
            <option value="" disabled>
              Story chapters…
            </option>
          )}
          {route === 'DLC'
            ? dlcGroups.map((g) => (
                <optgroup key={g} label={g === 'Xenologue' ? 'Xenologues' : g === 'Hero Battle' ? 'amiibo Hero Battles' : g}>
                  {mainMaps
                    .filter((m) => (m.heading ?? '') === g)
                    .map((m) => (
                      <option key={m.id} value={m.id}>
                        {set.chapterLabel(m)}
                      </option>
                    ))}
                </optgroup>
              ))
            : mainMaps.map((m) => (
                <option key={m.id} value={m.id}>
                  {set.chapterLabel(m)}
                </option>
              ))}
        </select>
        {paralogues.length > 0 && (
          <select value={onParalogue ? map.id : ''} onChange={(e) => choose(e.target.value)} className={select} aria-label={sideLabel}>
            {!onParalogue && (
              <option value="" disabled>
                {sideLabel} ({paralogues.length})…
              </option>
            )}
            {paralogues.map((m) => (
              <option key={m.id} value={m.id}>
                {set.chapterLabel(m)}
              </option>
            ))}
          </select>
        )}
        {third && challenges.length > 0 && (
          <select value={onChallenge ? map.id : ''} onChange={(e) => choose(e.target.value)} className={select} aria-label={third.label}>
            {!onChallenge && (
              <option value="" disabled>
                {third.label} ({challenges.length})…
              </option>
            )}
            {challenges.map((m) => (
              <option key={m.id} value={m.id}>
                {set.chapterLabel(m)}
              </option>
            ))}
          </select>
        )}
        {fourth && fourthMaps.length > 0 && (
          <select value={onFourth ? map.id : ''} onChange={(e) => choose(e.target.value)} className={select} aria-label={fourth.label}>
            {!onFourth && (
              <option value="" disabled>
                {fourth.label} ({fourthMaps.length})…
              </option>
            )}
            {fourthMaps.map((m) => (
              <option key={m.id} value={m.id}>
                {set.chapterLabel(m)}
              </option>
            ))}
          </select>
        )}
        {difficulty !== pickedDifficulty && (
          <span className="self-center text-sm text-neutral-500">{difficulties.find((d) => d.value === difficulty)?.label} only</span>
        )}
        {hasStandIns && (
          <button
            type="button"
            onClick={() => setStandIns((v) => !v)}
            aria-pressed={standIns}
            className={`rounded border px-2 py-1 ${standIns ? 'border-amber-500 bg-amber-950 text-amber-200' : 'border-neutral-700 bg-neutral-900'}`}
          >
            {standIns ? 'Showing stand-ins' : 'Show stand-ins'}
          </button>
        )}
        <button
          type="button"
          onClick={toggleInfoBelow}
          aria-pressed={infoBelow}
          title="Puts the tile and chapter panels under the map, so the map can use the full width."
          className={`rounded border px-2 py-1 ${infoBelow ? 'border-emerald-500 bg-emerald-950 text-emerald-200' : 'border-neutral-700 bg-neutral-900'}`}
        >
          {infoBelow ? 'Info below the map' : 'Info beside the map'}
        </button>
        {steps.length > 0 && !reach.on && (
          <div className="flex items-center gap-1" role="group" aria-label="The map by turn">
            <button
              type="button"
              onClick={() => setStep((s) => Math.max(0, s - 1))}
              disabled={step === 0}
              aria-label="The turn before"
              className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 disabled:opacity-40"
            >
              ‹
            </button>
            <select value={step} onChange={(e) => setStep(Number(e.target.value))} className={select} aria-label="The map as it stands">
              <option value={0}>Map at the start</option>
              {steps.map((s, i) => (
                <option key={s.turn} value={i + 1}>
                  Map from {s.label.charAt(0).toLowerCase() + s.label.slice(1)}
                </option>
              ))}
            </select>
            <button
              type="button"
              onClick={() => setStep((s) => Math.min(steps.length, s + 1))}
              disabled={step === steps.length}
              aria-label="The next turn"
              className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 disabled:opacity-40"
            >
              ›
            </button>
          </div>
        )}
        {map.clouds && (
          <select value={phase} onChange={(e) => setPhase(Number(e.target.value))} className={select} aria-label="Clouds at">
            {Array.from({ length: map.clouds.turns * 2 }, (_, i) => (
              <option key={i} value={i}>
                Clouds on turn {Math.floor(i / 2) + 1}, {i % 2 ? 'enemy' : 'player'} phase
              </option>
            ))}
          </select>
        )}
        {map.switchWalls && (
          <>
            <select value={wallStart} onChange={(e) => setWallStart(Number(e.target.value))} className={select} aria-label="Walls down at the battle's start">
              {map.switchWalls.starts.map((_, i) => (
                <option key={i} value={i}>
                  Battle start: set {i + 1} of {map.switchWalls!.starts.length} down
                </option>
              ))}
            </select>
            <select value={wallTurn} onChange={(e) => setWallTurn(Number(e.target.value))} className={select} aria-label="Walls on turn">
              {Array.from({ length: wallCycle(map.switchWalls) }, (_, i) => (
                <option key={i} value={i + 1}>
                  Walls on turn {i + 1}
                </option>
              ))}
            </select>
          </>
        )}
      </div>

      <div className={infoBelow ? 'flex flex-col gap-4' : 'grid grid-cols-1 gap-4 lg:grid-cols-[minmax(0,560px)_1fr]'}>
        <div className="flex flex-col gap-2">
          <MapGrid
            map={shown}
            unseen={unseen}
            sight={sight}
            difficulty={difficulty}
            selected={selected}
            radius={radius}
            potsBroken={potsBroken}
            previewing={active}
            arrivals={arrivals}
            triggers={triggers}
            onSelect={(t) => {
              // While digging, a tap on snow clears it and the four tiles beside it, as an attack on it does in the game.
              const dig = digging ? map.changes.find((c) => c.dig && !active.has(c.id)) : undefined
              if (dig && !dug.has(tileKey(t)) && (dig.patch ?? []).some((p) => sameTile(p.tile, t))) {
                setDug((prev) => new Set([...prev, ...digAt(dig, t)]))
                setSelected(t)
                return
              }
              setSelected((prev) => (prev && sameTile(prev, t) ? null : t))
            }}
          />
          <Legend map={shown} unseen={unseen} hidesFoes={!!sight} arrivals={arrivals} triggers={triggers} takeBy={set.takeBy} />
        </div>

        <div className={infoBelow ? 'grid grid-cols-1 items-start gap-4 lg:grid-cols-2' : 'flex flex-col gap-4'}>
          <TileInfo
            set={set}
            map={shown}
            unseen={unseen}
            sight={sight}
            difficulty={difficulty}
            tile={selected}
            closed={closed}
            potsBroken={potsBroken}
            previewing={active}
            arrivals={arrivals}
            onTogglePreview={togglePreview}
            onPreviewGroup={(ids, on) =>
              setPreviewing((prev) => {
                const next = new Set(prev)
                for (const id of ids) {
                  if (on) next.add(id)
                  else next.delete(id)
                }
                return next
              })
            }
            onReset={() => {
              setPreviewing(new Set())
              setStep(0)
              setDug(new Set())
              setDigging(false)
            }}
            digging={digging}
            dugCount={dug.size}
            onToggleDig={() => setDigging((v) => !v)}
          />
          <ArrivalsPanel
            map={cast}
            difficulty={difficulty}
            difficultyLabel={set.difficulties.find((d) => d.value === difficulty)?.label ?? difficulty}
            groups={groups}
            showJoiners={showJoiners}
            onToggleGroup={(id) => {
              if (!groups.has(id)) reachStep([whenText(cast.reinforcements!.find((g) => g.id === id)!, difficulty)])
              setGroups((prev) => {
                const next = new Set(prev)
                if (next.has(id)) next.delete(id)
                else next.add(id)
                return next
              })
            }}
            onSetGroups={(ids) => {
              reachStep((cast.reinforcements ?? []).filter((g) => ids.has(g.id) && !groups.has(g.id)).map((g) => whenText(g, difficulty)))
              setGroups(ids)
            }}
            onToggleJoiners={() => {
              if (!showJoiners) reachStep((cast.joiners ?? []).filter(joinsOn(difficulty)).map((j) => whenText(j, difficulty)))
              setShowJoiners((v) => !v)
            }}
          />
          <ChapterInfo map={cast} label={set.mapLabel(map)} difficulty={difficulty} />
        </div>
      </div>

      <PotList map={map} onSelect={setSelected} selected={selected} broken={potsBroken} />
    </div>
  )
}

function MapGrid({
  map,
  unseen,
  sight,
  difficulty,
  selected,
  radius,
  potsBroken,
  previewing,
  arrivals,
  triggers,
  onSelect,
}: {
  map: ChapterMap
  /** Tiles Thracia's fog keeps black (`inTheFog`): drawn over everything but the units. */
  unseen?: Set<string>
  /** What your army sees on a map fogged at the start (`inTheFog`): left unshaded. */
  sight?: Set<string>
  difficulty: Difficulty
  selected: Tile | null
  radius: Set<string>
  potsBroken: boolean
  previewing: Set<string>
  arrivals: ShownArrival[]
  triggers: NonNullable<Arrival['areas']>
  onSelect: (t: Tile) => void
}) {
  // SVG y grows downward, map y grows upward: screen row = height - y.
  const px = (x: number) => GUTTER + (x - 1) * CELL
  const py = (y: number) => (map.height - y) * CELL
  const tiles: Tile[] = []
  for (let y = map.height; y >= 1; y--) for (let x = 1; x <= map.width; x++) tiles.push([x, y])
  const dark = new Set((map.dark ?? []).map(tileKey))
  const under = groundUnder(map)
  const snowyMap = snowy(map)
  // A trail covering most of the map (Path of Radiance's Hillside Battle) is a floor too: its icon a small badge, not one on every tile.
  const trail = map.grid.reduce((n, row) => n + rowCodes(row).filter((c) => c === 'bl').length, 0) > 0.3 * map.width * map.height
  const visits = visitable(map)
  const lit = map.fog ? torchLight(map, previewing) : null
  const fixed = new Set((map.forced ?? []).flatMap((f) => (f.tile ? [tileKey(f.tile)] : [])))
  // The lord's and the forced units' tiles are starting tiles too, wherever a map's list leaves them out.
  const starts = new Set([...map.starts.map(tileKey), ...(map.corrinStart ? [tileKey(map.corrinStart)] : []), ...fixed])
  // Tile centre in SVG units; a unit walking in from off the map starts its arrow at the edge.
  const centre = ([x, y]: Tile) => {
    const cx = Math.min(Math.max(x, 0.5), map.width + 0.5)
    const cy = Math.min(Math.max(y, 0.5), map.height + 0.5)
    return [GUTTER + (cx - 1) * CELL + CELL / 2, (map.height - cy) * CELL + CELL / 2] as const
  }
  // One marker per tile even when several groups arrive on it; the tile panel lists them all.
  const arrivalMarkers = new Map<string, ShownArrival>()
  for (const a of arrivals) if (!arrivalMarkers.has(tileKey(arrivalTile(a)))) arrivalMarkers.set(tileKey(arrivalTile(a)), a)

  return (
    <svg
      viewBox={`0 0 ${GUTTER + map.width * CELL} ${map.height * CELL + GUTTER}`}
      className="w-full select-none rounded border border-neutral-800 bg-neutral-950"
      role="grid"
      aria-label={`${map.title} map`}
    >
      {tiles.map((t) => {
        const [x, y] = t
        const letter = terrainAt(map, t)
        const X = px(x)
        const Y = py(y)
        // A village's pieces, and an entrance among them, stand in its yard.
        const inYard =
          (letter[0] === 'v' && PIECE.test(letter)) ||
          (VILLAGE_INSIDE.has(letter) && ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => {
            const n: Tile = [x + dx, y + dy]
            const c = n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height ? terrainAt(map, n) : undefined
            return !!c && c[0] === 'v' && PIECE.test(c)
          }))
        const scenery = sceneryHouse(letter, tileKey(t), visits)
        const village = twoTileVillage(map, t)
        // A two-tile village's roof stands on the ground its front does.
        const ground = village === VILLAGE_HOUSE.middleTop ? under.get(tileKey([x, y - 1])) : under.get(tileKey(t))
        const yard = villageYardPiece(map, t)
        // A house with nothing to visit stands in its village's yard; on a map of grassland (Shadow Dragon and the Blade of Light's,
        // Mystery of the Emblem's) on the ground around it, as the game draws it (the user's call), and on a town's floor anywhere.
        const houseGround = scenery && ground && (INDOOR_GROUND.has(ground) || plainOf(map) === 'tv') ? ground : undefined
        const fill = houseGround ? fillOf(map, houseGround) : inYard || scenery ? villageYard(map) : fillOf(map, ground ?? letter)
        const fort = stairFortPart(map, t)
        const outside = (dx: number, dy: number) => {
          const n: Tile = [x + dx, y + dy]
          return n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height && !VILLAGE_INSIDE.has(terrainAt(map, n))
        }
        return (
          <g key={tileKey(t)} onClick={() => onSelect(t)} className="cursor-pointer">
            {letter === 'w8' ? (
              <VillageTile
                X={X}
                Y={Y}
                yard={villageYard(map)}
                sides={(['n', 's', 'w', 'e'] as const).filter((s) => outside(SIDE_STEP[s][0], SIDE_STEP[s][1]))}
              />
            ) : (
              <rect x={X} y={Y} width={CELL} height={CELL} fill={fill} />
            )}
            {WATER_CODES.has(letter) &&
              WAVES.map((d) => (
                <path key={d} d={d} transform={`translate(${X} ${Y})`} fill="none" stroke={shade(fill, 0.3)} strokeWidth={0.55} strokeLinecap="round" />
              ))}
            <GroundDetail
              code={
                map.rooftops?.ground?.includes(tileKey(t)) ? under.get(tileKey(t)) ?? letter
                  : FLOOR_BONUS.has(letter) ? 't1'
                    // An icon's tile has the texture of the ground it stands on (the user: chests on a castle's floor came out flat).
                    : (ground ?? letter) === 'tv' && snowyMap ? 't2'
                      : ground ?? letter
              }
              fill={fill}
              X={X}
              Y={Y}
              x={x}
              y={y}
            />
            {SAND_CODES.has(letter) && (
              // Sand: grains, and a ripple the wind left (the user: a shore read as a flat block).
              <>
                {GRAINS.map(([gx, gy]) => <rect key={`${gx}${gy}`} x={X + gx} y={Y + gy} width={0.6} height={0.6} fill={shade(fill, -0.22)} />)}
                <path d={`M${X + 1 + (variety(x, y) % 2) * 3} ${Y + 4.4 + (variety(x, y) % 3)} q1.5 -1 3 0 t3 0`} fill="none" stroke={shade(fill, -0.18)} strokeWidth={0.4} strokeLinecap="round" />
              </>
            )}
            {!under.has(tileKey(t)) && !village && WALL_PATTERN[letter]?.lines.map(([x1, y1, x2, y2], i) => {
              const { stroke } = WALL_PATTERN[letter]!
              return <line key={`wp${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={typeof stroke === 'number' ? shade(fill, stroke) : stroke} strokeWidth={0.5} />
            })}
            {(letter === 'tb' || letter === 'ts' || letter === 'wo') &&
              [2, 5, 8].map((o) => <line key={o} x1={X + o} x2={X + o} y1={Y} y2={Y + 10} stroke="#6b5033" strokeWidth={0.6} />)}
            {letter === 't8' && (
              // A stone bridge's deck: big slabs in staggered courses, worn a little lighter along their tops.
              <>
                {[0, 3.33, 6.67].map((o, i) => (
                  <g key={o}>
                    <line x1={X} x2={X + 10} y1={Y + o} y2={Y + o} stroke={shade(fill, -0.22)} strokeWidth={0.45} />
                    <line x1={X} x2={X + 10} y1={Y + o + 0.6} y2={Y + o + 0.6} stroke={shade(fill, 0.12)} strokeWidth={0.35} />
                    {(i % 2 ? [2.5, 7.5] : [5]).map((sx) => (
                      <line key={sx} x1={X + sx} x2={X + sx} y1={Y + o} y2={Y + o + 3.33} stroke={shade(fill, -0.22)} strokeWidth={0.45} />
                    ))}
                  </g>
                ))}
              </>
            )}
            {UNDER_SPRITE[letter] && <SpriteG sprite={UNDER_SPRITE[letter]} x={X} y={Y} />}
            {yard && <SpriteG sprite={yard} x={X} y={Y} />}
            {scenery ? (
              <SpriteG sprite={TOWN_HOUSE} x={X} y={Y} />
            ) : fort === 'e' ? (
              // A stair fort's middle: the platform, and the fort's mark small in its corner.
              <>
                <SpriteG sprite={STAIR_FORT_PIECES.e} x={X} y={Y} />
                <SpriteG sprite={FORT} x={X} y={Y} size={5} />
              </>
            ) : (
              spriteOf(map, letter, t) &&
              (BADGE_TERRAIN.has(letter) || (trail && letter === 'bl') ? (
                <SpriteG sprite={spriteOf(map, letter, t)!} x={X} y={Y} size={5} />
              ) : (
                <SpriteG sprite={spriteOf(map, letter, t)!} x={X} y={Y} />
              ))
            )}
            {LORD_BLOCKED.has(letter) && <SpriteG sprite={NO_LORD} x={X} y={Y} size={5} />}
            {map.rooftops?.chimneys.includes(tileKey(t)) && <SpriteG sprite={CHIMNEY} x={X} y={Y} />}
            {map.decor?.[tileKey(t)] && <SpriteG sprite={DECOR_SPRITE[map.decor[tileKey(t)]]} x={X} y={Y} />}
            {map.night && !(letter in (map.fills ?? {})) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0a0d14" opacity={0.5} pointerEvents="none" />}
            {dark.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.6} />}
            {lit &&
              (lit.has(tileKey(t)) ? (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#facc15" opacity={0.14} />
              ) : sight?.has(tileKey(t)) ? null : (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.5} />
              ))}
            {radius.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#ffffff" opacity={0.22} />}
            {starts.has(tileKey(t)) && (
              <g fill={map.corrinStart && sameTile(map.corrinStart, t) ? '#facc15' : fixed.has(tileKey(t)) ? FORCED : '#3b82f6'}>
                <path d={`M${X} ${Y}h3l-3 3z`} />
                <path d={`M${X + 10} ${Y + 10}h-3l3 -3z`} />
              </g>
            )}
          </g>
        )
      })}

      {/* Grid lines, drawn once on top of the terrain. */}
      {Array.from({ length: map.width + 1 }, (_, i) => (
        <line key={`v${i}`} x1={GUTTER + i * CELL} x2={GUTTER + i * CELL} y1={0} y2={map.height * CELL} stroke="#000" strokeOpacity={0.15} strokeWidth={0.3} pointerEvents="none" />
      ))}
      {Array.from({ length: map.height + 1 }, (_, i) => (
        <line key={`h${i}`} x1={GUTTER} x2={GUTTER + map.width * CELL} y1={i * CELL} y2={i * CELL} stroke="#000" strokeOpacity={0.15} strokeWidth={0.3} pointerEvents="none" />
      ))}

      {(map.walls ?? []).map(({ tile: [x, y], side, step }) => {
        const X = px(x)
        const Y = py(y)
        const [x1, y1, x2, y2] =
          side === 'n' ? [X, Y, X + CELL, Y] : side === 's' ? [X, Y + CELL, X + CELL, Y + CELL] : side === 'w' ? [X, Y, X, Y + CELL] : [X + CELL, Y, X + CELL, Y + CELL]
        if (step) return <Railing key={`wall${x},${y}${side}`} x1={x1} y1={y1} x2={x2} y2={y2} />
        return <line key={`wall${x},${y}${side}`} x1={x1} y1={y1} x2={x2} y2={y2} stroke={FENCE} strokeWidth={1.6} strokeLinecap="round" pointerEvents="none" />
      })}
      {railedSides(map).map(({ tile: [x, y], side }) => {
        const X = px(x)
        const Y = py(y)
        const [x1, y1, x2, y2] =
          side === 'n' ? [X, Y, X + CELL, Y] : side === 's' ? [X, Y + CELL, X + CELL, Y + CELL] : side === 'w' ? [X, Y, X, Y + CELL] : [X + CELL, Y, X + CELL, Y + CELL]
        return <Railing key={`rail${x},${y}${side}`} x1={x1} y1={y1} x2={x2} y2={y2} />
      })}

      {map.objectives.flatMap((o) =>
        o.tiles.map((t) =>
          o.type === 'burn' ? (
            <g key={`burn${tileKey(t)}`} pointerEvents="none">
              <rect x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="#f97316" fillOpacity={0.18} stroke={BURN} strokeWidth={1} strokeDasharray="2 1" />
              <SpriteG sprite={SUPPLIES} x={px(t[0])} y={py(t[1])} />
            </g>
          ) : (
            <rect key={`obj${tileKey(t)}`} x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="none" stroke="#38bdf8" strokeWidth={1.2} pointerEvents="none" />
          ),
        ),
      )}

      {map.objects.map((o) => {
        if (o.type === 'hidden') {
          // The dig area, outlined, with a glint in its middle.
          const [l, b, r, t] = o.area
          return (
            <g key={`hid${tileKey(o.tile)}`} pointerEvents="none">
              <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#c2410c" fillOpacity={0.14} stroke="#9a3412" strokeWidth={0.8} strokeDasharray="1.5 1" />
              <SpriteG sprite={BURIED} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
        if (o.type === 'pit') return <SpriteG key={`pit${tileKey(o.tile)}`} sprite={PIT} x={px(o.tile[0])} y={py(o.tile[1])} />
        // A village on ground of its own (Path of Radiance's keep the plain, coast or snow they stand on): its house on top.
        if (o.type === 'village' && !marksBuilding(terrainAt(map, o.tile)))
          return <SpriteG key={`vil${tileKey(o.tile)}`} sprite={doorMat(map, o.tile) ? DOOR_MAT : HOUSE} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'event') return <SpriteG key={`evt${tileKey(o.tile)}`} sprite={EVENT_TILE} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'trap') return <SpriteG key={`trap${tileKey(o.tile)}`} sprite={TRAP_SPRITE[o.kind]} x={px(o.tile[0])} y={py(o.tile[1])} />
        // A ballista a bow user stands on (the GBA games'): the machine is on ordinary ground, so it's drawn here.
        if (o.type === 'ballista' && o.mounted) return <SpriteG key={`bal${tileKey(o.tile)}`} sprite={BALLISTA} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'shiny') return <SpriteG key={`shiny${tileKey(o.tile)}`} sprite={SHINY} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'shop') {
          const sprite = SHOP_SPRITE[o.kind]
          if (!sprite || TERRAIN_SPRITE[terrainAt(map, o.tile)] === sprite) return null
          return <SpriteG key={`shop${tileKey(o.tile)}`} sprite={sprite} x={px(o.tile[0])} y={py(o.tile[1])} />
        }
        if (o.type === 'fire') {
          // The house, outlined, with a flame on its corner.
          const [l, b, r, t] = o.area
          return (
            <g key={`fire${tileKey(o.tile)}`} pointerEvents="none">
              <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#dc2626" fillOpacity={0.12} stroke="#dc2626" strokeWidth={0.8} strokeDasharray="1.5 1" />
              <SpriteG sprite={FLAME} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
        if (o.type !== 'pot') return null
        const X = px(o.tile[0])
        const Y = py(o.tile[1])
        return (
          <SpriteG
            key={`pot${tileKey(o.tile)}`}
            sprite={o.pot === 'medicine' ? VASE_MEDICINE : VASE_POISON}
            x={X}
            y={Y}
            opacity={potsBroken ? 0.2 : 1}
          />
        )
      })}

      {map.changes.map((c) => {
        if (c.wide) return null
        const [x, y] = resolveTile(c.tile, difficulty)
        if (c.trigger === 'boulder') {
          // The boulder, and while previewed, the path it rolls down.
          const path = c.path ?? []
          const at = (t: Tile) => centre(t)
          return (
            <g key={c.id} pointerEvents="none">
              {previewing.has(c.id) && path.length > 1 && (
                <polyline
                  points={path.map((t) => at(t).join(',')).join(' ')}
                  fill="none"
                  stroke="#f5f5f4"
                  strokeWidth={1.1}
                  strokeDasharray="2 1"
                  markerEnd="url(#arrival-head)"
                />
              )}
            </g>
          )
        }
        if (c.trigger === 'torch') {
          // Dim until it's previewed as lit.
          return <SpriteG key={c.id} sprite={TORCH} x={px(x)} y={py(y)} opacity={torchLit(c, previewing) ? 1 : 0.55} />
        }
        if (c.trigger === 'breakable' || c.trigger === 'event') {
          // Once previewed as broken, the crack (or the snag) goes: the tile is open ground then. A chest or a door that sets a change
          // off is its own mark (the user: chests read as breakable), and a doorway the chapter shuts is an open door.
          if (previewing.has(c.id) || (c.trigger === 'event' && ownMark(map, [x, y]))) return null
          return <SpriteG key={c.id} sprite={c.snag ? SNAG : shutsDoor(c, [x, y]) ? OPEN_DOOR : CRACK} x={px(x)} y={py(y)} />
        }
        if (c.trigger === 'eruption') {
          return previewing.has(c.id) ? null : <SpriteG key={c.id} sprite={FLAME} x={px(x)} y={py(y)} />
        }
        if (c.trigger === 'trap') {
          // A hidden pit (Path of Radiance Ch.23): its lid until previewed as sprung, then the hole it leaves.
          return previewing.has(c.id) ? null : <SpriteG key={c.id} sprite={PIT} x={px(x)} y={py(y)} />
        }
        return <SpriteG key={c.id} sprite={DRAGON_VEIN} x={px(x)} y={py(y)} className="animate-pulse" />
      })}

      {/* Coloured rooms, swapped while a vein that swaps them is previewed. */}
      {(map.rooms ?? []).flatMap((set, si) =>
        set.rects.map(([l, b, r, t]) => {
          const swapped = map.changes.some((c) => c.swapsRooms && previewing.has(c.id))
          const shown = swapped ? (set.color === 'red' ? 'blue' : 'red') : set.color
          const color = ROOM[shown]
          return (
            <rect
              key={`room${si}:${l},${b}`}
              x={px(l) + 0.5}
              y={py(t) + 0.5}
              width={(r - l + 1) * CELL - 1}
              height={(t - b + 1) * CELL - 1}
              fill={color}
              fillOpacity={ROOM_TINT[shown]}
              stroke={color}
              strokeWidth={0.6}
              pointerEvents="none"
            />
          )
        }),
      )}

      {(map.foeGroups ?? []).flatMap((g, gi) =>
        g.tiles.map((t) => (
          <rect
            key={`fg${gi}:${tileKey(t)}`}
            x={px(t[0]) + 0.5}
            y={py(t[1]) + 0.5}
            width={CELL - 1}
            height={CELL - 1}
            fill={FOE_GROUP[gi]}
            fillOpacity={0.12}
            stroke={FOE_GROUP[gi]}
            strokeWidth={0.8}
            strokeDasharray="1.6 0.9"
            pointerEvents="none"
          />
        )),
      )}

      {unseen &&
        tiles
          .filter((t) => unseen.has(tileKey(t)))
          .map((t) => <rect key={`unseen${tileKey(t)}`} x={px(t[0])} y={py(t[1])} width={CELL} height={CELL} fill="#050507" pointerEvents="none" />)}

      {/* Keyed by position in the list too: two units can share a tile (one per difficulty), and a repeated key
          leaves a stray sprite behind when the map changes. */}
      {/* A unit covering several tiles (Three Houses' monsters) has its icon stretched over its square, the badges at its corners. */}
      {map.units.map((u, i) => {
        const [x, y, span] = [px(u.tile[0]), py(u.tile[1]), CELL * (u.size ?? 1)]
        return (
          <g key={`${i}:${tileKey(u.tile)}`}>
            <SpriteG sprite={unitSprite(u)} x={x} y={y} size={span} />
            {u.drops?.length ? <SpriteG sprite={DROP_BADGE} x={x + span - 4.6} y={y - 0.4} size={5} /> : null}
            {u.looter && <SpriteG sprite={TORCH} x={x - 0.4} y={y + span - 4.6} size={5} />}
            {u.capturable && <SpriteG sprite={CAPTURE_BADGE} x={x + span - 4.6} y={y + span - 4.6} size={5} />}
            {u.steal?.length ? <SpriteG sprite={STEAL_BADGE} x={x - 0.4} y={y - 0.4} size={5} /> : null}
            {u.bars ? <HealthPips bars={u.bars} x={x} y={y} span={span} /> : null}
          </g>
        )
      })}

      {/* Each foe group's number in its tiles' corner, over the unit markers. */}
      {(map.foeGroups ?? []).flatMap((g, gi) =>
        g.tiles.map((t) => (
          <text
            key={`fgn${gi}:${tileKey(t)}`}
            x={px(t[0]) + 9.3}
            y={py(t[1]) + 3.4}
            textAnchor="end"
            fontSize={3.2}
            fontWeight="bold"
            fill={FOE_GROUP[gi]}
            stroke="#0a0a0a"
            strokeWidth={0.6}
            paintOrder="stroke"
            pointerEvents="none"
          >
            {gi + 1}
          </text>
        )),
      )}

      {/* Boulders on top of units: a rock-pusher often stands on one (Ch.25), so it shows as a corner badge then. */}
      {map.changes
        .filter((c) => c.trigger === 'boulder')
        .map((c) => {
          const [x, y] = resolveTile(c.tile, difficulty)
          const occupied = map.units.some((u) => covers(u, [x, y]))
          return occupied ? (
            <SpriteG key={`rock${c.id}`} sprite={BOULDER} x={px(x) - 0.4} y={py(y) + 5.4} size={5} />
          ) : (
            <SpriteG key={`rock${c.id}`} sprite={BOULDER} x={px(x)} y={py(y)} />
          )
        })}

      {/* -1 for both ends of an axis is all of it: a whole row or column; an area that's -1 every way is anywhere, not drawn. */}
      {triggers.filter(({ rect }) => !(rect[0] === -1 && rect[1] === -1)).map(({ who, rect, step }) => {
        const [l, r] = rect[0] === -1 ? [1, map.width] : [rect[0], rect[2]]
        const [b, t] = rect[1] === -1 ? [1, map.height] : [rect[1], rect[3]]
        const colour = who === 'enemy' ? '#ef4444' : '#f0883e'
        return (
          <g key={`trig${who}${l},${b},${r},${t}${step ?? ''}`} pointerEvents="none">
            <rect
              x={px(l) + 0.5}
              y={py(t) + 0.5}
              width={(r - l + 1) * CELL - 1}
              height={(t - b + 1) * CELL - 1}
              fill={colour}
              fillOpacity={0.08}
              stroke={colour}
              strokeWidth={0.7}
              strokeDasharray="2 1.2"
            />
            {/* A group set off in steps (one area, then another): each area carries its step's number, as its time names it. */}
            {step !== undefined && (
              <text x={px(l) + 1.6} y={py(t) + 6.4} fontSize={5.5} fontWeight="bold" fill={colour} stroke="#0a0a0a" strokeWidth={0.6} paintOrder="stroke">
                {step}
              </text>
            )}
          </g>
        )
      })}
      {map.changes
        .filter((c) => c.zone)
        .map((c) => {
          const [l, b, r, t] = c.zone!
          return (
            <rect
              key={`zone${c.id}`}
              x={px(l) + 0.5}
              y={py(t) + 0.5}
              width={(r - l + 1) * CELL - 1}
              height={(t - b + 1) * CELL - 1}
              fill={TRAP_ZONE}
              fillOpacity={previewing.has(c.id) ? 0 : 0.1}
              stroke={TRAP_ZONE}
              strokeWidth={0.7}
              strokeDasharray="1.2 1.2"
              pointerEvents="none"
            />
          )
        })}
      <defs>
        <marker id="arrival-head" viewBox="0 0 6 6" refX="5" refY="3" markerWidth="3" markerHeight="3" orient="auto">
          <path d="M0 0L6 3L0 6z" fill="context-stroke" />
        </marker>
      </defs>
      {arrivals.map((a, i) => {
        const from = arrivalFrom(a)
        const to = arrivalTile(a)
        if (!from || sameTile(from, to)) return null
        const [x1, y1] = centre(from)
        const [x2, y2] = centre(to)
        return (
          <line
            key={`arrow${i}`}
            x1={x1}
            y1={y1}
            x2={x2}
            y2={y2}
            stroke={a.kind === 'joiner' ? '#60a5fa' : '#f0883e'}
            strokeWidth={0.9}
            strokeDasharray="1.6 1"
            markerEnd="url(#arrival-head)"
            pointerEvents="none"
          />
        )
      })}
      {[...arrivalMarkers.values()].map((a) => {
        const [x, y] = arrivalTile(a)
        const span = CELL * (a.kind === 'reinforcement' ? (a.unit.size ?? 1) : 1)
        return (
          <g key={`arr${x},${y}`} pointerEvents="none">
            <SpriteG sprite={a.kind === 'joiner' ? joinerSprite(a.joiner) : reinforcementSprite(a.unit)} x={px(x)} y={py(y)} size={span} />
            {a.kind === 'reinforcement' && a.unit.drops?.length ? <SpriteG sprite={DROP_BADGE} x={px(x) + span - 4.6} y={py(y) - 0.4} size={5} /> : null}
            {(a.kind === 'reinforcement' ? a.unit.looter : a.joiner.looter) ? <SpriteG sprite={TORCH} x={px(x) - 0.4} y={py(y) + span - 4.6} size={5} /> : null}
            {a.kind === 'reinforcement' && a.unit.capturable ? <SpriteG sprite={CAPTURE_BADGE} x={px(x) + span - 4.6} y={py(y) + span - 4.6} size={5} /> : null}
            {a.kind === 'reinforcement' && a.unit.steal?.length ? <SpriteG sprite={STEAL_BADGE} x={px(x) - 0.4} y={py(y) - 0.4} size={5} /> : null}
            {a.kind === 'reinforcement' && a.unit.bars ? <HealthPips bars={a.unit.bars} x={px(x)} y={py(y)} span={span} /> : null}
          </g>
        )
      })}

      {[...map.units, ...arrivals.map((a) => (a.kind === 'reinforcement' ? a.unit : a.joiner))]
        .filter((u) => u.goesTo?.length && selected && covers(u, selected))
        .map((u, i) => {
          const goal = u.goesTo!
          const near = goal.reduce((a, b) => (distance(u.tile, b) < distance(u.tile, a) ? b : a))
          const [x1, y1] = centre(u.tile)
          const [x2, y2] = centre(near)
          return (
            <g key={`goes${i}`} pointerEvents="none">
              {goal.map((t) => (
                <rect key={tileKey(t)} x={px(t[0]) + 0.4} y={py(t[1]) + 0.4} width={CELL - 0.8} height={CELL - 0.8} fill={GOES_TO} fillOpacity={0.3} stroke={GOES_TO} strokeWidth={1.2} />
              ))}
              <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={GOES_TO} strokeWidth={0.9} strokeDasharray="1.6 1" markerEnd="url(#arrival-head)" />
            </g>
          )
        })}

      {/* A staircase's other end, outlined while one end is selected (the Rainbow Sage's platforms). */}
      {selected &&
        (map.links ?? [])
          .filter(([a, b]) => sameTile(a, selected) || sameTile(b, selected))
          .map(([a, b]) => (sameTile(a, selected) ? b : a))
          .map((t) => (
            <rect
              key={`link${tileKey(t)}`}
              x={px(t[0]) + 0.5}
              y={py(t[1]) + 0.5}
              width={CELL - 1}
              height={CELL - 1}
              fill="none"
              stroke="#67e8f9"
              strokeWidth={0.9}
              strokeDasharray="1.6 0.9"
              pointerEvents="none"
            />
          ))}

      {selected && (
        <rect x={px(selected[0]) + 0.3} y={py(selected[1]) + 0.3} width={CELL - 0.6} height={CELL - 0.6} fill="none" stroke="#fff" strokeWidth={0.8} pointerEvents="none" />
      )}

      {Array.from({ length: map.width }, (_, i) => (
        <text key={`x${i}`} x={GUTTER + i * CELL + 5} y={map.height * CELL + 5} textAnchor="middle" fontSize={3.4} fill="#737373">
          {i + 1}
        </text>
      ))}
      {Array.from({ length: map.height }, (_, i) => (
        <text key={`y${i}`} x={GUTTER - 1.2} y={i * CELL + 6.2} textAnchor="end" fontSize={3.4} fill="#737373">
          {map.height - i}
        </text>
      ))}
    </svg>
  )
}

/** A legend's tile: its colour, its texture and its icon, as the map draws it. */
function TileSwatch({ code, fill, sprite }: { code: TerrainCode; fill: string; sprite?: Sprite }) {
  const pattern = WALL_PATTERN[code]
  return (
    <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm" aria-hidden>
      <rect width={10} height={10} fill={fill} />
      {WATER_CODES.has(code) && WAVES.map((d) => <path key={d} d={d} fill="none" stroke={shade(fill, 0.3)} strokeWidth={0.55} strokeLinecap="round" />)}
      <GroundDetail code={FLOOR_BONUS.has(code) ? 't1' : code} fill={fill} X={0} Y={0} x={1} y={1} />
      {SAND_CODES.has(code) && GRAINS.map(([gx, gy]) => <rect key={`${gx}${gy}`} x={gx} y={gy} width={0.6} height={0.6} fill={shade(fill, -0.22)} />)}
      {pattern?.lines.map(([x1, y1, x2, y2], i) => (
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={typeof pattern.stroke === 'number' ? shade(fill, pattern.stroke) : pattern.stroke} strokeWidth={0.5} />
      ))}
      {(code === 'tb' || code === 'ts' || code === 'wo') && [2, 5, 8].map((o) => <line key={o} x1={o} x2={o} y1={0} y2={10} stroke="#6b5033" strokeWidth={0.6} />)}
      {sprite && <SpriteG sprite={sprite} x={0} y={0} />}
    </svg>
  )
}
/** A village's pieces keep the legend's plain icon on the yard (their sprites are drawn there already). */
const yardCode = (code: TerrainCode) => code === 'w8' || (code[0] === 'v' && PIECE.test(code))

function Legend({
  map,
  unseen,
  hidesFoes,
  arrivals,
  triggers,
  takeBy,
}: {
  map: ChapterMap
  /** Tiles Thracia's fog keeps black: their terrain isn't listed. */
  unseen?: Set<string>
  /** The spoiler block leaves a fog map's foes off. */
  hidesFoes?: boolean
  arrivals: ShownArrival[]
  triggers: NonNullable<Arrival['areas']>
  takeBy: MapSet['takeBy']
}) {
  // Only what this map actually has, so small maps get a short legend (and only what can be seen, under Thracia's fog).
  const visible = unseen
    ? map.grid.flatMap((row, r) => rowCodes(row).filter((_, c) => !unseen.has(tileKey([c + 1, map.height - r]))))
    : map.grid.flatMap(rowCodes)
  const changed = unseen ? [] : map.changes.flatMap((c) => (c.patch ?? []).map((p) => p.becomes))
  const codes = new Set([...visible, ...changed])
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  const items: { label: string; sprite?: Sprite; swatch?: string; outline?: boolean; corners?: string; code?: TerrainCode }[] = []
  if (pots.some((p) => p.pot === 'medicine')) items.push({ label: 'Medicine pot', sprite: VASE_MEDICINE })
  if (pots.some((p) => p.pot === 'poison')) items.push({ label: 'Poison pot', sprite: VASE_POISON })
  if (map.changes.some((c) => c.trigger === 'dragonVein')) items.push({ label: 'Dragon Vein', sprite: DRAGON_VEIN })
  if (map.changes.some((c) => c.trigger === 'breakable' && !c.snag)) items.push({ label: 'Breakable', sprite: CRACK })
  if (map.changes.some((c) => c.snag)) items.push({ label: 'Snag (breakable)', sprite: SNAG })
  const events = map.changes.filter((c) => c.trigger === 'event' && !ownMark(map, changeTile(c)))
  if (events.some((c) => shutsDoor(c, changeTile(c)))) items.push({ label: 'Doorway the chapter shuts (tap it)', sprite: OPEN_DOOR })
  if (events.some((c) => !shutsDoor(c, changeTile(c)))) items.push({ label: 'Changes during the chapter (tap it)', sprite: CRACK })
  if (map.changes.some((c) => c.trigger === 'eruption')) items.push({ label: 'Lava floor that turns to hazard (tap it)', sprite: FLAME })
  if (map.changes.some((c) => c.trigger === 'boulder')) items.push({ label: 'Boulder (tap to see its path)', sprite: BOULDER })
  if (map.walls?.some((w) => !w.all && !w.step)) items.push({ label: "Blocked side: ground units can't cross (fliers can)", swatch: FENCE })
  if (map.walls?.some((w) => w.step)) items.push({ label: "Step between levels: ground units can't cross (fliers can)", swatch: RAIL })
  if (map.walls?.some((w) => w.all)) items.push({ label: "Blocked side: no unit can cross", swatch: FENCE })
  if (railedSides(map).length) items.push({ label: 'Railing round a building or ground no unit can enter, fliers included', swatch: RAIL })
  const ownGround = map.objects.filter((o) => o.type === 'village' && !marksBuilding(terrainAt(map, o.tile)))
  if (ownGround.some((o) => !doorMat(map, o.tile))) items.push({ label: 'Village', sprite: HOUSE })
  if (ownGround.some((o) => doorMat(map, o.tile)) || codes.has('oc') && map.grid.some((row, i) =>
    rowCodes(row).some((c, x) => c === 'oc' && doorMat(map, [x + 1, map.height - i]))))
    items.push({ label: 'House to visit (at its door mat)', sprite: DOOR_MAT })
  if (map.changes.some((c) => c.trigger === 'trap' && !c.zone)) items.push({ label: 'Hidden pit (tap it)', sprite: PIT })
  // An area to search is a dig area; an item hidden on one tile (Awakening's Paralogue 14) is only a hidden item.
  const hidden = map.objects.filter((o) => o.type === 'hidden')
  if (hidden.length)
    items.push({
      label: hidden.some((o) => o.area[0] !== o.area[2] || o.area[1] !== o.area[3]) ? 'Hidden item (dig area)' : 'Hidden item',
      sprite: BURIED,
    })
  if (map.objects.some((o) => o.type === 'event')) items.push({ label: 'Event tile', sprite: EVENT_TILE })
  if (map.objects.some((o) => o.type === 'shiny')) items.push({ label: 'Shiny spot', sprite: SHINY })
  if (map.objects.some((o) => o.type === 'pit')) items.push({ label: 'Pit trap', sprite: PIT })
  for (const kind of ['fire', 'gas', 'arrow'] as const)
    if (map.objects.some((o) => o.type === 'trap' && o.kind === kind)) items.push({ label: `${TRAP_LABEL[kind]} (tap it)`, sprite: TRAP_SPRITE[kind] })
  if (map.objects.some((o) => o.type === 'ballista' && o.mounted)) items.push({ label: 'Ballista: an Archer or Sniper on it fires it', sprite: BALLISTA })
  if (map.objects.some((o) => o.type === 'shop' && o.kind === 'Secret shop' && terrainAt(map, o.tile) !== 'op'))
    items.push({ label: 'Secret shop (needs a membership card)', sprite: SECRET_SHOP })
  if (map.objects.some((o) => o.type === 'fire')) items.push({ label: 'House the arsonists can set alight', sprite: FLAME })
  if (map.changes.some((c) => c.trigger === 'torch')) items.push({ label: 'Torch (tap it to light it)', sprite: TORCH })
  if (map.fog && !unseen) items.push({ label: 'Fog (hidden until seen)', swatch: '#3b3542' })
  if (unseen) items.push({ label: "Unseen: the fog hides the land too, beyond your units' sight", swatch: '#050507' })
  if (hidesFoes) items.push({ label: "Foes your army can't see from its starting tiles are hidden", swatch: '#3b3542' })
  const unitKinds = new Map<string, Sprite>()
  for (const u of map.units) {
    const label =
      u.type === 'enemy'
        ? u.paired ? 'Paired enemies' : 'Enemy'
        : u.type === 'ally'
          ? u.neutral
            ? u.generic ? 'Neutral unit (yellow)' : 'Named neutral unit (yellow)'
            : u.yellow ? (u.generic ? 'Partner unit (yellow)' : 'Named partner unit (yellow)') : u.generic ? 'Ally' : 'Named ally'
          : UNIT_NAME[u.type]
    unitKinds.set(label, unitSprite(u))
  }
  for (const [label, sprite] of unitKinds) items.push({ label, sprite })
  if (map.units.some((u) => u.drops?.length) || arrivals.some((a) => a.kind === 'reinforcement' && a.unit.drops?.length))
    items.push({ label: 'Drops an item', sprite: DROP_BADGE })
  const looters = [...map.units, ...arrivals.map((a) => (a.kind === 'reinforcement' ? a.unit : a.joiner))].map((u) => u.looter)
  // Chests and villages in most games; Three Houses' Holy Tomb looters take the Crest Stones from its walls.
  if (looters.includes(true)) items.push({ label: 'Looter: goes for villages, chests or other treasure', sprite: TORCH })
  if (looters.includes('fire')) items.push({ label: 'Arsonist: makes for houses to set them alight', sprite: TORCH })
  if ([...map.units, ...arrivals.flatMap((a) => (a.kind === 'reinforcement' ? [a.unit] : []))].some((u) => u.bars))
    items.push({ label: 'Health bars (a pip each)', sprite: HEALTH_PIPS })
  if (map.units.some((u) => u.capturable) || arrivals.some((a) => a.kind === 'reinforcement' && a.unit.capturable))
    items.push({ label: 'Can be captured', sprite: CAPTURE_BADGE })
  if (map.units.some((u) => u.steal?.length) || arrivals.some((a) => a.kind === 'reinforcement' && a.unit.steal?.length))
    items.push({ label: takeBy === 'capture' ? 'Holds something rare: capture it to take it' : "Holds something rare to steal (it doesn't drop it)", sprite: STEAL_BADGE })
  if (arrivals.some((a) => a.kind === 'reinforcement' && a.unit.type !== 'boss' && a.unit.type !== 'named'))
    items.push({ label: 'Reinforcement', sprite: REINFORCEMENT })
  if (arrivals.some((a) => a.kind === 'reinforcement' && a.unit.type === 'named')) items.push({ label: 'Named foe arriving', sprite: NAMED_REINFORCEMENT })
  if (arrivals.some((a) => a.kind === 'reinforcement' && a.unit.type === 'boss')) items.push({ label: 'Boss arriving', sprite: BOSS_REINFORCEMENT })
  if (arrivals.some((a) => a.kind === 'joiner' && !a.joiner.ally)) items.push({ label: 'Joins your army', sprite: JOINER })
  const allies = arrivals.flatMap((a) => (a.kind === 'joiner' && a.joiner.ally ? [a.joiner] : []))
  if (allies.some((j) => !j.yellow && !j.neutral && !j.generic)) items.push({ label: 'Named green unit arrives', sprite: ALLY })
  if (allies.some((j) => !j.yellow && !j.neutral && j.generic)) items.push({ label: 'Green unit arrives', sprite: COMMON_ALLY })
  if (allies.some((j) => j.yellow && !j.generic)) items.push({ label: 'Named partner unit arrives (yellow)', sprite: PARTNER })
  if (allies.some((j) => j.yellow && j.generic)) items.push({ label: 'Partner unit arrives (yellow)', sprite: COMMON_PARTNER })
  if (allies.some((j) => j.neutral && !j.generic)) items.push({ label: 'Named neutral unit arrives (yellow)', sprite: PARTNER })
  if (allies.some((j) => j.neutral && j.generic)) items.push({ label: 'Neutral unit arrives (yellow)', sprite: COMMON_PARTNER })
  if (triggers.length) items.push({ label: 'Area that brings a group in', swatch: '#f0883e', outline: true })
  for (const set of map.rooms ?? []) items.push({ label: `${set.color === 'red' ? 'Red' : 'Blue'} room: ${set.effect}`, swatch: ROOM[set.color] })
  if (map.changes.some((c) => c.zone)) items.push({ label: 'Trap: one of your units stopping inside springs it (tap it)', swatch: TRAP_ZONE, outline: true })
  if (map.objectives.some((o) => o.type !== 'burn')) items.push({ label: 'Objective', swatch: '#38bdf8', outline: true })
  if (map.objectives.some((o) => o.type === 'burn')) items.push({ label: 'Supplies to burn (objective)', sprite: SUPPLIES })
  if ([...map.units, ...arrivals.map((a) => (a.kind === 'reinforcement' ? a.unit : a.joiner))].some((u) => u.goesTo))
    items.push({ label: 'Where the tapped unit is headed', swatch: GOES_TO, outline: true })
  for (const [gi, g] of (map.foeGroups ?? []).entries()) items.push({ label: `${g.label}'s tiles`, swatch: FOE_GROUP[gi], outline: true })
  if (map.starts.length) items.push({ label: 'Starting tile', corners: '#3b82f6' })
  if (map.corrinStart) items.push({ label: "Lord's start", corners: '#facc15' })
  if (map.forced?.some((f) => f.tile)) items.push({ label: 'Forced unit (fixed tile)', corners: FORCED })
  // Kinds of tile the game gives one name (Mystery of the Emblem's castle gate and its flanks, both "Castle") are labelled by what
  // each is, so the legend keeps them apart.
  // A building's pieces are one line: the building's.
  const shown = [...codes].filter((l) => l !== 'ta' && !(family(l) && [...codes].some((o) => family(o) === family(l) && o < l)))
  const kinds = new Map<string, Set<TerrainCode>>()
  for (const l of shown) kinds.set(terrainInfo(map, l).name, (kinds.get(terrainInfo(map, l).name) ?? new Set()).add(l))
  // Houses with nothing to visit are the village's scenery, a line of their own; the house line is for those with a visit.
  const visits = visitable(map)
  const houses = map.grid.flatMap((row, i) =>
    rowCodes(row).flatMap((c, x) => (c === 'ot' ? [tileKey([x + 1, map.height - i])] : [])),
  )
  for (const l of shown) {
    const name = terrainInfo(map, l).name
    const label = kinds.get(name)!.size > 1 && !family(l) ? TERRAIN_CODES[l] : name
    if (l === 'ot' && houses.some((k) => !visits.has(k)))
      items.push({ label: `${name}: nothing to visit (units stand in it)`, sprite: TOWN_HOUSE, swatch: villageYard(map) })
    if (l === 'ot' && !houses.some((k) => visits.has(k))) continue
    // Villages whose every visit is a door mat are the door mat's line.
    if (l === 'oc' && map.grid.every((row, i) => rowCodes(row).every((c, x) => c !== 'oc' || doorMat(map, [x + 1, map.height - i])))) continue
    // Odds and ends drawn as what the game's models put there: a line for each kind.
    if (l === 'o4') {
      const tiles = map.grid.flatMap((row, i) => rowCodes(row).flatMap((c, x): Tile[] => (c === 'o4' ? [[x + 1, map.height - i]] : [])))
      const kinds = new Set(tiles.map((t) => (spriteOf(map, 'o4', t) === CANDLESTICK ? 'candle' : map.props?.[tileKey(t)] ?? 'other')))
      const LABEL: Record<string, string> = {
        candle: 'lights', box: 'crates', barrel: 'barrels', cart: 'a cart', flowerpot: 'flower pots', statue: 'statues',
        pillar: 'small pillars', sandbags: 'sandbags', gold: 'gold',
      }
      for (const k of kinds.keys()) {
        if (k === 'other' || k === 'roof') continue
        const sprite = k === 'candle' ? CANDLESTICK : k === 'barrel' ? BARREL : PROP_SPRITES[k as keyof typeof PROP_SPRITES]
        items.push({ label: `${name} (${LABEL[k]})`, sprite, swatch: fillOf(map, l) })
      }
      if (!kinds.has('other')) continue
    }
    const yard = l === 'w8' || (PIECE.test(l) && l[0] === 'v')
    items.push({ label, sprite: spriteOf(map, l) ?? (LORD_BLOCKED.has(l) ? NO_LORD : undefined), swatch: yard ? villageYard(map) : fillOf(map, l), code: l })
  }
  const unique = items.filter((it, i) => items.findIndex((o) => o.label === it.label) === i)
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-neutral-400">
      {unique.map((it) => (
        <span key={it.label} className="flex items-center gap-1">
          {it.code && !yardCode(it.code) ? (
            <TileSwatch code={it.code} fill={it.swatch!} sprite={it.sprite} />
          ) : it.sprite ? (
            <PixelIcon sprite={it.sprite} size={16} />
          ) : it.corners ? (
            // The same corner marks the map draws on a starting tile.
            <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm bg-[#b89a6a]" aria-hidden>
              <g fill={it.corners}>
                <path d="M0 0h3l-3 3z" />
                <path d="M10 10h-3l3 -3z" />
              </g>
            </svg>
          ) : (
            <span
              className="inline-block h-3 w-3 rounded-sm"
              style={it.outline ? { border: `2px solid ${it.swatch}` } : { background: it.swatch }}
            />
          )}
          {it.label}
        </span>
      ))}
    </div>
  )
}

/** Who the game places on a unit's tile instead, and when (the map's stand-in toggle swaps them in): "If Lethe has died earlier, Kezhda
 * stands here instead", "If you recruited Felix into your house before this battle, a Mercenary stands here instead". */
function StandInLine({ standIn, note }: { standIn: StandIn; note?: string }) {
  // A note that already says it (Radiant Dawn's: 'If Lethe has died earlier, Kezhda (Lv 17 Cat) stands here instead') isn't repeated.
  if (note?.includes(standIn.when)) return null
  const common = standIn.generic || standIn.type === 'enemy'
  const who = common ? `${/^[AEIOU]/.test(standIn.name) ? 'an' : 'a'} ${standIn.name}` : standIn.name
  return (
    <p className="text-amber-200">
      If {standIn.when}, {who} stands here instead
      {standIn.note ? <span className="text-neutral-400"> ({standIn.note})</span> : null}.
    </p>
  )
}

function TileInfo({
  set,
  map,
  unseen,
  sight,
  difficulty,
  tile,
  closed,
  potsBroken,
  previewing,
  arrivals,
  onTogglePreview,
  onPreviewGroup,
  onReset,
  digging,
  dugCount,
  onToggleDig,
}: {
  set: MapSet
  map: ChapterMap
  /** Tiles Thracia's fog keeps black: nothing about them is shown. */
  unseen?: Set<string>
  /** What your army sees on a map fogged at the start (`inTheFog`). */
  sight?: Set<string>
  difficulty: Difficulty
  tile: Tile | null
  /** The closed rooms' tiles (closedRooms): what's in them isn't shown. */
  closed: Set<string>
  potsBroken: boolean
  previewing: Set<string>
  arrivals: ShownArrival[]
  onTogglePreview: (id: string) => void
  /** Previews every change in a group at once, or stops them all. */
  onPreviewGroup: (ids: string[], on: boolean) => void
  onReset: () => void
  digging: boolean
  dugCount: number
  onToggleDig: () => void
}) {
  if (!tile) {
    return (
      <section className="rounded border border-neutral-800 p-4 text-sm text-neutral-500">
        Tap a tile to see what's on it.{map.objects.some((o) => o.type === 'pot') && ' Tapping a pot shades every tile its effect reaches.'}
      </section>
    )
  }

  if (unseen?.has(tileKey(tile))) {
    return (
      <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm">
        <h3 className="font-semibold text-neutral-100">
          Tile ({tile[0]}, {tile[1]})
        </h3>
        <p className="text-neutral-400">In the fog: nothing here can be seen until one of your units comes close enough.</p>
      </section>
    )
  }
  const letter = terrainAt(map, tile)
  const terrain = terrainInfo(map, letter)
  const units = map.units.filter((u) => covers(u, tile))
  const objectives = map.objectives.filter((o) => o.tiles.some((t) => sameTile(t, tile)))
  const objects = objectsAt(map, tile)
  const pot = objects.find((o) => o.type === 'pot') as Pot | undefined
  const chest = objects.find((o) => o.type === 'chest')
  const village = objects.find((o) => o.type === 'village')
  const castle = objects.find((o) => o.type === 'castle')
  const shop = objects.find((o) => o.type === 'shop')
  const hidden = objects.filter((o) => o.type === 'hidden')
  // A ballista shows on its firing tile and on the machine beside it.
  const ballista = map.objects.find((o) => o.type === 'ballista' && (sameTile(o.tile, tile) || sameTile(o.machine, tile)))
  const pit = objects.find((o) => o.type === 'pit')
  const eventTile = objects.find((o) => o.type === 'event')
  const shiny = objects.find((o) => o.type === 'shiny')
  const fire = objects.find((o) => o.type === 'fire')
  const trap = objects.find((o) => o.type === 'trap')
  const inFog = map.fog && !torchLight(map, previewing).has(tileKey(tile)) && !sight?.has(tileKey(tile))
  const inZone = (z: [number, number, number, number]) => tile[0] >= z[0] && tile[0] <= z[2] && tile[1] >= z[1] && tile[1] <= z[3]
  const changes = map.changes.filter((c) =>
    c.wide
      ? (c.patch ?? []).some((p) => sameTile(p.tile, tile)) || (c.zone !== undefined && inZone(c.zone))
      : sameTile(resolveTile(c.tile, difficulty), tile),
  )
  const fixedHere = map.forced?.find((f) => f.tile && sameTile(f.tile, tile))
  const isStart = map.starts.some((t) => sameTile(t, tile)) || (!!map.corrinStart && sameTile(map.corrinStart, tile)) || !!fixedHere
  const here = arrivals.filter((a) => (a.kind === 'reinforcement' ? covers(a.unit, tile) : sameTile(arrivalTile(a), tile)))

  return (
    <section className="flex flex-col gap-3 rounded border border-neutral-800 p-4 text-sm">
      <h3 className="font-semibold text-neutral-100">
        Tile ({tile[0]}, {tile[1]})
      </h3>

      {units.map((u, i) => (
        <div key={`${u.name}-${i}`}>
          <p className={u.type === 'ally' ? (u.yellow || u.neutral ? 'text-yellow-300' : 'text-green-300') : 'text-red-300'}>
            <PixelIcon sprite={unitSprite(u)} /> {u.yellow ? 'Partner unit' : u.neutral ? 'Neutral' : UNIT_NAME[u.type]}:{' '}
            <span className="font-medium">{u.name}</span>
            {u.paired && !u.partner && u.type === 'enemy' && ' (two, paired up)'}
          </p>
          {u.partner && <p className="text-neutral-300">Paired up with: {u.partner}</p>}
          {u.carries?.length ? <p className="text-neutral-300">Carries {[...new Set(u.carries)].join(', ')}</p> : null}
          {u.talk && <p className="text-sky-300">{u.talk}</p>}
          {u.drops?.map((d) => (
            <p key={d} className="text-amber-300">
              <PixelIcon sprite={DROP_BADGE} /> Drops {d}
            </p>
          ))}
          {u.capturable && (
            <p className="text-neutral-300">
              <PixelIcon sprite={CAPTURE_BADGE} /> Can be captured
            </p>
          )}
          {u.steal?.length ? (
            <p className="text-fuchsia-300">
              <PixelIcon sprite={STEAL_BADGE} /> {set.takeBy === 'capture' ? 'Capture to take' : 'Steal'}: {u.steal.join(', ')}
            </p>
          ) : null}
          {u.note && <p className="text-neutral-400">{noteOn(u.note, difficulty)}</p>}
          {u.goesTo && <p className="text-green-300">Heads for {u.goesTo.map((t) => `(${t[0]}, ${t[1]})`).join(' / ')}, outlined in green.</p>}
          {u.standIn && <StandInLine standIn={u.standIn} note={u.note} />}
        </div>
      ))}

      {here.map((a, i) =>
        a.kind === 'joiner' ? (
          <p key={`j${i}`} className={a.joiner.yellow || a.joiner.neutral ? 'text-yellow-300' : a.joiner.ally ? 'text-green-300' : 'text-blue-300'}>
            <PixelIcon sprite={joinerSprite(a.joiner)} />{' '}
            {a.joiner.yellow
              ? 'Arrives as a partner unit (yellow)'
              : a.joiner.neutral ? 'Arrives neutral (yellow)' : a.joiner.ally ? 'Arrives as a green unit' : 'Joins your army'}:{' '}
            <span className="font-medium">{a.joiner.name}</span>
            {!sameTile(a.joiner.from, a.joiner.tile) && <span className="text-neutral-400"> · walks in from {where(a.joiner.from, map)}</span>}
            {whenText(a.joiner, difficulty) && <span className="block text-neutral-400">{whenText(a.joiner, difficulty)}</span>}
            {a.joiner.talk && <span className="block text-sky-300">{a.joiner.talk}</span>}
            {a.joiner.note && <span className="block text-neutral-400">{a.joiner.note}</span>}
            {a.joiner.goesTo && (
              <span className="block text-green-300">Heads for {a.joiner.goesTo.map((t) => `(${t[0]}, ${t[1]})`).join(' / ')}, outlined in green.</span>
            )}
          </p>
        ) : (
          <div key={`r${i}`}>
            <p className="text-orange-300">
              <PixelIcon sprite={reinforcementSprite(a.unit)} /> Reinforcement ({a.group})
              {a.unit.type === 'boss' ? ', boss' : a.unit.type === 'named' ? ', named foe' : ''}: <span className="font-medium">{a.unit.name}</span>
              {a.unit.paired && !a.unit.partner && ' (two, paired up)'}
              {a.unit.from && !sameTile(a.unit.from, a.unit.tile) && (
                <span className="text-neutral-400"> · enters from {where(a.unit.from, map)}</span>
              )}
            </p>
            {a.when && <p className="text-neutral-400">Arrives: {a.when}</p>}
            {a.unit.talk && <p className="text-sky-300">{a.unit.talk}</p>}
            {a.unit.partner && <p className="text-neutral-300">Paired up with: {a.unit.partner}</p>}
            {a.unit.carries?.length ? <p className="text-neutral-300">Carries {[...new Set(a.unit.carries)].join(', ')}</p> : null}
            {a.unit.drops?.map((d) => (
              <p key={d} className="text-amber-300">
                <PixelIcon sprite={DROP_BADGE} /> Drops {d}
              </p>
            ))}
            {a.unit.capturable && (
              <p className="text-neutral-300">
                <PixelIcon sprite={CAPTURE_BADGE} /> Can be captured
              </p>
            )}
            {a.unit.steal?.length ? (
              <p className="text-fuchsia-300">
                <PixelIcon sprite={STEAL_BADGE} /> {set.takeBy === 'capture' ? 'Capture to take' : 'Steal'}: {a.unit.steal.join(', ')}
              </p>
            ) : null}
            {a.unit.note && <p className="text-neutral-400">{noteOn(a.unit.note, difficulty)}</p>}
            {a.unit.standIn && <StandInLine standIn={a.unit.standIn} note={a.unit.note} />}
            {a.unit.goesTo && (
              <p className="text-green-300">Heads for {a.unit.goesTo.map((t) => `(${t[0]}, ${t[1]})`).join(' / ')}, outlined in green.</p>
            )}
          </div>
        ),
      )}

      {(map.walls ?? [])
        // A side is kept once, on the tile west or north of it: this tile's own, and its west and north neighbours' facing it.
        .flatMap((w) =>
          sameTile(w.tile, tile)
            ? [w]
            : w.side === 'e' && sameTile(w.tile, [tile[0] - 1, tile[1]])
              ? [{ ...w, side: 'w' as const }]
              : w.side === 's' && sameTile(w.tile, [tile[0], tile[1] + 1])
                ? [{ ...w, side: 'n' as const }]
                : [],
        )
        .map((w) => (
          <p key={w.side} className="text-amber-200">
            {w.step ? 'A step between levels' : 'Blocked'} on the {{ n: 'north', e: 'east', s: 'south', w: 'west' }[w.side]} side:{' '}
            {w.all ? 'no unit can cross there.' : "ground units can't cross there; fliers can."}
          </p>
        ))}

      {map.dark?.some((t) => sameTile(t, tile)) && (
        <p className="text-neutral-400">Under darkness: nothing can enter until the chapter lifts it.</p>
      )}

      {objectives.map((o) =>
        o.type === 'burn' ? (
          <p key={o.label} className="text-orange-300">
            <PixelIcon sprite={SUPPLIES} /> {o.label}
          </p>
        ) : (
          <p key={o.label} className="text-sky-300">
            Objective: {o.label}
          </p>
        ),
      )}

      {pot && (
        <div>
          <p className={pot.pot === 'medicine' ? 'text-emerald-300' : 'text-fuchsia-300'}>
            {pot.pot === 'medicine' ? 'Medicine pot' : 'Poison pot'}
            {potsBroken && ' (broken by the vein preview)'}
          </p>
          <p className="text-neutral-200">{describePotEffect(pot.effect)}</p>
          <p className="text-neutral-400">
            Hits every unit, yours and the enemy's, within {pot.radius} tiles when broken.
          </p>
        </div>
      )}

      {chest?.type === 'chest' && <p className="text-amber-300">Chest: {chest.contents}</p>}
      {ballista?.type === 'ballista' && (
        <p className="text-amber-300">
          <PixelIcon sprite={BALLISTA} /> {ballista.weapon}
          <span className="text-neutral-400">
            {' '}
            ·{' '}
            {ballista.mounted
              ? 'an Archer or Sniper standing on it fires it'
              : sameTile(ballista.tile, tile)
                ? `an archer or sniper standing here fires the machine beside them, at (${ballista.machine[0]}, ${ballista.machine[1]})`
                : `fired by an archer or sniper standing at (${ballista.tile[0]}, ${ballista.tile[1]})`}
          </span>
        </p>
      )}
      {trap?.type === 'trap' && (
        <p className="text-orange-300">
          <PixelIcon sprite={TRAP_SPRITE[trap.kind]} /> {TRAP_LABEL[trap.kind]}
          <span className="text-neutral-400"> · {trap.note}</span>
        </p>
      )}
      {inFog && <p className="text-neutral-400">In the fog: hidden unless one of your units, or a lit torch, can see it.</p>}
      {sceneryHouse(letter, tileKey(tile), visitable(map)) && (
        <p className="text-neutral-400">A house with nothing to visit: units stand in it (part of the village's scenery).</p>
      )}
      {closed.has(tileKey(tile)) && (
        <div>
          <p className="text-neutral-400">A closed room: what's inside can't be seen until a door into it opens.</p>
          {map.changes
            .filter((c) => !c.wide && (c.patch ?? []).some((p) => sameTile(p.tile, tile)))
            .map((c) => {
              const [x, y] = resolveTile(c.tile, difficulty)
              return (
                <p key={c.id} className="mt-1 text-cyan-300">
                  Opened by {c.id.startsWith('door') || /A door: /.test(c.effect ?? '') ? 'the door' : 'the change'} at ({x}, {y}){c.turn !== undefined && ` on turn ${c.turn}`}{' '}
                  <button
                    onClick={() => onTogglePreview(c.id)}
                    className="ml-1 rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
                  >
                    Preview it open
                  </button>
                </p>
              )
            })}
        </div>
      )}
      {fire && (
        <p className="text-red-300">
          <PixelIcon sprite={FLAME} /> A house the enemy's arsonists can set alight
          <span className="text-neutral-400"> · a unit next to it once it burns can put it out.</span>
        </p>
      )}
      {pit && (
        <p className="text-amber-300">
          <PixelIcon sprite={PIT} /> Pit trap
          <span className="text-neutral-400">
            {' '}
            · a ground unit that moves onto it falls in and can't move again until next turn (it can still counterattack). A flier
            doesn't fall, and while one stands on it, others can cross.
          </span>
        </p>
      )}
      {eventTile && (
        <p className="text-amber-300">
          <PixelIcon sprite={EVENT_TILE} /> Event tile
          <span className="text-neutral-400">
            {' '}
            · a unit that stops here gets a random bonus: experience, weapon experience, a random item, or support between a pair.
          </span>
        </p>
      )}
      {shiny && (
        <p className="text-cyan-300">
          <PixelIcon sprite={SHINY} /> Shiny spot
          <span className="text-neutral-400">
            {' '}
            · a unit that stops here finds gold (20%), ore (30%), an item (30%: one of the gifts My Castle's allies can give on your
            route by this chapter) or weapon experience (20%).
          </span>
        </p>
      )}
      {hidden.map(
        (h) =>
          h.type === 'hidden' && (
            <div key={h.contents}>
              <p className="text-amber-300">
                <PixelIcon sprite={BURIED} /> Hidden: {h.contents}
              </p>
              <p className="text-neutral-400">
                {h.note ??
                  'Buried somewhere in the outlined area. A unit that moves into it has a (Skill + 1)% chance to dig it up; Thieves and Assassins always find it.'}
              </p>
            </div>
          ),
      )}
      {castle?.type === 'castle' && (
        <p className="text-sky-200">
          <PixelIcon sprite={CASTLE} /> Castle: <span className="font-medium">{castle.name}</span>
          {castle.note && <span className="block text-neutral-400">{castle.note}</span>}
        </p>
      )}
      {shop?.type === 'shop' && (
        <p className="text-amber-200">
          {shop.kind}: <span className="text-neutral-300">sells {shop.stock.join(', ')}</span>
          {shop.note && <span className="block text-neutral-400">{shop.note}</span>}
        </p>
      )}
      {village?.type === 'village' && (
        <p className="text-amber-300">
          Village:{' '}
          {village.reward
            ? `visit for ${/^\d/.test(village.reward) ? '' : /^[AEIOU]/i.test(village.reward) ? 'an ' : 'a '}${village.reward}`
            : !village.note && 'a visit gives nothing'}
          {village.note && <span className="text-neutral-400"> {village.note}</span>}
        </p>
      )}

      {(map.switchWalls?.walls ?? [])
        .filter((w) => w.tiles.some((t) => sameTile(t, tile)))
        .map((w) => {
          const turns = map.switchWalls!.turns.find((t) => t.walls.includes(w.id))
          const vein = map.changes.find((c) => c.flips === w.id)
          return (
            <p key={`wall${w.id}`} className="text-orange-300">
              Wall {w.id}
              {turns && `: flips on turns ${firstMultiples(turns.every, turns.from).join(', ')}...`}
              {vein && `; the Dragon Vein at (${vein.tile.default[0]}, ${vein.tile.default[1]}) flips it`}
            </p>
          )
        })}

      {changes.map((c) => (
        <div key={c.id} className="rounded border border-cyan-900 bg-cyan-950/40 p-2">
          <p className="text-cyan-300">
            {c.trigger === 'breakable'
              ? 'Breakable'
              : c.trigger === 'boulder'
                ? 'Boulder'
                : c.trigger === 'torch'
                  ? `Torch, lit by: ${c.usableBy}`
                  : c.trigger === 'eruption'
                    ? 'Lava floor'
                    : c.trigger === 'event'
                      ? 'Changes during the chapter'
                      : c.trigger === 'trap'
                        ? 'Trap'
                        : `Dragon Vein, usable by: ${c.usableBy}`}
          </p>
          <p className="text-neutral-300">{c.effect}</p>
          {c.tile.Lunatic && <p className="text-neutral-500">This vein's tile changes with difficulty; showing {difficulty}.</p>}
          {c.dig && (
            <p className="text-neutral-400">
              {digging
                ? 'Digging: tap the snow on the map to clear a tile and the four beside it, and see what was under it.'
                : 'Dig to clear it a tile at a time, or clear it all at once.'}
            </p>
          )}
          <div className="mt-2 flex flex-wrap gap-2">
            {c.dig && !previewing.has(c.id) && (
              <button
                onClick={onToggleDig}
                aria-pressed={digging}
                className="rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
              >
                {digging ? 'Stop digging' : 'Dig'}
              </button>
            )}
            {!c.noPreview && (
              <button
                onClick={() => onTogglePreview(c.id)}
                className="rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
              >
                {c.dig
                  ? previewing.has(c.id) ? 'Cover it again' : 'Clear it all'
                  : c.trigger === 'torch' ? (torchLit(c, previewing) ? 'Put it out' : 'Light it') : previewing.has(c.id) ? 'Stop preview' : c.trigger === 'boulder' ? 'Show its path' : 'Preview'}
              </button>
            )}
            {c.group &&
              (() => {
                const ids = map.changes.filter((o) => o.group === c.group).map((o) => o.id)
                const all = ids.every((id) => previewing.has(id))
                return (
                  <button
                    onClick={() => onPreviewGroup(ids, !all)}
                    className="rounded border border-cyan-700 px-2 py-0.5 text-cyan-200 hover:bg-cyan-900"
                  >
                    {all ? `Stop all ${ids.length}` : `All ${ids.length} at once`}
                  </button>
                )
              })()}
            {(previewing.size > 0 || dugCount > 0) && (
              <button onClick={onReset} className="rounded border border-neutral-700 px-2 py-0.5 text-neutral-300 hover:bg-neutral-800">
                Reset map
              </button>
            )}
          </div>
        </div>
      ))}

      {(map.links ?? [])
        .filter(([a, b]) => sameTile(a, tile) || sameTile(b, tile))
        .map(([a, b]) => (sameTile(a, tile) ? b : a))
        .map((t) => (
          <p key={`link${tileKey(t)}`} className="text-cyan-300">
            Stairs: they lead to ({t[0]}, {t[1]}), outlined on the map
          </p>
        ))}

      {isStart &&
        (map.corrinStart && sameTile(map.corrinStart, tile) ? (
          <p className="text-yellow-300">{map.lord ?? set.lord}'s starting tile</p>
        ) : fixedHere ? (
          <p className="text-pink-300">Forced deployment: {fixedHere.name}, placed here by the game</p>
        ) : (
          <p className="text-blue-300">Starting tile</p>
        ))}

      <div className="border-t border-neutral-800 pt-2">
        {pot && !potsBroken ? (
          <>
            <p className="text-neutral-200">Terrain: Pot</p>
            <p className="text-neutral-400">{POT_TERRAIN_NOTE}</p>
          </>
        ) : (
          <>
            <p className="text-neutral-200">
              Terrain: {terrainName(map, tile)}
              <span className="text-neutral-400">
                {' '}
                {!set.noTerrainDef && ` · Def ${fmt(terrain.def)}`}
                {terrain.res !== undefined && ` · Res ${fmt(terrain.res)}`} · Avo {fmt(terrain.avo)}
                {terrain.heal > 0 && ` · Heals ${terrain.heal}${set.healInHp ? ' HP' : '%'} per turn`}
              </span>
            </p>
            {terrain.note && <p className="text-neutral-400">{terrain.note}</p>}
            {set.terrainNote && (terrain.def !== 0 || terrain.avo !== 0) && <p className="text-neutral-500">{set.terrainNote}</p>}
            <details className="mt-1">
              <summary className="cursor-pointer text-neutral-400 hover:text-neutral-200">Movement cost by class type</summary>
              <table className="mt-1 w-full text-xs">
                <tbody>
                  {set.moveClasses.map((mc) => {
                    const cost = terrain.move[mc]
                    return (
                      <tr key={mc} className="border-b border-neutral-900" title={set.moveClassExamples[mc]}>
                        <td className="py-0.5 pr-2 text-neutral-400">{mc}</td>
                        <td className={cost === null ? 'text-neutral-600' : 'text-neutral-200'}>{cost === null ? "Can't enter" : cost}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </details>
          </>
        )}
      </div>
    </section>
  )
}

const fmt = (n: number) => (n > 0 ? `+${n}` : String(n))

/** Tiles off the map (where a unit walks in from) read as "off the left edge, by (1, 16)". */
function where([x, y]: Tile, map: ChapterMap): string {
  const side = x < 1 ? 'left' : x > map.width ? 'right' : y < 1 ? 'bottom' : y > map.height ? 'top' : null
  if (!side) return `(${x}, ${y})`
  return `off the ${side} edge, by (${Math.min(Math.max(x, 1), map.width)}, ${Math.min(Math.max(y, 1), map.height)})`
}

/** A group's arrival sentence for the chosen difficulty, if the script gave one. */
function whenText(a: Arrival, difficulty: Difficulty): string | undefined {
  if (!a.when) return undefined
  return typeof a.when === 'string' ? a.when : a.when[difficulty]
}

/** Whether a joiner comes on this difficulty: one timed per difficulty comes only on those listed. */
const joinsOn = (difficulty: Difficulty) => (j: Joiner) => !j.when || typeof j.when === 'string' || j.when[difficulty] !== undefined

/** Joiners who arrive together, as "Silas, Elise". */
function joinerGroups(joiners: Joiner[]) {
  const byGroup = new Map<string, Joiner[]>()
  for (const j of joiners) byGroup.set(j.group, [...(byGroup.get(j.group) ?? []), j])
  return [...byGroup.values()].map((js) => ({ names: js.map((j) => j.name).join(', '), joiner: js[0] }))
}

function ArrivalsPanel({
  map,
  difficulty,
  difficultyLabel,
  groups,
  showJoiners,
  onToggleGroup,
  onSetGroups,
  onToggleJoiners,
}: {
  map: ChapterMap
  difficulty: Difficulty
  difficultyLabel: string
  groups: Set<string>
  showJoiners: boolean
  onToggleGroup: (id: string) => void
  onSetGroups: (ids: Set<string>) => void
  onToggleJoiners: () => void
}) {
  // Only the groups that bring anyone on this difficulty.
  const list = (map.reinforcements ?? [])
    .map((g) => ({ ...g, count: headcount(g.units.filter(onDifficulty(difficulty))) }))
    .filter((g) => g.count > 0)
  const joiners = (map.joiners ?? []).filter(joinsOn(difficulty))
  if (list.length === 0 && joiners.length === 0) return null
  const total = list.reduce((n, g) => n + g.count, 0)
  const chip = (on: boolean) =>
    `rounded border px-2 py-0.5 text-xs ${on ? 'border-orange-500 bg-orange-950/60 text-orange-200' : 'border-neutral-700 text-neutral-300 hover:bg-neutral-800'}`
  return (
    <section className="flex flex-col gap-2 rounded border border-neutral-800 p-4 text-sm">
      <h3 className="font-semibold text-neutral-100">Reinforcements & joiners</h3>
      {list.length > 0 && (
        <>
          <p className="text-neutral-400">
            {list.length} {list.length === 1 ? 'group' : 'groups'} on {difficultyLabel}
            {list.length > 1 && <> ({total} units across them)</>}
            {map.groupsNote
              ? `: ${map.groupsNote}`
              : map.randomSpawns
                ? ': enemies spawn at these points at random, on no set turn, so not every group arrives in one playthrough.'
                : ", timed by the chapter's own script."}{' '}
            {!map.groupsNote &&
              'Arrows run from where each unit enters to where it stops; dashed outlines mark the areas a group’s time names, those that bring it in or stop it.'}
          </p>
          <ul className="flex flex-col gap-1">
            {list.map((g) => (
              <li key={g.id} className="flex items-start gap-2">
                <button onClick={() => onToggleGroup(g.id)} aria-pressed={groups.has(g.id)} className={`${chip(groups.has(g.id))} shrink-0`}>
                  {g.label} · {g.count}
                </button>
                <span className="text-xs text-neutral-400">{whenText(g, difficulty) ?? "Timing not found in the chapter's script."}</span>
              </li>
            ))}
          </ul>
          <div className="flex gap-2">
            <button onClick={() => onSetGroups(new Set(list.map((g) => g.id)))} className={chip(false)}>
              Show all
            </button>
            {groups.size > 0 && (
              <button onClick={() => onSetGroups(new Set())} className={chip(false)}>
                Hide all
              </button>
            )}
          </div>
        </>
      )}
      {joiners.length > 0 && (
        <div className="flex flex-col gap-1 border-t border-neutral-800 pt-2">
          <div>
            <button onClick={onToggleJoiners} aria-pressed={showJoiners} className={chip(showJoiners)}>
              {showJoiners ? 'Hide joiners' : 'Show joiners'}
            </button>
          </div>
          <ul className="text-xs text-neutral-400">
            {joinerGroups(joiners).map(({ names, joiner }) => (
              <li key={names}>
                <span className="text-blue-300">{names}</span>
                {whenText(joiner, difficulty) && <> · {whenText(joiner, difficulty)}</>}
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function ChapterInfo({ map, label, difficulty }: { map: ChapterMap; label: string; difficulty: Difficulty }) {
  // Under the spoiler block a note that holds from a later map (an encounter from a later act) waits for it.
  const reach = useReach()
  return (
    <section className="flex flex-col gap-2 rounded border border-neutral-800 p-4 text-sm text-neutral-300">
      <h3 className="font-semibold text-neutral-100">
        {label}
      </h3>
      {map.location && <p className="text-neutral-500">{map.location}</p>}
      {map.victory && (
        <p>
          <span className="text-emerald-400">Win:</span> {map.victory}
        </p>
      )}
      {map.defeat && (
        <p>
          <span className="text-red-400">Lose:</span> {map.defeat}
        </p>
      )}
      {map.forced?.some((f) => !f.tile) && (
        <p>
          <span className="text-pink-300">Must deploy:</span>{' '}
          {map.forced.filter((f) => !f.tile).map((f) => f.name).join(', ')} <span className="text-neutral-500">(you choose the tile)</span>
        </p>
      )}
      {map.forced?.some((f) => f.tile) && (
        <p>
          <span className="text-pink-300">Placed by the game:</span>{' '}
          {map.forced
            .filter((f) => f.tile)
            .map((f) => `${f.name} (${f.tile![0]}, ${f.tile![1]})`)
            .join(', ')}
        </p>
      )}
      <ul className="list-disc space-y-1 pl-5 text-neutral-400">
        {notesOn(map, difficulty, reach.has).map((n) => (
          <li key={n}>{n}</li>
        ))}
      </ul>
      {map.unconfirmed && map.unconfirmed.length > 0 && (
        <div className="rounded border border-amber-900 bg-amber-950/30 p-2">
          <p className="text-amber-300">Not yet confirmed in-game</p>
          <ul className="list-disc space-y-1 pl-5 text-amber-200/80">
            {map.unconfirmed.map((n) => (
              <li key={n}>{n}</li>
            ))}
          </ul>
        </div>
      )}
    </section>
  )
}

function PotList({ map, selected, broken, onSelect }: { map: ChapterMap; selected: Tile | null; broken: boolean; onSelect: (t: Tile) => void }) {
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  if (pots.length === 0) return null
  // Top of the map first, like reading the grid.
  const sorted = [...pots].sort((a, b) => b.tile[1] - a.tile[1] || a.tile[0] - b.tile[0])
  return (
    <section className="grid grid-cols-1 gap-4 rounded border border-neutral-800 p-4 text-sm md:grid-cols-2">
      {(['medicine', 'poison'] as const).map((kind) => {
        const list = sorted.filter((p) => p.pot === kind)
        return (
          <div key={kind}>
            <h3 className={`mb-1 font-semibold ${kind === 'medicine' ? 'text-emerald-300' : 'text-fuchsia-300'}`}>
              {kind === 'medicine' ? 'Medicine' : 'Poison'} pots ({list.length})
            </h3>
            <ul className={broken ? 'opacity-50' : ''}>
              {list.map((p) => (
                <li key={tileKey(p.tile)}>
                  <button
                    onClick={() => onSelect(p.tile)}
                    className={`w-full rounded px-1 text-left hover:bg-neutral-800 ${selected && sameTile(selected, p.tile) ? 'bg-neutral-800' : ''}`}
                  >
                    <span className="inline-block w-16 text-neutral-500">
                      ({p.tile[0]}, {p.tile[1]})
                    </span>
                    {describePotEffect(p.effect)}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
    </section>
  )
}
