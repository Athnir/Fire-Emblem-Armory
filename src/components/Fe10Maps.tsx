import { FE10_MAP_SET } from '../data/fe10/fe10MapSet'
import { MapViewer } from './MapViewer'

/** Radiant Dawn's maps, in the same viewer as Fates' and Path of Radiance's. */
export function Fe10Maps() {
  return <MapViewer set={FE10_MAP_SET} />
}
