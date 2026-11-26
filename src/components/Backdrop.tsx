import { useEffect, useRef, useState, useSyncExternalStore, type ComponentType } from 'react'
import { RouteBackground } from './RouteBackground'
import type { Route } from '../data/types'

/**
 * The page's backdrop: art behind every tab, one per game and per route (the user's call, 2026-11-26), the same in both apps: this
 * file is word for word the same in the Roster and the Armory (`src/components/Backdrop.tsx`), and so is RouteBackground.tsx; a change
 * to one goes to both. Each game's art is drawn in code, original, nothing from the games. A game's art takes the route it's shown for
 * and fades its own route changes in a second (Fates' colours and flowers); changing the game fades the whole backdrop over a second.
 *
 * Every game has its slot here; those still without art show the plain page until theirs is made. The routes each one's art can
 * follow are listed beside it.
 */
type Art = ComponentType<{ route?: string }>

const FATES_ROUTES = ['Birthright', 'Conquest', 'Revelation']

function FatesArt({ route }: { route?: string }) {
  return <RouteBackground route={(route && FATES_ROUTES.includes(route) ? route : 'all') as Route} />
}

export const BACKDROPS: Record<string, { art?: Art; routes?: string[] }> = {
  fe1: {},
  fe2: { routes: ['Alm', 'Celica'] },
  fe3: { routes: ['Book 1', 'Book 2'] },
  fe4: { routes: ['First generation', 'Second generation'] },
  fe5: { routes: ['16A', '16B'] },
  fe6: { routes: ['10A', '10B', 'Ilia', 'Sacae'] },
  fe7: { routes: ["Lyn's story", "Eliwood's story", "Hector's story"] },
  fe8: { routes: ["Eirika's route", "Ephraim's route"] },
  fe9: {},
  fe10: { routes: ['Part 1', 'Part 2', 'Part 3', 'Part 4'] },
  fe11: {},
  fe12: {},
  fe13: {},
  fates: { art: FatesArt, routes: FATES_ROUTES },
  fe15: { routes: ['Alm', 'Celica'] },
  fe16: { routes: ['Black Eagles', 'Blue Lions', 'Golden Deer', 'Crimson Flower', 'Silver Snow', 'Azure Moon', 'Verdant Wind'] },
  fe17: { routes: ['Main story', 'Fell Xenologue'] },
}

// The route each game's backdrop follows, as its screens report it (`useBackdropRoute`): kept for the visit, not saved.
let routes: Record<string, string | undefined> = {}
const listeners = new Set<() => void>()
const subscribe = (listener: () => void) => {
  listeners.add(listener)
  return () => listeners.delete(listener)
}

/** A game's screens tell the backdrop which route they're on (Fates' route; a game without one says nothing). */
export function useBackdropRoute(gameId: string, route?: string) {
  useEffect(() => {
    if (routes[gameId] === route) return
    routes = { ...routes, [gameId]: route }
    listeners.forEach((l) => l())
  }, [gameId, route])
}

/** The plain page, for the home screen and a game whose art isn't made yet. */
function Plain() {
  return <div className="h-full w-full bg-[#0a0a0a]" />
}

interface Layer {
  key: string
  gameId?: string
  /** The route it was showing when the next game's took over, kept while it fades out. */
  route?: string
}

/** The backdrop for the game shown (none: the home screen) and its route, fading over a second from the one before. */
export function Backdrop({ gameId }: { gameId?: string }) {
  const route = useSyncExternalStore(subscribe, () => (gameId ? routes[gameId] : undefined))
  const key = gameId ?? 'home'
  const [layers, setLayers] = useState<Layer[]>([{ key, gameId }])
  // The route shown at the last render, kept for the game's backdrop as it fades out.
  const shown = useRef(route)
  useEffect(() => {
    if (layers[layers.length - 1].key === key) return
    const leaving = shown.current
    setLayers((now) => [{ ...now[now.length - 1], route: leaving }, { key, gameId }])
    const done = window.setTimeout(() => setLayers((now) => now.slice(-1)), 1000)
    return () => window.clearTimeout(done)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  useEffect(() => {
    shown.current = route
  })
  return (
    <div aria-hidden="true" className="pointer-events-none fixed inset-0 -z-20">
      {layers.map((l, i) => {
        const Art = (l.gameId && BACKDROPS[l.gameId]?.art) || Plain
        const last = i === layers.length - 1
        return (
          <div key={l.key} className={`absolute inset-0 ${last && layers.length > 1 ? 'backdrop-fade-in' : ''}`}>
            <Art route={last ? route : l.route} />
          </div>
        )
      })}
    </div>
  )
}
