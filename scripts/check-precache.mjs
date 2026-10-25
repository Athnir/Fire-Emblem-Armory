// After the build: every script and stylesheet in dist/assets must be in the service worker's precache list, or a game's
// file would only load online. The build already fails on a file over the size limit; this catches one left out of the list.
import { readdirSync, readFileSync } from 'node:fs'

const sw = readFileSync('dist/sw.js', 'utf8')
const missing = readdirSync('dist/assets')
  .filter((f) => /\.(js|css)$/.test(f))
  .filter((f) => !sw.includes(`assets/${f}`))
if (missing.length) {
  console.error(`Not in the offline cache: ${missing.join(', ')}`)
  process.exit(1)
}
console.log('Every script and stylesheet is in the offline cache.')
