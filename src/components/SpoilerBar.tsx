import type { Game } from '../games'

const button = 'rounded border px-3 py-1 text-sm disabled:cursor-default disabled:opacity-40'

/**
 * The spoiler block's control for one game: which chapter you're on, a button to open the next one, and a way back.
 * Everything else in the app reads how far it's open and hides what's beyond.
 */
export function SpoilerBar({ game, at, onChange }: { game: Game; at: number; onChange: (at: number) => void }) {
  const story = game.story!
  const maps = story.maps
  const here = maps[at]
  const next = maps[at + 1]
  const count = game.weaponsHere?.(here.id) ?? 0
  return (
    <section aria-label="Spoiler block" className="flex flex-col gap-2 rounded border border-emerald-900 bg-emerald-950/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto text-neutral-200">
          <span className="text-neutral-400">Opened up to </span>
          <strong className="text-neutral-100">{story.name(here)}</strong>
        </p>
        <button
          onClick={() => onChange(at - 1)}
          disabled={at === 0}
          className={`${button} border-neutral-700 text-neutral-300 hover:bg-neutral-800`}
        >
          ‹ Back
        </button>
        <button
          onClick={() => onChange(at + 1)}
          disabled={!next}
          className={`${button} border-emerald-600 bg-emerald-900/60 text-emerald-100 hover:bg-emerald-800/60`}
        >
          {next ? `Proceed to ${story.name(next)} ›` : 'End of the story'}
        </button>
        <select
          value={at}
          onChange={(e) => onChange(Number(e.target.value))}
          aria-label="Jump to a chapter"
          className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
        >
          {maps.map((m, i) => (
            <option key={m.id} value={i}>
              {i === at ? `Jump to… (now ${story.name(m)})` : story.name(m)}
            </option>
          ))}
        </select>
      </div>
      {(count > 0 || (!next && game.afterStory)) && (
        <p className="text-neutral-400">
          {count > 0 && `${story.name(here)} has ${count} ${count === 1 ? 'weapon' : 'weapons'} to get: from its base, base conversations, chests and drops.`}
          {!next && game.afterStory && ` ${game.afterStory} are open now.`}
        </p>
      )}
    </section>
  )
}
