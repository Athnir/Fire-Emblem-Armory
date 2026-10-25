import { FATES_MAP_SET } from '../data/maps'
import { MapViewer } from './MapViewer'

/** Fates' maps, in the same viewer as the other games'. */
export function FatesMaps() {
  return <MapViewer set={FATES_MAP_SET} />
}
