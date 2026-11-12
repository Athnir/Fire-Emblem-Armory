import { describe, expect, it } from 'vitest'
import { FE6_MAPS } from '../../data/fe6/fe6Maps'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE8_MAPS } from '../../data/fe8/fe8Maps'
import { FE17_MAPS } from '../../data/fe17/fe17Maps'
import type { ChapterMap, Tile } from '../../data/maps/types'
import { applyChanges, arrivalTurn, closedRooms, mapSteps, terrainAt, tileKey } from '../maps'

const find = (maps: ChapterMap[], id: string) => maps.find((m) => m.id === id)!
/** The map as it stands after its first `n` turns' changes. */
const atStep = (m: ChapterMap, n: number) => applyChanges(m, new Set(mapSteps(m).slice(0, n).flatMap((s) => s.ids)))

describe("a map its script changes on set turns: its states in turn order (the user's call)", () => {
  const ship = find(FE8_MAPS, 'fe8-ephraim-11')

  it("steps through the Phantom Ship's turns: a ship moves up on turn 2, the gangplanks drop on turn 3, a ship sails in on turn 5", () => {
    expect(mapSteps(ship).map((s) => s.turn)).toEqual([2, 3, 5])
    expect(mapSteps(ship).map((s) => s.label)).toEqual(['Turn 2, your phase', 'Turn 3, your phase', 'Turn 5, your phase'])
    expect(ship.changes.find((c) => c.turn === 5)!.effect).toBe('Turn 5, your phase: a ship sails in.')
    expect(ship.changes.find((c) => c.turn === 3)!.effect).toBe('Turn 3, your phase: the gangplanks are lowered.')
  })

  it("has the joiners arrive on the turn-5 ship's deck, not in the sea", () => {
    const joiners = ship.joiners!
    expect(joiners.map((j) => j.name).sort()).toEqual(["Dozla", "L'Arachel"])
    for (const j of joiners) {
      expect(terrainAt(ship, j.tile), j.name).toBe('we')
      const turn = arrivalTurn(typeof j.when === 'string' ? j.when : undefined)!
      expect(turn).toBe(5)
      const by = mapSteps(ship).filter((s) => s.turn <= turn).length
      expect(terrainAt(atStep(ship, by), j.tile), j.name).toBe('t3')
    }
  })

  it("leaves no piece of a ship behind: turn 2 undoes the opening's ship before drawing it alongside (0x2721)", () => {
    // The opening's ship stood in the bottom right; once it has moved up, only sea is left there.
    const moved = atStep(ship, 1)
    for (const t of [[17, 1], [18, 5], [19, 8]] as Tile[]) expect(terrainAt(ship, t)).not.toBe('we')
    for (const t of [[17, 1], [18, 5], [19, 8]] as Tile[]) expect(terrainAt(moved, t), tileKey(t)).toBe('we')
  })

  it('makes each turn change on the map as the turns before left it, so every timed change changes something', () => {
    for (const m of [...FE6_MAPS, ...FE7_MAPS, ...FE8_MAPS]) {
      const steps = mapSteps(m)
      steps.forEach((s, i) => {
        const before = atStep(m, i)
        const after = atStep(m, i + 1)
        expect(after.grid, `${m.id} turn ${s.turn}`).not.toEqual(before.grid)
      })
    }
  })

  it("reads an arrival's first turn from its words", () => {
    expect(arrivalTurn('Turn 5, your phase')).toBe(5)
    expect(arrivalTurn('Every turn from 4 to 6, your phase')).toBe(4)
    expect(arrivalTurn('Turn 3 (Hard: turn 2)')).toBe(3)
    expect(arrivalTurn('Every turn, enemy phase')).toBe(1)
    expect(arrivalTurn('As soon as one of your units stops in the marked area')).toBeUndefined()
  })
})

describe("a closed room hides what's in it until a door into it opens (the user's call)", () => {
  it("keeps The Trap's rooms closed, Sue and the chests in them, until a door's preview opens one", () => {
    const trap = find(FE6_MAPS, 'fe6-6')
    const sue = trap.units.find((u) => u.name === 'Sue')!
    const closed = closedRooms(trap)
    expect(closed.has(tileKey(sue.tile))).toBe(true)
    expect(trap.objects.filter((o) => o.type === 'chest' && closed.has(tileKey(o.tile))).length).toBeGreaterThan(0)
    const door = trap.changes.find((c) => (c.patch ?? []).some((p) => p.tile[0] === sue.tile[0] && p.tile[1] === sue.tile[1]))!
    expect(closedRooms(applyChanges(trap, new Set([door.id]))).has(tileKey(sue.tile))).toBe(false)
  })

  it('leaves open a room one of your starting tiles is in', () => {
    const sk = find(FE17_MAPS, 'fe17-m015-sk')
    const inRooms = sk.starts.filter((t) => terrainAt(sk, t) === 'ws')
    expect(inRooms.length).toBeGreaterThan(0)
    for (const t of inRooms) expect(closedRooms(sk).has(tileKey(t))).toBe(false)
  })
})
