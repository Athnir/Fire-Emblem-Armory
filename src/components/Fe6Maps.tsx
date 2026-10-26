import { FE6_MAP_SET } from '../data/fe6/fe6MapSet'
import { MapViewer } from './MapViewer'

/** The Binding Blade's maps, in the same viewer as the other games'. */
export function Fe6Maps() {
  return <MapViewer set={FE6_MAP_SET} />
}
