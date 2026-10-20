import { FE9_MAP_SET } from '../data/fe9/fe9MapSet'
import { MapViewer } from './MapViewer'

/** Path of Radiance's maps, in the same viewer as Fates'. */
export function Fe9Maps() {
  return <MapViewer set={FE9_MAP_SET} />
}
