import type { StoryOrder } from '../data/maps/mapSet'
import type { GameParts } from '../games'

const button = 'rounded border px-3 py-1 text-sm disabled:cursor-default disabled:opacity-40'
const proceed = `${button} border-emerald-600 bg-emerald-900/60 text-emerald-100 hover:bg-emerald-800/60`

/**
 * The spoiler block's control for one game: which chapter you're on, a button to open the next one, and a way back. A game
 * whose story splits (Fates) asks which route you're on when the shared chapters run out. Everything else in the app reads
 * how far it's open and hides what's beyond.
 */
export function SpoilerBar({
  game,
  story,
  at,
  route,
  onChange,
  onRoute,
}: {
  game: GameParts
  story: StoryOrder
  at: number
  route?: string
  onChange: (at: number) => void
  onRoute: (route: string, proceed: boolean) => void
}) {
  const maps = story.maps
  const here = maps[at]
  const next = maps[at + 1]
  const count = game.newWeapons?.(here.id, route) ?? 0
  // The shared chapters are done and no route is picked yet: the next step is choosing one.
  const choosing = !!game.fork && !route && !next
  return (
    <section aria-label="Spoiler block" className="flex flex-col gap-2 rounded border border-emerald-900 bg-emerald-950/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto text-neutral-200">
          <span className="text-neutral-400">Opened up to </span>
          <strong className="text-neutral-100">{story.name(here)}</strong>
          {route && <span className="text-neutral-500"> · {route}</span>}
        </p>
        <button
          onClick={() => onChange(at - 1)}
          disabled={at === 0}
          className={`${button} border-neutral-700 text-neutral-300 hover:bg-neutral-800`}
        >
          ‹ Back
        </button>
        {choosing ? (
          game.fork!.choices.map((c) => (
            <button key={c.id} onClick={() => onRoute(c.id, true)} className={proceed}>
              Proceed as {c.label} ›
            </button>
          ))
        ) : (
          <button onClick={() => onChange(at + 1)} disabled={!next} className={proceed}>
            {next ? `Proceed to ${story.name(next)} ›` : 'End of the story'}
          </button>
        )}
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
        {game.fork && route && (
          <select
            value={route}
            onChange={(e) => onRoute(e.target.value, false)}
            aria-label="Route"
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            {game.fork.choices.map((c) => (
              <option key={c.id} value={c.id}>
                Route: {c.label}
              </option>
            ))}
          </select>
        )}
      </div>
      {(count > 0 || (!next && game.afterStory)) && (
        <p className="text-neutral-400">
          {count > 0 && `${story.name(here)} brings ${count} new ${count === 1 ? 'weapon' : 'weapons'}.`}
          {!next && game.afterStory && ` ${game.afterStory} are open now.`}
        </p>
      )}
      {choosing && <p className="text-neutral-400">The story splits here: pick the route you're playing to carry on.</p>}
    </section>
  )
}
