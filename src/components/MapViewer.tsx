import { useBackdropRoute } from './Backdrop'
import { useMemo, useState } from 'react'
import { useReach } from './Reach'
import { ColourBlindContext, useColourBlind } from './ColourBlind'
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
  BULWARK, GRAVE, FELL_FLOOR, SHINY, COTTAGE, SNAG, CREST_STONE, HEALTH_PIPS, FLOOR_TRAP, ONAGER, FIRE_ORB,
  FOG, PUDDLE, STONE_PILLARS, MIASMA, FROST, TUNNEL, VILLAGE_PIECES, VILLAGE_VARIANTS, CASTLE_PIECES, TOWN_HOUSE, MOUNTAIN, LAVA_CRACK, BARREL, BONES,
  HOUSE_PIECES, HOUSE_SIDE_PIECES, FOUNTAIN_PIECES, ROOFTOP_PIECES, ROOFTOP_DOORS, CHIMNEY, HOUSE_VARIANTS, HOUSE_FRONT, MARKET_STALL, CRATES, ODDS_AND_ENDS, CANDLESTICK, PROP_SPRITES, FLOOR_PATTERNS, COAST_VARIANTS, SNOW_TREE, SNOW_THICK_WOOD, DEF_SIGIL, DEF2_SIGIL, RES_SIGIL, LAVA_POOL, CHURCH_PIECES, CAMP_PIECES, WATCHTOWER,
  CHURCH_FRONT_PLAIN, CAMP_FRONT_PLAIN, DOOR_MAT, VILLAGE_HOUSE, WALLED_VILLAGE, RUINED_VILLAGE_TOP, RUINED_VILLAGE_FRONT,
  SEALED_DOOR, STAIR_FORT_PIECES, BRIDGE_SIDE, OPEN_DOOR, RAISED_BRIDGE, ALTAR, ALTAR_PIECES, MAST, FORT_PIECES, RAMPART_GATE, MAP_EVENT, CHERRY_TREE,
  WOOD_FORT_PIECES, HALL_PIECES, KEEP_PIECES, SUPPLY_DEPOT, LEVER, LAUNCHER, RUINS, CRACKED_WALL, STATUE, BRIDGE_PLANKS, WINDMILL, YURT,
  SUPPLY_BOXES, TENT_PIECES, TENT_SIDE, SANDBAG_WALL, PILLAR_TOP, UMBRELLA, PALM, PARASOL, DRAGON_STATUE, SHACK, ROCK_PEAK,
  CASTLE_ROW, STAIRS_DOWN, WIDE_STAIRWELL, HORSE, CARRIAGE, SARCOPHAGUS, STONE_TABLE, YURT_HOUSE, YURT_FORT, GARDEN, roundFountainPiece, BOAT_BOW, ICE_CRYSTALS, frozenFountainPiece, canopyPiece, ruinedRoofPiece, ruinedShellPiece,
  roundYurtPiece, zenGardenPiece, bigTreePiece, OBSTACLE, WARP_SIGIL, WARP_PAD, FLAME_WALL, FLAME_VENT, cratePiece, boulderPiece, slabPiece, bonePiece, vaseTablePiece, RUBBLE_VARIANTS, HOUSE_DOOR, SHOP_ROOF, SHOP_SIGN, SHOP_SIGN_CLEAR, ARENA_PIECES, SMALL_SHOP, SMALL_SHOP_SIGN, EAVES, DEPOT_FRONT, layered, recoloured,
  STONE_PILE, CORAL, SUPPLY_CACHE, bigPillarPiece, SUPPLY_CRATES, supplyMarked, PALISADE, COFFIN, STATUE_SMALL, TORCH_UNLIT, COLOUR_BLIND,
} from '../icons/sprites'
import { applyChanges, arrivalTurn, beforeBuilding, doorMat, sceneryHouse, visitable, atStart, closedRooms, covers, describePotEffect, digAt, inTheFog, mapSteps, noteOn, notesOn, objectsAt, resolveTile, rowCodes, sameTile, terrainAt, terrainInfo, terrainName, tileKey, tilesInRadius, WATER_CODES, wholeBridgeBoxes, wideBridgeSpans, withStandIns, withSwitchWalls } from '../logic/maps'
import { VOID_COLOUR, visibleFills } from '../logic/mapFills'
import { setSideStoryShown, useSideStories } from '../logic/sideStories'

const CELL = 10
const GUTTER = 7 // room for the axis numbers
/** The dev server's review captures (`?reveal`): every map shown whole, with no fog and each closed room's contents in view. */
const REVEAL = import.meta.env.DEV && typeof location !== 'undefined' && new URLSearchParams(location.search).has('reveal')

/** A fence along a tile side. */
const FENCE = '#7c4a1e'
/** A railing along a step between two heights: a rail on posts, light against the fence's brown (the user: like the fence). */
const RAIL = '#e7d3a8'

/** A wooden bridge (the user: it read as a brown block): its planks laid across its span, each lit along one edge with a gap
 * between, and a rail along each side over water. Its span runs between the banks: across a river flowing north to south, along one
 * flowing east to west. */
function WoodBridge({ map, t: [x, y], fill, railed }: { map: ChapterMap; t: Tile; fill: string; railed?: boolean }) {
  const X = GUTTER + (x - 1) * CELL
  const Y = (map.height - y) * CELL
  const open = (dx: number, dy: number) => {
    const c = x + dx >= 1 && y + dy >= 1 && x + dx <= map.width && y + dy <= map.height ? terrainAt(map, [x + dx, y + dy]) : undefined
    // Over a bog too where its muck is drawn as one (Fates' Boo Camp: the user, its bridge over the hot spring railed as the game has it).
    return !!c && (WATER_CODES.has(c) || c[0] === 'w' || (c === 'db' && !!map.muckAsBog))
  }
  const [n, s, w, e] = [open(0, 1), open(0, -1), open(-1, 0), open(1, 0)]
  // The span runs the way its bridge tiles run (its end tile, water only at its sides, turned the wrong way: Radiant Dawn's Part 4
  // Prologue, the user), a wide bridge's across the water along its sides; a lone tile by the water round it: water above or below,
  // the span runs east to west, its planks upright.
  const own = terrainAt(map, [x, y])
  const same = (dx: number, dy: number) =>
    x + dx >= 1 && y + dy >= 1 && x + dx <= map.width && y + dy <= map.height && terrainAt(map, [x + dx, y + dy]) === own
  // A gangplank (`railed`) runs the way its tiles do.
  const plank = (dx: number, dy: number) => !!map.gangplanks?.includes(tileKey([x + dx, y + dy]))
  const along = railed ? (plank(1, 0) || plank(-1, 0) ? 'ew' : plank(0, 1) || plank(0, -1) ? 'ns' : undefined) : undefined
  // A bridge read whole (`wholeBridges`): its box's span, its rails only along the box's long sides.
  const whole = map.wholeBridges ? wholeBridgeBoxes(map).get(tileKey([x, y])) : undefined
  // A bridge that turns or jogs, every tile of it one way (`bridgeSpans`: Fates' Chapter 3, the user).
  const run = along ?? map.bridgeSpans?.[tileKey([x, y])] ?? whole?.span ??
    wideBridgeSpans(map).get(tileKey([x, y])) ?? (same(0, 1) || same(0, -1) ? 'ns' : same(1, 0) || same(-1, 0) ? 'ew' : undefined)
  const eastWest = run ? run === 'ew' : n || s || !(w || e)
  const gap = shade(fill, -0.45)
  const lit = shade(fill, 0.3)
  const rail = shade(fill, 0.42)
  return (
    <g pointerEvents="none">
      {[0, 2.5, 5, 7.5].map((o) =>
        eastWest ? (
          <g key={o}>
            <line x1={X + o + 0.25} x2={X + o + 0.25} y1={Y} y2={Y + 10} stroke={gap} strokeWidth={0.5} />
            <line x1={X + o + 0.85} x2={X + o + 0.85} y1={Y} y2={Y + 10} stroke={lit} strokeWidth={0.4} />
          </g>
        ) : (
          <g key={o}>
            <line y1={Y + o + 0.25} y2={Y + o + 0.25} x1={X} x2={X + 10} stroke={gap} strokeWidth={0.5} />
            <line y1={Y + o + 0.85} y2={Y + o + 0.85} x1={X} x2={X + 10} stroke={lit} strokeWidth={0.4} />
          </g>
        ),
      )}
      {(eastWest ? ([['n', n], ['s', s]] as const) : ([['w', w], ['e', e]] as const)).map(([side, over]) => {
        // A gangplank has its rail along each side, over water or not; a bridge read whole only along its box's sides.
        if (!over && !railed) return null
        if (whole && !{ n: y === whole.box[3], s: y === whole.box[2], w: x === whole.box[0], e: x === whole.box[1] }[side]) return null
        const [rx, ry, rw, rh] = { n: [0, 0, 10, 1.5], s: [0, 8.5, 10, 1.5], w: [0, 0, 1.5, 10], e: [8.5, 0, 1.5, 10] }[side]
        return <rect key={side} x={X + rx} y={Y + ry} width={rw} height={rh} fill={rail} stroke={gap} strokeWidth={0.35} />
      })}
    </g>
  )
}

/** The closed sides drawn: all but those between two ledges side by side on a map whose ledges climb (`ledgeUp`: the user, no fence
 * between them; the game still keeps units from running along a ledge, and the tile's panel says so). */
function shownWalls(map: ChapterMap): NonNullable<ChapterMap['walls']> {
  if (!map.ledgeUp) return map.walls ?? []
  const ledge = (t: Tile) => codeAt(map, t) === 'bg'
  return (map.walls ?? []).filter(({ tile: [x, y], side }) => {
    const [dx, dy] = { n: [0, 1], s: [0, -1], e: [1, 0], w: [-1, 0] }[side]
    return !(ledge([x, y]) && ledge([x + dx, y + dy]))
  })
}

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

/** Okabe and Ito's colours, which stay apart for red-green and blue-yellow colour blindness alike: the colour-blind look's
 * (`ColourBlindContext`; its markers are `COLOUR_BLIND`). */
const OKABE = { orange: '#e69f00', sky: '#56b4e9', green: '#009e73', yellow: '#f0e442', blue: '#0072b2', vermillion: '#d55e00', purple: '#cc79a7' }
type Line = { colour: string; dash?: string }
/** Each kind of outline in the colour-blind look: a colour and dashes of its own. */
const CB_LINE = {
  objective: { colour: OKABE.sky },
  area: { colour: OKABE.orange, dash: '2.4 1.2' },
  foeArea: { colour: OKABE.vermillion, dash: '0.7 0.9' },
  trap: { colour: OKABE.purple, dash: '3 1 0.8 1' },
  dig: { colour: OKABE.yellow, dash: '1.5 1' },
  fire: { colour: OKABE.vermillion, dash: '1.5 1' },
  burn: { colour: OKABE.orange, dash: '2 1' },
} satisfies Record<string, Line>
const CB_FOE_GROUP: Line[] = [{ colour: OKABE.yellow, dash: '1.6 0.9' }, { colour: OKABE.purple, dash: '0.6 0.9' }]

/** An outline in the colour-blind look: its colour and dashes a little thicker than the usual line, over a dark line of its own. */
function CbRect({ x, y, width, height, line, strokeWidth, fillOpacity = 0 }: {
  x: number
  y: number
  width: number
  height: number
  line: Line
  strokeWidth: number
  fillOpacity?: number
}) {
  return (
    <g pointerEvents="none">
      <rect x={x} y={y} width={width} height={height} fill={line.colour} fillOpacity={fillOpacity} stroke="#0a0a0a" strokeOpacity={0.75} strokeWidth={strokeWidth + 0.9} />
      <rect x={x} y={y} width={width} height={height} fill="none" stroke={line.colour} strokeWidth={strokeWidth + 0.3} strokeDasharray={line.dash} />
    </g>
  )
}

/** A starting tile's corner marks: the lord's start, a forced unit's fixed tile or any other. The colour-blind look tells them apart by
 * their corners too: the lord's all four, a forced unit's the other two. */
type StartKind = 'start' | 'lord' | 'forced'
function startCorners(kind: StartKind, cb: boolean): { fill: string; paths: (X: number, Y: number) => string[] } {
  const tl = (X: number, Y: number) => `M${X} ${Y}h3l-3 3z`
  const br = (X: number, Y: number) => `M${X + 10} ${Y + 10}h-3l3 -3z`
  const tr = (X: number, Y: number) => `M${X + 10} ${Y}h-3l3 3z`
  const bl = (X: number, Y: number) => `M${X} ${Y + 10}h3l-3 -3z`
  if (!cb) return { fill: kind === 'lord' ? '#facc15' : kind === 'forced' ? FORCED : '#3b82f6', paths: (X, Y) => [tl(X, Y), br(X, Y)] }
  if (kind === 'lord') return { fill: OKABE.yellow, paths: (X, Y) => [tl(X, Y), tr(X, Y), bl(X, Y), br(X, Y)] }
  if (kind === 'forced') return { fill: OKABE.purple, paths: (X, Y) => [tr(X, Y), bl(X, Y)] }
  return { fill: OKABE.sky, paths: (X, Y) => [tl(X, Y), br(X, Y)] }
}

/** A trap that goes off on its own (the GBA games' fire tiles, gas vents and arrow launchers). */
const TRAP_SPRITE = { fire: LAVA_CRACK, gas: GAS_VENT, arrow: ARROW_TRAP } as const
const TRAP_LABEL = { fire: 'Fire trap', gas: 'Gas vent', arrow: 'Arrow launcher' } as const

/** Steps between two tiles. */
const distance = (a: Tile, b: Tile) => Math.abs(a[0] - b[0]) + Math.abs(a[1] - b[1])

const TERRAIN_FILL: Record<TerrainCode, string> = {
  // An obstacle stands on the ground round it; this is its tile's colour where a map gives none.
  xa: '#7a6b52',
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
  gf: '#b3a488',
  gg: '#6a9a4a',
  gh: '#9c7d4e',
  gi: '#9c7d4e',
  gj: '#9c7d4e',
  // Sand beyond a castle's walls no unit enters (Shadow Dragon's Chapter 23's corner), the art's sand.
  gk: '#c8b48c',
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
  gl: '#a08a64',
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
  wp: '#8a3418',
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
  // Shadow Dragon: a ledge climbed at a cost (the rough ground Shadow Dragon and the Blade of Light has on its tiles, in that ground's
  // colour: the user), a castle only fliers cross, and the tiles the lord can't enter (their base's colour).
  tt: '#8f8676',
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
  // A small stone fort's pieces (Gaiden's), its stone; the middle (the fort tile) its floor (fortFloor).
  qa: '#b9b7ad', qb: '#b9b7ad', qc: '#b9b7ad', qd: '#b9b7ad', qe: '#b9b7ad', qf: '#b9b7ad', qg: '#b9b7ad', qh: '#b9b7ad', qi: '#b9b7ad',
  ja: '#b89a6a', jb: '#b89a6a', jc: '#b89a6a', jd: '#b89a6a', je: '#b89a6a', jf: '#b89a6a', jg: '#b89a6a', jh: '#b89a6a', ji: '#b89a6a',
  la: '#b89a6a', lb: '#b89a6a', lc: '#b89a6a', ld: '#b89a6a', le: '#b89a6a', lf: '#b89a6a', lg: '#b89a6a', lh: '#b89a6a', li: '#b89a6a',
  ma: '#b89a6a', mb: '#b89a6a', mc: '#b89a6a', md: '#b89a6a', me: '#b89a6a', mf: '#b89a6a', mg: '#b89a6a', mh: '#b89a6a', mi: '#b89a6a',
  // An army's tent (Radiant Dawn's camps) stands on the ground around it.
  ua: '#b89a6a', ub: '#b89a6a', uc: '#b89a6a', ud: '#b89a6a', ue: '#b89a6a', uf: '#b89a6a', ug: '#b89a6a', uh: '#b89a6a', ui: '#b89a6a',
  // Mountains drawn as what the art shows (Gaiden's): a rocky shore's rock, a ship's raised deck's planks; a castle floor drawn as a
  // stone bridge's deck (Regal's slabs), the bridge's stone.
  na: '#886325', nb: '#cb882e', nc: '#9d978c',
  // Supplies stand on the ground round them, as a fort does.
  nd: '#b89a6a',
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
  // Castle bricks: their mortar a shade that shows on the wall's own colour ('contrast').
  w0: { stroke: 'contrast', lines: BRICKS },
  wx: { stroke: -0.32, lines: BLOCKS },
  // A wall a game keeps as one (Fates'): big blocks in a shade of its map's own colour.
  wa: { stroke: -0.3, lines: BLOCKS },
  w1: { stroke: '#55604a', lines: [[0, 4, 4, 4], [6, 6, 10, 6], [4, 4, 4, 7], [6, 2, 6, 6], [2, 7.5, 3.5, 9.5], [7.5, 0.5, 9, 2.5]] },
  w2: {
    stroke: '#7a3c2a',
    lines: [[0, 2.5, 10, 2.5], [0, 5, 10, 5], [0, 7.5, 10, 7.5], [2.5, 0, 2.5, 2.5], [7.5, 0, 7.5, 2.5], [5, 2.5, 5, 5], [2.5, 5, 2.5, 7.5], [7.5, 5, 7.5, 7.5], [5, 7.5, 5, 10]],
  },
  w3: { stroke: '#3a3354', lines: [[2, 2, 8, 2], [2, 8, 8, 8], [5, 2, 5, 8], [2, 2, 2, 8], [8, 2, 8, 8]] },
  w5: { stroke: '#86683a', lines: BRICKS },
  w6: { stroke: '#93a8b4', lines: BRICKS },
  w9: { stroke: '#4a331d', lines: [[0, 2.5, 10, 2.5], [0, 5, 10, 5], [0, 7.5, 10, 7.5]] },
  // A barrier of light: bright streaks rising through it.
  wu: { stroke: '#cfe2ff', lines: [[1.5, 1, 1.5, 6], [4, 3.5, 4, 9], [6.5, 0.5, 6.5, 5], [8.8, 4, 8.8, 9.5]] },
  // A building no unit enters (Engage's edifices, Radiant Dawn's): its stone in big blocks, as a game's walls kept as one.
  oe: { stroke: -0.3, lines: BLOCKS },
  // A wall that breaks (Three Houses' and Fates'), and Engage's junk: blocks with a crack through them.
  wz: { stroke: -0.32, lines: [...BLOCKS, [1, 1.5, 2.5, 3], [2.5, 3, 2, 4.5], [6, 6, 7.5, 7.5], [7.5, 7.5, 7, 9]] },
  // A fence or partition: two rails on three posts.
  wg: { stroke: -0.38, lines: [[0, 3.5, 10, 3.5], [0, 7, 10, 7], [1.5, 1.8, 1.5, 9], [5, 1.8, 5, 9], [8.5, 1.8, 8.5, 9]] },
}
/** A low outer wall's stone: its map's walls' (sandstone on a sandy map, snowy on a snowy one), else a weathered grey. */
function lowWallFill(map: ChapterMap): string {
  const has = (c: TerrainCode) => map.grid.some((row) => rowCodes(row).includes(c))
  // The map's own wall colour as the castle walls beside it are drawn (lifted on a dark map: Radiant Dawn's Part 1 Ch.7, the user).
  return map.fills?.w5 ?? (has('w5') ? TERRAIN_FILL.w5! : has('w6') ? TERRAIN_FILL.w6! : map.fills?.w0 ? fillOf(map, 'w0') : '#8f8a7e')
}
/** A barrier the game files with its walls (Awakening's dream map, the Premonition: the user, a dark barrier): a dark haze with streaks
 * of light rising through it, as a barrier of light's. */
const darkBarrier = (map: ChapterMap, t: Tile) => codeAt(map, t) === 'wa' && terrainName(map, t) === 'Barrier'
const DARK_BARRIER = '#2b2140'
/** What a wall that shares its numbers with other kinds is drawn as, by its model (Radiant Dawn's sandbags, outer walls, pillars); a
 * low wall the game files with its obstacles (Engage's) a low stone wall, or a ship's rail beside its deck (the user, the ship at the
 * Caring Princess's beach: not a ruin). */
const wallLook = (map: ChapterMap, t: Tile) => {
  const look = map.wallLooks?.[tileKey(t)]
  // The void (Echoes' caverns and trenches: the user, black, not a cliff) only while its tile is a wall: a script that turns it to floor
  // (the royal chambers' earthquakes) leaves floor.
  if (look === 'void' && codeAt(map, t)?.[0] !== 'w') return undefined
  return look ?? (lowWall(map, t) ? 'wall' : undefined)
}
/** A ship's wooden wall or rail: a low wall the game files with its obstacles beside its deck (Engage's), or one its art draws as the
 * ship's wood (The Blazing Blade's cabin walls). */
const shipWall = (map: ChapterMap, t: Tile) => lowWall(map, t) === 'ship' || map.wallLooks?.[tileKey(t)] === 'ship'
/** A low stone wall's stone (the GBA games' fences, which their art draws as low walls of tan stone: the user's call): the sandstone
 * castle walls' on a map that has them, all its walls one stone (The Binding Blade's 11A and 10B: the user), else its art's colour,
 * else sandstone. */
const stoneWallFill = (map: ChapterMap) => (hasSandstone(map) ? fillOf(map, 'w5') : map.fills?.wg ?? TERRAIN_FILL.w5!)
const SANDSTONE = new WeakMap<ChapterMap, boolean>()
function hasSandstone(map: ChapterMap): boolean {
  if (!SANDSTONE.has(map)) SANDSTONE.set(map, map.grid.some((row) => rowCodes(row).includes('w5')))
  return SANDSTONE.get(map)!
}
/** The ground most common beside a tile (its eight neighbours), for a wooden fence standing on it (a yard's grass, a ship's deck: The
 * Blazing Blade's Chapter 17's rails, the user). */
function groundBeside(map: ChapterMap, [x, y]: Tile): TerrainCode | undefined {
  const count = new Map<TerrainCode, number>()
  for (let dy = -1; dy <= 1; dy++)
    for (let dx = -1; dx <= 1; dx++) {
      const c = codeAt(map, [x + dx, y + dy])
      if (c && (dx || dy) && GROUND_CODES.has(c)) count.set(c, (count.get(c) ?? 0) + 1)
    }
  return [...count.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
}
/** A cave's wall's face, filed with the castle walls only fliers cross (Gaiden's caves): its rock a step darker than the rock over it, so
 * the wall stands apart from the ground beside it (the user: it melted into the bog's mud, Chapter 5-1's, and the dungeons'). */
const caveFace = (map: ChapterMap) => shade(fillOf(map, 'wt'), -0.3)
/** Mist (Fates' Boo Camp: the user, dark fog): a smoky grey, its haze drifting over it. */
const MIST = '#45464d'
/** A building's timber walls (Fates' Birthright 19, beside its floors: the user, a wood wall), red-brown as its art paints them. */
const TIMBER = '#6a3b2e'
/** A cliff's rock where the game files walls or partitions (Fates' Conquest 21's terraces' edges, Conquest 15's cliffs: the user). */
const cliffRock = (map: ChapterMap) => shade(fillOf(map, 'wt'), -0.18)
/** The sky seen past the map's edge or through a rift (Fates' Conquest 15: the user, not bricks): its colour on the map's art. */
const skyBelow = (map: ChapterMap) => map.fills?.wf ?? TERRAIN_FILL.wf!
/** A ship's wood where the game files walls (Path of Radiance's masts, cabins and hulls: the user, 'just use wood'): its deck's, darker. */
const shipWood = (map: ChapterMap) => shade(fillOf(map, 't3'), -0.25)
function lowWall(map: ChapterMap, t: Tile): 'ship' | 'stone' | undefined {
  if (codeAt(map, t) !== 'wj' || !/^low wall$/i.test(terrainName(map, t))) return undefined
  return ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => codeAt(map, [t[0] + dx, t[1] + dy]) === 't3') ? 'ship' : 'stone'
}
/** A breakable wall the game gives a plain wall's code, set in walls of one kind (Radiant Dawn's Part 1 Ch.4: the user, not a grey block
 * in a sandstone wall): drawn as the wall around it, its crack over it. A tile the map draws as another code (`looksAs`: Echoes' towers
 * in its ramparts) takes that code's look. */
function breakableLook(map: ChapterMap, [x, y]: Tile): TerrainCode | undefined {
  const code = codeAt(map, [x, y])
  const as = map.looksAs?.[tileKey([x, y])]
  if (as && code?.[0] === 'w') return as
  // A map whose breakable walls all take the walls round them (`breakablesAsWalls`: Three Houses'), its own code for them too.
  const own = map.breakablesAsWalls && code === 'wz'
  if ((code !== 'wa' && !own) || !map.changes.some((c) => c.trigger === 'breakable' && sameTile(changeTile(c), [x, y]))) return undefined
  const count = new Map<TerrainCode, number>()
  for (let dy = -1; dy <= 1; dy++)
    for (let dx = -1; dx <= 1; dx++) {
      const n = codeAt(map, [x + dx, y + dy])
      // A neighbour drawn as a roof, stalls or in ruins is a building, not a wall to match (on the maps that ask: Three Houses').
      const built = own && (!!map.decor?.[tileKey([x + dx, y + dy])] || !!map.ruins?.includes(tileKey([x + dx, y + dy])))
      if (n && n !== code && n[0] === 'w' && WALL_PATTERN[n] && !built) count.set(n, (count.get(n) ?? 0) + 1)
    }
  // With no wall round it, a plain wall's stones in its own colour.
  return [...count.entries()].sort((a, b) => b[1] - a[1])[0]?.[0] ?? (own ? 'wa' : undefined)
}

/** A tile's colour: its map's own where the map gives one (the GBA games' ground and water, from their art), else its code's. */
/** The Tower's Defense and Resistance floors: the hall's flagstone (the map's floor colour and slabs) with an emblem inlaid; and the
 * same for the castle floors that give Avoid (Gaiden's and Echoes', Mystery of the Emblem's): a pattern laid in the floor, not a
 * shield on every tile (the user's call, as the Tower's). */
const FLOOR_BONUS = new Set<TerrainCode>(['bo', 'bp', 'bq', 'br', 'b0', 'by', 'b9', 'hh', 'hf', 'bw', 'bx'])
const fillOf = (map: ChapterMap, code: TerrainCode): string =>
  visibleFills(map.fills)[code] ??
  // A floor with a bonus is its map's floor (Mystery of the Emblem's is the floor closed to mounts) with its pattern laid in; a tunnel
  // into a mountain its peaks' rock (the user: its own colour stood out of the mountainside).
  (FLOOR_BONUS.has(code) ? fillOf(map, map.fills?.t1 || !map.fills?.tn ? 't1' : 'tn') : code === 'tp' ? fillOf(map, 'bu')
    // A ship's hull a step darker than its deck, so the two woods part (Echoes' Act 6 ship: the user).
    : code === 'w9' && map.fills?.t3 ? shade(fillOf(map, 't3'), -0.3) : TERRAIN_FILL[code])

/** A colour mixed toward white (amount > 0) or black (< 0). */
function shade(hex: string, amount: number): string {
  const to = amount > 0 ? 255 : 0
  const a = Math.abs(amount)
  const mix = (i: number) => Math.round(parseInt(hex.slice(i, i + 2), 16) * (1 - a) + to * a)
  return `#${[1, 3, 5].map((i) => mix(i).toString(16).padStart(2, '0')).join('')}`
}

/** A pattern's lines in a shade of their tile's colour that shows on it: lighter on a dark colour, darker on a light one (castle
 * bricks: a fixed brown-grey vanished on Mystery of the Emblem's olive walls, a darker shade on Shadow Dragon's navy ones). */
function contrasting(hex: string): string {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16) / 255)
  return shade(hex, (Math.max(r, g, b) + Math.min(r, g, b)) / 2 < 0.4 ? 0.3 : -0.32)
}

/** Water's ripples and sand's grains, in a tile's own 10 x 10 units, drawn in a lighter or darker shade of its colour. */
const WAVES = ['M1 3.2 q1.2 -1.1 2.4 0 t2.4 0', 'M5 7.2 q1.2 -1.1 2.4 0 t2.4 0']
const SAND_CODES = new Set<TerrainCode>(['tk', 'td', 'gk'])
const GRAINS: [number, number][] = [[1.5, 2], [5.5, 1.2], [8.2, 3.6], [3.2, 5.4], [6.8, 6.6], [1.2, 8.4], [4.6, 8.8], [8.6, 8.2]]

/** The code a map's plains are drawn with where its art gives them a colour: the plain, or the plain with Avo +5 (Shadow Dragon and
 * the Blade of Light's and Mystery of the Emblem's grassland). */
// A map's plain: its own plain's colour where the art gives one (a game that keeps plain and floor as one, Fates' and Engage's `ta`,
// last: Fates' snowfields are its plain, so their mountains are snowy peaks: the user's call).
const plainOf = (map: ChapterMap): TerrainCode | undefined => (map.fills?.t0 ? 't0' : map.fills?.tv ? 'tv' : map.fills?.ta ? 'ta' : undefined)

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
function floorPattern(map: ChapterMap, code: TerrainCode, at?: Tile) {
  if (code === 'bw' || code === 'bx') return wardPiece(map, at)
  // A floor that gives Avoid in a pattern of its own where the map asks (`avoFloors`: Three Houses' Avo Floor apart from its Cover).
  const kind = map.avoFloors && code === 'b9' ? 'avo' : code === 'bp' ? 'def2' : code === 'bq' ? 'res' : code === 'hf' ? 'heal' : 'def'
  const base = [...map.id].reduce((n, ch) => n + ch.charCodeAt(0), 0)
  const step = { def: 0, def2: 2, res: 4, heal: 0, avo: 0 }[kind]
  return FLOOR_PATTERNS[kind][(base + step) % FLOOR_PATTERNS[kind].length]
}

/** A magic floor's or seal's piece of the sigil pattern (Thracia 776's): its place in its sigil's box, the floors and seals joined
 * corner to corner (a ring round its seal, or a block), a-c its top row, d-f its middle, g-i its bottom; the middle repeats where a
 * sigil is wider or taller than three. Engage's Fell sigils, blocks of three by three, take the same pattern (the user, in the game,
 * 2026-11-27: Fell Xenologue 6's, "replace the 3x3 ground structures with the sigils from the early games"). */
function wardPiece(map: ChapterMap, at?: Tile) {
  if (!at) return FLOOR_PATTERNS.ward[4]
  const fell = codeAt(map, at) === 'tx'
  const ward = (t: Tile) => (fell ? codeAt(map, t) === 'tx' : codeAt(map, t) === 'bw' || codeAt(map, t) === 'bx')
  const seen = new Set<string>()
  const todo: Tile[] = [at]
  let [x0, x1, y0, y1] = [at[0], at[0], at[1], at[1]]
  while (todo.length) {
    const t = todo.pop()!
    if (seen.has(tileKey(t)) || !ward(t)) continue
    seen.add(tileKey(t))
    ;[x0, x1, y0, y1] = [Math.min(x0, t[0]), Math.max(x1, t[0]), Math.min(y0, t[1]), Math.max(y1, t[1])]
    for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) if (dx || dy) todo.push([t[0] + dx, t[1] + dy])
  }
  const col = at[0] === x0 ? 0 : at[0] === x1 ? 2 : 1
  const row = at[1] === y1 ? 0 : at[1] === y0 ? 2 : 1
  return FLOOR_PATTERNS.ward[row * 3 + col]
}

/** An altar's piece: a block of altar tiles three by three or more is one dais, each tile its piece by its place (the middle repeats
 * where it's bigger: Awakening's Premonition, the user: one picture, not nine altars); a smaller one an altar on each tile. */
function altarPiece(map: ChapterMap, at: Tile): Sprite {
  const altar = (t: Tile) => codeAt(map, t) === 'wa' && /^altar$/i.test(terrainName(map, t))
  const seen = new Set<string>()
  const todo: Tile[] = [at]
  let [x0, x1, y0, y1] = [at[0], at[0], at[1], at[1]]
  while (todo.length) {
    const t = todo.pop()!
    if (seen.has(tileKey(t)) || !altar(t)) continue
    seen.add(tileKey(t))
    ;[x0, x1, y0, y1] = [Math.min(x0, t[0]), Math.max(x1, t[0]), Math.min(y0, t[1]), Math.max(y1, t[1])]
    todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
  }
  if (x1 - x0 < 2 || y1 - y0 < 2 || seen.size !== (x1 - x0 + 1) * (y1 - y0 + 1)) return ALTAR
  const col = at[0] === x0 ? 0 : at[0] === x1 ? 2 : 1
  const row = at[1] === y1 ? 0 : at[1] === y0 ? 2 : 1
  return ALTAR_PIECES['abcdefghi'[row * 3 + col] as keyof typeof ALTAR_PIECES]
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
/** The pieces a two-tile village is drawn with: the DS games' walled compound of houses, as they draw it, else the older games' small
 * house with its low wall (both the user's calls). */
const villagePieces = (map: ChapterMap) => (map.walledVillages ? WALLED_VILLAGE : VILLAGE_HOUSE)
/** A village's yard drawn whole (`va`-`vi`) on a map of walled villages: the DS games' walled compound, its piece by its place (Awakening's
 * DLC's and paralogues' compounds, the zoomed-out villages: the user's call, 2026-11-26, drawn as Shadow Dragon's and New Mystery's). */
const COMPOUND_PLACE = {
  a: 'leftTop', b: 'middleTop', c: 'rightTop', d: 'leftTop', e: 'middleTop', f: 'rightTop', g: 'leftFront', h: 'middleFront', i: 'rightFront',
} as const
const compoundPiece = (map: ChapterMap, code: TerrainCode): Sprite | undefined =>
  map.walledVillages && /^v[a-i]$/.test(code) ? WALLED_VILLAGE[COMPOUND_PLACE[code[1] as keyof typeof COMPOUND_PLACE]] : undefined

function twoTileVillage(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  // Its building over it is a village building (Shadow Dragon and the Blade of Light's, Mystery of the Emblem's) or a village's houses
  // (their remakes': a lone tile of them, the user: a two-tile village there too).
  const top = (c: TerrainCode | undefined) => c === 'w2' || c === 'w8'
  if (top(code) && codeAt(map, [x, y - 1]) === 'oc' && codeAt(map, [x, y + 1]) !== 'w8') return villagePieces(map).middleTop
  if (code === 'oc' && top(codeAt(map, [x, y + 1])) && codeAt(map, [x, y + 2]) !== 'w8') return villagePieces(map).middleFront
  if (code === 'od' && codeAt(map, [x, y - 1]) === 'od') return RUINED_VILLAGE_TOP
  if (code === 'od' && codeAt(map, [x, y + 1]) === 'od') return RUINED_VILLAGE_FRONT
  // Its houses over a village destroyed before the battle (its tile rubble: the DS games' MS_TER_DESTROYVILLAGE): in ruins too
  // (New Mystery's Paralogue 5: the user).
  if (top(code) && codeAt(map, [x, y - 1]) === 'tm') return RUINED_VILLAGE_TOP
  if (code === 'tm' && top(codeAt(map, [x, y + 1]))) return RUINED_VILLAGE_FRONT
  return undefined
}

/** The wings a village of two tiles has on the grass either side (the game draws the village three tiles wide: the user's call), for
 * a tile of that grass, which stays grassland. */
function villageYardPiece(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  // On its grass, its ground drawn as the art shows it (dirt, paving: the DS games', the user, villages chopped where they stood), or
  // on the walls the game files beside it there (Mystery of the Emblem's Book 2 Chapter 5: the user, house tiles).
  if (code !== 'tv' && code !== 't0' && code !== 'w0' && code !== 'w2' && !/^g[a-k]$/.test(code ?? '')) return undefined
  const P = villagePieces(map)
  const right = twoTileVillage(map, [x + 1, y])
  if (right === P.middleTop) return P.leftTop
  if (right === P.middleFront) return P.leftFront
  const left = twoTileVillage(map, [x - 1, y])
  if (left === P.middleTop) return P.rightTop
  if (left === P.middleFront) return P.rightFront
  return undefined
}

/** A castle one tile tall over its gate (the DS games'), drawn as they draw it: a castle three tiles by three, its row the middle, its
 * top on the open ground above and its lower corners on the ground either side of the gate (New Mystery's Chronicles 2: the user, it
 * was too small). Only where all three tiles above are open ground in the map: else its row stays towers either side of its keep. */
const OPEN_GROUND = (c: TerrainCode | undefined) => !!c && !WATER_CODES.has(c) && !/^[wcv]/.test(c) && !/^[bo]/.test(c)
function shortCastleRow(map: ChapterMap, [x, y]: Tile): 0 | 1 | 2 | undefined {
  const code = codeAt(map, [x, y])
  if (!isPiece(code) || isPiece(codeAt(map, [x, y + 1])) || isPiece(codeAt(map, [x, y - 1]))) return undefined
  const left = isPiece(codeAt(map, [x - 1, y])), right = isPiece(codeAt(map, [x + 1, y]))
  const place = !left ? 0 : !right ? 2 : 1
  const x0 = x - place
  if (isPiece(codeAt(map, [x0 - 1, y])) || isPiece(codeAt(map, [x0 + 3, y])) || !isPiece(codeAt(map, [x0 + 2, y]))) return undefined
  for (let dx = 0; dx < 3; dx++) {
    if (!OPEN_GROUND(codeAt(map, [x0 + dx, y + 1])) || isPiece(codeAt(map, [x0 + dx, y - 1]))) return undefined
  }
  if (codeAt(map, [x0 + 1, y - 1]) !== 'bd') return undefined
  return place
}

/** A short castle's top on the ground above it, and its corners beside its gate (shortCastleRow). */
function castleWing(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  if (!OPEN_GROUND(codeAt(map, [x, y]))) return undefined
  const below = shortCastleRow(map, [x, y - 1])
  if (below !== undefined) return [CASTLE_PIECES.a, CASTLE_PIECES.b, CASTLE_PIECES.c][below]
  const above = shortCastleRow(map, [x, y + 1])
  if (above === 0) return CASTLE_PIECES.g
  if (above === 2) return CASTLE_PIECES.i
  return undefined
}

/** A castle's gate row under its pieces (Mystery of the Emblem's: the castle tile you seize between its flanks, which keep their own
 * stats): drawn as the castle's front, so the castle stands whole (the user: it was missing tiles). */
const GATE_ROW = new Set<TerrainCode>(['ou', 'ol'])
const isPiece = (c: TerrainCode | undefined) => !!c && /^c[a-i]$/.test(c)
function castleFront(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  if (!code || !GATE_ROW.has(code) || !isPiece(codeAt(map, [x, y + 1]))) return undefined
  // A castle tile with the building's pieces below it too is its keep (Genealogy of the Holy War's castles, drawn whole over the
  // ramparts round them, their gate two tiles below).
  if (isPiece(codeAt(map, [x, y - 1]))) return code === 'ol' ? CASTLE_PIECES.e : undefined
  if (code === 'ol') return CASTLE_PIECES.h
  const inRow = (dx: number) => GATE_ROW.has(codeAt(map, [x + dx, y]) as TerrainCode) && isPiece(codeAt(map, [x + dx, y + 1]))
  return !inRow(-1) ? CASTLE_PIECES.g : !inRow(1) ? CASTLE_PIECES.i : CASTLE_PIECES.h
}

/** Thracia 776's buildings entered by a gate, drawn whole: each family's pieces. */
const GATED_BUILDINGS: Record<string, Record<'a' | 'b' | 'c' | 'd' | 'e' | 'f' | 'g' | 'h' | 'i', Sprite>> = {
  j: WOOD_FORT_PIECES, l: HALL_PIECES, m: KEEP_PIECES,
  // A castle round a gate in the middle of its front (The Binding Blade's Chapter 23's gatehouse).
  c: CASTLE_PIECES,
}
/** The gate in the front of one of those buildings (its pieces above it and either side): drawn as the building's door, so the
 * building stands whole, as Mystery of the Emblem's castle gates are; the tile keeps the gate's numbers. */
function buildingDoor(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  if (codeAt(map, [x, y]) !== 'bd' && codeAt(map, [x, y]) !== 'bv') return undefined
  const above = codeAt(map, [x, y + 1]) ?? ''
  const pieces = /^[jlm][a-i]$/.test(above) ? GATED_BUILDINGS[above[0]] : undefined
  if (!pieces) return undefined
  const same = (t: Tile) => (codeAt(map, t) ?? '')[0] === above[0] && PIECE.test(codeAt(map, t) ?? '')
  return same([x - 1, y]) && same([x + 1, y]) ? pieces.h : undefined
}

/** An entrance a village's lot or a house's front holds: a village (open or closed), a house, a shop, an arena, a church; Thracia
 * 776's house tiles, which units stand in (`oe`). */
const ENTRANCES = new Set<TerrainCode>(['oc', 'od', 'ot', 'oe', 'om', 'on', 'oo', 'op', 'oj', 'oq'])
type ShopKind = keyof typeof SHOP_ROOF
const SHOP_KIND: Partial<Record<TerrainCode, ShopKind>> = { om: 'armory', on: 'vendor', op: 'secret' }
/** A town house's roof pieces in each shop's colours, and with its sign hung over the door: the signs on a light board, or on a dark
 * one (`clearSigns`: every game's, as each takes it up). */
const shopRoofs = (signs: Record<ShopKind, Sprite>) =>
  Object.fromEntries(
    (Object.keys(SHOP_ROOF) as ShopKind[]).map((k) => [
      k,
      Object.fromEntries(
        (['a', 'b', 'c'] as const).flatMap((p) => {
          const roof = recoloured(HOUSE_PIECES[p], SHOP_ROOF[k])
          return [[p, roof], [`${p}-sign`, layered(roof, signs[k])]]
        }),
      ),
    ]),
  ) as Record<ShopKind, Record<string, Sprite>>
const SHOP_ROOFS = shopRoofs(SHOP_SIGN)
const SHOP_ROOFS_CLEAR = shopRoofs(SHOP_SIGN_CLEAR)
/** A shop standing alone on its tile on a zoomed-in map: a small house in its colours, its sign on its roof. */
const SMALL_SHOPS = Object.fromEntries(
  (Object.keys(SHOP_ROOF) as ShopKind[]).map((k) => [k, layered(recoloured(SMALL_SHOP, SHOP_ROOF[k]), SMALL_SHOP_SIGN[k])]),
) as Record<ShopKind, Sprite>
/** A lot's tile with no building on it: its yard alone. */
const YARD: Sprite = { palette: {}, rows: Array(10).fill('..........') }
const BUILT = new WeakMap<ChapterMap, Map<string, Sprite>>()
/**
 * The buildings a map's villages and houses are drawn as, by tile (the user's calls, the zoomed-in maps: a village drawn as the house,
 * shop or arena the game draws in it, not a yard of little houses; a house's door open where there's something to visit, shut where
 * there isn't, and no door mat):
 * - The GBA games' village lots on a zoomed-in map (`villageBuildings`): a lot's pieces and the entrances in them, its columns shared
 *   out among its entrances (each to the nearest), each entrance's columns a building from the lot's top down to the entrance's row: a
 *   house's roof along its top, its front with the door on the entrance; a shop's roof in its colour, its sign over the door; an arena
 *   a colosseum. A lot with no entrance is a house no one enters, its door shut. A zoomed-out map's (`zoomedOut`) stay fenced yards of
 *   little houses, each building alone on a tile its icon; on either, a lot round a castle gate is the castle drawn whole.
 * - A town house with an entrance in its front row (Thracia 776's: its house tile, a village, a shop), its door there, its roof a
 *   shop's where it's a shop.
 */
function buildings(map: ChapterMap): Map<string, Sprite> {
  const cached = BUILT.get(map)
  if (cached) return cached
  const out = new Map<string, Sprite>()
  BUILT.set(map, out)
  const visits = visitable(map)
  const at = (x: number, y: number) => (x >= 1 && y >= 1 && x <= map.width && y <= map.height ? terrainAt(map, [x, y]) : undefined)
  const roofs = map.clearSigns ? SHOP_ROOFS_CLEAR : SHOP_ROOFS
  // Open where there's something to visit: a shop, a visit, a supply depot (Thracia 776's: its convoy).
  const doorOf = (code: TerrainCode, t: Tile, side: '' | '-left' | '-right') =>
    HOUSE_DOOR[`${SHOP_KIND[code] || code === 'oq' || visits.has(tileKey(t)) ? 'open' : 'shut'}${side}` as keyof typeof HOUSE_DOOR]
  const build = (tiles: Tile[], door: Tile, code: TerrainCode | undefined) => {
    const xs = tiles.map((t) => t[0])
    const [x0, x1, top] = [Math.min(...xs), Math.max(...xs), Math.max(...tiles.map((t) => t[1]))]
    const shop = code && SHOP_KIND[code]
    for (const [x, y] of tiles) {
      const col = x === x0 && x !== x1 ? 0 : x === x1 && x !== x0 ? 2 : 1
      const row = y === door[1] ? 2 : y === top ? 0 : 1
      const place = 'abcdefghi'[row * 3 + col] as keyof typeof HOUSE_PIECES
      out.set(
        tileKey([x, y]),
        code === 'oo' ? ARENA_PIECES[(row === 2 ? 'ghi' : 'abc')[col] as keyof typeof ARENA_PIECES]
        : x === door[0] && y === door[1]
          ? (code ? doorOf(code, door, col === 0 ? '-left' : col === 2 ? '-right' : '')
            : HOUSE_DOOR[`shut${col === 0 ? '-left' : col === 2 ? '-right' : ''}` as keyof typeof HOUSE_DOOR])
          : row === 0 && shop ? roofs[shop][x === door[0] ? `${place}-sign` : place]
            // A front's middle away from the door: a window or a blank wall, not another door.
            : place === 'h' ? [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(x, y) % 2]
              : HOUSE_PIECES[place],
      )
    }
  }
  if (map.villageBuildings || map.zoomedOut) {
    const lotPiece = (c?: TerrainCode) => !!c && /^v[a-i]$/.test(c)
    const seen = new Set<string>()
    for (let y = 1; y <= map.height; y++)
      for (let x = 1; x <= map.width; x++) {
        if (seen.has(tileKey([x, y])) || !lotPiece(at(x, y))) continue
        // The lot: its pieces and the entrances beside them (an entrance leads no further: a shop by another lot is that lot's).
        const lot: Tile[] = []
        const todo: Tile[] = [[x, y]]
        while (todo.length) {
          const t = todo.pop()!
          const c = at(t[0], t[1])
          if (seen.has(tileKey(t)) || !(lotPiece(c) || (c && ENTRANCES.has(c)))) continue
          seen.add(tileKey(t))
          lot.push(t)
          if (lotPiece(c)) for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) todo.push([t[0] + dx, t[1] + dy])
        }
        // A lot round a castle gate, with no house's or shop's entrance (The Sacred Stones' Eirika 12: the user, not a village): a
        // castle drawn whole round its gate, its walls the village's (fliers cross them).
        const gate = lot.flatMap(([lx, ly]) => ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).map(([dx, dy]): Tile => [lx + dx, ly + dy]))
          .find(([gx, gy]) => at(gx, gy) === 'bd' || at(gx, gy) === 'bv')
        if (gate && !lot.some(([lx, ly]) => ENTRANCES.has(at(lx, ly)!))) {
          const xs = lot.map((t) => t[0])
          const [x0, x1, top] = [Math.min(...xs), Math.max(...xs), Math.max(...lot.map((t) => t[1]))]
          for (const [lx, ly] of [...lot, gate]) {
            const col = lx === x0 ? 0 : lx === x1 ? 2 : 1
            const row = ly === gate[1] ? 2 : ly === top ? 0 : 1
            out.set(tileKey([lx, ly]), CASTLE_PIECES['abcdefghi'[row * 3 + col] as keyof typeof CASTLE_PIECES])
          }
          continue
        }
        // A zoomed-out map's village stays its fenced yard of little houses (the user: The Sacred Stones' Chapter 2).
        if (map.zoomedOut) continue
        // Its entrances by column (the lowest in each), else one door, shut, in the middle of its front.
        const doors = new Map<number, Tile>()
        for (const t of lot) if (ENTRANCES.has(at(t[0], t[1])!) && (!doors.has(t[0]) || t[1] < doors.get(t[0])![1])) doors.set(t[0], t)
        if (!doors.size) {
          const xs = lot.map((t) => t[0])
          const mid = Math.round((Math.min(...xs) + Math.max(...xs)) / 2)
          doors.set(mid, [mid, Math.min(...lot.filter((t) => t[0] === mid).map((t) => t[1]))])
        }
        const cols = [...doors.keys()].sort((a, b) => a - b)
        // A lot four columns wide with one entrance: two houses two wide side by side, the entrance's with its door, the other's shut
        // (The Sacred Stones' Chapter 5: the user, it looks more natural than a house and a sliver).
        const [lx0, lx1] = [Math.min(...lot.map((t) => t[0])), Math.max(...lot.map((t) => t[0]))]
        if (lx1 - lx0 === 3 && cols.length === 1 && lot.some((t) => ENTRANCES.has(at(t[0], t[1])!))) {
          const door = doors.get(cols[0])!
          const code = at(door[0], door[1])
          for (const a of [lx0, lx0 + 2]) {
            const half = lot.filter((t) => t[0] >= a && t[0] <= a + 1 && !(ENTRANCES.has(at(t[0], t[1])!) && t[0] !== door[0]))
            if (door[0] >= a && door[0] <= a + 1) build(half.filter((t) => t[1] >= door[1]), door, code)
            else build(half, [a, Math.min(...half.filter((t) => t[0] === a).map((t) => t[1]))], undefined)
          }
          for (const t of lot) if (!out.has(tileKey(t))) out.set(tileKey(t), YARD)
          continue
        }
        const owner = (cx: number) => cols.reduce((best, c) => (Math.abs(c - cx) < Math.abs(best - cx) ? c : best))
        // Each entrance's building three columns wide at most, round its door.
        for (const c of cols) {
          const door = doors.get(c)!
          const code = at(door[0], door[1])
          build(lot.filter((t) => owner(t[0]) === c && Math.abs(t[0] - c) <= 1 && t[1] >= door[1]), door,
            code && ENTRANCES.has(code) ? code : undefined)
        }
        // The columns further from every entrance are houses of their own no one enters, their doors shut (The Sacred Stones'
        // Chapter 5's long lot: a house, then two more).
        const rest = [...new Set(lot.map((t) => t[0]))].filter((cx) => Math.abs(cx - owner(cx)) > 1).sort((a, b) => a - b)
        for (let i = 0; i < rest.length; ) {
          let j = i
          while (j + 1 < rest.length && rest[j + 1] === rest[j] + 1 && j - i < 2) j++
          const run = rest.slice(i, j + 1)
          const tiles = lot.filter((t) => run.includes(t[0]))
          const mid = run[Math.floor((run.length - 1) / 2)]
          build(tiles, [mid, Math.min(...tiles.filter((t) => t[0] === mid).map((t) => t[1]))], undefined)
          i = j + 1
        }
        for (const t of lot) if (!out.has(tileKey(t))) out.set(tileKey(t), YARD)
      }
  }
  // A shop standing alone on its tile there (no lot or house round it): a small house of its kind, an arena its colosseum.
  if (map.villageBuildings)
    for (let y = 1; y <= map.height; y++)
      for (let x = 1; x <= map.width; x++) {
        const code = at(x, y)
        const alone = ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).every(([dx, dy]) => !/^[vr][a-i]$/.test(at(x + dx, y + dy) ?? ''))
        if (!code || out.has(tileKey([x, y])) || !alone) continue
        // A shop on a ship's deck is its icon, on its plaque (`deckShops`: the user, houses make no sense on boats).
        if (map.deckShops && ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => at(x + dx, y + dy) === 't3')) continue
        if (SHOP_KIND[code]) out.set(tileKey([x, y]), SMALL_SHOPS[SHOP_KIND[code]!])
        else if (code === 'oo') out.set(tileKey([x, y]), ARENA)
      }
  // A town house with entrances in its front row (its roof over it, or the map's edge: Thracia 776's): its front from its left end
  // (`rg`) to its right (`ri`), each column its nearest entrance's, a door on each entrance, a window or a blank wall between them, and
  // each shop's roof over its columns in its colour.
  const inFront = (c?: TerrainCode) => !!c && (/^r[g-i]$/.test(c) || ENTRANCES.has(c))
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      const code = at(x, y)
      if (!code || !ENTRANCES.has(code) || out.has(tileKey([x, y]))) continue
      if (!/^r[a-f]$/.test(at(x, y + 1) ?? '') && !(y === map.height && (/^r[gh]$/.test(at(x - 1, y) ?? '') || /^r[hi]$/.test(at(x + 1, y) ?? ''))))
        continue
      let [xl, xr] = [x, x]
      // Its own front: from its left end to its right, never on into the house beside it.
      while (inFront(at(xl - 1, y)) && at(xl, y) !== 'rg' && at(xl - 1, y) !== 'ri') xl--
      while (inFront(at(xr + 1, y)) && at(xr, y) !== 'ri' && at(xr + 1, y) !== 'rg') xr++
      const doors: number[] = []
      for (let cx = xl; cx <= xr; cx++) if (ENTRANCES.has(at(cx, y)!)) doors.push(cx)
      const owner = (cx: number) => doors.reduce((best, d) => (Math.abs(d - cx) < Math.abs(best - cx) ? d : best))
      // On the map's top edge, its roof off the map (Thracia 776's Chapters 3 and 20): each building's bottom by its kind, so they still
      // part (the user): an arena its colosseum's arches, a supply depot its wooden front under its thatch, a shop or a house its front
      // with the roof's eaves along its top in the roof's colour.
      const edge = y === map.height
      for (let cx = xl; cx <= xr; cx++) {
        const c = at(cx, y)!
        const side = cx === xl && xr !== xl ? '-left' : cx === xr && xl !== xr ? '-right' : ''
        const own = at(owner(cx), y)!
        if (edge) {
          const front = ENTRANCES.has(c) ? doorOf(c, [cx, y], side)
            : c === 'rh' ? [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(cx, y) % 2] : TERRAIN_SPRITE[c]
          const shop = SHOP_KIND[own]
          out.set(tileKey([cx, y]), own === 'oo' ? ARENA_PIECES[cx === owner(cx) ? 'h' : cx < owner(cx) ? 'g' : 'i']
            : own === 'oq' ? layered(recoloured(front!, DEPOT_FRONT), recoloured(EAVES, DEPOT_FRONT))
              : layered(front!, shop ? recoloured(EAVES, SHOP_ROOF[shop]) : EAVES))
          continue
        }
        if (ENTRANCES.has(c)) out.set(tileKey([cx, y]), c === 'oo' ? ARENA_PIECES.h : doorOf(c, [cx, y], side))
        else if (c === 'rh') out.set(tileKey([cx, y]), [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(cx, y) % 2])
        const shop = SHOP_KIND[own]
        if (shop)
          for (let cy = y + 1; /^r[a-f]$/.test(at(cx, cy) ?? ''); cy++) {
            const r = at(cx, cy)!
            if (/^r[a-c]$/.test(r)) out.set(tileKey([cx, cy]), roofs[shop][cx === owner(cx) ? `${r[1]}-sign` : r[1]])
          }
      }
    }
  return out
}

/** A fort drawn whole with stairs up its front (Gaiden's small forts): its middle row's part ('d' and 'f' its sides, 'e' the fort in
 * the middle), which is the raised platform the stairs climb to, not a castle's walls (the user's call). */
function stairFortPart(map: ChapterMap, [x, y]: Tile): 'd' | 'e' | 'f' | undefined {
  const code = codeAt(map, [x, y])
  const middle = (cx: number) => {
    const c = codeAt(map, [cx, y])
    return (c === 'bb' || c === 'ce' || c === 'nd') && codeAt(map, [cx, y - 1]) === 'tc' && codeAt(map, [cx - 1, y]) === 'cd' && codeAt(map, [cx + 1, y]) === 'cf'
  }
  if (code === 'cd' && middle(x + 1)) return 'd'
  if (code === 'cf' && middle(x - 1)) return 'f'
  if ((code === 'bb' || code === 'ce' || code === 'nd') && middle(x)) return 'e'
  return undefined
}

/** The middle of a small stone fort (Gaiden's: the fort tile, its stairs and the floor between its corners; Echoes' supplies), which
 * stands on the fort's stone floor, not the grass outside: a tile with its pieces on two sides or more. */
const STONE_FORT_FLOOR = '#a9a79d'
function inStoneFort(map: ChapterMap, [x, y]: Tile): boolean {
  const c = codeAt(map, [x, y])
  if (!c || !(c === 'bb' || c === 'nd' || c === 'tc' || FLOOR_BONUS.has(c))) return false
  const piece = (dx: number, dy: number) => /^q[a-i]$/.test(codeAt(map, [x + dx, y + dy]) ?? '')
  return [piece(1, 0), piece(-1, 0), piece(0, 1), piece(0, -1)].filter(Boolean).length >= 2
}

/** Walls a script opens as a gate: castle walls (Genealogy of the Holy War's passes), outdoor walls and a cracked wall (Thracia 776's
 * gatehouses), fences (The Binding Blade's Chapter 19B). */
const GATE_WALLS = new Set<TerrainCode>(['w0', 'wx', 'wg', 'wj'])
/** A wall the chapter's script opens: a gate of its own (the user's calls: a gate, not the wall's bricks), by place in it: two halves
 * side by side (a middle between them where it's wider), or a gate two tiles deep, its lintel over the doors. A wall a unit can also
 * break keeps its crack. */
function rampartGate(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  // A pit a script fills or opens is still a pit, not a gate (Echoes' Duma Temple trenches: the user).
  const opens = (t: Tile) =>
    map.wallLooks?.[tileKey(t)] !== 'pit' && map.wallLooks?.[tileKey(t)] !== 'void' &&
    GATE_WALLS.has(codeAt(map, t) as TerrainCode) &&
    !map.changes.some((c) => c.trigger === 'breakable' && (c.patch ?? []).some((p) => sameTile(p.tile, t))) &&
    map.changes.some((c) => c.trigger === 'event' && (c.patch ?? []).some((p) => sameTile(p.tile, t) && p.becomes[0] !== 'w'))
  if (!opens([x, y])) return undefined
  const left = opens([x - 1, y])
  const right = opens([x + 1, y])
  if (!left && !right && opens([x, y - 1]) !== opens([x, y + 1])) return opens([x, y - 1]) ? RAMPART_GATE.top : RAMPART_GATE.bottom
  return left && right ? RAMPART_GATE.middle : right ? RAMPART_GATE.left : left ? RAMPART_GATE.right : RAMPART_GATE.alone
}

/** A drawbridge standing raised (Mystery of the Emblem's code of its own; Shadow Dragon and the Blade of Light's a river tile a key
 * lowers into a bridge): which way it crosses, 'ns' where the river runs east to west under it, else 'ew'. Lowered (previewed), it's
 * the bridge. */
function raisedBridge(map: ChapterMap, [x, y]: Tile): 'ns' | 'ew' | undefined {
  const code = codeAt(map, [x, y])
  const lowers = map.changes.some((c) => c.id.startsWith('bridge-') && sameTile(changeTile(c), [x, y]))
  if (code !== 'wo' && !(lowers && code && WATER_CODES.has(code))) return undefined
  const water = (c: TerrainCode | undefined) => !!c && (WATER_CODES.has(c) || c === 'wo')
  return water(codeAt(map, [x - 1, y])) || water(codeAt(map, [x + 1, y])) ? 'ns' : 'ew'
}

/** A tile's icon: its code's, but a mountain is the snowy peak on a snowy map (the user's call: rocky elsewhere), and a village
 * piece in a building wider or taller than 3 one of its place's variants, tile by tile (`at`: the tile, to pick by). */
/** A lone pair of stairs side by side with railings on them (the Tellius games' stairwells, one of them a goal tile at times: Path of
 * Radiance's Ch.13 hatch, its defend tile): a stairwell going down across the two tiles (the user's call), its half for a tile. */
function wideStairwell(map: ChapterMap, [x, y]: Tile): 'left' | 'right' | undefined {
  // A gangplank the game names stairs is no stairwell (`gangplanks`: Path of Radiance's Ch.11, the user).
  const stair = (t: Tile) => (codeAt(map, t) === 'tc' || codeAt(map, t) === 'bc') && !map.gangplanks?.includes(tileKey(t))
  if (!stair([x, y]) || stair([x - 1, y]) === stair([x + 1, y])) return undefined
  const a: Tile = stair([x + 1, y]) ? [x, y] : [x - 1, y]
  const b: Tile = [a[0] + 1, y]
  if (stair([a[0] - 1, y]) || stair([b[0] + 1, y]) || [a, b].some(([px]) => stair([px, y + 1]) || stair([px, y - 1]))) return undefined
  if (codeAt(map, a) !== 'tc' && codeAt(map, b) !== 'tc') return undefined
  return (map.walls ?? []).some((w) => sameTile(w.tile, a) || sameTile(w.tile, b)) ? (sameTile(a, [x, y]) ? 'left' : 'right') : undefined
}

/** Sacae's dwellings drawn as yurts (`yurts`: the user's call): a house on its tile a little yurt; a castle drawn whole a chieftain's great
 * yurt, each tile its piece by its place in the castle's block, its gate the great yurt's steps. */
function yurtPiece(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const code = codeAt(map, [x, y])
  if (code === 'ot') return YURT_HOUSE
  const part = (t: Tile) => { const c = codeAt(map, t); return !!c && (/^c[a-i]$/.test(c) || c === 'bd') }
  if (!part([x, y])) return undefined
  let [x0, y1] = [x, y]
  const seen = new Set<string>()
  const todo: Tile[] = [[x, y]]
  while (todo.length) {
    const t = todo.pop()!
    if (seen.has(tileKey(t)) || !part(t)) continue
    seen.add(tileKey(t))
    x0 = Math.min(x0, t[0])
    y1 = Math.max(y1, t[1])
    todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
  }
  const [row, col] = [y1 - y, x - x0]
  if (seen.size < 3 || row > 2 || col > 2) return undefined
  return YURT_FORT['abcdefghi'[row * 3 + col] as keyof typeof YURT_FORT]
}

/** A ledge's chevrons turned to point up it, toward its higher ground (`ledgeUp`; LEDGE itself points down, south). */
const LEDGE_TURNED = new Map<'n' | 's' | 'e' | 'w', Sprite>()
function ledgeTurned(dir: 'n' | 's' | 'e' | 'w'): Sprite {
  let s = LEDGE_TURNED.get(dir)
  if (!s) {
    const rows = LEDGE.rows
    const n = rows.length
    const at = (r: number, c: number) => rows[r][c]
    // Down to the left is a quarter turn clockwise, to the right one anticlockwise, up a half turn.
    const cell = (r: number, c: number) =>
      dir === 'w' ? at(n - 1 - c, r) : dir === 'e' ? at(c, n - 1 - r) : dir === 'n' ? at(n - 1 - r, n - 1 - c) : at(r, c)
    s = { ...LEDGE, rows: rows.map((_, r) => rows.map((__, c) => cell(r, c)).join('')) }
    LEDGE_TURNED.set(dir, s)
  }
  return s
}

/** A boat's bow pointing the way it goes (`boatEnds`; BOAT_BOW itself points east, its deck to the west). */
const BOW_TURNED = new Map<'n' | 's' | 'e' | 'w', Sprite>()
function bowTurned(dir: 'n' | 's' | 'e' | 'w'): Sprite {
  let s = BOW_TURNED.get(dir)
  if (!s) {
    const rows = BOAT_BOW.rows
    const n = rows.length
    const at = (r: number, c: number) => rows[r][c]
    // North a quarter turn anticlockwise, south one clockwise, west left for right.
    const cell = (r: number, c: number) =>
      dir === 'n' ? at(c, n - 1 - r) : dir === 's' ? at(n - 1 - c, r) : dir === 'w' ? at(r, n - 1 - c) : at(r, c)
    s = { ...BOAT_BOW, rows: rows.map((_, r) => rows.map((__, c) => cell(r, c)).join('')) }
    BOW_TURNED.set(dir, s)
  }
  return s
}

/** A house's sprite with its roof grey (`greyRoofs`). */
const GREY_ROOFED = new WeakMap<Sprite, Sprite>()
function greyRoofed(s: Sprite): Sprite {
  let g = GREY_ROOFED.get(s)
  if (!g) GREY_ROOFED.set(s, (g = { ...s, palette: { ...s.palette, r: '#7d7c76', R: '#5d5c57', l: '#9d9c95' } }))
  return g
}

/** A sprite turned round, left for right. */
const FLIPPED = new WeakMap<Sprite, Sprite>()
function flipped(s: Sprite): Sprite {
  let f = FLIPPED.get(s)
  if (!f) FLIPPED.set(s, (f = { ...s, rows: s.rows.map((r) => [...r].reverse().join('')) }))
  return f
}
/** A tile's icon or building piece; in a block the user turned round (`mirror`), its partner's across the block, flipped. */
function spriteOf(map: ChapterMap, code: TerrainCode, at?: Tile): Sprite | undefined {
  // A town's houses roofed grey where its art paints them so (`greyRoofs`: Fates' Paralogue 20, the user).
  if (map.greyRoofs && /^r[a-r]$/.test(code)) {
    const s = tileSprite(map, code, at)
    return s && greyRoofed(s)
  }
  const box = at && map.mirror?.find(([x0, x1, y0, y1]) => at[0] >= x0 && at[0] <= x1 && at[1] >= y0 && at[1] <= y1)
  if (!at || !box) return tileSprite(map, code, at)
  const partner: Tile = [box[0] + box[1] - at[0], at[1]]
  const s = tileSprite(map, terrainAt(map, partner), partner)
  return s && flipped(s)
}
function tileSprite(map: ChapterMap, code: TerrainCode, at?: Tile) {
  // Muck drawn as a bog, no icon over its mud (`muckAsBog`: Fates' Boo Camp, the user).
  if (code === 'db' && map.muckAsBog) return undefined
  const compound = compoundPiece(map, code)
  if (compound) return compound
  // A tile whose mark the game doesn't draw (`bareTiles`: a Fates challenge's spent village with no house over it).
  if (at && map.bareTiles?.includes(tileKey(at))) return undefined
  // Bones lying in a block, one great bone (`boneBlocks`: Awakening's Chapter 10, the user).
  if (at && code === 'o2' && map.boneBlocks) {
    const bone = (dx: number, dy: number) => codeAt(map, [at[0] + dx, at[1] + dy]) === 'o2'
    const [u, d, l, r] = [bone(0, 1), bone(0, -1), bone(-1, 0), bone(1, 0)]
    if (u || d || l || r) return bonePiece(!u, !l, !r, !d, boneAxis(map).get(tileKey(at)) ?? 'ns', variety(at[0], at[1]))
  }
  // A ledge's chevrons point up it (`ledgeUp`: Radiant Dawn's, the user).
  const up = at && code === 'bg' ? map.ledgeUp?.[tileKey(at)] : undefined
  if (up) return ledgeTurned(up)
  // A tile the game names an altar (Mystery of the Emblem's, New Mystery's): the altar every game's is drawn as (the user's call).
  if (code === 'oi' && /altar/i.test(at ? terrainName(map, at) : terrainInfo(map, 'oi')?.name ?? '')) return ALTAR
  // Rocks where the game's bones lie (Awakening's Chapter 9), barrels on a ship's side (The Sacred Stones' Chapter 9): the decor
  // draws them, not the tile's own mark.
  if (at && REPLACES_ICON.has(map.decor?.[tileKey(at)] ?? '')) return undefined
  // A village's or house's building, drawn whole (buildings).
  const built = at && buildings(map).get(tileKey(at))
  if (built) return built
  const yurt = at && map.yurts && yurtPiece(map, at)
  if (yurt) return yurt
  const well = at && wideStairwell(map, at)
  if (well) return WIDE_STAIRWELL[well]
  // A tent turned side-on, its door in its side (tentDoors, by the tent's middle tile).
  if (at && map.tentDoors && /^u[a-i]$/.test(code)) {
    const k = 'abcdefghi'.indexOf(code[1])
    const side = map.tentDoors[tileKey([at[0] + 1 - (k % 3), at[1] - 1 + Math.floor(k / 3)])]
    if (side) return TENT_SIDE[side][code[1] as keyof typeof TENT_PIECES]
  }
  if ((code === 'bm' || code === 'b7') && snowy(map)) return SNOW_PEAK
  // A peak keeps its snowcaps only on a snowy map, as a mountain is snowy only there (the user, Melkaen Coast's rock).
  if (code === 'bu' && !snowy(map)) return ROCK_PEAK
  if (at) {
    // A barricade of sandbags and a pillar standing alone (Radiant Dawn's), drawn as themselves.
    const look = wallLook(map, at)
    if (look === 'sandbags') return SANDBAG_WALL
    if (look === 'pillar') return PILLAR_TOP
    const village = twoTileVillage(map, at)
    if (village) return village
    const front = castleFront(map, at)
    if (front) return front
    const door = buildingDoor(map, at)
    if (door) return door
    const fort = stairFortPart(map, at)
    if (fort === 'd' || fort === 'f') return STAIR_FORT_PIECES[fort]
    // A castle one tile tall over its gate with open ground above it (the DS games'): the middle of a castle three tiles by three,
    // its gate the castle's front (castleWing draws its top and corners on the ground round it).
    const short = shortCastleRow(map, at)
    if (short !== undefined) return [CASTLE_PIECES.d, CASTLE_PIECES.e, CASTLE_PIECES.f][short]
    if (code === 'bd' && shortCastleRow(map, [at[0], at[1] + 1]) === 1) return CASTLE_PIECES.h
    // A castle one tile tall (the DS games', its gate below): towers either side of its keep, not a strip of a taller castle's.
    if (/^c[a-i]$/.test(code) && !isPiece(codeAt(map, [at[0], at[1] + 1])) && !isPiece(codeAt(map, [at[0], at[1] - 1])))
      return !isPiece(codeAt(map, [at[0] - 1, at[1]])) ? CASTLE_ROW.left : !isPiece(codeAt(map, [at[0] + 1, at[1]])) ? CASTLE_ROW.right : CASTLE_ROW.middle
  }
  // A snowy map's trees (Mystery of the Emblem's, its grassland snow) are snowy, as its art draws them.
  if (code === 'ba' && map.fills?.tv && snowy(map)) return SNOW_TREE
  // A valley its map draws as lava (the GBA games' volcanoes: every one of theirs) is molten, as Radiant Dawn's lava is (the user's call).
  if (code === 'wn' && molten(map)) return LAVA_POOL
  // Rubble a game names as something else is drawn as it (Fates': cherry trees, graves, stones, barrels: the user, its cherry trees
  // came out as ruins).
  // Doors side by side are one gate two or three tiles wide, and doors one over the other a gate two deep (the user's calls: Three
  // Houses' and Engage's gates, The Sacred Stones' and Awakening's), its halves either side, not a row of little doors.
  if (at && code === 'ob') {
    const door = (dx: number, dy: number) => codeAt(map, [at[0] + dx, at[1] + dy]) === 'ob'
    const [l, r, u, d] = [door(-1, 0), door(1, 0), door(0, 1), door(0, -1)]
    if (l || r) return l && r ? RAMPART_GATE.middle : r ? RAMPART_GATE.left : RAMPART_GATE.right
    if (u !== d) return d ? RAMPART_GATE.top : RAMPART_GATE.bottom
  }
  // A pillar among a ship's decks is its mast (Echoes' ships name them pillars: the user, boat fixes); a fort the game names supplies
  // its crates, an orange tree a tree; a castle tile the game names a broken bridge the bridge's planks (Echoes').
  // A bridge's railing, filed with its walls (Echoes' Act 3 bridges, the user): the stone bridge's side.
  if (at && code[0] === 'w' && /railing/i.test(terrainName(map, at))) return BRIDGE_SIDE
  if (at && (code === 'wa' || code === 'bb' || code === 'b0' || code === 'wg')) {
    const name = terrainName(map, at)
    // An altar no unit steps onto, filed with the walls (Awakening's dream map), is drawn as one; a mast the game names (Engage's), a mast.
    if (code === 'wa' && /^altar$/i.test(name)) return altarPiece(map, at)
    if (code === 'wa' && /^mast$/i.test(name)) return MAST
    // Supplies the game files with its fences and partitions (Awakening's ships' cargo) are crates; a block of them one heap (the user:
    // a 2x2 of boxes, Chapters 12 and 15).
    if (code === 'wg' && /suppl/i.test(name)) return crateOrHeap(map, at, CRATES)
    if (code === 'wa' && /pillar/i.test(name) && [[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => codeAt(map, [at[0] + dx, at[1] + dy]) === 't3'))
      return MAST
    // Supplies are cargo on a ship (crates); elsewhere a fort in all but looks (Echoes' Duma Temple's green sigils, the user).
    if (code === 'bb' && /suppl/i.test(name) && hasDeck(map)) return crateOrHeap(map, at, CRATES)
    if (code === 'bb' && /tree/i.test(name)) return TREE
    if (code === 'b0' && /bridge/i.test(name)) return BRIDGE_PLANKS
  }
  // Supplies that work as a fort (Echoes' own code for them): on a ship's deck its cargo, crates marked with the supplies' green +
  // (the user: so they read as supplies); elsewhere the supplies.
  if (at && code === 'nd' && shipCargo(map, at)) {
    const crates = crateOrHeap(map, at, SUPPLY_CRATES)
    return crates === SUPPLY_CRATES ? crates : supplyMarked(crates, 5, 5)
  }
  // What plays as a pillar but is a thicket or coral (Echoes' one terrain for all three: the user's review), drawn as it.
  if (at && code === 'b3') {
    const name = terrainName(map, at)
    if (/thicket/i.test(name)) return THICKET
    if (/coral/i.test(name)) return CORAL
  }
  if (at && code === 'wj') {
    const name = terrainName(map, at)
    if (lowWall(map, at)) return undefined
    // Rubble across a bridge over water (Engage's Crux of Fate: the user, a ruined bridge) is the bridge broken: its planks.
    const along = (dx: number) => ['tb', 't8', 'wj'].includes(codeAt(map, [at[0] + dx, at[1]]) ?? '')
    const water = (dy: number) => WATER_CODES.has(codeAt(map, [at[0], at[1] + dy]) as TerrainCode)
    if (along(-1) && along(1) && water(1) && water(-1)) return BRIDGE_PLANKS
    if (/cherry/i.test(name)) return CHERRY_TREE
    if (/grave/i.test(name)) return GRAVE
    // A stone or rock the game names so a heap of a few stones: a round boulder is only a rock units push (every game: the user,
    // 2026-11-27, "if its not a pushable one it shouldnt be a round stone").
    if (/stone|rock/i.test(name)) return STONE_PILE
    if (/barrel/i.test(name)) return BARREL
    if (/cracked wall/i.test(name)) return CRACKED_WALL
    // Rubble laid in a line three tiles or more is a ruin's wall (Engage's ruined walls and mazes), but on a map whose rubble is all
    // rubble (`plainRubble`: Fell Xenologue 5's, the user); the rest is rubble, its three small rocks (the user's call).
    if (/ruin/i.test(name) || (!map.plainRubble && inLine(map, at, 'wj', 3))) return RUINS
  }
  // A house in ruins (a Fates challenge's, its village spent; Engage's ruined villages) is a ruin's walls; its village before it no
  // house but rubble-strewn ground (GroundDetail's stones).
  if (at && map.ruins?.includes(tileKey(at))) {
    if (!(/^r[a-r]$/.test(code) || code === 'oe' || code[0] === 'w')) return undefined
    // A map's ruins varied tile to tile (`variedRuins`: Three Houses', the user): a wall's stub among fallen drums, blocks and arches.
    return map.variedRuins ? [RUINS, ...RUBBLE_VARIANTS][variety(at[0], at[1])] : RUINS
  }
  if (at && map.rooftops && roofAt(map, at)) return rooftopOf(map, at)
  // A tile the user marked as no house is odds and ends (the user: the packed towns' odd tiles are small objects), its own terrain kept.
  if (at && map.rooftops?.houses?.[tileKey(at)] === 0) return TERRAIN_SPRITE.o4
  if (at && map.rooftops?.stalls?.includes(tileKey(at))) return TERRAIN_SPRITE.o8
  if (at && code === 'o4' && map.props?.[tileKey(at)] === 'roof') return rooftopOf(map, at)
  if (map.snowyTrees && code === 'ba') return SNOW_TREE
  if (map.snowyTrees && code === 'wh') return SNOW_THICK_WOOD
  if (at && code === 'oc' && doorMat(map, at)) return DOOR_MAT
  // Before a walled house drawn over its building (Fates' Ballistician Blitz), its door mat.
  if (at && code === 'oc' && map.decor?.[tileKey([at[0], at[1] + 1])] === 'walledHouse') return DOOR_MAT
  if (at && code === 'oc' && beforeBuilding(map, at)) return undefined
  // A closed village before a house drawn whole is the ground before its shut door, as a village with nothing to visit is (Fates'
  // Paralogue 20: the user, its villages and houses).
  if (at && code === 'od' && beforeBuilding(map, at)) return undefined
  if (at && code === 'o4') {
    // The prop the game's model puts there; a map that names none: a castle's halls hold its lights.
    const kind = map.props?.[tileKey(at)]
    if (kind === 'roof') return rooftopOf(map, at)
    if (kind === 'box') return crateOrHeap(map, at, PROP_SPRITES.box)
    if (kind) return kind === 'candle' ? CANDLESTICK : kind === 'barrel' ? BARREL : PROP_SPRITES[kind]
    if (!map.props && onFloor(map, at)) return CANDLESTICK
  }
  // A shore's look: the pebbles (the user's pick of the shore's looks).
  if (code === 'b4') return COAST_VARIANTS[3]
  if (FLOOR_BONUS.has(code)) return floorPattern(map, code, at)
  if (code === 'tx') return wardPiece(map, at)
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
    // No mat before it: one door, in the middle of its front (the user: Path of Radiance's Ch.1's was on its first tile).
    if (code === 'rh' && x0 < x1)
      return x === Math.floor((x0 + x1) / 2) ? HOUSE_PIECES.h : [HOUSE_FRONT.window, HOUSE_FRONT.blank][variety(x, y) % 2]
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
  if (at && code === 'o3') return crateOrHeap(map, at, CRATES)
  if (at && map.roundFountains && /^f[a-i]$/.test(code)) {
    const box = fountainBoxes(map).get(tileKey(at))
    if (box) return roundFountainPiece(at[0] - box[0], box[3] - at[1], box[1] - box[0] + 1, box[3] - box[2] + 1)
  }
  return TERRAIN_SPRITE[code]
}

/** Each fountain tile's block (x0, x1, y0, y1), on a map whose fountains are drawn round (`roundFountains`). */
const FOUNTAIN_BOXES = new WeakMap<ChapterMap, Map<string, [number, number, number, number]>>()
function fountainBoxes(map: ChapterMap): Map<string, [number, number, number, number]> {
  const cached = FOUNTAIN_BOXES.get(map)
  if (cached) return cached
  const out = new Map<string, [number, number, number, number]>()
  FOUNTAIN_BOXES.set(map, out)
  const isF = (t: Tile) => /^f[a-i]$/.test(codeAt(map, t) ?? '')
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      if (!isF([x, y]) || out.has(tileKey([x, y]))) continue
      const part: Tile[] = []
      const todo: Tile[] = [[x, y]]
      const seen = new Set<string>()
      while (todo.length) {
        const t = todo.pop()!
        if (seen.has(tileKey(t)) || !isF(t)) continue
        seen.add(tileKey(t))
        part.push(t)
        todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
      }
      const xs = part.map((t) => t[0]), ys = part.map((t) => t[1])
      const box: [number, number, number, number] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
      for (const t of part) out.set(tileKey(t), box)
    }
  return out
}

/** Whether a map has a ship's deck (its supplies are cargo, crates). */
const HAS_DECK = new WeakMap<ChapterMap, boolean>()
function hasDeck(map: ChapterMap): boolean {
  if (!HAS_DECK.has(map)) HAS_DECK.set(map, map.grid.some((row) => rowCodes(row).includes('t3')))
  return HAS_DECK.get(map)!
}

/** Supplies that work as a fort beside a ship's deck: its cargo (Echoes': the user, crates on its ships), not the supply tile. */
const shipCargo = (map: ChapterMap, [x, y]: Tile) =>
  ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => codeAt(map, [x + dx, y + dy]) === 't3')

/** Whether a tile is drawn as crates: cargo, a crate prop, supplies filed with the walls or on a ship, crates laid over a tile. */
function isCrateAt(map: ChapterMap, t: Tile): boolean {
  if (t[0] < 1 || t[1] < 1 || t[0] > map.width || t[1] > map.height) return false
  if (map.decor?.[tileKey(t)] === 'crates') return true
  const c = terrainAt(map, t)
  if (c === 'o3') return true
  if (c === 'o4') return map.props?.[tileKey(t)] === 'box'
  if (c === 'wg') return /suppl/i.test(terrainName(map, t))
  if (c === 'bb') return /suppl/i.test(terrainName(map, t)) && hasDeck(map)
  if (c === 'nd') return shipCargo(map, t)
  return false
}

/** Crates beside other crates are one heap, a crate a tile with its outline round the heap (the user: a 2x2 of boxes, Awakening's
 * Chapters 12 and 15, then every game's ships and ports, 2026-11-24); a lone tile keeps its own crates. */
function crateOrHeap(map: ChapterMap, [x, y]: Tile, single: Sprite): Sprite {
  const [u, d, l, r] = [isCrateAt(map, [x, y + 1]), isCrateAt(map, [x, y - 1]), isCrateAt(map, [x - 1, y]), isCrateAt(map, [x + 1, y])]
  return u || d || l || r ? cratePiece(!u, !l, !r, !d) : single
}

/** Whether a tile is a ship's mast: its own code, a wall the game names a mast (Engage's), a pillar among a ship's decks (Echoes'). */
function isMast(map: ChapterMap, t: Tile): boolean {
  const c = terrainAt(map, t)
  if (c === 'w4') return true
  if (c !== 'wa') return false
  const name = terrainName(map, t)
  return /^mast$/i.test(name) ||
    (/pillar/i.test(name) && ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => codeAt(map, [t[0] + dx, t[1] + dy]) === 't3'))
}

/** The ground drawn as itself (plain, floor, snowfield, deck, paving, glacier, rocky ground, road, sand): what an icon stands on. */
const GROUND_CODES = new Set<TerrainCode>(['t0', 't1', 't2', 't3', 't4', 't5', 't6', 't7', 't9', 'ty', 'ge', 'ga', 'gb', 'gc', 'gd', 'gf', 'gg', 'gh', 'gi', 'gj',
  'tl', 'tk', 'td', 'tv', 'tn'])
/** Floors indoors: a tree stands on them only where no ground outdoors is near (the user: Shadow Dragon and the Blade of Light's trees
 * by a town's paving came out on the paving). */
const INDOOR_GROUND = new Set<TerrainCode>(['t1', 'tn', 'ge', 'gi', 't5', 't9', 'b0', 'by', 'bo', 'bp', 'bq', 'br'])
/** Ground drawn as cobbles: paving, a town's paved plain and road, mossy cobbles. */
const COBBLED = new Set<TerrainCode>(['t4', 'gb', 'gf', 'gc'])
/** Trees and thickets, which the games draw on grass. */
const TREE_CODES = new Set<TerrainCode>(['ba', 'bt', 'wh', 'b5', 'b8'])
/** Mountains (not peaks, which are rock to their feet): drawn on grass as trees are. */
const MOUNTAIN_CODES = new Set<TerrainCode>(['bm', 'b7'])
/** A town's pillars, shops and arenas: on the town's floor beside them, else on grass (Shadow Dragon and the Blade of Light's market). */
const ON_A_FLOOR = new Set<TerrainCode>(['bh', 'b3', 'om', 'on', 'oo', 'op', 'os', 'gl', 'bz'])
/** A shop, an armory and an arena stand on a plaque of their own, one colour in every game (the user: a single background for these
 * icons, something they show up on, not the ground under them). */
const SHOP_CODES = new Set<TerrainCode>(['om', 'on', 'oo', 'op', 'os'])
const SHOP_PLAQUE = '#d8c79a'
/** Buildings and markers drawn over the ground around them (the user: a house, an arena or a grave on its own tan block read as
 * wrong): shops, houses, castles, a closed village, graves; stairs going down, a hole in the floor round it. */
const ON_THE_GROUND = new Set<TerrainCode>(['om', 'on', 'oo', 'op', 'os', 'ot', 'ol', 'ou', 'od', 'oq', 'b2', 'b3', 'gl', 'bz', 'xa'])
/** A building units walk into (Thracia 776's houses, a house on its tile: on the ground round it like every house, not a block of
 * its own, the user), not one no one enters (Radiant Dawn's, whose blocks are walls). */
const OPEN_BUILDING = new WeakMap<ChapterMap, boolean>()
function openBuilding(map: ChapterMap): boolean {
  if (!OPEN_BUILDING.has(map))
    OPEN_BUILDING.set(map, Object.entries(terrainInfo(map, 'oe')?.move ?? {}).some(([cls, v]) => v != null && !/fl[iy]/i.test(cls)))
  return OPEN_BUILDING.get(map)!
}

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

/** Each rock's boulder (decor 'rock'): its block of rocks parted into boulders at most two tiles by two, from its top left, the box
 * (x0, x1, y0, y1) of the one it's in. */
const BOULDERS = new WeakMap<ChapterMap, Map<string, [number, number, number, number]>>()
function boulders(map: ChapterMap): Map<string, [number, number, number, number]> {
  const cached = BOULDERS.get(map)
  if (cached) return cached
  const out = blocks2x2(map, 'rock')
  BOULDERS.set(map, out)
  return out
}
/** A kind of decor's tiles shared out into blocks two tiles by two at most, from the top left (boulders, Fates' big trees). */
function blocks2x2(map: ChapterMap, kind: string): Map<string, [number, number, number, number]> {
  const key = `${kind}`
  let byKind = DECOR_BLOCKS.get(map)
  if (!byKind) DECOR_BLOCKS.set(map, (byKind = new Map()))
  const cached = byKind.get(key)
  if (cached) return cached
  const out = new Map<string, [number, number, number, number]>()
  byKind.set(key, out)
  const rock = (x: number, y: number) => map.decor?.[tileKey([x, y])] === kind && !out.has(tileKey([x, y]))
  for (let y = map.height; y >= 1; y--)
    for (let x = 1; x <= map.width; x++) {
      if (!rock(x, y)) continue
      const wide = rock(x + 1, y)
      const tall = rock(x, y - 1)
      const box: [number, number, number, number] = wide && tall && rock(x + 1, y - 1) ? [x, x + 1, y - 1, y] : wide ? [x, x + 1, y, y]
        : tall ? [x, x, y - 1, y] : [x, x, y, y]
      for (let by = box[2]; by <= box[3]; by++) for (let bx = box[0]; bx <= box[1]; bx++) out.set(tileKey([bx, by]), box)
    }
  return out
}

const DECOR_BLOCKS = new WeakMap<ChapterMap, Map<string, Map<string, [number, number, number, number]>>>()

/** On a map whose bones lie in blocks (`boneBlocks`), each bone tile's grain: along its block's longer side. */
const BONE_AXIS = new WeakMap<ChapterMap, Map<string, 'ns' | 'ew'>>()
function boneAxis(map: ChapterMap): Map<string, 'ns' | 'ew'> {
  const cached = BONE_AXIS.get(map)
  if (cached) return cached
  const out = new Map<string, 'ns' | 'ew'>()
  BONE_AXIS.set(map, out)
  const seen = new Set<string>()
  for (let y = 1; y <= map.height; y++)
    for (let x = 1; x <= map.width; x++) {
      if (codeAt(map, [x, y]) !== 'o2' || seen.has(tileKey([x, y]))) continue
      const part: Tile[] = []
      const todo: Tile[] = [[x, y]]
      while (todo.length) {
        const t = todo.pop()!
        if (seen.has(tileKey(t)) || codeAt(map, t) !== 'o2') continue
        seen.add(tileKey(t))
        part.push(t)
        todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
      }
      const xs = part.map((t) => t[0]), ys = part.map((t) => t[1])
      const axis = Math.max(...ys) - Math.min(...ys) >= Math.max(...xs) - Math.min(...xs) ? 'ns' : 'ew'
      for (const t of part) out.set(tileKey(t), axis)
    }
  return out
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
function GroundDetail({ code: given, fill, X, Y, x, y, scales }: { code: TerrainCode; fill: string; X: number; Y: number; x: number; y: number; scales?: boolean }) {
  const v = variety(x, y)
  const dark = shade(fill, -0.2)
  if (scales && given === 't0')
    // A dragon's back (`scales`: Awakening's Endgame on Grima, the user): two rows of scales a tile, each row half a scale over from
    // the last so a field of tiles reads as one hide, each scale a dark rim with a lit one inside it.
    return (
      <>
        {[0, 1].flatMap((row) =>
          (row ? [0, 5, 10] : [2.5, 7.5]).map((cx) => {
            const cy = row * 5 + 1.6
            return (
              <g key={`${row}${cx}`}>
                <path d={`M${X + cx - 2.5} ${Y + cy} q2.5 3.2 5 0`} fill="none" stroke={shade(fill, -0.4)} strokeWidth={0.55} />
                <path d={`M${X + cx - 1.6} ${Y + cy + 0.5} q1.6 2 3.2 0`} fill="none" stroke={shade(fill, 0.24)} strokeWidth={0.35} />
              </g>
            )
          }),
        )}
      </>
    )
  // A game's plain or floor kept as one (Fates' "plain / floor", drawn in its map's colour) has the texture its colour reads as: grass
  // where it's green, a floor's slabs where it's grey, dirt elsewhere (the user: Fates' ground had none).
  const code: TerrainCode = given === 'ta' || given === 'tu' ? plainLook(fill) : given
  if (code === 't0' || code === 'tv' || code === 'gg')
    return (
      <>
        {TUFTS[v].map(([tx, ty]) => (
          // Three blades side by side, leaning out: a tuft, not an arrow.
          <path key={`${tx}${ty}`} d={`M${X + tx - 0.6} ${Y + ty} l-0.3 -1 M${X + tx} ${Y + ty} v-1.4 M${X + tx + 0.6} ${Y + ty} l0.3 -1`}
            fill="none" stroke={dark} strokeWidth={0.4} strokeLinecap="round" />
        ))}
      </>
    )
  if (code === 't1' || code === 'ge' || code === 'tn' || code === 'tw')
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
  if (code === 't4' || code === 'gb' || code === 'gf')
    // Paving: cobblestones in staggered rows (a town's paved plain and road too).
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
  if (code === 't3' || code === 'ty' || code === 'nb' || code === 'gh' || code === 'gi' || code === 'gj')
    return (
      <>
        {[3.33, 6.67].map((o) => <line key={o} x1={X} x2={X + 10} y1={Y + o} y2={Y + o} stroke={dark} strokeWidth={0.45} />)}
        <line x1={X + 2 + v * 2} x2={X + 2 + v * 2} y1={Y} y2={Y + 3.33} stroke={dark} strokeWidth={0.35} />
      </>
    )
  if (code === 'ti' || code === 'db' || code === 'df' || code === 'th') {
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
  if (code === 'wb' || code === 'wt' || code === 'na' || code === 'wn')
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
  if (code === 'tm' || code === 'tt')
    // Rubble: broken stones lying about, each lit along its top, and a crack between. Shadow Dragon's ledges the same, the rough ground
    // Shadow Dragon and the Blade of Light has on their tiles (the user: not mountains, not a ledge's chevrons).
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
  if (code === 'te')
    // Wasteland: bare dry earth, a crack in it and a pebble or two.
    return (
      <>
        <path d={`M${X} ${Y} ${CRACKS[(v + 1) % 4].replace(/^M/, 'm')}`} fill="none" stroke={shade(fill, -0.24)} strokeWidth={0.35} />
        {PEBBLES[v].map(([px, py]) => <rect key={`${px}${py}`} x={X + px} y={Y + py} width={0.8} height={0.6} rx={0.2} fill={dark} />)}
      </>
    )
  if (code === 'wd')
    // A chasm: ledges far down its sides, in the dark.
    return (
      <>
        {STRATA[v].map(([sx, sy, len]) => (
          <line key={`${sx}${sy}`} x1={X + sx} x2={X + sx + len} y1={Y + sy} y2={Y + sy} stroke={shade(fill, -0.32)} strokeWidth={0.45} />
        ))}
      </>
    )
  if (code === 'wf')
    // Sky: a wisp of cloud drifting by.
    return (
      <path d={`M${X + 1 + v} ${Y + 3 + v} q1.5 -1 3 0 q1 -0.8 2.4 0.2`} fill="none" stroke={shade(fill, 0.35)} strokeWidth={0.5} strokeLinecap="round" />
    )
  if (code === 'bn')
    // A cloud: puffs heaped together.
    return (
      <>
        {[[3, 6, 1.9], [5.4, 4.8, 2.4], [7.4, 6.2, 1.7]].map(([cx, cy, r]) => (
          <circle key={cx} cx={X + cx} cy={Y + cy} r={r} fill="none" stroke={shade(fill, -0.14)} strokeWidth={0.4} />
        ))}
      </>
    )
  if (code === 'wv' && fill !== VOID_COLOUR)
    // Falling water, or an abyss: streaks running down it (none where it's drawn as the void: the Tower's, the user).
    return (
      <>
        {[2, 5, 8].map((sx, i) => (
          <line key={sx} x1={X + sx} x2={X + sx} y1={Y + ((v + i) % 3)} y2={Y + 6 + ((v + i) % 3)} stroke={shade(fill, 0.25)} strokeWidth={0.45} />
        ))}
      </>
    )
  if (code === 'sa' || code === 't6')
    // Ice (a frozen lake, a glacier): a pale sheen across it and a crack.
    return (
      <>
        <path d={`M${X + 1} ${Y + 3 + v * 0.5} l3 -1.5`} stroke={shade(fill, 0.4)} strokeWidth={0.6} strokeLinecap="round" />
        <path d={`M${X} ${Y} ${CRACKS[v].replace(/^M/, 'm')}`} fill="none" stroke={shade(fill, -0.22)} strokeWidth={0.35} />
      </>
    )
  if (code === 'sb')
    // Darkness: a haze drifting through it.
    return (
      <>
        {[3, 7].map((o) => (
          <path key={o} d={`M${X} ${Y + o + (v % 2)} q2.5 -1 5 0 t5 0`} fill="none" stroke={shade(fill, 0.18)} strokeWidth={0.4} />
        ))}
      </>
    )
  if (code === 'wi')
    // A storm: gusts curling across.
    return (
      <>
        {[3, 7].map((o) => (
          <path key={o} d={`M${X + 1} ${Y + o} h4 q1.6 0 1.6 -1.2 q0 -1 -1 -1`} fill="none" stroke={shade(fill, 0.35)} strokeWidth={0.45} strokeLinecap="round" />
        ))}
      </>
    )
  if (code === 'sc')
    // A floor that turns to lava (Awakening's): dark crust with faint seams glowing in it, not yet the cracked magma that hurts.
    return (
      <>
        <path d={`M${X} ${Y} ${CRACKS[v].replace(/^M/, 'm')}`} fill="none" stroke="#a5482a" strokeWidth={0.4} />
        <path d={`M${X} ${Y} ${CRACKS[(v + 2) % 4].replace(/^M/, 'm')}`} fill="none" stroke={shade(fill, -0.3)} strokeWidth={0.35} />
      </>
    )
  if (code === 'bc')
    // A throne's dais: a rug bordered in gold under the seat (no icon: a boss nearly always sits there).
    return (
      <>
        <rect x={X + 1.3} y={Y + 1.3} width={7.4} height={7.4} fill={shade(fill, -0.12)} stroke="#c9a24a" strokeWidth={0.5} />
        <rect x={X + 3} y={Y + 3} width={4} height={4} fill="none" stroke={shade(fill, 0.18)} strokeWidth={0.35} />
      </>
    )
  if (code === 'w7' && fill !== VOID_COLOUR)
    // A roof's shingles: rows of curved tiles, each row's edge shaded (none on a roof drawn as the void: Thracia 776's unlit ones).
    return (
      <>
        {[3.2, 6.6, 10].map((o) => (
          <path key={o} d={`M${X} ${Y + o} ${SHINGLES}`} fill="none" stroke="#6e3a2a" strokeWidth={0.5} />
        ))}
      </>
    )
  return null
}

/** Whether a tile is in a straight run of `code` tiles at least `n` long, across or down. */
function inLine(map: ChapterMap, [x, y]: Tile, code: TerrainCode, n: number): boolean {
  const run = (dx: number, dy: number) => {
    let k = 1
    while (codeAt(map, [x + dx * k, y + dy * k]) === code) k++
    return k - 1
  }
  return run(1, 0) + run(-1, 0) + 1 >= n || run(0, 1) + run(0, -1) + 1 >= n
}

/** Whether a map's valleys are lava: its own colour for them a fiery red. */
function molten(map: ChapterMap): boolean {
  const fill = map.fills?.wn
  if (!fill) return false
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(fill.slice(i, i + 2), 16))
  return r >= 1.45 * g && r >= 1.45 * b
}

/** The texture a plain-or-floor tile's own colour reads as: grass (green), a floor's slabs (grey), dirt (any other). */
function plainLook(fill: string): TerrainCode {
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(fill.slice(i, i + 2), 16) / 255)
  const max = Math.max(r, g, b)
  const min = Math.min(r, g, b)
  const sat = max ? (max - min) / max : 0
  if (sat < 0.12) return 't1'
  return g >= r && g >= b ? 't0' : 'ga'
}

/** A chest or a door on a tile: the mark of a change it sets off (opening it), so no other mark is drawn there. */
const ownMark = (map: ChapterMap, t: Tile) =>
  ['oa', 'or', 'ob'].includes(codeAt(map, t) ?? '') || map.objects.some((o) => o.type === 'chest' && sameTile(o.tile, t)) ||
  !!raisedBridge(map, t) || !!rampartGate(map, t)
/** A change's tile (the legend's: any difficulty's will do, the kind of mark is the same). */
const changeTile = (c: MapChange): Tile => c.tile.default
/** A change that shuts the door on its own tile (a doorway open at the start). */
const shutsDoor = (c: MapChange, t: Tile) => (c.patch ?? []).some((p) => p.becomes === 'ob' && sameTile(p.tile, t))

/** The holes and heaps of the ruined houses the legend shows. */
const RUIN_ICON = 8
/** What the game draws on a tile that its terrain doesn't say (`decor`): a door nothing opens in a wall and a stone bridge's side
 * (Gaiden's), bones on the ground (Mystery of the Emblem's deserts). */
const DECOR_SPRITE: Record<NonNullable<ChapterMap['decor']>[string], Sprite> = {
  door: SEALED_DOOR, bones: BONES, bridge: BRIDGE_SIDE, altar: ALTAR, stairs: STAIRS, statue: STATUE.a, windmill: WINDMILL.a,
  yurt: YURT.h, crates: CRATES, rock: STONE_PILE, umbrella: UMBRELLA.a, palm: PALM.a, parasol: PARASOL.a,
  pillar: PILLAR_TOP, dragon: DRAGON_STATUE.a, shack: SHACK.a, barrel: BARREL, downstairs: STAIRS_DOWN, house: TOWN_HOUSE, grave: GRAVE,
  fountain: FOUNTAIN_PIECES.e, horse: HORSE, carriage: CARRIAGE, sarcophagus: SARCOPHAGUS.b, rubble: RUBBLE, candle: CANDLESTICK,
  table: STONE_TABLE, candelabra: CANDLESTICK, garden: GARDEN, tree: TREE, slab: slabPiece(true, true, true, true, 0),
  ice: ICE_CRYSTALS.a, frozenFountain: frozenFountainPiece(1, 1, 3, 3),
  'stall-red': canopyPiece('red', 0, 0, 1, 1), 'stall-blue': canopyPiece('blue', 0, 0, 1, 1), 'stall-yellow': canopyPiece('yellow', 0, 0, 1, 1),
  'stall-orange': canopyPiece('orange', 0, 0, 1, 1), 'stall-purple': canopyPiece('purple', 0, 0, 1, 1), warpSigil: WARP_SIGIL, warpPad: WARP_PAD,
  'roof-red': canopyPiece('red', 0, 0, 1, 1), 'roof-blue': canopyPiece('blue', 0, 0, 1, 1), 'roof-yellow': canopyPiece('yellow', 0, 0, 1, 1),
  'roof-slate': canopyPiece('slate', 0, 0, 1, 1), 'roof-grey': canopyPiece('grey', 0, 0, 1, 1), 'roof-tan': canopyPiece('tan', 0, 0, 1, 1),
  'roof-green': canopyPiece('green', 0, 0, 1, 1), 'roof-brown': canopyPiece('brown', 0, 0, 1, 1),
  'ruin-red': ruinedRoofPiece('red', 0, 0, 1, 1, RUIN_ICON), 'ruin-blue': ruinedRoofPiece('blue', 0, 0, 1, 1, RUIN_ICON),
  'ruin-yellow': ruinedRoofPiece('yellow', 0, 0, 1, 1, RUIN_ICON), 'ruin-slate': ruinedRoofPiece('slate', 0, 0, 1, 1, RUIN_ICON),
  'ruin-grey': ruinedRoofPiece('grey', 0, 0, 1, 1, RUIN_ICON), 'ruin-tan': ruinedRoofPiece('tan', 0, 0, 1, 1, RUIN_ICON),
  'ruin-green': ruinedRoofPiece('green', 0, 0, 1, 1, RUIN_ICON), 'ruin-brown': ruinedRoofPiece('brown', 0, 0, 1, 1, RUIN_ICON),
  shell: ruinedShellPiece(0, 0, 1, 1, RUIN_ICON),
  roundYurt: roundYurtPiece(1, 1, 3, 3), zenGarden: zenGardenPiece(1, 1), cherry: CHERRY_TREE, walledHouse: VILLAGE_HOUSE.middleFront,
  stones: STONE_PILE, thickPillar: PILLAR_TOP, torch: CANDLESTICK, outcrop: STONE_PILE, palisade: PALISADE, coffin: COFFIN,
  // A brazier, lit (Radiant Dawn's Part 2 Ch.2 torch: the user, braziers are no candlesticks) or put out.
  brazier: TORCH, brazierOut: TORCH_UNLIT, vaseTable: vaseTablePiece(true, true, true, true, 'ew'),
}
/** Decor drawn in place of its tile's own icon: rocks where the game's bones lie, barrels, and Fates' big trees, boulders, rubble,
 * crates, stalls, roofs, yurts, gardens and walled house over its rubble and buildings. */
const REPLACES_ICON = new Set(['rock', 'barrel', 'cherry', 'rubble', 'crates', 'pillar', 'roundYurt', 'zenGarden', 'walledHouse', 'stones', 'thickPillar', 'torch', 'outcrop',
  'palisade', 'coffin', 'brazier', 'brazierOut',
  'stall-red', 'stall-blue', 'stall-yellow', 'stall-orange', 'stall-purple', 'roof-red', 'roof-blue', 'roof-yellow', 'roof-slate', 'roof-grey',
  'roof-tan', 'roof-green', 'roof-brown', 'ruin-red', 'ruin-blue', 'ruin-yellow', 'ruin-slate', 'ruin-grey', 'ruin-tan', 'ruin-green',
  'ruin-brown', 'shell'])
/** Ground of planks: a ship's deck, a pier's or a hall's boards, a road of boards, a wooden pedestal. */
const WOOD_GROUND = new Set<TerrainCode>(['t3', 'gi', 'gh', 'gj', 'ty'])
/** Decor that is a building or a heap standing on the ground around it, not marks on its tile. */
const DECOR_ON_GROUND = new Set(['vaseTable', 'statue', 'windmill', 'yurt', 'crates', 'rock', 'umbrella', 'palm', 'parasol', 'pillar', 'dragon', 'shack', 'barrel', 'bones', 'house', 'grave', 'horse', 'carriage', 'sarcophagus', 'rubble', 'candle', 'table', 'candelabra', 'garden', 'tree', 'slab', 'ice',
  'stall-red', 'stall-blue', 'stall-yellow', 'stall-orange', 'stall-purple', 'roof-red', 'roof-blue', 'roof-yellow', 'roof-slate', 'roof-grey',
  'roof-tan', 'roof-green', 'roof-brown', 'ruin-red', 'ruin-blue', 'ruin-yellow', 'ruin-slate', 'ruin-grey', 'ruin-tan', 'ruin-green',
  'ruin-brown', 'shell', 'roundYurt', 'zenGarden', 'cherry', 'walledHouse', 'warpSigil', 'warpPad', 'stones', 'thickPillar', 'torch', 'outcrop',
  'palisade', 'coffin', 'brazier', 'brazierOut'])
/** A tile's decor: a statue's piece by its place in the two by two (its other tiles beside it). */
/** What's drawn over a tile (`decor`); in a block the user turned round (`mirror`), its partner's across the block, flipped (Radiant
 * Dawn's Part 3 Ch.12's carriage, the user: it faced away from its horse). */
function decorOf(map: ChapterMap, at: Tile): Sprite | undefined {
  const box = map.mirror?.find(([x0, x1, y0, y1]) => at[0] >= x0 && at[0] <= x1 && at[1] >= y0 && at[1] <= y1)
  if (!box) return decorAt(map, at)
  const s = decorAt(map, [box[0] + box[1] - at[0], at[1]])
  return s && flipped(s)
}
function decorAt(map: ChapterMap, [x, y]: Tile): Sprite | undefined {
  const kind = map.decor?.[tileKey([x, y])]
  const same = (dx: number, dy: number) => map.decor?.[tileKey([x + dx, y + dy])] === kind
  if (kind === 'crates') return crateOrHeap(map, [x, y], CRATES)
  // A table holding vases along a run of tiles (Fates' Paralogue 22): one table, its rim where it ends, its grain along it.
  if (kind === 'vaseTable') {
    const [u, d, l, r] = [same(0, 1), same(0, -1), same(-1, 0), same(1, 0)]
    return vaseTablePiece(!u, !l, !r, !d, u || d ? 'ns' : 'ew')
  }
  // One stone outcrop over its tiles, whatever their shape (Three Houses' a77: the user, one outcrop), each tile's boulder open toward
  // the others.
  if (kind === 'outcrop') {
    const [u, d, l, r] = [same(0, 1), same(0, -1), same(-1, 0), same(1, 0)]
    // A rock alone a heap of a few stones (a round boulder is only a rock units push: the user, 2026-11-27).
    const rock = u || d || l || r ? boulderPiece(!u, !l, !r, !d, variety(x, y)) : STONE_PILE
    // In the colour of the rock it's drawn over (`outcropTint`: Engage's, as its scenes draw them).
    const own = map.outcropTint && codeAt(map, [x, y])
    return own ? tintedRock(rock, fillOf(map, own)) : rock
  }
  // A statue standing alone on its tile (Engage's), its plinth under it; statues two tiles by two are drawn whole below.
  if (kind === 'statue' && !([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => same(dx, dy))) return STATUE_SMALL
  // Thick pillars two tiles by two are one great pillar (Echoes' 太柱: the user, 2x2 pillars), a lone one its top on its base.
  if (kind === 'thickPillar') {
    const [x0, x1, y0, y1] = blocks2x2(map, 'thickPillar').get(tileKey([x, y])) ?? [x, x, y, y]
    if (x1 > x0 && y1 > y0) return bigPillarPiece(x === x0 ? (y === y1 ? 'a' : 'c') : y === y1 ? 'b' : 'd')
    return PILLAR_TOP
  }
  // Large stone rubble (the user: Awakening's Apotheosis, all its partitions): one heap over the tiles side by side.
  if (kind === 'slab') {
    const [u, d, l, r] = [same(0, 1), same(0, -1), same(-1, 0), same(1, 0)]
    return slabPiece(!u, !l, !r, !d, variety(x, y))
  }
  // Rocks side by side are one boulder (the user: large boulders, Awakening's Chapter 9 and the Hot-Spring Scramble), a lone one a heap
// of a few stones (a round boulder is only a rock units push: the user, 2026-11-27).
  if (kind === 'rock') {
    // Each boulder at most two tiles by two, a big block of rocks several boulders (the Hot-Spring Scramble's, as its scene draws them).
    const [x0, x1, y0, y1] = boulders(map).get(tileKey([x, y])) ?? [x, x, y, y]
    if (x0 === x1 && y0 === y1) return STONE_PILE
    return boulderPiece(y === y1, x === x0, x === x1, y === y0, variety(x, y))
  }
  // Rubble in a block two by two or more is large stone rubble (the user: Awakening's Apotheosis); in lines or alone, its pieces varied
  // tile to tile (the user: The Future Past 3, different rubble along its pillars and arches).
  if (kind === 'rubble') {
    const [u, d, l, r] = [same(0, 1), same(0, -1), same(-1, 0), same(1, 0)]
    const block = ([[1, 1], [1, -1], [-1, 1], [-1, -1]] as const).some(([dx, dy]) => same(dx, 0) && same(0, dy) && same(dx, dy))
    if (block) return slabPiece(!u, !l, !r, !d, variety(x, y))
    return [RUBBLE, ...RUBBLE_VARIANTS][variety(x, y)]
  }
  if (kind === 'yurt' || kind === 'sarcophagus') {
    // Its place in the three by two: the top over the row below it, then left, middle or right.
    const top = same(0, -1)
    const col = !same(-1, 0) ? 0 : !same(1, 0) ? 2 : 1
    const place = (top ? 'abc' : 'ghi')[col] as 'a' | 'b' | 'c' | 'g' | 'h' | 'i'
    return kind === 'yurt' ? YURT[place] : SARCOPHAGUS[place]
  }
  // A dragon statue: its piece by its place in the five by five.
  if (kind === 'dragon') {
    let [x0, y0] = [x, y]
    while (map.decor?.[tileKey([x0 - 1, y])] === kind) x0--
    while (map.decor?.[tileKey([x, y0 + 1])] === kind) y0++
    return DRAGON_STATUE['abcdefghijklmnopqrstuvwxy'[(y0 - y) * 5 + (x - x0)] as keyof typeof DRAGON_STATUE]
  }
  // A fountain's basin drawn over the fences the game files it as (Path of Radiance's Endgame): its piece by its place in the basin.
  if (kind === 'fountain') {
    const row = !same(0, 1) ? 0 : !same(0, -1) ? 2 : 1
    const col = !same(-1, 0) ? 0 : !same(1, 0) ? 2 : 1
    return FOUNTAIN_PIECES['abcdefghi'[row * 3 + col] as keyof typeof FOUNTAIN_PIECES]
  }
  // A parasol: its canopy on the top tile, its pole on the one below.
  if (kind === 'parasol') return same(0, 1) ? PARASOL.b : PARASOL.a
  // A stall's canopy or a house's roof seen from above (Fates'), over its block: its piece by its place in the block.
  if (kind && /^(stall|roof)-/.test(kind)) {
    const [x0, x1, y0, y1] = decorBox(map, [x, y])
    return canopyPiece(kind.split('-')[1] as Parameters<typeof canopyPiece>[0], x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1)
  }
  // A house standing in ruins (Three Houses' Crimson Flower 37): its roof caved in over its block, its holes by where the house stands;
  // a destroyed one (its Chapel Ruins) roofless, its walls round the rubble.
  if (kind?.startsWith('ruin-')) {
    const [x0, x1, y0, y1] = decorBox(map, [x, y])
    return ruinedRoofPiece(kind.slice(5) as Parameters<typeof canopyPiece>[0], x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1, x0 * 31 + y1 * 17)
  }
  if (kind === 'shell') {
    const [x0, x1, y0, y1] = decorBox(map, [x, y])
    return ruinedShellPiece(x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1, x0 * 31 + y1 * 17)
  }
  // A round yurt (Birthright 8) or a small garden (Birthright 9) over its block.
  if (kind === 'roundYurt') {
    const [x0, x1, y0, y1] = decorBox(map, [x, y])
    return roundYurtPiece(x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1)
  }
  if (kind === 'zenGarden') {
    const [x0, , , y1] = decorBox(map, [x, y])
    return zenGardenPiece(x - x0, y1 - y)
  }
  // Big trees over blocks two tiles by two (Conquest 24's cherry trees), the rest the trees they were.
  if (kind === 'cherry') {
    const [x0, x1, y0, y1] = blocks2x2(map, 'cherry').get(tileKey([x, y])) ?? [x, x, y, y]
    if (x0 === x1 || y0 === y1) return CHERRY_TREE
    return bigTreePiece(x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1)
  }
  // The small house with a low wall close round it, as Shadow Dragon and the Blade of Light and Mystery of the Emblem draw a village,
  // over a block three tiles by two (Fates' Ballistician Blitz, a map from those games: the user).
  if (kind === 'walledHouse') {
    const [x0, x1, , y1] = decorBox(map, [x, y])
    const col = x === x0 ? 'left' : x === x1 ? 'right' : 'middle'
    return VILLAGE_HOUSE[`${col}${y === y1 ? 'Top' : 'Front'}` as keyof typeof VILLAGE_HOUSE]
  }
  // A frozen fountain (Fates' Birthright 17): its piece of the round basin by its place in the block.
  if (kind === 'frozenFountain') {
    const [x0, x1, y0, y1] = decorBox(map, [x, y])
    return frozenFountainPiece(x - x0, y1 - y, x1 - x0 + 1, y1 - y0 + 1)
  }
  if (kind !== 'statue' && kind !== 'windmill' && kind !== 'umbrella' && kind !== 'palm' && kind !== 'shack' && kind !== 'ice') return kind && DECOR_SPRITE[kind]
  const pieces = kind === 'statue' ? STATUE : kind === 'windmill' ? WINDMILL : kind === 'umbrella' ? UMBRELLA : kind === 'shack' ? SHACK
    : kind === 'ice' ? ICE_CRYSTALS : PALM
  const top = same(0, -1)
  const left = same(1, 0)
  return top ? (left ? pieces.a : pieces.b) : left ? pieces.c : pieces.d
}

/** A boulder's or an outcrop's piece in a rock's own colour (its lit top a step lighter, its shaded side and outline darker). */
function tintedRock(s: Sprite, base: string): Sprite {
  return { ...s, palette: { ...s.palette, o: shade(base, -0.62), d: shade(base, -0.3), g: base, l: shade(base, 0.3) } }
}

/** The box (x0, x1, y0, y1) round a tile's block of decor of its kind. */
const DECOR_BOXES = new WeakMap<ChapterMap, Map<string, [number, number, number, number]>>()
function decorBox(map: ChapterMap, at: Tile): [number, number, number, number] {
  let boxes = DECOR_BOXES.get(map)
  if (!boxes) DECOR_BOXES.set(map, (boxes = new Map()))
  const known = boxes.get(tileKey(at))
  if (known) return known
  // The boxes the map gives (`decorBoxes`: Three Houses' buildings parted into their roofs), else the block of its kind round it.
  const given = map.decorBoxes?.find(([x0, x1, y0, y1]) => at[0] >= x0 && at[0] <= x1 && at[1] >= y0 && at[1] <= y1)
  if (given) {
    boxes.set(tileKey(at), given)
    return given
  }
  const kind = map.decor?.[tileKey(at)]
  const part: Tile[] = []
  const seen = new Set<string>()
  const todo: Tile[] = [at]
  while (todo.length) {
    const t = todo.pop()!
    if (seen.has(tileKey(t)) || map.decor?.[tileKey(t)] !== kind) continue
    seen.add(tileKey(t))
    part.push(t)
    todo.push([t[0] + 1, t[1]], [t[0] - 1, t[1]], [t[0], t[1] + 1], [t[0], t[1] - 1])
  }
  const xs = part.map((t) => t[0]), ys = part.map((t) => t[1])
  const box: [number, number, number, number] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)]
  for (const t of part) boxes.set(tileKey(t), box)
  return box
}

/** The ground a fountain drawn over its block stands in (`frozenFountain`: Birthright 17's in its lake, its challenge's on the snow):
 * the code most common round the block, water too. */
function fountainRing(map: ChapterMap, at: Tile): TerrainCode | undefined {
  if (map.decor?.[tileKey(at)] !== 'frozenFountain') return undefined
  const [x0, x1, y0, y1] = decorBox(map, at)
  const count = new Map<TerrainCode, number>()
  for (let y = y0 - 1; y <= y1 + 1; y++)
    for (let x = x0 - 1; x <= x1 + 1; x++) {
      const c = x < x0 || x > x1 || y < y0 || y > y1 ? codeAt(map, [x, y]) : undefined
      if (c && c[0] !== 'w' || (c && WATER_CODES.has(c))) count.set(c!, (count.get(c!) ?? 0) + 1)
    }
  return [...count.entries()].sort((a, b) => b[1] - a[1])[0]?.[0]
}

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
  // a castle came out wall-coloured), nor on ground that hurts (the user: Gaiden's graves came out on its swamp, not their own earth).
  const ground = (c: TerrainCode | undefined): c is TerrainCode =>
    !!c && (GROUND_CODES.has(c) || (c in fills && !WATER_CODES.has(c) && c[0] !== 'w' && c[0] !== 'd' && c !== 'tb' && c !== 't8' && c !== 'nc'))
  let common: TerrainCode | null | undefined
  // The map's grass, where it has any: trees and mountains stand on it wherever they are (the user's call: one ground for each kind
  // of icon, game-wide, not the paving or floor beside them).
  const plain = plainOf(map)
  const grass = plain && rows.some((r) => r.includes(plain)) ? plain : undefined
  for (let y = 1; y <= map.height; y++) {
    for (let x = 1; x <= map.width; x++) {
      const c = at(x, y)!
      // Where the user set the ground an icon stands on (The Blazing Blade's Badon: a barrel on the dock's wood).
      const set = map.standOn?.[tileKey([x, y])]
      if (set) {
        out.set(tileKey([x, y]), set)
        continue
      }
      // An effect laid over stairs on the stairs (onStairs).
      if (onStairs(map, [x, y])) {
        out.set(tileKey([x, y]), 'tc')
        continue
      }
      // A barrel beside a pier's or a ship's boards stands on the wood (`barrelsOnWood`: The Sacred Stones' Eirika 9, the user).
      if (map.barrelsOnWood && c === 'o1') {
        let wood: TerrainCode | undefined
        for (let dy = -1; dy <= 1 && !wood; dy++)
          for (let dx = -1; dx <= 1 && !wood; dx++) {
            const n = at(x + dx, y + dy)
            if (n && WOOD_GROUND.has(n)) wood = n
          }
        if (wood) {
          out.set(tileKey([x, y]), wood)
          continue
        }
      }
      // A rooftop town's stalls on a wall stand on its ground too, and its bare walls drawn as ground are that ground.
      const walledGround = !!map.rooftops?.stalls?.includes(tileKey([x, y])) || !!map.rooftops?.ground?.includes(tileKey([x, y])) ||
        DECOR_ON_GROUND.has(map.decor?.[tileKey([x, y])] ?? '') || !!map.ruins?.includes(tileKey([x, y]))
      // Rubble a game names as a tree, a grave, a stone or a barrel stands on the ground around it, as those do (a tree on grass).
      const named = c === 'wj' || c === 'oi' ? terrainName(map, [x, y]) : ''
      // An altar too (Mystery of the Emblem's and New Mystery's), on the floor round it.
      const onGround = /cherry|grave|stone|rock|barrel|altar/i.test(named)
      // A church alone on its tile on a zoomed-in map (Thracia 776's) stands on the ground round it, as its houses do (the user).
      // A mast stands on its deck, over the deck's colour and planks as a tree over the grass (the user, 2026-11-24: every game's).
      // So do supplies the game files with its walls (Awakening's crates: the user, Chapter 12's lone ones on the quay's cobbles), and
      // a round fountain's corners (`roundFountains`).
      // So does a walled village's compound (`walledVillages`), its corners on the ground beside it.
      const standsOnGround = isMast(map, [x, y]) || (c === 'wg' && /suppl/i.test(terrainName(map, [x, y]))) ||
        (!!map.roundFountains && /^f[a-i]$/.test(c)) || !!compoundPiece(map, c)
      const building = ON_THE_GROUND.has(c) || (c === 'oe' && openBuilding(map)) || (c === 'oj' && !!map.villageBuildings) || standsOnGround
      if (!walledGround && !onGround && !standsOnGround && (c in fills || (TERRAIN_FILL[c] !== TERRAIN_FILL.ta && !building))) continue
      // A town's one-tile houses and a church alone (Thracia 776's: Chapter 14's town, the churches of 15, 17A and 21) stand on grass,
      // as its art draws them (the user), not on the street or the sand.
      if (grass && (TREE_CODES.has(c) || MOUNTAIN_CODES.has(c) || /cherry/i.test(named) || map.decor?.[tileKey([x, y])] === 'house'
        || (c === 'oj' && !!map.villageBuildings))) {
        out.set(tileKey([x, y]), grass)
        continue
      }
      // A town's pillar, shop or arena stands on the floor beside it, else on the grass beside it.
      if (ON_A_FLOOR.has(c)) {
        const beside = new Map<TerrainCode, number>()
        for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) {
          const n = at(x + dx, y + dy)
          if (ground(n) && (INDOOR_GROUND.has(n) || n === grass)) beside.set(n, (beside.get(n) ?? 0) + (INDOOR_GROUND.has(n) ? 100 : 1))
        }
        if (beside.size) {
          out.set(tileKey([x, y]), [...beside.entries()].sort((a, b) => b[1] - a[1])[0][0])
          continue
        }
      }
      // A tree or a mountain stands on the ground outdoors where there's any near, never a castle's floor by it (the user: Gaiden's
      // 4a-5's mountains by its stairs came out on the floor).
      for (const outdoors of TREE_CODES.has(c) || MOUNTAIN_CODES.has(c) ? [true, false] : [false]) {
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

/** A building's piece (its group, v a village's, c a castle's, r a town house's, k a church's, p a prison camp's, q a small stone
 * fort's, j a wooden fort's, l a timber hall's or m a stone keep's, then its place a-i). */
const PIECE = /^[vcrkpqjlmu][a-i]$/
/** The pieces that make up one kind of thing (a building, a market's stalls): one line in the legend. */
const family = (code: TerrainCode) => (PIECE.test(code) ? code[0] : /^o[5-8]$/.test(code) ? 'stall' : null)

/** Terrain that gets a pixel-art icon on top of its fill; the rest (floor, wall, water, chasm,
 * bridge, building) reads fine as colour alone. */
const TERRAIN_SPRITE: Partial<Record<TerrainCode, Sprite>> = {
  tc: STAIRS, ba: TREE, bb: FORT, bd: GATE, be: OLD_GATE, bf: GATEWAY, bv: GATE, bg: LEDGE, bh: PILLAR, bm: MOUNTAIN, bo: DEF_SIGIL,
  bp: DEF2_SIGIL, bq: RES_SIGIL, br: DEF_SIGIL, ha: HEAL, hb: HEAL, hd: VASE_MEDICINE, he: HEAL, hf: HEAL_FLOOR,
  xa: OBSTACLE, dd: LAVA_CRACK, de: SPIKES, wc: SNOW_PEAK, wh: THICK_WOOD, wj: RUBBLE, wq: RUBBLE_WALL, wr: ICE_BLOCK, oa: CHEST, ob: DOOR, oc: HOUSE, of: BALLISTA, oy: BALLISTA, oz: FIRE_ORB, ol: CASTLE,
  bu: PEAK, om: ARMORY, on: VENDOR, oo: ARENA, op: SECRET_SHOP, or: CHEST, bw: RES_FLOOR, bx: RES_FLOOR, os: VENDOR, by: DEF_FLOOR, bz: STAIRS_DOWN,
  b0: DEF_FLOOR, b1: BULWARK, b2: GRAVE, b3: PILLAR, tq: FELL_FLOOR,
  // Supplies that work as a fort (Echoes' 補給: the user's call, a supply tile, not a fort).
  nd: SUPPLY_CACHE,
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
  // A ship's mast (Gaiden's, the GBA games', Awakening's): its yard and furled sail over it.
  w4: MAST,
  // Stairs going down: a stairwell (the GBA games').
  gl: STAIRS_DOWN,
  ...Object.fromEntries(Object.entries(FORT_PIECES).map(([p, sprite]) => [`q${p}`, sprite])),
  // Thracia 776's buildings entered by a gate: its wooden forts, timber halls and stone keeps, each drawn whole; its supply depot.
  ...Object.fromEntries(Object.entries(WOOD_FORT_PIECES).map(([p, sprite]) => [`j${p}`, sprite])),
  ...Object.fromEntries(Object.entries(HALL_PIECES).map(([p, sprite]) => [`l${p}`, sprite])),
  ...Object.fromEntries(Object.entries(KEEP_PIECES).map(([p, sprite]) => [`m${p}`, sprite])),
  // Radiant Dawn's army tents, drawn whole.
  ...Object.fromEntries(Object.entries(TENT_PIECES).map(([p, sprite]) => [`u${p}`, sprite])),
  oq: SUPPLY_DEPOT,
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
  // Shadow Dragon's tiles the lord can't enter keep their base's icon, with no badge (the user: not needed; their names say it).
  b5: TREE, b6: FORT, b7: MOUNTAIN,
  // Three Houses: its lighter thicket is woods to look at; its Avoid floor is a floor bonus like the others, a pattern laid in the
  // floor (FLOOR_BONUS, as Engage's protection tiles: the user's call, not a shield on each); the prayer stone heals; the Holy Tomb's
  // Crest Stones sit in its walls.
  b8: TREE, hg: HEAL, ow: CREST_STONE,
  // Its floor traps and craters, and the siege engines a unit fires: onagers and fire orbs (Fates' fire orbs too). (Its swamp is mud,
  // drawn as Radiant Dawn's bog: GroundDetail.)
  dg: FLOOR_TRAP, dh: LAVA_CRACK, ox: ONAGER, og: FIRE_ORB,
  // Engage's effects laid over a tile (Dragon Vein terrain, miasma), each a badge over the tile's own icon.
  ea: FOG, eb: FOG, ec: PUDDLE, ed: PUDDLE, ee: STONE_PILLARS, eg: MIASMA, eh: MIASMA, ei: FROST,
  // Fire that hurts is the cracked magma in every game (the user's call: Engage's flames on the ground too); fire that doesn't is
  // something else.
  ef: LAVA_CRACK,
  // Three Houses' levers, Fates' dagger batteries (its bow batteries are ballistae), Engage's Fell sigils. (Shadow Dragon's ledges have
  // none: climbed at a mountain's costs with no bonus, none of a ledge's battle effects by the way you cross it, which the chevrons
  // mean, they're the rough ground the original has there: the user.)
  ov: LEVER, oh: LAUNCHER, tx: FELL_FLOOR,
}

/** An effect laid over woods or pillars keeps their icon under its badge. */
const UNDER_SPRITE: Partial<Record<TerrainCode, Sprite>> = { eb: TREE, ed: TREE, eh: PILLAR }
/** An effect laid over stairs, which the game names so ("Miasma on stairs": Engage's), keeps the stairs under its badge, on the stairs'
 * ground (Fell Xenologue 5's (25, 4), the middle of its flight: the user, in the game, "25-4 is a staircase"). */
const onStairs = (map: ChapterMap, t: Tile) => {
  const c = codeAt(map, t)
  return !!c && c[0] === 'e' && BADGE_TERRAIN.has(c) && / on stairs$/i.test(terrainName(map, t))
}

/** Terrain whose own icon is a building you visit (a village, the GBA games' houses, a church: Thracia 776's churches you visit, the
 * user, not a house on them): a village or house standing on it needs no house drawn on top. */
const marksBuilding = (code: TerrainCode) => TERRAIN_SPRITE[code] === HOUSE || TERRAIN_SPRITE[code] === COTTAGE || code === 'oj'

/** A shop's icon by kind: drawn over a shop that sits on terrain without one (Mystery of the Emblem's secret shops are ordinary tiles). */
const SHOP_SPRITE: Record<string, Sprite> = { Armory: ARMORY, Vendor: VENDOR, 'Secret shop': SECRET_SHOP }

/** Terrain whose icon is a small top-left badge instead (the drop badge is top-right): the Tower's floors cover
 * most of the Endgame's maps, and Echoes' castle floors most of its castles, so full-size icons would hide the map. */
const BADGE_TERRAIN = new Set<TerrainCode>(['hc', 'ea', 'eb', 'ec', 'ed', 'ee',
  'eg', 'eh', 'ei'])

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

/** The army markers as usual; the colour-blind look has its own set (`COLOUR_BLIND`). */
const USUAL_MARKERS: typeof COLOUR_BLIND = {
  commonEnemy: COMMON_ENEMY, commonPair: COMMON_PAIR, namedEnemy: NAMED_ENEMY, commonAlly: COMMON_ALLY, ally: ALLY, commonPartner: COMMON_PARTNER,
  partner: PARTNER, joiner: JOINER, reinforcement: REINFORCEMENT, namedReinforcement: NAMED_REINFORCEMENT, bossReinforcement: BOSS_REINFORCEMENT,
}
const markers = (cb: boolean) => (cb ? COLOUR_BLIND : USUAL_MARKERS)

/** Boss, named foes, allies and pairs get their own sprite; everyone else is a plain red marker. Drops are a badge on top. */
function unitSprite(u: MapUnit, cb = false): Sprite {
  const k = markers(cb)
  if (u.type === 'boss') return SKULL
  if (u.type === 'named') return k.namedEnemy
  // The person icon is for named green units; generic ones are a plain green dot. A partner unit, or a neutral one (no game has
  // both), is the same in yellow.
  if (u.type === 'ally' && (u.yellow || u.neutral)) return u.generic ? k.commonPartner : k.partner
  if (u.type === 'ally') return u.generic ? k.commonAlly : k.ally
  if (u.paired) return k.commonPair
  return k.commonEnemy
}
const UNIT_NAME: Record<MapUnit['type'], string> = { boss: 'Boss', named: 'Named enemy', enemy: 'Enemy', ally: 'Ally' }

/** A reinforcement's marker: the orange ring, or a named foe's figure or a boss's skull in the ring's orange. */
const reinforcementSprite = (u: MapUnit, cb = false) =>
  u.type === 'boss' ? markers(cb).bossReinforcement : u.type === 'named' ? markers(cb).namedReinforcement : markers(cb).reinforcement

/** A green joiner's marker: the person icon if it's named, a plain green dot if not; a partner's the same in yellow. */
const joinerSprite = (j: Joiner, cb = false) => {
  const k = markers(cb)
  return !j.ally ? k.joiner : j.yellow || j.neutral ? (j.generic ? k.commonPartner : k.partner) : j.generic ? k.commonAlly : k.ally
}


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
const COLOUR_BLIND_KEY = 'fe-armory-map-colour-blind'

/** Whether this device last turned the colour-blind friendly look on. */
function savedColourBlind() {
  try {
    return localStorage.getItem(COLOUR_BLIND_KEY) === '1'
  } catch {
    return false
  }
}

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
  // A side story (Engage's Fell Xenologue, Three Houses' Cindered Shadows) stays off the page until its switch is ticked.
  const sides = useSideStories()
  const sideShown = set.sideStory ? !!sides[set.sideStory.game] : false
  const sideRoute = set.sideStory && set.routes ? set.sideStory.route : undefined
  const hiddenSide = (m: ChapterMap) =>
    !!sideRoute &&
    !sideShown &&
    (!!set.sideStory!.also?.(m) ||
      [set.routes!.maps(sideRoute), set.routes!.side(sideRoute), set.routes!.third?.maps(sideRoute) ?? [], set.routes!.fourth?.maps(sideRoute) ?? []].some(
        (list) => list.some((x) => x.id === m.id),
      ))
  const picked = all.find((m) => m.id === mapId && reach.has(m.id) && !hiddenSide(m)) ?? newest ?? all[0]
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
  // The routes the page offers: a side story only with its switch ticked; under the block, the bar's own (a game's `walked`: Three
  // Houses' house, then its route) or every route with a chapter reached.
  const routeList = set.routes
    ? set.routes.list.filter((r) => {
        if (r === sideRoute) return sideShown && (!reach.on || set.routes!.maps(r).some((m) => reach.has(m.id)))
        if (!reach.on) return true
        if (set.routes!.walked) return set.routes!.walked(reach.route).includes(r)
        return set.routes!.maps(r).some((m) => reach.has(m.id))
      })
    : []
  /** The route a map goes with: its own where the page offers it, else an offered route that lists it. */
  const routeFor = (m: ChapterMap) => {
    const own = set.routes!.of(m)
    return routeList.includes(own) ? own : (routeList.find((r) => set.routes!.maps(r).some((x) => x.id === m.id)) ?? routeList[0] ?? own)
  }
  const [routePick, setRoute] = useState(set.routes ? set.routes.of(map) : '')
  const route = set.routes ? (routeList.includes(routePick) ? routePick : routeFor(map)) : ''
  // The backdrop follows the route picked here (Fates').
  useBackdropRoute(set.backdropGame ?? '', set.backdropGame ? route : undefined)
  // The second dropdown: a route's paralogues (Fates), or the game's side maps (trial maps).
  const paralogues = (set.routes ? set.routes.side(route) : (set.extras?.maps ?? [])).filter((m) => reach.has(m.id) && !hiddenSide(m))
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
  // Supplies to burn shown alight (the user's call: boxes heaped up until then).
  const [burned, setBurned] = useState(false)
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
  // The colour-blind friendly look: markers, corners and outlines told apart by shape and dashes, in colours that stay apart.
  const [colourBlind, setColourBlind] = useState(savedColourBlind)
  function toggleColourBlind() {
    setColourBlind((v) => {
      try {
        localStorage.setItem(COLOUR_BLIND_KEY, v ? '0' : '1')
      } catch {
        // Not remembered this time.
      }
      return !v
    })
  }
  const hasStandIns = [...map.units, ...(map.reinforcements ?? []).flatMap((g) => g.units), ...(map.joiners ?? []), ...(map.forced ?? [])].some(
    (u) => u.standIn,
  )
  const cast = useMemo(() => {
    const m = standIns ? withStandIns(map) : map
    // A forced unit stands on its tile on the difficulties it says (The Sacred Stones' Chapter 3: Neimi is moved on Easy alone).
    return m.forced?.some((f) => f.difficulties) ? { ...m, forced: m.forced.filter((f) => !f.difficulties || f.difficulties.includes(difficulty)) } : m
  }, [map, standIns, difficulty])
  // The map's states through its turns, and every change made in the one shown: the previewed ones, and its turns' up to `step`.
  const steps = useMemo(() => mapSteps(map), [map])
  const active = useMemo(() => {
    const made = step ? new Set([...previewing, ...steps.slice(0, step).flatMap((s) => s.ids)]) : previewing
    // A group shown that comes through a door opening its room (`opens`: Three Houses' Shambhala) shows the room open, with it in.
    const through = (map.reinforcements ?? []).flatMap((g) => (groups.has(g.id) && g.opens ? [g.opens] : []))
    return through.length ? new Set([...made, ...through]) : made
  }, [previewing, steps, step, map, groups])

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
    // And what stands in it (Mystery of the Emblem's Book 2 Ch.14's stone before its throne).
    const decor = seen.decor && Object.fromEntries(Object.entries(seen.decor).filter(([k]) => !closed.has(k)))
    return {
      ...seen,
      units: units.filter((u) => !closed.has(tileKey(u.tile))),
      objects: seen.objects.filter((o) => !hidden(o.tile)),
      ...(seen.walls ? { walls } : {}),
      ...(decor ? { decor } : {}),
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
    // The route buttons follow the bar too (Fates' route after its split, Three Houses' house and then its route).
    if (set.routes) setRoute(routeFor(newest))
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
    <ColourBlindContext.Provider value={colourBlind}>
    <div className="flex flex-col gap-4">
      {set.routes && (
      <div className="flex flex-wrap gap-1" role="group" aria-label="Route">
        {routeList.map((r) => (
          <button
            key={r}
            onClick={() => chooseRoute(r)}
            aria-pressed={route === r}
            className={`rounded border px-3 py-1 text-sm ${
              route === r ? 'border-violet-500 bg-violet-950/60 text-violet-100' : 'border-neutral-700 text-neutral-300 hover:bg-neutral-800'
            }`}
          >
            {reach.on && set.routes!.label ? set.routes!.label(r, reach) : r}
          </button>
        ))}
        {set.sideStory && (
          <label className="ml-1 flex items-center gap-1 text-sm text-neutral-300">
            <input type="checkbox" checked={sideShown} onChange={(e) => setSideStoryShown(set.sideStory!.game, e.target.checked)} />
            {set.sideStory.label}
          </label>
        )}
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
          className={`rounded border px-2 py-1 ${infoBelow ? 'border-violet-500 bg-violet-950 text-violet-200' : 'border-neutral-700 bg-neutral-900'}`}
        >
          {infoBelow ? 'Info below the map' : 'Info beside the map'}
        </button>
        <button
          type="button"
          onClick={toggleColourBlind}
          aria-pressed={colourBlind}
          title="Tells the armies apart by their markers' shapes and edges, the starting tiles by their corners and every outline by its dashes, in colors that stay apart for red-green and blue-yellow color blindness."
          className={`rounded border px-2 py-1 ${colourBlind ? 'border-sky-500 bg-sky-950 text-sky-200' : 'border-neutral-700 bg-neutral-900'}`}
        >
          {colourBlind ? 'Colorblind-friendly: on' : 'Colorblind-friendly'}
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
            burned={burned}
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
            burned={burned}
            onToggleBurn={() => setBurned((v) => !v)}
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
    </ColourBlindContext.Provider>
  )
}

export function MapGrid({
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
  burned = false,
}: {
  map: ChapterMap
  /** Supplies to burn shown alight. */
  burned?: boolean
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
  const cb = useColourBlind()
  // SVG y grows downward, map y grows upward: screen row = height - y.
  const px = (x: number) => GUTTER + (x - 1) * CELL
  const py = (y: number) => (map.height - y) * CELL
  const tiles: Tile[] = []
  for (let y = map.height; y >= 1; y--) for (let x = 1; x <= map.width; x++) tiles.push([x, y])
  const dark = new Set((map.dark ?? []).map(tileKey))
  const under = groundUnder(map)
  const snowyMap = snowy(map)
  const underRock = new Map<string, TerrainCode>()
  for (const c of map.changes) {
    if (c.trigger !== 'boulder') continue
    for (const p of c.patch ?? []) if (!previewing.has(c.id)) underRock.set(tileKey(p.tile), p.becomes as TerrainCode)
  }
  // A building units walk into (Thracia 776's houses) isn't walled: only a building no one walks into gets its blocks (one fliers
  // cross still does: Radiant Dawn's, the user's Part 3 Ch.12, a bare tile).
  const walkIn = openBuilding(map)
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
        // A pushable rock's tile is drawn as the ground its rolling away leaves (Radiant Dawn's Part 3 Ch.12: its wooden pedestals, the
        // user), the rock over it; the tile keeps its own numbers.
        // A ship's gangplank is drawn as a wooden bridge, its rails along both sides (`gangplanks`: the user), whatever the game calls it;
        // a floor its art draws as a bridge as one (`bridgeFloors`).
        const plank = !!map.gangplanks?.includes(tileKey(t))
        // A frozen fountain stands in the ground round its block (its lake, or the snow), drawn over it.
        const letter = plank || map.bridgeFloors?.includes(tileKey(t)) ? 'tb' : underRock.get(tileKey(t)) ?? fountainRing(map, t) ?? terrainAt(map, t)
        const X = px(x)
        const Y = py(y)
        // A village's pieces, and an entrance among them, stand in its yard (but a walled village's compound on the ground round it).
        const inYard = !map.walledVillages && (
          (letter[0] === 'v' && PIECE.test(letter)) ||
          (VILLAGE_INSIDE.has(letter) && ([[1, 0], [-1, 0], [0, 1], [0, -1]] as const).some(([dx, dy]) => {
            const n: Tile = [x + dx, y + dy]
            const c = n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height ? terrainAt(map, n) : undefined
            return !!c && c[0] === 'v' && PIECE.test(c)
          })))
        const built = buildings(map).has(tileKey(t))
        const scenery = !built && sceneryHouse(letter, tileKey(t), visits)
        const village = twoTileVillage(map, t)
        // A two-tile village's roof stands on the ground its front does.
        const ground = village === villagePieces(map).middleTop ? under.get(tileKey([x, y - 1])) : under.get(tileKey(t))
        const yard = villageYardPiece(map, t) ?? castleWing(map, t)
        // A village's wing over a wall stands on the grass round it, with no pattern of the wall's under it.
        const wing = !!yard && letter[0] === 'w'
        // A house with nothing to visit stands in its village's yard; on a map of grassland (Shadow Dragon and the Blade of Light's,
        // Mystery of the Emblem's) on the ground around it, as the game draws it (the user's call), and on a town's floor anywhere.
        // On sand, on the sand round it (`sandYards`: The Blazing Blade's deserts, the user).
        const houseGround = scenery && ground && (INDOOR_GROUND.has(ground) || plainOf(map) === 'tv' || (map.sandYards && SAND_CODES.has(ground)))
          ? ground : undefined
        // A raised drawbridge: the river under its leaves.
        const drawbridge = raisedBridge(map, t)
        const fortFloor = inStoneFort(map, t)
        const gate = rampartGate(map, t)
        // A wall's face (floor below it) darker and its top lighter, on a map drawn so (`wallFaces`: the Lagdou Ruins, the user).
        const faced = !!map.wallFaces && letter === 'w1'
        const face = faced && y > 1 && (codeAt(map, [x, y - 1]) ?? 'w')[0] !== 'w'
        const baseFill = drawbridge && letter === 'wo' ? fillOf(map, map.fills?.tg || !map.fills?.we ? 'tg' : 'we')
          : map.boatEnds?.[tileKey(t)] ? fillOf(map, 'we')
          : letter === 'wm' && /^mist$/i.test(terrainName(map, t)) ? MIST
          : map.flameWalls?.includes(tileKey(t)) && letter[0] === 'w' ? fillOf(map, 'ga' in (map.fills ?? {}) ? 'ga' : 'ta')
          : fortFloor ? STONE_FORT_FLOOR
            : wing ? fillOf(map, plainOf(map) ?? 'tv')
            : houseGround ? fillOf(map, houseGround) : inYard || scenery ? villageYard(map)
              : SHOP_CODES.has(letter) && !built ? SHOP_PLAQUE
              : shipWall(map, t) ? TERRAIN_FILL.w9! : wallLook(map, t) === 'wall' ? lowWallFill(map) : wallLook(map, t) === 'stone' ? stoneWallFill(map)
                : wallLook(map, t) === 'rock' ? caveFace(map) : wallLook(map, t) === 'wood' ? shipWood(map)
                : wallLook(map, t) === 'timber' ? TIMBER : wallLook(map, t) === 'cliff' ? cliffRock(map) : wallLook(map, t) === 'sky' ? skyBelow(map)
                : wallLook(map, t) === 'pit' ? TERRAIN_FILL.wd! : wallLook(map, t) === 'void' ? VOID_COLOUR
                : wallLook(map, t) === 'fence' ? fillOf(map, groundBeside(map, t) ?? plainOf(map) ?? 'ta')
                : darkBarrier(map, t) ? DARK_BARRIER
                : fillOf(map, breakableLook(map, t) ?? ground ?? letter)
        const fill = !faced ? baseFill : face ? shade(baseFill, -0.3) : shade(baseFill, 0.14)
        const fort = stairFortPart(map, t)
        // A boat's end (`boatEnds`): its bow over the water, the way it points.
        const bow = map.boatEnds?.[tileKey(t)]
        // Mist the game files with its dark waters (Fates' Boo Camp: the user, dark fog, not dark water): fog drifting, no ripples.
        const mist = letter === 'wm' && /^mist$/i.test(terrainName(map, t))
        // A flame wall (`flameWalls`): up, a wall of flames; down, its seam in the ground.
        const flame = map.flameWalls?.includes(tileKey(t)) ? (letter[0] === 'w' ? 'up' : 'down') : undefined
        const outside = (dx: number, dy: number) => {
          const n: Tile = [x + dx, y + dy]
          return n[0] >= 1 && n[1] >= 1 && n[0] <= map.width && n[1] <= map.height && !VILLAGE_INSIDE.has(terrainAt(map, n))
        }
        return (
          <g key={tileKey(t)} onClick={() => onSelect(t)} className="cursor-pointer">
            {letter === 'w8' && !village ? (
              <VillageTile
                X={X}
                Y={Y}
                yard={villageYard(map)}
                sides={(['n', 's', 'w', 'e'] as const).filter((s) => outside(SIDE_STEP[s][0], SIDE_STEP[s][1]))}
              />
            ) : (
              <rect x={X} y={Y} width={CELL} height={CELL} fill={fill} />
            )}
            {((WATER_CODES.has(letter) && !mist) || drawbridge || bow) &&
              WAVES.map((d) => (
                <path key={d} d={d} transform={`translate(${X} ${Y})`} fill="none" stroke={shade(fill, 0.3)} strokeWidth={0.55} strokeLinecap="round" />
              ))}
            <GroundDetail
              code={
                // A village's yard grass through and through (`yardGrass`: The Sacred Stones', the user: 'green cobble'), and in every
                // game never the texture of the cobbles beside it (the user, 2026-11-24: no game has solid green cobble).
                !houseGround && (inYard || scenery) && (map.yardGrass || COBBLED.has(ground ?? letter)) ? plainOf(map) ?? 't0'
                : bow ? 'we'
                : mist ? 'sb'
                : SHOP_CODES.has(letter) ? letter
                : map.rooftops?.ground?.includes(tileKey(t)) ? under.get(tileKey(t)) ?? letter
                  : map.ruins?.includes(tileKey(t)) && !/^r[a-r]$/.test(letter) ? 'tm'
                  : wallLook(map, t) === 'rock' ? 'wt'
                  : wallLook(map, t) === 'pit' ? 'wd'
                  : wallLook(map, t) === 'void' ? 'wy'
                  : wallLook(map, t) === 'wood' || wallLook(map, t) === 'timber' ? 't3'
                  : wallLook(map, t) === 'cliff' ? 'wt'
                  : wallLook(map, t) === 'sky' ? 'wf'
                  // A roof drawn in bricks has no shingles.
                  : wallLook(map, t) === 'bricks' ? 'w0'
                  : FLOOR_BONUS.has(letter) || fortFloor ? 't1'
                  // A wall drawn as another code (`looksAs`: Echoes' cave walls as rock) has that code's texture.
                  : map.looksAs?.[tileKey(t)] && letter[0] === 'w' ? map.looksAs[tileKey(t)]!
                    // An icon's tile has the texture of the ground it stands on (the user: chests on a castle's floor came out flat).
                    : (ground ?? letter) === 'tv' && snowyMap ? 't2'
                      : ground ?? letter
              }
              fill={fill}
              X={X}
              Y={Y}
              x={x}
              y={y}
              scales={map.scales}
            />
            {SAND_CODES.has(letter) && !map.standOn?.[tileKey(t)] && (
              // Sand: grains, and a ripple the wind left (the user: a shore read as a flat block); none where the user set the ground
              // drawn there (`standOn`: Shadow Dragon's Chapter 23's row of grass beyond its walls).
              <>
                {GRAINS.map(([gx, gy]) => <rect key={`${gx}${gy}`} x={X + gx} y={Y + gy} width={0.6} height={0.6} fill={shade(fill, -0.22)} />)}
                <path d={`M${X + 1 + (variety(x, y) % 2) * 3} ${Y + 4.4 + (variety(x, y) % 3)} q1.5 -1 3 0 t3 0`} fill="none" stroke={shade(fill, -0.18)} strokeWidth={0.4} strokeLinecap="round" />
              </>
            )}
            {/* The void beyond a map (a wall all but black) has no pattern: Thracia 776's unlit roofs. */}
            {face &&
              // A wall's face: its bricks (the Lagdou Ruins' dark brick fronts).
              BRICKS.map(([x1, y1, x2, y2], i) => (
                <line key={`fb${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={shade(fill, -0.38)} strokeWidth={0.5} />
              ))}
            {fill !== VOID_COLOUR && !face && !built && !wing && !bow && !flame && !under.has(tileKey(t)) && !village && !gate && !(letter === 'oe' && walkIn) && !wallLook(map, t) && WALL_PATTERN[darkBarrier(map, t) ? 'wu' : breakableLook(map, t) ?? letter]?.lines.map(([x1, y1, x2, y2], i) => {
              const { stroke } = darkBarrier(map, t) ? { stroke: '#8a6cc0' } : WALL_PATTERN[breakableLook(map, t) ?? letter]!
              return <line key={`wp${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={typeof stroke === 'number' ? shade(fill, stroke) : stroke === 'contrast' ? contrasting(fill) : stroke} strokeWidth={0.5} />
            })}
            {SHOP_CODES.has(letter) && !built && <rect x={X + 0.4} y={Y + 0.4} width={9.2} height={9.2} fill="none" stroke="#6b5636" strokeWidth={0.8} />}
            {letter === 'w1' &&
              // A ruin's walls edged where they meet open ground (the user, the Lagdou Ruins: they read flat, as a floor).
              (['n', 's', 'w', 'e'] as const).map((side) => {
                const n = codeAt(map, [x + SIDE_STEP[side][0], y + SIDE_STEP[side][1]])
                if (!n || n[0] === 'w') return null
                const [x1, y1, x2, y2] = { n: [0, 0.3, 10, 0.3], s: [0, 9.7, 10, 9.7], w: [0.3, 0, 0.3, 10], e: [9.7, 0, 9.7, 10] }[side]
                return <line key={`edge${side}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={shade(fill, -0.45)} strokeWidth={0.7} />
              })}
            {wallLook(map, t) === 'bricks' &&
              // A roof drawn in bricks in its own colour (Thracia 776's: the user, not a roof's tiles).
              BRICKS.map(([x1, y1, x2, y2], i) => (
                <line key={`br${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={shade(fill, -0.35)} strokeWidth={0.5} />
              ))}
            {shipWall(map, t) &&
              WALL_PATTERN.w9!.lines.map(([x1, y1, x2, y2], i) => (
                <line key={`rail${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={WALL_PATTERN.w9!.stroke as string} strokeWidth={0.5} />
              ))}
            {(wallLook(map, t) === 'wall' || wallLook(map, t) === 'stone') && !shipWall(map, t) &&
              // A low outer wall or a low stone wall: the regular bricks in its own stone, which join up whichever way the wall runs
              // (the user: courses turned to follow it never met).
              BRICKS.map(([x1, y1, x2, y2], i) => (
                <line key={`lw${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={shade(fill, -0.38)} strokeWidth={0.5} />
              ))}
            {wallLook(map, t) === 'fence' && (
              // A wooden fence round a yard (Engage's windmill's): two rails on three posts, on the ground of the yard; light wood edged
              // dark where a game's are drawn bolder (`boldFences`: Radiant Dawn's, the user: they were hard to see on the ground).
              <>
                {map.boldFences &&
                  WALL_PATTERN.wg!.lines.map(([x1, y1, x2, y2], i) => (
                    <line key={`fo${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke="#241a10" strokeWidth={1.5} strokeLinecap="round" />
                  ))}
                {WALL_PATTERN.wg!.lines.map(([x1, y1, x2, y2], i) => (
                  <line key={`fe${i}`} x1={X + x1} y1={Y + y1} x2={X + x2} y2={Y + y2} stroke={map.boldFences ? '#c9a26c' : '#5b4630'} strokeWidth={0.7} />
                ))}
              </>
            )}
            {(letter === 'tb' || letter === 'ts' || (letter === 'wo' && !drawbridge)) && <WoodBridge map={map} t={t} fill={fill} railed={plank} />}
            {bow && <SpriteG sprite={bowTurned(bow)} x={X} y={Y} />}
            {flame && <SpriteG sprite={flame === 'up' ? FLAME_WALL : FLAME_VENT} x={X} y={Y} />}
            {drawbridge && <SpriteG sprite={RAISED_BRIDGE[drawbridge]} x={X} y={Y} />}
            {gate && <SpriteG sprite={gate} x={X} y={Y} />}
            {(letter === 't8' || letter === 'nc') && (
              // A stone bridge's deck: big slabs in staggered courses, worn a little lighter along their tops, and a parapet along each
              // side over water or a drop (the user: a deck alone read as stone bricks). Gaiden's castle floor between a stone bridge's
              // ends (Regal's slabs) is the same deck.
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
                {(['n', 's', 'w', 'e'] as const).map((side) => {
                  const n = codeAt(map, [x + SIDE_STEP[side][0], y + SIDE_STEP[side][1]])
                  // Over water or a drop; a fence or sandbags standing on the bridge are no edge (Radiant Dawn's Part 3 Ch.11).
                  if (!n || n === 'wg' || !(WATER_CODES.has(n) || n[0] === 'w')) return null
                  // A bridge given its span (`bridgeSpans`: Echoes' Rigel Falls, broken mid-river) is railed only along its sides, never
                  // across its break (the user: the railings in the wrong spots).
                  const span = map.bridgeSpans?.[tileKey(t)]
                  if (span && (span === 'ns' ? side === 'n' || side === 's' : side === 'w' || side === 'e')) return null
                  const [rx, ry, rw, rh] = { n: [0, 0, 10, 1.6], s: [0, 8.4, 10, 1.6], w: [0, 0, 1.6, 10], e: [8.4, 0, 1.6, 10] }[side]
                  return (
                    <g key={`rail${side}`}>
                      <rect x={X + rx} y={Y + ry} width={rw} height={rh} fill={shade(fill, 0.3)} stroke={shade(fill, -0.45)} strokeWidth={0.35} />
                    </g>
                  )
                })}
              </>
            )}
            {(UNDER_SPRITE[letter] || onStairs(map, t)) && <SpriteG sprite={UNDER_SPRITE[letter] ?? STAIRS} x={X} y={Y} />}
            {yard && <SpriteG sprite={yard} x={X} y={Y} />}
            {scenery ? (
              <SpriteG sprite={map.yurts ? YURT_HOUSE : TOWN_HOUSE} x={X} y={Y} />
            ) : fort === 'e' ? (
              // A stair fort's middle: the platform, and the fort's mark small in its corner.
              <>
                <SpriteG sprite={STAIR_FORT_PIECES.e} x={X} y={Y} />
                <SpriteG sprite={FORT} x={X} y={Y} size={5} />
              </>
            ) : (
              // A scripted gate is drawn in place of the wall's own mark (Thracia 776's cracked wall that gives way as a gate).
              !gate &&
              spriteOf(map, letter, t) &&
              (BADGE_TERRAIN.has(letter) || (trail && letter === 'bl') || (letter === 'wz' && !!map.decor?.[tileKey(t)]) ? (
                <SpriteG sprite={spriteOf(map, letter, t)!} x={X} y={Y} size={5} />
              ) : (
                <SpriteG sprite={spriteOf(map, letter, t)!} x={X} y={Y} />
              ))
            )}
            {map.rooftops?.chimneys.includes(tileKey(t)) && <SpriteG sprite={CHIMNEY} x={X} y={Y} />}
            {map.decor?.[tileKey(t)] && <SpriteG sprite={decorOf(map, t)!} x={X} y={Y} />}
            {map.night && !(letter in (map.fills ?? {})) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0a0d14" opacity={0.5} pointerEvents="none" />}
            {dark.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.6} />}
            {lit &&
              (lit.has(tileKey(t)) ? (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#facc15" opacity={0.14} />
              ) : sight?.has(tileKey(t)) ? null : (
                <rect x={X} y={Y} width={CELL} height={CELL} fill="#0b0912" opacity={0.5} />
              ))}
            {radius.has(tileKey(t)) && <rect x={X} y={Y} width={CELL} height={CELL} fill="#ffffff" opacity={0.22} />}
            {starts.has(tileKey(t)) && !cb && (
              <g fill={map.corrinStart && sameTile(map.corrinStart, t) ? '#facc15' : fixed.has(tileKey(t)) ? FORCED : '#3b82f6'}>
                <path d={`M${X} ${Y}h3l-3 3z`} />
                <path d={`M${X + 10} ${Y + 10}h-3l3 -3z`} />
              </g>
            )}
            {starts.has(tileKey(t)) && cb && (() => {
              const look = startCorners(map.corrinStart && sameTile(map.corrinStart, t) ? 'lord' : fixed.has(tileKey(t)) ? 'forced' : 'start', true)
              return (
                <g fill={look.fill} stroke="#0a0a0a" strokeWidth={0.35} strokeLinejoin="round">
                  {look.paths(X, Y).map((d) => <path key={d} d={d} />)}
                </g>
              )
            })()}
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

      {shownWalls(map).map(({ tile: [x, y], side, step }) => {
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
              {cb ? (
                <CbRect x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} line={CB_LINE.burn} strokeWidth={1} fillOpacity={0.18} />
              ) : (
                <rect x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} fill="#f97316" fillOpacity={0.18} stroke={BURN} strokeWidth={1} strokeDasharray="2 1" />
              )}
              <SpriteG sprite={burned ? SUPPLIES : SUPPLY_BOXES} x={px(t[0])} y={py(t[1])} />
            </g>
          ) : cb ? (
            <CbRect key={`obj${tileKey(t)}`} x={px(t[0]) + 0.6} y={py(t[1]) + 0.6} width={CELL - 1.2} height={CELL - 1.2} line={CB_LINE.objective} strokeWidth={1.2} />
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
              {cb ? (
                <CbRect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} line={CB_LINE.dig} strokeWidth={0.8} fillOpacity={0.14} />
              ) : (
                <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#c2410c" fillOpacity={0.14} stroke="#9a3412" strokeWidth={0.8} strokeDasharray="1.5 1" />
              )}
              <SpriteG sprite={BURIED} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
        if (o.type === 'pit') return <SpriteG key={`pit${tileKey(o.tile)}`} sprite={PIT} x={px(o.tile[0])} y={py(o.tile[1])} />
        // A village on ground of its own (Path of Radiance's keep the plain, coast or snow they stand on): its house on top.
        if (o.type === 'village' && !marksBuilding(terrainAt(map, o.tile)) && !buildings(map).has(tileKey(o.tile)))
          return <SpriteG key={`vil${tileKey(o.tile)}`} sprite={doorMat(map, o.tile) ? DOOR_MAT : HOUSE} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'event') return <SpriteG key={`evt${tileKey(o.tile)}`} sprite={EVENT_TILE} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'trap') return <SpriteG key={`trap${tileKey(o.tile)}`} sprite={TRAP_SPRITE[o.kind]} x={px(o.tile[0])} y={py(o.tile[1])} />
        // A ballista a bow user stands on (the GBA games'): the machine is on ordinary ground, so it's drawn here.
        if (o.type === 'ballista' && o.mounted) return <SpriteG key={`bal${tileKey(o.tile)}`} sprite={BALLISTA} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'shiny') return <SpriteG key={`shiny${tileKey(o.tile)}`} sprite={SHINY} x={px(o.tile[0])} y={py(o.tile[1])} />
        if (o.type === 'shop') {
          const sprite = SHOP_SPRITE[o.kind]
          if (!sprite || TERRAIN_SPRITE[terrainAt(map, o.tile)] === sprite || buildings(map).has(tileKey(o.tile))) return null
          return <SpriteG key={`shop${tileKey(o.tile)}`} sprite={sprite} x={px(o.tile[0])} y={py(o.tile[1])} />
        }
        if (o.type === 'fire') {
          // The house, outlined, with a flame on its corner.
          const [l, b, r, t] = o.area
          return (
            <g key={`fire${tileKey(o.tile)}`} pointerEvents="none">
              {cb ? (
                <CbRect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} line={CB_LINE.fire} strokeWidth={0.8} fillOpacity={0.12} />
              ) : (
                <rect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} fill="#dc2626" fillOpacity={0.12} stroke="#dc2626" strokeWidth={0.8} strokeDasharray="1.5 1" />
              )}
              <SpriteG sprite={FLAME} x={px(o.tile[0])} y={py(o.tile[1])} />
            </g>
          )
        }
        if (o.type !== 'pot') return null
        const X = px(o.tile[0])
        const Y = py(o.tile[1])
        return (
          <g key={`pot${tileKey(o.tile)}`} opacity={potsBroken ? 0.2 : 1}>
            {/* The round stone base it stands on, as the game draws it (Conquest 12: the user). */}
            <circle cx={X + 5} cy={Y + 5.6} r={4.3} fill="#8d8a84" stroke="#5c5a55" strokeWidth={0.5} />
            <circle cx={X + 5} cy={Y + 5.6} r={2.9} fill="none" stroke="#a9a6a0" strokeWidth={0.4} />
            <SpriteG sprite={o.pot === 'medicine' ? VASE_MEDICINE : VASE_POISON} x={X} y={Y} />
          </g>
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
          // A wall that breaks over two tiles or more is cracked on each of them (the user: one crack read as one tile).
          if (c.trigger === 'breakable' && !c.snag) {
            // Only the walls that give way: not a closed room the break opens (its tiles are revealed, not broken: Path of Radiance's
            // Ch.27, the user) nor a tile that becomes another wall.
            // Doors too: a door three tiles wide breaks across all three (Engage's Chapters 5 and 10, the user).
            const walls = (c.patch ?? [])
              .filter((p) => {
                const now = codeAt(map, p.tile) ?? ''
                return (now[0] === 'w' || now === 'ob') && now !== 'ws' && String(p.becomes)[0] !== 'w'
              })
              .map((p) => p.tile)
            const marks = walls.length ? walls : [[x, y] as Tile]
            return (
              <g key={c.id}>
                {/* A breakable drawn as what it is (Engage's junk as shacks) keeps its crack as a small badge, so it shows; an altar
                    takes the full crack (The Shepherd Exalt's crystals: the user, "the full breakable crack on it"). */}
                {marks.map((t) => {
                  const decor = map.decor?.[tileKey(t)]
                  return <SpriteG key={tileKey(t)} sprite={CRACK} x={px(t[0])} y={py(t[1])} size={decor && decor !== 'altar' ? 5 : undefined} />
                })}
              </g>
            )
          }
          return <SpriteG key={c.id} sprite={c.snag ? SNAG : shutsDoor(c, [x, y]) ? OPEN_DOOR : c.trigger === 'event' ? MAP_EVENT : CRACK} x={px(x)} y={py(y)} />
        }
        if (c.trigger === 'eruption') {
          // An islet that erupts on its turn: a script's change's mark, not a flame (the user: flames read as tiles that burn).
          return previewing.has(c.id) ? null : <SpriteG key={c.id} sprite={MAP_EVENT} x={px(x)} y={py(y)} />
        }
        if (c.trigger === 'trap') {
          // A hidden pit (Path of Radiance Ch.23): its lid until previewed as sprung, then the hole it leaves.
          return previewing.has(c.id) ? null : <SpriteG key={c.id} sprite={PIT} x={px(x)} y={py(y)} />
        }
        return <SpriteG key={c.id} sprite={DRAGON_VEIN} x={px(x)} y={py(y)} className="animate-pulse" />
      })}

      {/* Coloured rooms, swapped while a vein that swaps them is previewed. The colour-blind look hatches the red ones, so the two read
          apart without their colours. */}
      {cb && map.rooms?.length ? (
        <defs>
          <pattern id="cb-hatch" width={2.5} height={2.5} patternUnits="userSpaceOnUse" patternTransform="rotate(45)">
            <line x1={0} y1={0} x2={0} y2={2.5} stroke="#1c0f05" strokeOpacity={0.6} strokeWidth={0.8} />
          </pattern>
        </defs>
      ) : null}
      {(map.rooms ?? []).flatMap((set, si) =>
        set.rects.map(([l, b, r, t]) => {
          const swapped = map.changes.some((c) => c.swapsRooms && previewing.has(c.id))
          const shown = swapped ? (set.color === 'red' ? 'blue' : 'red') : set.color
          const color = ROOM[shown]
          if (cb) {
            const [x, y, w, h] = [px(l) + 0.5, py(t) + 0.5, (r - l + 1) * CELL - 1, (t - b + 1) * CELL - 1]
            return (
              <g key={`room${si}:${l},${b}`} pointerEvents="none">
                <rect x={x} y={y} width={w} height={h} fill={color} fillOpacity={ROOM_TINT[shown]} stroke={color} strokeWidth={0.6} />
                {shown === 'red' && <rect x={x} y={y} width={w} height={h} fill="url(#cb-hatch)" />}
              </g>
            )
          }
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
        g.tiles.map((t) => cb ? (
          <CbRect key={`fg${gi}:${tileKey(t)}`} x={px(t[0]) + 0.5} y={py(t[1]) + 0.5} width={CELL - 1} height={CELL - 1} line={CB_FOE_GROUP[gi]} strokeWidth={0.8} fillOpacity={0.12} />
        ) : (
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
            <SpriteG sprite={unitSprite(u, cb)} x={x} y={y} size={span} />
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
            fill={cb ? CB_FOE_GROUP[gi].colour : FOE_GROUP[gi]}
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
        const line = who === 'enemy' ? CB_LINE.foeArea : CB_LINE.area
        const colour = cb ? line.colour : who === 'enemy' ? '#ef4444' : '#f0883e'
        return (
          <g key={`trig${who}${l},${b},${r},${t}${step ?? ''}`} pointerEvents="none">
            {cb ? (
              <CbRect x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} line={line} strokeWidth={0.7} fillOpacity={0.08} />
            ) : (
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
            )}
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
          if (cb)
            return (
              <CbRect key={`zone${c.id}`} x={px(l) + 0.5} y={py(t) + 0.5} width={(r - l + 1) * CELL - 1} height={(t - b + 1) * CELL - 1} line={CB_LINE.trap}
                strokeWidth={0.7} fillOpacity={previewing.has(c.id) ? 0 : 0.1} />
            )
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
            stroke={cb ? (a.kind === 'joiner' ? OKABE.sky : OKABE.orange) : a.kind === 'joiner' ? '#60a5fa' : '#f0883e'}
            strokeWidth={0.9}
            strokeDasharray={cb && a.kind === 'joiner' ? '0.7 0.9' : '1.6 1'}
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
            <SpriteG sprite={a.kind === 'joiner' ? joinerSprite(a.joiner, cb) : reinforcementSprite(a.unit, cb)} x={px(x)} y={py(y)} size={span} />
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

      {/* A staircase's other end, outlined while one end is selected (the Rainbow Sage's platforms); a warp's platform, or the
          sigils that send units to a platform (Revelation 18's). */}
      {selected &&
        [...(map.links ?? []), ...(map.warps ?? [])]
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
        <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={typeof pattern.stroke === 'number' ? shade(fill, pattern.stroke) : pattern.stroke === 'contrast' ? contrasting(fill) : pattern.stroke} strokeWidth={0.5} />
      ))}
      {(code === 'tb' || code === 'ts' || code === 'wo') && (
        // A wooden bridge's planks across its span and its rails, as on the map.
        <>
          {[0, 2.5, 5, 7.5].map((o) => (
            <g key={o}>
              <line x1={o + 0.25} x2={o + 0.25} y1={0} y2={10} stroke={shade(fill, -0.45)} strokeWidth={0.5} />
              <line x1={o + 0.85} x2={o + 0.85} y1={0} y2={10} stroke={shade(fill, 0.3)} strokeWidth={0.4} />
            </g>
          ))}
          {[0, 8.5].map((ry) => <rect key={ry} x={0} y={ry} width={10} height={1.5} fill={shade(fill, 0.42)} stroke={shade(fill, -0.45)} strokeWidth={0.35} />)}
        </>
      )}
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
  const cb = useColourBlind()
  const k = markers(cb)
  // Only what this map actually has, so small maps get a short legend (and only what can be seen, under Thracia's fog).
  // A gangplank is listed as one, not as the stairs or goal its tiles are to the game.
  const planks = new Set([...(map.gangplanks ?? []), ...(map.bridgeFloors ?? [])])
  const visible = map.grid.flatMap((row, r) =>
    rowCodes(row).filter((_, c) => !unseen?.has(tileKey([c + 1, map.height - r])) && !planks.has(tileKey([c + 1, map.height - r]))))
  const changed = unseen ? [] : map.changes.flatMap((c) => (c.patch ?? []).map((p) => p.becomes))
  const codes = new Set([...visible, ...changed])
  const pots = map.objects.filter((o): o is Pot => o.type === 'pot')
  const items: {
    label: string
    sprite?: Sprite
    swatch?: string
    outline?: boolean
    /** The outline's dashes (the colour-blind look). */
    dash?: string
    /** Hatched, as the colour-blind look draws the red rooms. */
    hatch?: boolean
    corners?: StartKind
    code?: TerrainCode
    wallPattern?: [number, number, number, number][]
  }[] = []
  if (pots.some((p) => p.pot === 'medicine')) items.push({ label: 'Medicine pot', sprite: VASE_MEDICINE })
  if (pots.some((p) => p.pot === 'poison')) items.push({ label: 'Poison pot', sprite: VASE_POISON })
  if (map.changes.some((c) => c.trigger === 'dragonVein')) items.push({ label: 'Dragon Vein', sprite: DRAGON_VEIN })
  if (map.changes.some((c) => c.trigger === 'breakable' && !c.snag)) items.push({ label: 'Breakable', sprite: CRACK })
  const snag = map.changes.find((c) => c.snag)
  if (snag)
    items.push({
      label: /dead tree/i.test(terrainName(map, changeTile(snag))) ? 'Dead tree (breakable: it falls across as a bridge)' : 'Snag (breakable)',
      sprite: SNAG,
    })
  const events = map.changes.filter((c) => c.trigger === 'event' && !ownMark(map, changeTile(c)))
  if (events.some((c) => shutsDoor(c, changeTile(c)))) items.push({ label: 'Doorway the chapter shuts (tap it)', sprite: OPEN_DOOR })
  if (map.changes.some((c) => rampartGate(map, changeTile(c)))) items.push({ label: 'Gate the chapter opens (tap it)', sprite: RAMPART_GATE.alone })
  if (map.changes.some((c) => raisedBridge(map, changeTile(c)))) items.push({ label: 'Raised drawbridge: a key lowers it (tap it)', sprite: RAISED_BRIDGE.ns })
  if (events.some((c) => !shutsDoor(c, changeTile(c)))) items.push({ label: 'Changes during the chapter (tap it)', sprite: MAP_EVENT })
  if (map.changes.some((c) => c.trigger === 'eruption'))
    items.push({ label: 'Lava floor that turns to hazard, cracked magma, on its turn (tap it)', sprite: MAP_EVENT })
  if (map.changes.some((c) => c.trigger === 'boulder'))
    items.push({ label: map.changes.some((c) => c.trigger === 'boulder' && !c.noPreview) ? 'Boulder (tap to see its path)' : 'Boulder', sprite: BOULDER })
  const sides = shownWalls(map)
  if (sides.some((w) => !w.all && !w.step)) items.push({ label: "Blocked side: ground units can't cross (fliers can)", swatch: FENCE })
  if (sides.some((w) => w.step)) items.push({ label: "Step between levels: ground units can't cross (fliers can)", swatch: RAIL })
  if (sides.some((w) => w.all)) items.push({ label: "Blocked side: no unit can cross", swatch: FENCE })
  if (railedSides(map).length) items.push({ label: 'Railing round a building or ground no unit can enter, fliers included', swatch: RAIL })
  const ownGround = map.objects.filter((o) => o.type === 'village' && !marksBuilding(terrainAt(map, o.tile)))
  if (ownGround.some((o) => !doorMat(map, o.tile))) items.push({ label: 'Village', sprite: HOUSE })
  if (ownGround.some((o) => doorMat(map, o.tile)) || codes.has('oc') && map.grid.some((row, i) =>
    rowCodes(row).some((c, x) => c === 'oc' && doorMat(map, [x + 1, map.height - i]))))
    items.push({ label: map.walledVillages ? 'Village to visit (at the door mat before its gate)' : 'House to visit (at its door mat)', sprite: DOOR_MAT })
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
    unitKinds.set(label, unitSprite(u, cb))
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
    items.push({ label: 'Reinforcement', sprite: k.reinforcement })
  if (arrivals.some((a) => a.kind === 'reinforcement' && a.unit.type === 'named')) items.push({ label: 'Named foe arriving', sprite: k.namedReinforcement })
  if (arrivals.some((a) => a.kind === 'reinforcement' && a.unit.type === 'boss')) items.push({ label: 'Boss arriving', sprite: k.bossReinforcement })
  if (arrivals.some((a) => a.kind === 'joiner' && !a.joiner.ally)) items.push({ label: 'Joins your army', sprite: k.joiner })
  const allies = arrivals.flatMap((a) => (a.kind === 'joiner' && a.joiner.ally ? [a.joiner] : []))
  if (allies.some((j) => !j.yellow && !j.neutral && !j.generic)) items.push({ label: 'Named green unit arrives', sprite: k.ally })
  if (allies.some((j) => !j.yellow && !j.neutral && j.generic)) items.push({ label: 'Green unit arrives', sprite: k.commonAlly })
  if (allies.some((j) => j.yellow && !j.generic)) items.push({ label: 'Named partner unit arrives (yellow)', sprite: k.partner })
  if (allies.some((j) => j.yellow && j.generic)) items.push({ label: 'Partner unit arrives (yellow)', sprite: k.commonPartner })
  if (allies.some((j) => j.neutral && !j.generic)) items.push({ label: 'Named neutral unit arrives (yellow)', sprite: k.partner })
  if (allies.some((j) => j.neutral && j.generic)) items.push({ label: 'Neutral unit arrives (yellow)', sprite: k.commonPartner })
  // An area a foe sets off (Fates' acid bogs: "as soon as an enemy reaches") is drawn red, a line of its own.
  if (triggers.some((a) => a.who !== 'enemy'))
    items.push({ label: 'Area that brings a group in', swatch: cb ? CB_LINE.area.colour : '#f0883e', dash: cb ? CB_LINE.area.dash : undefined, outline: true })
  if (triggers.some((a) => a.who === 'enemy'))
    items.push({ label: 'Area a foe reaching brings a group in', swatch: cb ? CB_LINE.foeArea.colour : '#ef4444', dash: cb ? CB_LINE.foeArea.dash : undefined, outline: true })
  for (const set of map.rooms ?? [])
    items.push({ label: `${set.color === 'red' ? 'Red' : 'Blue'} room: ${set.effect}`, swatch: ROOM[set.color], hatch: cb && set.color === 'red' })
  if (map.changes.some((c) => c.zone))
    items.push({
      label: 'Trap: one of your units stopping inside springs it (tap it)',
      swatch: cb ? CB_LINE.trap.colour : TRAP_ZONE,
      dash: cb ? CB_LINE.trap.dash : undefined,
      outline: true,
    })
  if (map.objectives.some((o) => o.type !== 'burn')) items.push({ label: 'Objective', swatch: cb ? CB_LINE.objective.colour : '#38bdf8', outline: true })
  if (map.objectives.some((o) => o.type === 'burn')) items.push({ label: 'Supplies to burn (objective)', sprite: SUPPLY_BOXES })
  if ([...map.units, ...arrivals.map((a) => (a.kind === 'reinforcement' ? a.unit : a.joiner))].some((u) => u.goesTo))
    items.push({ label: 'Where the tapped unit is headed', swatch: GOES_TO, outline: true })
  for (const [gi, g] of (map.foeGroups ?? []).entries())
    items.push({ label: `${g.label}'s tiles`, swatch: cb ? CB_FOE_GROUP[gi].colour : FOE_GROUP[gi], dash: cb ? CB_FOE_GROUP[gi].dash : undefined, outline: true })
  if (map.starts.length) items.push({ label: 'Starting tile', corners: 'start' })
  if (map.corrinStart) items.push({ label: "Lord's start", corners: 'lord' })
  if (map.forced?.some((f) => f.tile)) items.push({ label: 'Forced unit (fixed tile)', corners: 'forced' })
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
    // Shadow Dragon's ledges, drawn as rough ground, say how they play.
    const label = (kinds.get(name)!.size > 1 && !family(l)) || l === 'tt' ? TERRAIN_CODES[l] : name
    // Tiles drawn as another code (`looksAs`: Echoes' towers as its ramparts, its cave's walls as rock): a line for each look, named as
    // the game names them.
    if (map.looksAs) {
      const as = new Map<TerrainCode, string>()
      map.grid.forEach((row, i) =>
        rowCodes(row).forEach((c, x) => {
          const t: Tile = [x + 1, map.height - i]
          const to = map.looksAs?.[tileKey(t)]
          if (c === l && to && !as.has(to)) as.set(to, terrainName(map, t))
        }),
      )
      for (const [to, text] of as) items.push({ label: text, swatch: fillOf(map, to), code: to })
    }
    if (l === 'ot' && houses.some((k) => !visits.has(k) && !buildings(map).has(k)))
      items.push({ label: `${name}: nothing to visit (units stand in it)`, sprite: map.yurts ? YURT_HOUSE : TOWN_HOUSE, swatch: villageYard(map) })
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
    // A code whose every tile is drawn bare (`bareTiles`) has no line.
    if (map.bareTiles && map.grid.every((row, i) => rowCodes(row).every((c, x) => c !== l || !!map.bareTiles?.includes(tileKey([x + 1, map.height - i])))))
      continue
    // Partitions that are all boats' ends (Fates' Birthright 12) are the bows' line.
    if (l === 'wg' && map.boatEnds &&
      map.grid.every((row, i) => rowCodes(row).every((c, x) => c !== 'wg' || !!map.boatEnds?.[tileKey([x + 1, map.height - i])]))) {
      items.push({ label: `${name} (a boat's end)`, sprite: BOAT_BOW, swatch: fillOf(map, 'we') })
      continue
    }
    // A code whose every tile is drawn as rocks (Awakening's Chapter 9's bones) is the rocks' line.
    if ((map.decor || map.looksAs) && map.grid.every((row, i) => rowCodes(row).every((c, x) => c !== l ||
      ['rock', 'ice', 'frozenFountain', 'cherry', 'rubble', 'roundYurt', 'zenGarden', 'walledHouse', 'stones', 'thickPillar', 'torch', 'outcrop',
        'palisade', 'coffin', 'brazier', 'brazierOut', 'pillar', 'candle', 'statue'].includes(map.decor?.[tileKey([x + 1, map.height - i])] ?? '') ||
      !!map.looksAs?.[tileKey([x + 1, map.height - i])] ||
      /^(stall|roof)-/.test(map.decor?.[tileKey([x + 1, map.height - i])] ?? ''))))
      continue
    // Fences, sandbags and outer walls (Radiant Dawn's one terrain), and pillars among castle walls: a line for each look.
    if (map.wallLooks && (l === 'wg' || l === 'w0' || l === 'wx' || l === 'w7' || l === 'wa' || l === 'wb' || l === 'wd')) {
      const looks = new Set(
        map.grid.flatMap((row, i) => rowCodes(row).flatMap((c, x) => {
          const t: Tile = [x + 1, map.height - i]
          return c === l ? [wallLook(map, t) ?? (map.looksAs?.[tileKey(t)] ? 'as' : 'own')] : []
        })),
      )
      // A pit's or the void's line by its own tiles' name where the code's tiles go by several (Engage's Chapter 7: its sky the void,
      // its collapsed floor holes).
      const lookName = (look: string) => {
        const names = new Set(map.grid.flatMap((row, i) => rowCodes(row).flatMap((c, x) => {
          const t: Tile = [x + 1, map.height - i]
          return c === l && wallLook(map, t) === look ? [terrainName(map, t)] : []
        })))
        return names.size === 1 ? [...names][0] : name
      }
      if (looks.has('sandbags')) items.push({ label: 'Sandbags', sprite: SANDBAG_WALL })
      if (looks.has('pillar')) items.push({ label: 'Pillar', sprite: PILLAR_TOP })
      if (looks.has('wall'))
        items.push({ label: 'Outer wall', swatch: lowWallFill(map), wallPattern: BRICKS })
      if (looks.has('stone')) items.push({ label: `${name} (a low stone wall)`, swatch: stoneWallFill(map), wallPattern: BRICKS })
      if (looks.has('rock')) items.push({ label: `${name} (a cave's wall)`, swatch: caveFace(map), code: 'wt' })
      if (looks.has('pit')) items.push({ label: `${lookName('pit')} (a pit)`, swatch: TERRAIN_FILL.wd!, code: 'wd' })
      if (looks.has('ship')) items.push({ label: `${name} (a ship's wooden wall)`, swatch: TERRAIN_FILL.w9!, wallPattern: WALL_PATTERN.w9!.lines })
      if (looks.has('bricks')) items.push({ label: name, swatch: fillOf(map, l), wallPattern: BRICKS })
      if (looks.has('wood')) items.push({ label: `${name} (a ship's mast, cabin or hull)`, swatch: shipWood(map), code: 't3' })
      if (looks.has('timber')) items.push({ label: `${name} (a wooden wall)`, swatch: TIMBER, code: 't3' })
      if (looks.has('cliff')) items.push({ label: `${name} (a cliff)`, swatch: cliffRock(map), code: 'wt' })
      if (looks.has('sky')) items.push({ label: `${name} (the sky below)`, swatch: skyBelow(map), code: 'wf' })
      if (looks.has('void')) items.push({ label: `${lookName('void')} (a drop into the dark)`, swatch: VOID_COLOUR })
      if (!looks.has('own')) continue
    }
    // Rubble is drawn as what it is tile by tile (rubble, a ruin's walls, the trees, graves, stones and barrels a game names): a line
    // for each look the map has.
    // Supplies (Echoes'): the supply tile, and crates where they're a ship's cargo.
    if (l === 'nd') {
      const tiles = map.grid.flatMap((row, i) => rowCodes(row).flatMap((c, x): Tile[] => (c === 'nd' ? [[x + 1, map.height - i]] : [])))
      if (tiles.some((t) => shipCargo(map, t))) items.push({ label: `${name} (a ship's cargo)`, sprite: SUPPLY_CRATES, swatch: fillOf(map, 't3') })
      if (tiles.some((t) => !shipCargo(map, t))) items.push({ label, sprite: SUPPLY_CACHE, swatch: fillOf(map, l), code: l })
      continue
    }
    if (l === 'wj' || l === 'b3') {
      const looks = new Map<Sprite, string>()
      map.grid.forEach((row, i) =>
        rowCodes(row).forEach((c, x) => {
          if (c !== l) return
          const t: Tile = [x + 1, map.height - i]
          const sprite = spriteOf(map, l, t)
          if (sprite && !looks.has(sprite)) looks.set(sprite, sprite === RUINS ? `${name} (a ruin's walls)` : sprite === RUBBLE ? name : terrainName(map, t))
        }),
      )
      for (const [sprite, text] of looks) items.push({ label: text, sprite, swatch: fillOf(map, l) })
      continue
    }
    // A walled village's compound: its gate, on the ground round it.
    if (compoundPiece(map, l)) {
      items.push({ label, sprite: WALLED_VILLAGE.middleFront, swatch: fillOf(map, plainOf(map) ?? 'ta'), code: l })
      continue
    }
    const yard = l === 'w8' || (PIECE.test(l) && l[0] === 'v')
    // Drawn as a building's piece (buildings): that piece, in its yard.
    const built = [...buildings(map)].find(([k, s]) => s !== YARD && terrainAt(map, k.split(',').map(Number) as Tile) === l)?.[1]
    items.push({
      label, sprite: built ?? spriteOf(map, l),
      swatch: yard || built ? villageYard(map) : SHOP_CODES.has(l) ? SHOP_PLAQUE : fillOf(map, l), code: l,
    })
  }
  // Buildings and heaps drawn over their tiles (Engage's windmills, yurts and crates, Fates' statues) and buildings in ruins.
  const DECOR_LABEL: Record<string, string> = {
    statue: 'Statue', windmill: 'Windmill', yurt: 'Yurt', crates: 'Crates', rock: 'Rocks', umbrella: 'Beach umbrella', palm: 'Palm tree',
    parasol: 'Parasol', pillar: 'Pillar', dragon: 'Dragon statue', shack: 'Shack (junk: it can be attacked down)', barrel: 'Barrels',
    downstairs: 'Stairs (down)', house: 'House (no unit stands in it)', fountain: 'Fountain', grave: 'Cemetery (no unit enters)',
    horse: 'Horse and carriage', carriage: 'Horse and carriage', sarcophagus: 'Sarcophagus', rubble: 'Rubble',
    candle: 'Candlestick (no unit enters)', table: 'Stone table (no unit enters)', candelabra: 'Candelabra (on the floor)',
    garden: 'Garden (no unit enters)', tree: 'Tree (no unit enters)', slab: 'Large stone rubble (no unit enters)',
    ice: 'Ice crystals (no unit enters)', frozenFountain: 'Frozen fountain (no unit enters)',
    'stall-red': 'Market stall (no unit enters)', 'stall-blue': 'Market stall (no unit enters)', 'stall-yellow': 'Market stall (no unit enters)',
    'stall-orange': 'Market stall (no unit enters)', 'stall-purple': 'Market stall (no unit enters)',
    'roof-red': 'House, its roof (no unit enters)', 'roof-blue': 'House, its roof (no unit enters)', 'roof-yellow': 'House, its roof (no unit enters)',
    'roof-slate': 'House, its roof (no unit enters)', 'roof-grey': 'House, its roof (no unit enters)', 'roof-tan': 'House, its roof (no unit enters)',
    'roof-green': 'House, its roof (no unit enters)', 'roof-brown': 'House, its roof (no unit enters)',
    'ruin-red': 'House in ruins (no unit enters)', 'ruin-blue': 'House in ruins (no unit enters)', 'ruin-yellow': 'House in ruins (no unit enters)',
    'ruin-slate': 'House in ruins (no unit enters)', 'ruin-grey': 'House in ruins (no unit enters)', 'ruin-tan': 'House in ruins (no unit enters)',
    'ruin-green': 'House in ruins (no unit enters)', 'ruin-brown': 'House in ruins (no unit enters)',
    shell: 'House in ruins (no unit enters)',
    roundYurt: 'Yurt (no unit enters)', zenGarden: 'Garden (no unit enters)', cherry: 'Cherry trees (no unit enters)',
    walledHouse: 'House (no unit enters)', warpSigil: 'Sigil: it sends a unit standing on it to its platform',
    warpPad: 'Warp platform: where a sigil sends a unit',
    stones: 'Heap of stones (no unit enters)', thickPillar: 'Pillar (no unit enters)', torch: 'Torch (no unit enters)',
    outcrop: 'Rock outcrop (no unit enters)', palisade: 'Palisade (only fliers cross it)', coffin: 'Coffin (no unit enters)',
    brazier: 'Brazier (no unit enters)', brazierOut: 'Brazier, unlit (no unit enters)', vaseTable: 'Table with vases (no unit enters)',
  }
  // A roof over a building fliers cross (Three Houses') says so, with the building's name.
  const roofLabel = (kind: string) => {
    const at = Object.entries(map.decor ?? {}).find(([, k]) => k === kind)?.[0].split(',').map(Number) as Tile | undefined
    const fliers = !!at && !!terrainInfo(map, terrainAt(map, at)).move?.Fliers
    if (at && kind.startsWith('roof-') && fliers) return `${terrainName(map, at)}, its roof (only fliers cross it)`
    if (at && (kind.startsWith('ruin-') || kind === 'shell') && fliers) return `${terrainName(map, at)} in ruins (only fliers cross it)`
    // Anything else drawn over a tile fliers cross says so (Fates' candlesticks and tables on its partitions).
    if (fliers && DECOR_LABEL[kind]?.endsWith('(no unit enters)')) return DECOR_LABEL[kind].replace('(no unit enters)', '(only fliers cross it)')
    return DECOR_LABEL[kind]
  }
  // Statues standing alone (Engage's) are the small statue's line.
  const lone = (kind: string) => Object.entries(map.decor ?? {}).some(([k, v]) => {
    if (v !== kind) return false
    const [x, y] = k.split(',').map(Number)
    return ![[1, 0], [-1, 0], [0, 1], [0, -1]].some(([dx, dy]) => map.decor?.[tileKey([x + dx, y + dy])] === kind)
  })
  // An outcrop says what the game calls it and who crosses it, tile by tile (Engage's rocks and peaks let fliers over, its boulders
  // no one), in its rock's colour where the map gives one.
  for (const [k, v] of Object.entries(map.decor ?? {})) {
    if (v !== 'outcrop') continue
    const t = k.split(',').map(Number) as Tile
    const fliers = !!terrainInfo(map, terrainAt(map, t)).move?.Fliers
    const code = codeAt(map, t)
    items.push({
      label: `${terrainName(map, t)} (a rock outcrop: ${fliers ? 'only fliers cross it' : 'no unit enters'})`,
      sprite: map.outcropTint && code ? tintedRock(STONE_PILE, fillOf(map, code)) : STONE_PILE,
    })
  }
  for (const kind of new Set(Object.values(map.decor ?? {})))
    if (DECOR_LABEL[kind] && kind !== 'outcrop') items.push({ label: roofLabel(kind), sprite: kind === 'statue' ? (lone(kind) ? STATUE_SMALL : STATUE.a) : kind === 'windmill' ? WINDMILL.a : kind === 'yurt' ? YURT.h : kind === 'rock' ? STONE_PILE
        : kind === 'umbrella' ? UMBRELLA.a : kind === 'palm' ? PALM.a : kind === 'parasol' ? PARASOL.a : kind === 'pillar' ? PILLAR_TOP
        : kind === 'downstairs' ? STAIRS_DOWN : kind === 'house' ? TOWN_HOUSE : kind === 'fountain' ? FOUNTAIN_PIECES.e
        : kind === 'dragon' ? DRAGON_STATUE.m : kind === 'shack' ? SHACK.a : kind === 'barrel' ? BARREL : kind === 'grave' ? GRAVE
        : kind === 'horse' ? HORSE : kind === 'carriage' ? CARRIAGE : kind === 'sarcophagus' ? SARCOPHAGUS.b : kind === 'rubble' ? RUBBLE
        : kind === 'candle' || kind === 'candelabra' ? CANDLESTICK : kind === 'table' ? STONE_TABLE : kind === 'garden' ? GARDEN
        : kind === 'tree' ? TREE : kind === 'slab' ? slabPiece(true, true, true, true, 0) : kind === 'ice' ? ICE_CRYSTALS.a
        : kind === 'frozenFountain' ? frozenFountainPiece(1, 1, 3, 3) : DECOR_SPRITE[kind as keyof typeof DECOR_SPRITE] ?? CRATES })
  if (map.ruins?.length) items.push({ label: 'In ruins', sprite: RUINS })
  if (map.gangplanks?.length) items.push({ label: "Gangplank (the ship's stairs)", swatch: fillOf(map, 'tb') })
  if (map.bridgeFloors?.length) items.push({ label: 'Bridge the game calls floor (plays as floor)', swatch: fillOf(map, 'tb') })
  const unique = items.filter((it, i) => items.findIndex((o) => o.label === it.label) === i)
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1.5 text-xs text-neutral-400">
      {unique.map((it) => (
        <span key={it.label} className="flex items-center gap-1">
          {it.wallPattern ? (
            <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm" aria-hidden>
              <rect width={10} height={10} fill={it.swatch} />
              <line x1={0} x2={10} y1={0.8} y2={0.8} stroke={shade(it.swatch!, 0.3)} strokeWidth={0.6} />
              {it.wallPattern.map(([x1, y1, x2, y2], i) => <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke={shade(it.swatch!, -0.38)} strokeWidth={0.5} />)}
            </svg>
          ) : it.code && !yardCode(it.code) ? (
            <TileSwatch code={it.code} fill={it.swatch!} sprite={it.sprite} />
          ) : it.sprite ? (
            <PixelIcon sprite={it.sprite} size={16} />
          ) : it.corners ? (
            // The same corner marks the map draws on a starting tile.
            <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm bg-[#b89a6a]" aria-hidden>
              <g fill={startCorners(it.corners, cb).fill} {...(cb ? { stroke: '#0a0a0a', strokeWidth: 0.35, strokeLinejoin: 'round' as const } : {})}>
                {startCorners(it.corners, cb).paths(0, 0).map((d) => <path key={d} d={d} />)}
              </g>
            </svg>
          ) : it.outline && cb ? (
            // The outline as the colour-blind look draws it: its colour and dashes over a dark line.
            <svg width={16} height={16} viewBox="0 0 10 10" className="inline-block shrink-0" aria-hidden>
              <rect x={1.2} y={1.2} width={7.6} height={7.6} fill={it.swatch} fillOpacity={0.12} stroke="#0a0a0a" strokeOpacity={0.75} strokeWidth={2.1} />
              <rect x={1.2} y={1.2} width={7.6} height={7.6} fill="none" stroke={it.swatch} strokeWidth={1.4} strokeDasharray={it.dash} />
            </svg>
          ) : it.hatch ? (
            <svg width={12} height={12} viewBox="0 0 10 10" className="inline-block shrink-0 rounded-sm" aria-hidden>
              <rect width={10} height={10} fill={it.swatch} />
              {[2.5, 5, 7.5, 10, 12.5, 15, 17.5].map((o) => (
                <line key={o} x1={o - 10} y1={10} x2={o} y2={0} stroke="#1c0f05" strokeOpacity={0.6} strokeWidth={1} />
              ))}
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
  burned,
  onToggleBurn,
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
  burned: boolean
  onToggleBurn: () => void
}) {
  const cb = useColourBlind()
  const reach = useReach()
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
            <PixelIcon sprite={unitSprite(u, cb)} /> {u.yellow ? 'Partner unit' : u.neutral ? 'Neutral' : UNIT_NAME[u.type]}:{' '}
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
            <PixelIcon sprite={joinerSprite(a.joiner, cb)} />{' '}
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
              <PixelIcon sprite={reinforcementSprite(a.unit, cb)} /> Reinforcement ({a.group})
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
            <PixelIcon sprite={burned ? SUPPLIES : SUPPLY_BOXES} /> {o.label}{' '}
            <button onClick={onToggleBurn} aria-pressed={burned} className="rounded border border-orange-700 px-2 py-0.5 text-orange-200 hover:bg-orange-900">
              {burned ? 'Show them unburnt' : 'Show them burning'}
            </button>
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
          {!reach.on && <p className="text-neutral-200">{describePotEffect(pot.effect)}</p>}
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
      {(map.warps ?? [])
        .filter(([a]) => sameTile(a, tile))
        .map(([, b]) => (
          <p key={`warp${tileKey(b)}`} className="text-cyan-300">
            Warp: a unit standing here is sent to ({b[0]}, {b[1]}), outlined on the map
          </p>
        ))}
      {(map.warps ?? []).some(([, b]) => sameTile(b, tile)) && (
        <p className="text-cyan-300">
          Warp platform: units are sent here from{' '}
          {(map.warps ?? [])
            .filter(([, b]) => sameTile(b, tile))
            .map(([a]) => `(${a[0]}, ${a[1]})`)
            .join(', ')}
          , outlined on the map
        </p>
      )}

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
  // Under the spoiler block a pot is only its kind, as the game names it: what it does shows once it's broken in the game.
  const reach = useReach()
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
                    {!reach.on && describePotEffect(p.effect)}
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
