# Detect the open edges when boundaries aren't given

## Why

- **Every case opens all four edges by default.** `configure_forcings()` defaults
  `boundaries` to south, north, west and east, so a domain against a coast still gets a
  segment, a fetch and a regrid for an edge that is all land.
- **Which edges are open is a fact of the grid and topography,** and regional-mom6
  already works it out: `Segment.detect_open_cardinal_boundaries(topo)` keeps the edges
  that touch at least one ocean point in `topo.supergridmask`. #269 used it; Q16 (#338)
  left it out because it changes the default for every case.

## What

- **`boundaries=None` is the new default** and detects the open edges. An explicit list
  overrides it unchanged. Custom and interior segments can't be inferred, so they are
  always given explicitly.
- **On a grid cyclic in x** (Q17), east and west are never opened.
- **The detected list is written to config.json** as the `boundaries` input, so a case
  read back from its caseroot, or forked, keeps it without detecting again.
- Docs: the `boundaries` argument and the case setup page say what the default does.

## Tests

- One parametrized test of the default: an all-land edge is left out, an explicit list is
  kept as given, and a cyclic grid never gets east or west.

## Notes

- **Behaviour change:** a case whose domain has an all-land edge, configured with the
  default, gets one segment fewer, and the segments after it are renumbered
  (`OBC_SEGMENT_00N`, the tide segments, config.json's boundary list). Reconfiguring an
  existing case of that kind changes its segments; its earlier boundary files are then
  stale and are removed.
- Built from #269's `interior-obc-new` (b22a680f), `Case.configure_forcings`'s
  `if boundaries is None:` branch, on top of Q16 and Q17.

Closes #352

🤖 Generated with [Claude Code](https://claude.com/claude-code)
