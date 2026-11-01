import { createContext, useContext } from 'react'
import type { Difficulty } from '../data/maps/types'

/** The difficulty picked in the bar for the game being shown: every screen shows only that difficulty's data. */
export const DifficultyContext = createContext<Difficulty>('Normal')

export const useDifficulty = () => useContext(DifficultyContext)

/** Whether something that holds on `on` (every difficulty when absent) holds on the picked difficulty. */
export const onDifficulty = (difficulty: Difficulty, on?: readonly string[]) => !on || on.includes(difficulty)
