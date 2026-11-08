import { gameLabel, pickerList } from '../games'

/** What the app opens on with no game picked (as the Roster does): what it is, the spoiler block, and every game in the series' order. */
export function Home({ block, onPick }: { block: boolean; onPick: (id: string) => void }) {
  const games = pickerList()
  const section = 'space-y-2 rounded-lg border border-neutral-800 bg-neutral-950/60 p-4'

  return (
    <div className="mx-auto w-full max-w-3xl space-y-4 text-sm text-neutral-300">
      <section className={section}>
        <h2 className="text-base font-semibold text-neutral-100">What this is</h2>
        <p>
          A datasheet for each game: its weapons and where every one turns up, forging and shops, true hit, the weapon triangle, every
          map with its units, reinforcements and events, and what supports give. Each game's tools sit in its own tabs. Its partner app,
          the Fire Emblem Roster, covers your units: who joins and when, growths, classes, skills, supports and builds.
        </p>
      </section>

      <section className={section}>
        <h2 className="text-base font-semibold text-neutral-100">The spoiler block {block ? 'is on' : 'is off'}</h2>
        <p>
          {block
            ? "Pick a game and it starts from its first chapter: weapons, maps and their units show once the chapter that reveals them is reached, and each chapter you reach on its bar opens up more. A story's split is asked for when you get there. Turn the block off at the top to see everything."
            : 'Everything in every game shows. Turn the block on at the top to play along chapter by chapter, with nothing shown before the chapter that reveals it.'}
        </p>
      </section>

      <section className={section}>
        <h2 className="text-base font-semibold text-neutral-100">The games</h2>
        <ul className="grid gap-1 sm:grid-cols-2">
          {games.map((e) =>
            e.game ? (
              <li key={e.game.id}>
                <button type="button" onClick={() => onPick(e.game.id)} className="w-full rounded-md px-2 py-1 text-left hover:bg-neutral-800">
                  <span className="text-neutral-100">{gameLabel(e.game)}</span>
                </button>
              </li>
            ) : (
              <li key={e.missing.title} className="px-2 py-1 text-neutral-600">
                {gameLabel(e.missing)} <span className="text-xs">({e.missing.why})</span>
              </li>
            ),
          )}
        </ul>
      </section>

      <section className={section}>
        <h2 className="text-base font-semibold text-neutral-100">On this device</h2>
        <p>
          The game you were on, each game's difficulty and your place under the spoiler block stay on this device. Every game works
          offline once the app has been opened, and "Check for updates" at the top looks for a new version only when you tap it.
        </p>
      </section>
    </div>
  )
}
