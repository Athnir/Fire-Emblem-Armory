import { FE4_MAP_SET } from '../data/fe4/fe4MapSet'
import { MapViewer } from './MapViewer'

/** Genealogy of the Holy War's maps, in the same viewer as the other games'. */
export function Fe4Maps() {
  return <MapViewer set={FE4_MAP_SET} />
}
