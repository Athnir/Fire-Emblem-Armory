import { createContext, useContext } from 'react'

/**
 * The map page's colour-blind friendly look (its switch, remembered on the device; off by default, so the approved maps keep their look):
 * the armies told apart by their markers' shapes and edges, the starting tiles by their corners and every outline by its dashes, in Okabe
 * and Ito's colours, which stay apart for red-green and blue-yellow colour blindness alike.
 */
export const ColourBlindContext = createContext(false)

export const useColourBlind = () => useContext(ColourBlindContext)
