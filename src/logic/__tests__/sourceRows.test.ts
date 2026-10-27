import { describe, expect, it } from 'vitest'
import { FE7_ITEM_SOURCES } from '../../data/fe7/fe7ItemSources'
import { FE7_MAPS } from '../../data/fe7/fe7Maps'
import { FE7_ROUTE_NAME, FE7_STORY } from '../../data/fe7/fe7MapSet'
import { sourceRows } from '../sourceRows'

const mapOf = (id: string) => FE7_MAPS.find((m) => m.id === id)
const rows = (name: string) => sourceRows(FE7_ITEM_SOURCES[name], mapOf, FE7_STORY.short, FE7_ROUTE_NAME)

describe('the weapon page\'s "Where it turns up"', () => {
  it('puts every shop selling a weapon in one story on one row, with its chapters', () => {
    const shops = rows('Iron sword').filter((r) => r.text === 'Sold at the armory')
    expect(shops.map((r) => r.route)).toEqual(["Lyn's story", "Eliwood's story", "Hector's story"])
    for (const r of shops) expect(r.chapters.length).toBeGreaterThan(1)
  })

  it('keeps each way of getting a weapon apart, and each story', () => {
    expect(rows('Mani Katti')).toEqual([
      { text: 'Given to Lyn at the end of the chapter', later: false, route: "Lyn's story", chapters: ['Ch.2'] },
      { text: 'Carried by Lyn on joining', later: false, route: "Eliwood's story", chapters: ['Ch.15'] },
      { text: 'Carried by Lyn on joining', later: false, route: "Hector's story", chapters: ['Ch.16'] },
    ])
  })
})
