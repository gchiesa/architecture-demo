// Sanity-check for `sidebar.yaml`: prints the computed VitePress sidebar
// without running a full build. Used by `mise run gen-sidebar` and by the
// `new-doc-type` skill after wiring in a new section.
import { buildSidebar } from '../sidebar.mjs'

console.log(JSON.stringify(buildSidebar(), null, 2))
