# Set the PE layout from the number of ocean points

## Why

- **Every case gets at least two nodes.** `Case._compute_pecount` asks for S, M or L
  from `ceil(points / (170 × MAX_TASKS_PER_NODE))`, which is at least 1 for any domain
  with ocean, so even a 96-point test case gets MOM_interface's S tier: 256 tasks on two
  nodes. Small and test runs have to pass `ntasks_ocn` by hand to reach the develop
  queue.
- **`ntasks_ocn` leaves the case unbuildable.** It is xmlchanged after visualCaseGen's
  `case.setup`, and nothing resets, so CIME's locked-file check stops `case.build` until
  you run `case.setup --reset` yourself.
- **The layout lives in another repo.** The task counts are in MOM_interface's
  `config_pes.xml` (Derecho only), and CrocoDash only picks a tier name. Those regional
  layouts are to be removed from MOM_interface.

## What

- **A `PELayout` configurator** (`forcing/pe_layout.py`), active for every MOM6 case,
  sets NTASKS, ROOTPE, NTASKS_OCN and ROOTPE_OCN in `configure_forcings()`:
  - MOM6 needs one task per 170 ocean points, 60 with MARBL, counted from the
    topography file's mask.
  - **Up to 64 MOM6 tasks:** one shared node, every component from PE 0. MOM6 gets the
    smallest of 1, 16, 32 or 64 tasks that fits, everything else one task. The 1-task
    tier is MOM_interface's default regional layout.
  - **More:** MOM_interface's S/M/L tiers, carried over unchanged as whole MOM6 nodes
    after node 0 (MOM6 on 128, 384 or 896 tasks; 384, 1152 or 2560 with MARBL). They are
    chosen by `_compute_pecount`'s rule: one node S, up to three M, more L. The node size
    comes from `MAX_TASKS_PER_NODE`, so other machines scale.
  - `Case(ntasks_ocn=...)` replaces the computed count.
  - The wave model, active or stub, goes with the other components.
- **`case.setup --reset` runs only when the layout changed.** A reset also forces a
  rebuild, so configuring a built case again with the same layout leaves it alone.
- **`Case` no longer picks a layout.** `_compute_pecount`, `_max_tasks_per_node`, the
  PECOUNT setting and the late `NTASKS_OCN` xmlchange are removed; `ntasks_ocn` is
  stored for the configurator. Until `configure_forcings()` runs, a case has CIME's
  default layout.
- The `ntasks_ocn` row of the case setup docs says where the layout comes from.

## Tests

- `test_pe_layout_picks_the_smallest_tier_that_fits`: one parametrized test of the tier
  choice (the 1-task tier, the 32 tier, S, M, L, MARBL's S, and an `ntasks_ocn`
  override). The configurator smoke and serialization tests cover the class.
- Checked by hand, outside the suite:
  - For every point count from 1 to 300,000, with and without MARBL, each domain above
    the small tiers gets exactly the layout `_compute_pecount` plus MOM_interface's
    blocks gave (585,280 counts, none differ).
  - A real 96-point NYF case on Casper: `Case()` alone had CIME's default layout; the
    first `configure_forcings()` set every component to one task at PE 0 and ran
    `case.setup --reset`; a second call changed nothing and didn't reset; CIME's
    locked-file check then passes.

## Notes

- Merge hazard with the queue branches: each conflicts in `case.py` on the removed
  `NTASKS_OCN` xmlchange, the `_apply_final_xmlchanges(ntasks_ocn, …)` call and
  `import math`. Take this branch's side and keep the rest of theirs.
- Follow-ups in other repos: remove the regional layouts from MOM_interface's
  `config_pes.xml` and bump the CESM `crocodash` branch's pointer (either order works,
  since this configurator sets the whole layout); later, visualCaseGen's own
  `NTASKS_OCN` estimate before `case.setup` can go.

## Merge note

Moved into 1.0.x (2026-11-06). Open it after #357 merges, then rebase: this PR deletes the
`NTASKS_OCN` xmlchange and the `case.setup --reset` that #357 adds to
`_apply_final_xmlchanges`, because the PELayout configurator now sets `ntasks_ocn` and
resets.

Closes #350

🤖 Generated with [Claude Code](https://claude.com/claude-code)
