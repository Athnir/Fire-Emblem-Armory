/** Combat bonuses a support gives (Hit, Avoid, Crit, Dodge), by name. */
export type CombatBonus = Partial<Record<'hit' | 'avoid' | 'crit' | 'dodge' | 'atk' | 'def', number>>
/** Stat bonuses (Pair Up), by stat. */
export type StatBonus = Partial<Record<'str' | 'mag' | 'skl' | 'spd' | 'lck' | 'def' | 'res' | 'mov', number>>
