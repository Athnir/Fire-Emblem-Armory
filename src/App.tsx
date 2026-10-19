import { useState } from 'react'
import { TrueHitCalculator } from './components/TrueHitCalculator'
import { DEFAULT_GAME, GAMES } from './games'

type Tool = 'weapons' | 'trueHit' | 'maps'
const TOOLS: { id: Tool; label: string }[] = [
  { id: 'weapons', label: 'Weapons & forging' },
  { id: 'trueHit', label: 'True hit' },
  { id: 'maps', label: 'Maps' },
]

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
  const [gameId, setGameId] = useState(savedGame)
  const [tool, setTool] = useState<Tool>('weapons')
  const game = GAMES.find((g) => g.id === gameId) ?? GAMES[0]

  function chooseGame(id: string) {
    setGameId(id)
    try {
      localStorage.setItem(GAME_KEY, id)
    } catch {
      // Not remembered this time; nothing else depends on it.
    }
  }

  const Weapons = game.weapons
  const Maps = game.maps

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 text-neutral-200">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Fire Emblem Armory</h1>
            <p className="text-sm text-neutral-500">Weapons and forging, true hit, and maps.</p>
          </div>
          <select
            value={game.id}
            onChange={(e) => chooseGame(e.target.value)}
            aria-label="Game"
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1 text-neutral-100"
          >
            {GAMES.map((g) => (
              <option key={g.id} value={g.id}>
                {g.title}
              </option>
            ))}
          </select>
        </div>
        <nav className="flex gap-1 border-b border-neutral-800">
          {TOOLS.map((t) => (
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
      </header>

      {/* key: switching games starts each tool fresh rather than carrying one game's filters into another. */}
      {tool === 'trueHit' && <TrueHitCalculator key={game.id} system={game.hitSystem} gameName={game.short} />}
      {tool === 'maps' && (Maps ? <Maps key={game.id} /> : <ComingSoon what="maps" game={game.short} />)}
      {tool === 'weapons' && (Weapons ? <Weapons key={game.id} /> : <ComingSoon what="weapons" game={game.short} />)}
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
