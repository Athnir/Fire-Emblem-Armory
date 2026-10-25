import { useMemo, useState } from 'react'
import { ReachContext } from './components/Reach'
import { SpoilerBar } from './components/SpoilerBar'
import { TrueHitCalculator } from './components/TrueHitCalculator'
import { DEFAULT_GAME, GAMES } from './games'
import { reachOf, SEES_ALL } from './logic/spoiler'
import { saveBlock, saveProgress, savedBlock, savedProgress } from './logic/spoilerStore'

type Tool = 'weapons' | 'trueHit' | 'maps' | 'supports'
const TOOLS: { id: Tool; label: string }[] = [
  { id: 'weapons', label: 'Weapons & forging' },
  { id: 'trueHit', label: 'True hit' },
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
  const [tool, setTool] = useState<Tool>('weapons')
  const [progress, setProgress] = useState(savedProgress)
  const game = GAMES.find((g) => g.id === gameId) ?? null

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

  const story = game?.story
  const last = story ? story.maps.length - 1 : 0
  const at = Math.min(progress[gameId] ?? 0, last)

  function moveTo(next: number) {
    const updated = { ...progress, [gameId]: Math.max(0, Math.min(next, last)) }
    setProgress(updated)
    saveProgress(updated)
  }

  const reach = useMemo(() => (block && story ? reachOf(story, at) : SEES_ALL), [block, story, at])
  const Weapons = game?.weapons
  const Maps = game?.maps
  const Supports = game?.supports
  // Weapons and maps show what the story hands out, so a game with no chapter order yet can't be shown under the block.
  const held = block && !!game && !story && NEEDS_STORY.includes(tool)

  return (
    <div className="mx-auto flex min-h-screen max-w-6xl flex-col gap-4 p-4 text-neutral-200">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-end justify-between gap-2">
          <div>
            <h1 className="text-2xl font-bold text-neutral-100">Fire Emblem Armory</h1>
            <p className="text-sm text-neutral-500">Weapons and forging, true hit, maps and supports.</p>
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
        )}
      </header>

      {!game && (
        <p className="rounded border border-neutral-800 p-4 text-neutral-400">
          The spoiler block is on. Pick a game to start from its first chapter; each chapter you reach opens up more.
        </p>
      )}

      {game && block && story && <SpoilerBar game={game} at={at} onChange={moveTo} />}

      {/* key: switching games starts each tool fresh rather than carrying one game's filters into another. */}
      {game && (
        <ReachContext.Provider value={reach}>
          {held && (
            <p className="rounded border border-neutral-800 p-4 text-neutral-400">
              The spoiler block isn't set up for {game.short} yet, so its {tool === 'maps' ? 'maps' : 'weapons'} stay hidden. Turn the
              block off to see them.
            </p>
          )}
          {!held && tool === 'trueHit' && <TrueHitCalculator key={game.id} system={game.hitSystem} gameName={game.short} />}
          {!held && tool === 'maps' && (Maps ? <Maps key={game.id} /> : <ComingSoon what="maps" game={game.short} />)}
          {!held && tool === 'weapons' && (Weapons ? <Weapons key={game.id} /> : <ComingSoon what="weapons" game={game.short} />)}
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

