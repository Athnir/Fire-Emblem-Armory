import type { Weapon } from '../data/types'

export function WeaponList({
  weapons,
  selectedId,
  onSelect,
}: {
  weapons: Weapon[]
  selectedId: string | null
  onSelect: (id: string) => void
}) {
  return (
    <table className="w-full min-w-[520px] border-collapse text-sm">
      <thead>
        <tr className="border-b border-neutral-700 text-left text-neutral-400">
          <th className="py-1 pr-3">Name</th>
          <th className="py-1 pr-3">Rank</th>
          <th className="py-1 pr-3">Mt</th>
          <th className="py-1 pr-3">Hit</th>
          <th className="py-1 pr-3">Crit</th>
          <th className="py-1 pr-3">Rng</th>
        </tr>
      </thead>
      <tbody>
        {weapons.map((w) => (
          <tr
            key={w.id}
            onClick={() => onSelect(w.id)}
            className={`cursor-pointer border-b border-neutral-800 hover:bg-neutral-800 ${
              selectedId === w.id ? 'bg-neutral-800' : ''
            }`}
          >
            <td className="py-1 pr-3 text-neutral-100">
              {w.name}
              {w.isMagic && (
                <span className="ml-1 text-indigo-400" title="Magic weapon — hits Resistance, not Defence">
                  ✦
                </span>
              )}
            </td>
            <td className="py-1 pr-3 text-neutral-400">{w.rank}</td>
            <td className="py-1 pr-3">{w.stats.mt}</td>
            <td className="py-1 pr-3">{w.stats.hit}</td>
            <td className="py-1 pr-3">{w.stats.crit}</td>
            <td className="py-1 pr-3">{w.stats.range}</td>
          </tr>
        ))}
        {weapons.length === 0 && (
          <tr>
            <td colSpan={6} className="py-4 text-center text-neutral-500">
              No weapons match the current filters.
            </td>
          </tr>
        )}
      </tbody>
    </table>
  )
}
