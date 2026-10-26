import type { StoryOrder } from '../data/maps/mapSet'
import type { GameParts } from '../games'
import { walkFork } from '../logic/spoiler'

const button = 'rounded border px-3 py-1 text-sm disabled:cursor-default disabled:opacity-40'
const proceed = `${button} border-emerald-600 bg-emerald-900/60 text-emerald-100 hover:bg-emerald-800/60`

/**
 * The spoiler block's control for one game: which chapter you're on, a button to open the next one, and a way back. A game
 * whose story splits (Fates; The Binding Blade at Chapters 10 and 17) asks which route you're on when the chapters before the
 * split run out. Everything else in the app reads how far it's open and hides what's beyond.
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
  const walked = game.fork ? walkFork(game.fork, route) : undefined
  const path = (walked?.chosen ?? []).map((c) => c.choice.id)
  // The chapters before a split are done and no route is picked for it yet: the next step is choosing one.
  const choosing = !!walked?.pending && !next
  return (
    <section aria-label="Spoiler block" className="flex flex-col gap-2 rounded border border-emerald-900 bg-emerald-950/30 p-3 text-sm">
      <div className="flex flex-wrap items-center gap-2">
        <p className="mr-auto text-neutral-200">
          <span className="text-neutral-400">Opened up to </span>
          <strong className="text-neutral-100">{story.name(here)}</strong>
          {walked && walked.chosen.length > 0 && <span className="text-neutral-500"> · {walked.chosen.map((c) => c.choice.label).join(', ')}</span>}
        </p>
        <button
          onClick={() => onChange(at - 1)}
          disabled={at === 0}
          className={`${button} border-neutral-700 text-neutral-300 hover:bg-neutral-800`}
        >
          ‹ Back
        </button>
        {choosing ? (
          walked!.pending!.choices.map((c) => (
            <button key={c.id} onClick={() => onRoute([...path, c.id].join('/'), true)} className={proceed}>
              {c.proceed ?? `Proceed as ${c.label}`} ›
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
        {walked?.chosen.map(({ fork, choice }, i) => (
          // One select per split passed; changing an earlier one drops the choices after it.
          <select
            key={i}
            value={choice.id}
            onChange={(e) => onRoute([...path.slice(0, i), e.target.value].join('/'), false)}
            aria-label={i === 0 ? 'Route' : `Route at split ${i + 1}`}
            className="rounded border border-neutral-700 bg-neutral-900 px-2 py-1"
          >
            {fork.choices.map((c) => (
              <option key={c.id} value={c.id}>
                Route: {c.label}
              </option>
            ))}
          </select>
        ))}
      </div>
      {(count > 0 || (!next && !choosing && game.afterStory)) && (
        <p className="text-neutral-400">
          {count > 0 && `${story.name(here)} brings ${count} new ${count === 1 ? 'weapon' : 'weapons'}.`}
          {!next && !choosing && game.afterStory && ` ${game.afterStory} are open now.`}
        </p>
      )}
      {choosing && <p className="text-neutral-400">The story splits here: pick the route you're playing to carry on.</p>}
    </section>
  )
}
