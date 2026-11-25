import type { TerrainInfo } from './fatesTerrain'

/**
 * Map data model. Coordinates everywhere are the games' own convention: the bottom-left tile is
 * (1, 1), X counts right and Y counts up. Some sources count rows from the top instead (the Fire
 * Emblem Wiki's chapter pages do), so each source's numbering is converted once, at data entry.
 */
/** The difficulties the games name: Shadow Dragon's Hard modes are Hard, Brutal, Savage, Fiendish and Merciless. */
export type Difficulty =
  | 'Easy'
  | 'Normal'
  | 'Hard'
  | 'Lunatic'
  | 'Brutal'
  | 'Savage'
  | 'Fiendish'
  | 'Merciless'
  | 'Maddening'
  | 'Maniac'
  | 'Reverse Lunatic'
export const DIFFICULTIES: Difficulty[] = ['Normal', 'Hard', 'Lunatic']

export type Tile = [x: number, y: number]

/** A tile that can differ by difficulty. Conquest 12's Dragon Vein, for one, sits on a different
 * tile on Lunatic. `default` applies to any difficulty not listed. */
export type DifficultyTile = { default: Tile } & Partial<Record<Difficulty, Tile>>

import type { TerrainCode } from './terrainCodes'

export type { TerrainCode }

export type StatKey = 'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'res'

/** What breaking a pot does to every unit (either side) within its radius. */
export type PotEffect =
  | { type: 'heal'; percent: number }
  | { type: 'damage'; percent: number }
  /** +/- to listed stats. `kind` follows the game's split: a "tonic" boost (+2) and a "status"
   * boost (+4) stack with each other, but not with another of the same kind. */
  | { type: 'stats'; kind: 'tonic' | 'status' | 'debuff'; changes: Partial<Record<StatKey, number>> }
  | { type: 'silence' }
  | { type: 'freeze' }
  | { type: 'hex' }

export type MapObject =
  | { type: 'pot'; tile: Tile; pot: 'medicine' | 'poison'; effect: PotEffect; radius: number }
  | { type: 'chest'; tile: Tile; contents: string }
  | { type: 'door'; tile: Tile }
  /** `reward` is empty when a visit gives nothing. */
  | { type: 'village'; tile: Tile; reward: string; note?: string }
  /** A castle on the map (Genealogy of the Holy War): its name, and what it means for the chapter (home castle, the one to seize). */
  | { type: 'castle'; tile: Tile; name: string; note?: string }
  /** Something buried in an area ([left, bottom, right, top]) for a unit to find (Path of Radiance's desert). */
  | { type: 'hidden'; tile: Tile; area: [number, number, number, number]; contents: string; note?: string }
  /** A ballista (Path of Radiance): a bow user on `tile` fires the `weapon` of the machine on `machine`, next to it. `mounted`: the
   * bow user stands on the machine itself (The Blazing Blade's and The Sacred Stones': an Archer or Sniper). */
  | { type: 'ballista'; tile: Tile; machine: Tile; weapon: string; mounted?: true; difficulties?: Difficulty[] }
  /** A trap that goes off on its own (The Blazing Blade's and The Sacred Stones' fire tiles, gas vents and arrow launchers): what it
   * does and when. `difficulties` when only some difficulties have it (The Sacred Stones' extra traps on Hard). */
  | { type: 'trap'; tile: Tile; kind: 'fire' | 'gas' | 'arrow'; note: string; difficulties?: Difficulty[] }
  /** A pit trap in the floor (Path of Radiance's Ch.23 bridge): a ground unit that steps on it falls in and stops. */
  | { type: 'pit'; tile: Tile }
  /** A house ([left, bottom, right, top]) the enemy's arsonists can set alight; a unit beside it can put it out
   * (Radiant Dawn Part 3 Ch.9). */
  | { type: 'fire'; tile: Tile; area: [number, number, number, number] }
  /** A shop on the map (The Binding Blade): an armory, a vendor or a secret shop, and what it sells. `note`: how it's reached,
   * where its tile isn't open from the start (Thracia 776's Chapter 24 secret shop, on a door). */
  | { type: 'shop'; tile: Tile; kind: string; stock: string[]; note?: string }
  /** An event tile (Awakening): a unit that stops on it gets a random bonus. */
  | { type: 'event'; tile: Tile }
  /** A shiny spot (Fates' challenge battles): a unit that stops on it finds gold, ore, an item or weapon experience. */
  | { type: 'shiny'; tile: Tile }

export interface MapUnit {
  /** boss = the chapter's boss; named = another named foe worth drawing attention to; enemy = a
   * common foe (shown as a plain marker); ally = a named green (NPC) unit. */
  type: 'boss' | 'named' | 'enemy' | 'ally'
  name: string
  tile: Tile
  /** A unit that covers a square of tiles, this many on a side (Three Houses' monsters: 2, or 3 for the largest), its `tile` the
   * square's top-left one. Its icon is stretched over the square, and tapping any tile of it shows the unit. */
  size?: number
  /** A monster's health bars (Three Houses: two to four), each a pip along the bottom of its marker. */
  bars?: number
  note?: string
  /** Two units paired up on one tile. */
  paired?: boolean
  /** The supporting unit of a pair-up, when it's worth naming (a generic one is just its army's name). */
  partner?: string
  /** Items dropped on defeat. */
  drops?: string[]
  /** What it can't be disarmed of: locked to it in the placement file (Radiant Dawn's '/L' slots: Ike's Ragnell in Part 3 Ch.13). */
  locked?: string[]
  /** What the unit carries and fights with (a foe's own weapons, staves and items), from the placement files. */
  carries?: string[]
  /** Who can talk to them, and whether that recruits them ('Recruit: talk with Ike'). */
  talk?: string
  /** Set only on bosses / named foes that Niles (Conquest) or Orochi (Birthright) can capture: the ones the game keeps a
   * prisoner record for (`PID_捕獲_…`). Anyone playable on any route never can; generic foes can but aren't worth noting. */
  capturable?: true
  /** Rare things it holds that you can take from it and it doesn't drop: nothing in the game sells them (an Energy Drop, a Red
   * Gem, a crest). Taken by the game's own way, a thief's Steal, or capturing it where the map set says so (Thracia 776, where
   * capture takes weapons too). A small gem badge of its own. */
  steal?: string[]
  /** Only present on these difficulties; on all of them when omitted. */
  difficulties?: Difficulty[]
  /** A green unit with no name of its own (another army's soldier, a horse): drawn as a plain green dot, not the
   * person icon, which is kept for named green units. */
  generic?: true
  /** Where its AI sends it, when that's a fixed spot rather than the nearest (Radiant Dawn Part 3 Ch.3's
   * horses each run for their own exit): shown when the unit is tapped. */
  goesTo?: Tile[]
  /** Who the game places on this tile instead when this character is gone (Radiant Dawn: Lethe died earlier, so
   * Kezhda stands here; Jill left Micaiah's army, so a Dragonmaster does). The map's stand-in toggle swaps them all. */
  standIn?: StandIn
  /** Hidden under terrain a change clears (Revelation 10's foes under the snow): shown once its tile is dug. */
  buried?: true
  /** A partner unit (Path of Radiance's army 3): another army that fights on your side and that you can partly direct, drawn in
   * yellow rather than green. */
  yellow?: true
  /** An army neutral to yours (Genealogy of the Holy War's third relation: it neither fights you nor helps you until a script turns
   * it), drawn in a colour of its own (yellow). */
  neutral?: true
  /** Goes for villages and chests, razing or looting what it reaches (and some leave by an exit after), or, as 'fire', for houses
   * to set alight (Radiant Dawn's Part 3 Ch.9): a small torch badge. */
  looter?: true | 'fire'
}

export interface StandIn {
  type: MapUnit['type']
  name: string
  note: string
  generic?: true
  drops?: string[]
  steal?: string[]
  /** What a talk with it does, where the game takes it and the one it stands in for alike (Genealogy of the Holy War's 0x15 and
   * 0x16 talks take a child and their substitute as one). */
  talk?: string
  /** When it stands in: 'Lethe has died earlier'. */
  when: string
}

/** When a group arrives, read from the chapter's script, and any map areas whose entry triggers it. */
export interface Arrival {
  /** One sentence, or one per difficulty when they differ ("Turn 4, enemy phase"). */
  when?: string | Partial<Record<Difficulty, string>>
  /** Entering (or, for 'enemy', reaching) one of these brings the group in, or stops it where its time says so ("until one of your
   * units enters the marked area"): [left, bottom, right, top]. A group set off in steps
   * (Three Houses' Chapter 8: one area at the start of your phase, then another at an enemy phase's) numbers each area by its step,
   * as its time names them ('area 1', 'area 2'). */
  areas?: { who: 'player' | 'enemy'; rect: [number, number, number, number]; step?: number }[]
}

/** A group of enemies that arrives mid-chapter: each moves from where it enters to its tile. */
export interface ReinforcementGroup extends Arrival {
  id: string
  /** The game's own group number ("Group 3"). */
  label: string
  units: (MapUnit & { from?: Tile })[]
}

/** A playable unit that joins mid-chapter, walking in from `from` to `tile`. */
export interface Joiner extends Arrival {
  name: string
  tile: Tile
  from: Tile
  /** Joiners listed together arrive together. */
  group: string
  /** Arrives as a green unit (another army, or a recruit you still have to talk to), not under your control. */
  ally?: boolean
  /** A green unit with no name of its own: a plain green dot, like `MapUnit.generic`. */
  generic?: true
  /** Arrives as a partner unit (Radiant Dawn's army 3, Part 3 Ch.11's Tibarn): drawn in yellow, like `MapUnit.yellow`. */
  yellow?: true
  /** Arrives neutral to your army, like `MapUnit.neutral`. */
  neutral?: true
  /** Anything else about them ('Carrying Leanne'). */
  note?: string
  /** Who can talk to them, and whether that recruits them. */
  talk?: string
  /** Goes for villages and chests, as `MapUnit.looter` (The Sacred Stones' Colm, a green thief): a small torch badge. */
  looter?: true
  /** Where its AI sends it, as `MapUnit.goesTo`: shown when it's tapped. */
  goesTo?: Tile[]
  /** Who comes instead when this character is gone, as `MapUnit.standIn` (Genealogy of the Holy War's substitutes: Creidne
   * when Larcei wasn't born). */
  standIn?: StandIn
}

export interface MapObjective {
  /** burn: supplies to set alight (Radiant Dawn Part 3 Ch.3), one objective per set. */
  type: 'escape' | 'seize' | 'defend' | 'arrive' | 'burn'
  tiles: Tile[]
  label: string
}

/** Something that reshapes the map when triggered. Previewed one at a time from its own panel. */
export interface MapChange {
  id: string
  /** A Dragon Vein a royal uses, a wall / partition attacked down, a boulder rolling down its path, a torch
   * lit on a fog map (Radiant Dawn), a lava floor that turns to hazard on set turns (Awakening Ch.18), or another
   * change a chapter's script makes (Awakening Ch.23's barrier falling). */
  trigger: 'dragonVein' | 'breakable' | 'boulder' | 'torch' | 'eruption' | 'event' | 'trap'
  tile: DifficultyTile
  usableBy: string
  effect: string
  /** Breaks every pot on the map (each one's effect still fires). */
  breaksAllPots?: boolean
  /** Tiles this change reshapes, and what each becomes. */
  patch?: { tile: Tile; becomes: TerrainCode }[]
  /** A boulder's route, from where it starts to where it ends. */
  path?: Tile[]
  /** A torch: once lit, it lights every tile within this many steps. */
  radius?: number
  /** A torch already lit when the chapter starts: previewing it puts it out. */
  lit?: boolean
  /** A change that covers an area rather than one tile (Revelation 10's snow): listed on every tile it reshapes, with no
   * marker of its own. */
  wide?: true
  /** Cleared a tile at a time (Revelation 10's snow): digging a tile clears it and the four beside it. Previewed tile by tile
   * as you dig, or all at once. */
  dig?: true
  /** A vein whose effect can't be shown from the chapter's start (Revelation 11's only lower spikes a trap has raised): no
   * preview, its text says what it does. */
  noPreview?: true
  /** The switching wall (`ChapterMap.switchWalls`) this vein flips, up or down, instead of a patch (Revelation 16). */
  flips?: number
  /** Swaps the map's coloured rooms while previewed (Revelation 21's veins). */
  swapsRooms?: true
  /** A trap: one of your units stopping in this zone ([left, bottom, right, top]) springs it (Birthright 10's bamboo spikes).
   * Outlined on the map. */
  zone?: [number, number, number, number]
  /** Changes of one kind that can be previewed all at once as well as one by one (Path of Radiance Ch.23's pits). */
  group?: string
  /** A breakable that's a snag, not a wall (the GBA games' fallen trees on bridges): drawn as one. */
  snag?: true
  /** The difficulties it happens on, where it isn't all of them (Fell Xenologue 6's islands sinking on Hard and Maddening). */
  difficulties?: Difficulty[]
  /** The turn a chapter's script makes it on (the GBA games): the map's states step through these in turn order, each patch made
   * on the map as the turns before left it (The Sacred Stones' Phantom Ship: a ship sails up on turn 2, another on turn 5). */
  turn?: number
}

/** A fence: a thin barrier along one side of a tile that units can't cross. */
export interface MapWall {
  tile: Tile
  side: 'n' | 'e' | 's' | 'w'
  /** No unit crosses it, fliers included. Without it, only ground units are stopped (Path of Radiance's fences). */
  all?: true
  /** A step between two heights (Path of Radiance: a ship's decks, a terrace's edge), drawn as a railing, not a fence. */
  step?: true
}

/**
 * Walls a chapter's script raises and lowers (Revelation 16's flame walls). The map's grid has them all up; the battle starts with
 * one of `starts` down (the game picks it at random), each of `turns` flips its walls on every turn that divides by `every`, from
 * turn `from`, and a vein flips its own. A tile two walls share stays up while either is; a tile with every wall on it down is
 * `down`.
 */
export interface SwitchWalls {
  down: TerrainCode
  walls: { id: number; tiles: Tile[] }[]
  starts: number[][]
  turns: { every: number; from: number; walls: number[] }[]
}

/** Three Houses' routes from Chapter 12 (each also lists the White Clouds chapters of the house it comes from), and the DLC's side
 * story. */
export type ThreeHousesRoute = 'Crimson Flower' | 'Silver Snow' | 'Azure Moon' | 'Verdant Wind' | 'Cindered Shadows'

export interface ChapterMap {
  id: string
  /** Fates' routes; The Blazing Blade's stories (Lyn's, Eliwood's, Hector's); The Sacred Stones' routes and side maps; 'Story' for
   * a game without them, and 'Trial' for Path of Radiance's trial maps. */
  route:
    | 'Birthright'
    | 'Conquest'
    | 'Revelation'
    | 'Shared'
    | 'Paralogue'
    | 'DLC'
    | 'Story'
    | 'Trial'
    | 'Lyn'
    | 'Eliwood'
    | 'Hector'
    | 'Eirika'
    | 'Ephraim'
    | 'Extra'
    | 'Alm'
    | 'Celica'
    | 'Challenge'
    | 'Skirmish'
    | ThreeHousesRoute
    | 'Auxiliary'
    /** Engage's DLC side story, a story of its own. */
    | 'Fell Xenologue'
  /** Paralogues, challenge battles and The Sacred Stones' skirmishes only: the routes that can reach it. */
  availableIn?: ('Birthright' | 'Conquest' | 'Revelation' | 'Eirika' | 'Ephraim' | ThreeHousesRoute)[]
  /** A challenge battle (Fates): the chapter or paralogue map it's fought on, whose terrain it keeps. */
  challengeOf?: string
  /** A world-map skirmish (Awakening, The Sacred Stones): the chapter or paralogue whose location it's fought at. */
  skirmishOf?: string
  /** A challenge battle's foe groups (Fates): the tiles each one's foes can stand on, outlined on the map. A battle has one
   * group, either one, or both in a dual-boss battle. */
  foeGroups?: { label: string; tiles: Tile[] }[]
  /** Coloured rooms that do something to whoever acts in them (Revelation 21: blue promotes an enemy, red demotes it), each set
   * with its colour and what it does. A change marked `swapsRooms` swaps the sets' colours and effects while it's previewed. */
  rooms?: { color: 'red' | 'blue'; effect: string; rects: [number, number, number, number][] }[]
  /** Walls the chapter raises and lowers (Revelation 16's flame walls): picked on the map by the set the battle started with
   * and the turn, with the veins that flip them previewed on top. */
  switchWalls?: SwitchWalls
  /** The game's heading for it, where it isn't a plain chapter ('Xenologue', 'Heirs of Fate', 'Hero Battle'). */
  heading?: string
  chapter: number
  title: string
  location?: string
  width: number
  height: number
  /** Top row FIRST (y = height), so the file reads like the map. Two characters (one TerrainCode) per tile. */
  grid: string[]
  /** The map's own colours for its ground and water codes (the GBA games': scripts/gba_ground.py, read from each map's art), so
   * Ilia's plains are snow and a castle's floor its own stone. Unset: each code's colour. */
  fills?: Partial<Record<TerrainCode, string>>
  /** Stairs that take a unit to another tile (the Rainbow Sage's platforms): each pair's ends lead to each other. */
  links?: [Tile, Tile][]
  /** Fences along tile sides (Path of Radiance). */
  walls?: MapWall[]
  /** Its trees are snowy (pale grey on the game's minimap: Radiant Dawn's Part 3 Endgame and Part 4 Prologue). */
  snowyTrees?: true
  /** What the game's art draws on a tile that its terrain doesn't say ("x,y" -> its kind), over the tile's own look: a door nothing
   * opens in a wall and a stone bridge's side under its deck (Gaiden's, which play as the walls they are), bones lying on the ground
   * (Mystery of the Emblem's deserts), an altar no unit steps onto (Shadow Dragon and the Blade of Light's Chapter 24), stairs on a
   * floor or path (Mystery of the Emblem's, which play as the tile they're on), rocks where the game's bones lie (Awakening's Chapter 9,
   * whose scene draws rocks there). */
  decor?: Record<
    string,
    | 'door' | 'bones' | 'bridge' | 'altar' | 'stairs' | 'statue' | 'windmill' | 'yurt' | 'crates' | 'rock' | 'umbrella' | 'palm' | 'parasol'
    | 'pillar' | 'dragon' | 'shack' | 'barrel' | 'downstairs' | 'house' | 'fountain' | 'grave' | 'horse' | 'carriage'
    | 'sarcophagus' | 'rubble' | 'candle' | 'table' | 'candelabra' | 'garden' | 'tree' | 'slab' | 'ice' | 'frozenFountain'
    | 'stall-red' | 'stall-blue' | 'stall-yellow' | 'stall-orange' | 'stall-purple' | 'roof-red' | 'roof-blue' | 'roof-yellow'
    | 'roof-slate' | 'roof-grey' | 'roof-tan' | 'roof-green' | 'roof-brown'
    | 'roundYurt' | 'zenGarden' | 'cherry' | 'walledHouse' | 'warpSigil' | 'warpPad'
  >
  /** The blocks its roofs and stalls are drawn over, (x0, x1, y0, y1) each, where buildings side by side would join into one block of
   * one paint (Three Houses': each building block parted into the rectangles a roof covers, the user's call: roofs as Fates' are). */
  decorBoxes?: [number, number, number, number][]
  /** Its breakable walls drawn as the walls round them (a plain wall where none are), the crack of a wall you break over them (Three
   * Houses': the user, one breakable overlay over the tile it is, not a look of its own for each kind of breakable). */
  breakablesAsWalls?: true
  /** Its floors that give Avoid drawn in a pattern of their own, apart from those that give Def (Three Houses' Avo Floor and Cover: the
   * user, two kinds of tile with their own numbers drawn alike). */
  avoFloors?: true
  /** A zoomed-in map's villages and shops drawn as the buildings in them (the GBA games' and Thracia 776's, which draw a village's
   * house, a shop or an arena in each lot or on its tile: the user's call): each lot shared out among its entrances, a shop alone a
   * small house of its kind (MapViewer's buildings). */
  villageBuildings?: true
  /** Its art draws the map zoomed out (the GBA games' world-scale tilesets: the user's call, 2026-11-23): its villages are fenced
   * yards of little houses and every building alone on a tile (a house, a shop, an arena) its icon, never the zoomed-in maps' big
   * houses; a lot round a castle gate is still the castle drawn whole (MapViewer's buildings). */
  zoomedOut?: true
  /** Its dwellings are Sacae's yurts (the GBA games' plains of Sacae: the user's call): a house on its tile a little yurt, a castle drawn
   * whole a chieftain's great yurt with four small ones round it. */
  yurts?: true
  /** A shop on a ship's deck is drawn as its icon, not a house (The Blazing Blade's: the user, houses make no sense on boats). */
  deckShops?: true
  /** A house with nothing to visit on sand stands on the sand, not a village's green yard (The Blazing Blade's deserts: the user). */
  sandYards?: true
  /** Shop signs on a dark board, their sword, potion or card bright (The Blazing Blade's and The Sacred Stones': the user, the sword was
   * nearly invisible; wanted in every game, the frozen ones on the user's say). */
  clearSigns?: true
  /** A village's yard grass through and through, never the texture of the cobbles beside it (The Sacred Stones': the user, 'green
   * cobble'). */
  yardGrass?: true
  /** A barrel beside wood (a pier's or a ship's boards) stands on the wood (The Sacred Stones': the user). */
  barrelsOnWood?: true
  /** Its walls drawn with a top and a face: a wall with floor below it its face, darker, in bricks; the rest its top, lighter (the Lagdou
   * Ruins: the user, as Gaiden's cave walls). */
  wallFaces?: true
  /** Buildings the user turned round, [x0, x1, y0, y1] each: every tile in the block drawn as its partner across it, flipped (The
   * Blazing Blade's Lyn 6 house, its door over the cobbles; Chapter 12's tower). */
  mirror?: [number, number, number, number][]
  /** The ground an icon stands on where the user set it, "x,y" -> its code (The Blazing Blade's Badon: a barrel at the dock's edge on
   * the dock's wood). */
  standOn?: Record<string, TerrainCode>
  /** Its wooden fences drawn bolder, light wood edged dark, so they show on the ground (Radiant Dawn's: the user, Part 3 Ch.3's were
   * hard to see). */
  boldFences?: true
  /** Which way each ledge climbs, "x,y" -> the side of its higher ground ('n', 's', 'e', 'w', as drawn): its chevrons point up the ledge,
   * the way the height's advantage lies (Radiant Dawn's: the user). A map with them doesn't draw the sides the game closes between two
   * ledges side by side (a unit can't run along a ledge), though they stay closed. */
  ledgeUp?: Record<string, 'n' | 's' | 'e' | 'w'>
  /** A ship's gangplank, its tiles ("x,y") drawn as a wooden bridge's planks with a rail along each side, whatever the game names them
   * (Path of Radiance's Ch.11: the user, a gangplank up to the ship, not stairs down). The tiles keep their own numbers. */
  gangplanks?: string[]
  /** Its bridges two tiles wide or more are each drawn as one bridge, its planks laid across the water along its sides and a rail along
   * each side over water (Shadow Dragon and the Blade of Light's: the user, Chapter 13), not each tile the way its neighbours run. */
  wideBridges?: true
  /** Its bridges each read by the box round them, as if whole, broken spans and zigzags too: every tile's planks across the box's
   * span, and a rail only along the box's long sides (Shadow Dragon's Chapter 20x: the user, rails at the gaps and planks turned). The
   * boxes (x0, x1, y0, y1) are given where its pieces would make a box no bridge has (New Mystery's Chapter 12: the castle's flanks
   * beside its top walkway). */
  wholeBridges?: true | [number, number, number, number][]
  /** Floor its art draws as a wooden bridge, drawn as one, its numbers kept (New Mystery's Chapter 12's walkway down to its castle). */
  bridgeFloors?: string[]
  /** Bridges whose tiles all run one way though the bridge turns or jogs, by tile ("x,y" -> its span): each tile's planks laid across
   * that way, a rail on each of its sides over water (Fates' Chapter 3: the user, a turning bridge, not a broken one two tiles wide). */
  bridgeSpans?: Record<string, 'ew' | 'ns'>
  /** Each partition at a boat's end ("x,y" -> the way it points), drawn as the boat's bow over the water (Fates' Birthright 12 and
   * Conquest 14: the user, a cap for the boats' ends, turned and mirrored, over the water). */
  boatEnds?: Record<string, 'n' | 's' | 'e' | 'w'>
  /** Its bones lying in blocks are each one great bone, its grain along it (Awakening's Chapter 10, the giant skeleton's ribs: the user,
   * not an icon a tile). */
  boneBlocks?: true
  /** Its plain is a dragon's back, drawn as its scales (Awakening's Endgame, on Grima: the user, a dragon scale pattern). */
  scales?: true
  /** Its fountains drawn round, as its scene shows them, the plaza's ground in the block's corners (Awakening's Harvest Scramble: the
   * user, the fountain and plaza as circles). */
  roundFountains?: true
  /** Its houses' roofs grey, as its art paints them (Fates' Paralogue 20: the user's notes on its houses), not the town houses' red. */
  greyRoofs?: true
  /** Its muck drawn as a bog, its mud and puddles with no icon (Fates' Boo Camp: the user, the bog texture). */
  muckAsBog?: true
  /** Tiles whose mark the game doesn't draw there ("x,y"), drawn as the ground round them, their numbers kept (a Fates challenge's spent
   * village with no house over it: Revelation 14's at (2, 21) and (15, 21), the user: not there). */
  bareTiles?: string[]
  /** Sigils that send a unit standing on one to another tile, [from, to] (Fates' Revelation 18: the user, the warp platforms and where
   * each warp goes). */
  warps?: [Tile, Tile][]
  /** The tiles of walls the chapter raises and lowers (Fates' Revelation 16's flame walls), drawn as flame walls up or down wherever
   * they stand (the user: a fire wall tile with an up and a down look), the challenge's all down. */
  flameWalls?: string[]
  /** Its two-tile villages are walled compounds of little houses round a paved yard, as the DS games draw them (Shadow Dragon's and
   * New Mystery's: the user's call), not the older games' small house with a low wall. */
  walledVillages?: true
  /** Tents turned side-on, their doors in their sides (Radiant Dawn's Part 3 Ch.3, where units come out the side: the user), by the
   * tent's middle tile: the side its door is on. */
  tentDoors?: Record<string, 'e' | 'w'>
  /** Tiles drawn in ruins though their terrain stands (a Fates challenge battle's houses whose villages are spent: the user's call),
   * by tile key: the house's own tiles, and its village before it as rubble-strewn ground. */
  ruins?: string[]
  /** What a wall that shares its numbers with other kinds is, by the 3D model on it (Radiant Dawn's: its fences, sandbags and outer
   * walls are one terrain, as its pillars and castle walls are): "x,y" -> sandbags, a low outer wall or a pillar; a fence has none. A
   * wall the art draws as something else: a low stone wall (the GBA games' fences), rock (Gaiden's cave walls' faces, which fliers
   * cross), a ship's wooden wall (The Blazing Blade's cabins), bricks in its own colour (Thracia 776's lit roofs), a ship's wood
   * (Path of Radiance's masts, cabins and hulls). */
  wallLooks?: Record<string, 'sandbags' | 'wall' | 'pillar' | 'stone' | 'rock' | 'ship' | 'bricks' | 'wood' | 'pit' | 'fence' | 'timber' | 'cliff' | 'sky'>
  /** What each odds-and-ends tile holds, by the 3D model on it (the Tellius maps): "x,y" -> its kind. */
  props?: Record<string, 'candle' | 'box' | 'barrel' | 'cart' | 'flowerpot' | 'statue' | 'pillar' | 'sandbags' | 'gold' | 'roof'>
  /** A town packed so close that its houses show only their roofs (Radiant Dawn's Part 1 Ch.1 and Ch.3): every house tile a roof but a
   * door over each place to visit, a church's front row kept, and a chimney on these tiles ("x,y"). `houses`: the user's marks, which
   * roof tiles make each house ("x,y" -> its number; 0 is no house: odds and ends, drawn as such),
   * the game's house models where the user hasn't marked them; a wall a house's model stands on is that house, and one a market's
   * stands on (`stalls`) its stalls, both railed round (no unit enters them, fliers included: the Prologue's, the user's call); `ground`: bare walls drawn as the
   * ground round them, railed off the same way (the user's call). */
  rooftops?: { chimneys: string[]; houses?: Record<string, number>; stalls?: string[]; ground?: string[] }
  /** A night chapter (Path of Radiance's Flight! and Day Breaks): what its own colours don't cover (trees, props) is drawn in shade. */
  night?: true
  /** Tiles under Revelation's darkness: the grid holds the terrain beneath; nothing enters until it lifts. */
  dark?: Tile[]
  /** A grinding map (Fates DLC): its reinforcements spawn at random, so not every group arrives. Every other
   * map's reinforcements are fixed by its script. */
  randomSpawns?: true
  /** What the groups are, where they aren't reinforcements (Echoes: a dungeon's formations and fixed encounters, a cemetery's
   * layouts): said in place of the usual line about when they arrive. */
  groupsNote?: string
  /** Fog of war: everything outside the light of the torches being previewed as lit is shaded. */
  fog?: boolean
  /** Fog on these difficulties only (Path of Radiance's Ch.5, on Hard). */
  fogOn?: string[]
  /** How many steps your army sees in the fog where the fog is there at the start (the chapter's vision): the map shows a foe only
   * within that of the tiles it starts on, or in a lit torch's light. */
  vision?: number
  /** The game draws what your units can't see black, the ground too (Thracia 776): how many steps each of them sees (the chapter's
   * vision). Under the spoiler block every tile further than that from the starting tiles is black. */
  blackFog?: number
  /** Clouds that drift one tile left each phase (Radiant Dawn Part 2's Prologue): the whole map's pattern on the
   * shown rows (top first, '#' a cloud), the pattern column at the map's column 1, and the chapter's turns. */
  clouds?: { pattern: string[]; left: number; turns: number }
  victory: string
  defeat: string
  objectives: MapObjective[]
  units: MapUnit[]
  starts: Tile[]
  reinforcements?: ReinforcementGroup[]
  joiners?: Joiner[]
  /** What each of your own units starts the chapter carrying (Fates): weapons you hold from this chapter on. */
  kit?: { name: string; items: string[] }[]
  /** The lord's own starting tile (Corrin's, Ike's; one of `starts`), when known. */
  corrinStart?: Tile
  /** Whose starting tile `corrinStart` is, where it isn't the game's one lord (Radiant Dawn's change with each Part). */
  lord?: string
  /** Units besides Corrin the game deploys for you: on a fixed tile, or (no tile) wherever you place them. */
  forced?: { name: string; tile?: Tile; standIn?: Pick<StandIn, 'name' | 'when'> }[]
  objects: MapObject[]
  changes: MapChange[]
  /** Short facts only (who can't deploy, when reinforcements come), not strategy. */
  notes: string[]
  /** Notes that hold on some difficulties only, shown on those (The Binding Blade's Hard: foes gain levels' worth of growth their
   * shown level doesn't count); one with `from` holds only once that story map is reached (Echoes' encounters from a later act). */
  notesOn?: { note: string; difficulties: Difficulty[]; from?: string }[]
  /** Facts still to be confirmed in-game, shown in the UI rather than presented as certain. */
  unconfirmed?: string[]
  /** This map's exceptions to the game-wide terrain table (e.g. Chapter 1's 50% healing tile). */
  terrainOverrides?: Partial<Record<TerrainCode, Partial<TerrainInfo>>>
  /** The difficulties this map is played on, where it's fewer than the game's (The Blazing Blade's Lyn's story: Normal only). */
  difficulties?: Difficulty[]
  /** The game's own terrain table, for a game other than Fates. */
  terrain?: Partial<Record<TerrainCode, TerrainInfo>>
}
