import { createContext, useContext } from 'react'
import { SEES_ALL } from '../logic/spoiler'
import type { Reach } from '../logic/spoiler'

/** How far the spoiler block has opened the game being shown; every screen reads it to hide what's ahead. */
export const ReachContext = createContext<Reach>(SEES_ALL)

export const useReach = () => useContext(ReachContext)
