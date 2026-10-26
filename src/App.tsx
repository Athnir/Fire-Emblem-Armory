import { useEffect, useMemo, useState } from 'react'
import { ReachContext } from './components/Reach'
import { SpoilerBar } from './components/SpoilerBar'
import { TriangleTab } from './components/TriangleTab'
import { TrueHitCalculator } from './components/TrueHitCalculator'
import { DEFAULT_GAME, GAMES } from './games'
import type { GameParts } from './games'
import { reachOf, SEES_ALL, walkFork } from './logic/spoiler'
import { saveBlock, saveProgress, saveRoutes, savedBlock, savedProgress, savedRoutes } from './logic/spoilerStore'

type Tool = 'weapons' | 'trueHit' | 'triangle' | 'maps' | 'supports'
const TOOLS: { id: Tool; label: string }[] = [
  { id: 'weapons', label: 'Weapons & forging' },
  { id: 'trueHit', label: 'True hit' },
  { id: 'triangle', label: 'Weapon triangle' },
  { id: 'maps', label: 'Maps' },
  { id: 'supports', label: 'Supports' },
]
/** Tools that show what the story hands out, so the spoiler block has to know the game's chapters. */
const NEEDS_STORY: Tool[] = ['weapons', 'maps']

const GAME_KEY = 'fe-armory-game'

/** The last game picked on this device, so the app reopens on it. */
function savedGame(): string {
  try {
    const id = localStorage.getItem(GAME_KEY)
    if (id && GAMES.some((g) => g.id === id)) return id
  } catch {
    // Storage can be blocked (private mode); fall back to the default game.
  }
  return DEFAULT_GAME
}

function App() {
  const [block, setBlock] = useState(savedBlock)
  // With the spoiler block on, the app opens on a blank field rather than on a game.
  const [gameId, setGameId] = useState(() => (savedBlock() ? '' : savedGame()))
  const [picked, setTool] = useState<Tool>('weapons')
  const [progress, setProgress] = useState(savedProgress)
  const [routes, setRoutes] = useState(savedRoutes)
  const game = GAMES.find((g) => g.id === gameId) ?? null
  // A game's screens and data are their own file, fetched the first time it's picked (the build precaches them all, so
  // that works offline too once the app has installed).
  const [loaded, setLoaded] = useState<Record<string, GameParts>>({})
  const [failed, setFailed] = useState<string | null>(null)
  const [attempt, setAttempt] = useState(0)
  const parts = game ? loaded[game.id] : undefined
  // A game with nothing like supports (FE4) has no Supports tab; one picked on another game falls back to the weapons.
  const tools = TOOLS.filter((t) => !(t.id === 'supports' && parts?.supports === null))
  const tool = tools.some((t) => t.id === picked) ? picked : 'weapons'
  useEffect(() => {
    if (!game || loaded[game.id]) return
    let live = true
    setFailed(null)
    game
      .load()
      .then((p) => live && setLoaded((l) => ({ ...l, [game.id]: p })))
      .catch(() => live && setFailed(game.id))
    return () => {
      live = false
    }
  }, [game, loaded, attempt])

  function chooseGame(id: string) {
    setGameId(id)
    try {
      localStorage.setItem(GAME_KEY, id)
    } catch {
      // Not remembered this time; nothing else depends on it.
    }
  }

  function toggleBlock() {
    const on = !block
    setBlock(on)
    saveBlock(on)
    // Turning it off with no game picked brings back the one the app would have opened on.
    if (!on && !game) setGameId(savedGame())
  }

  // A game whose story splits (Fates; The Binding Blade twice) walks the shared chapters until you pick a route, then that route's.
  const fork = parts?.fork
  const route = routes[gameId]
  const story = parts?.story ?? (fork ? walkFork(fork, route).story : undefined)
  const last = story ? story.maps.length - 1 : 0
  const at = Math.min(progress[gameId] ?? 0, last)

  function moveTo(next: number) {
    const updated = { ...progress, [gameId]: Math.max(0, Math.min(next, last)) }
    setProgress(updated)
    saveProgress(updated)
  }

  /** Picks (or changes) the route: the choices so far, joined by '/'. Choosing at a split carries on into the route's next chapter;
   * changing an earlier choice drops the later ones, so the block asks again when it reaches their split. */
  function chooseRoute(id: string, proceed: boolean) {
    const chosen = fork ? walkFork(fork, id) : undefined
    if (!chosen?.chosen.length) return
    const nextRoutes = { ...routes, [gameId]: id }
    setRoutes(nextRoutes)
    saveRoutes(nextRoutes)
    const next = Math.min(at + (proceed ? 1 : 0), chosen.story.maps.length - 1)
    const updated = { ...progress, [gameId]: next }
    setProgress(updated)
    saveProgress(updated)
  }

  const reach = useMemo(() => (block && story ? reachOf(story, at, route) : SEES_ALL), [block, story, at, route])
  const Weapons = parts?.weapons
  const Maps = parts?.maps
  const Supports = parts?.supports
  // Weapons and maps show what the story hands out, so a game with no chapter order yet can't be shown under the block.
  const held = block && !!parts && !story && NEEDS_STORY.includes(tool)

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 text-neutral-200">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Fire Emblem Armory</h1>
            <p className="text-sm text-neutral-500">Weapons and forging, true hit, the weapon triangle, maps and supports.</p>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              onClick={toggleBlock}
              aria-pressed={block}
              title="Hides everything from chapters you haven't reached, and opens on a blank field."
              className={`rounded border px-2 py-1 text-sm ${
                block ? 'border-emerald-500 bg-emerald-950 text-emerald-200' : 'border-neutral-700 bg-neutral-900 text-neutral-300'
              }`}
            >
              Spoiler block: {block ? 'on' : 'off'}
            </button>
            <select
              value={game?.id ?? ''}
              onChange={(e) => chooseGame(e.target.value)}
              aria-label="Game"
              className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-100"
            >
              {!game && (
                <option value="" disabled>
                  Choose a game…
                </option>
              )}
              {GAMES.map((g) => (
                <option key={g.id} value={g.id}>
                  {g.title}
                </option>
              ))}
            </select>
          </div>
        </div>
        {game && (
          <nav className="flex flex-wrap gap-x-1 border-b border-neutral-800">
            {tools.map((t) => (
              <button
                key={t.id}
                onClick={() => setTool(t.id)}
                className={`-mb-px border-b-2 px-3 py-1.5 text-sm ${
                  tool === t.id
                    ? 'border-emerald-400 text-neutral-100'
                    : 'border-transparent text-neutral-400 hover:text-neutral-200'
                }`}
              >
                {t.label}
              </button>
            ))}
          </nav>
        )}
      </header>

      {!game && (
        <p className="rounded border border-neutral-800 p-4 text-neutral-400">
          The spoiler block is on. Pick a game to start from its first chapter; each chapter you reach opens up more.
        </p>
      )}

      {game && block && parts && story && <SpoilerBar game={parts} story={story} at={at} route={route} onChange={moveTo} onRoute={chooseRoute} />}

      {/* key: switching games starts each tool fresh rather than carrying one game's filters into another. */}
      {game && !parts && (
        <p className="rounded border border-neutral-800 p-4 text-neutral-400">
          {failed === game.id ? (
            <>
              {game.short} couldn't be loaded. Check the connection.{' '}
              <button onClick={() => setAttempt((n) => n + 1)} className="underline">
                Try again
              </button>
            </>
          ) : (
            `Loading ${game.short}…`
          )}
        </p>
      )}

      {game && parts && (
        <ReachContext.Provider value={reach}>
          {held && (
            <p className="rounded border border-neutral-800 p-4 text-neutral-400">
              The spoiler block isn't set up for {game.short} yet, so its {tool === 'maps' ? 'maps' : 'weapons'} stay hidden. Turn the
              block off to see them.
            </p>
          )}
          {!held &&
            tool === 'trueHit' &&
            (game.hitSystem ? <TrueHitCalculator key={game.id} system={game.hitSystem} gameName={game.short} /> : <ComingSoon what="true hit" game={game.short} />)}
          {!held && tool === 'maps' && (Maps ? <Maps key={game.id} /> : <ComingSoon what="maps" game={game.short} />)}
          {!held && tool === 'weapons' && (Weapons ? <Weapons key={game.id} /> : <ComingSoon what="weapons" game={game.short} />)}
          {tool === 'triangle' &&
            (parts.triangle ? <TriangleTab key={game.id} rules={parts.triangle} /> : <ComingSoon what="weapon triangle details" game={game.short} />)}
          {tool === 'supports' && (Supports ? <Supports key={game.id} /> : <ComingSoon what="supports" game={game.short} />)}
        </ReachContext.Provider>
      )}
    </div>
  )
}

function ComingSoon({ what, game }: { what: string; game: string }) {
  return (
    <p className="rounded border border-neutral-800 p-4 text-neutral-400">
      {game}'s {what} are being built from the game's own files and aren't in yet.
    </p>
  )
}

export default App

