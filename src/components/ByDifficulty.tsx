/**
 * Chapters that can differ by difficulty, as one line: "Part 3: Ch.4 on every difficulty" when they're the
 * same, "… on Easy and Normal, … on Hard" when they're not.
 */
export function ByDifficulty({ value, none }: { value: { normal: string; hard: string }; none: string }) {
  const where = (chapters: string) => (chapters ? <span className="text-neutral-200">{chapters}</span> : <span className="text-neutral-500">{none}</span>)
  if (value.normal === value.hard) return <>{where(value.normal)} on every difficulty</>
  return (
    <>
      {where(value.normal)} on Easy and Normal, {where(value.hard)} on Hard
    </>
  )
}
