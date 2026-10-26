# Name the grid files in the create config instead of building grids

## Why

A create config described the grids in `grid:`, `topo:` and `vgrid:` sections, whose keys
went straight to mom6_forge (`Grid(**grid)`, `topo.set_from_dataset(**source)`,
`VGrid.hyperbolic(**vgrid)`). So:
- the YAML changed whenever mom6_forge's API did, and CrocoDash couldn't keep it
  compatible;
- it was the one part of the config the forcing walkthrough can't ask for, because
  nothing describes those keys the way the forcing inputs are described.

Everything else already passes grids around as files: `crocodash dump`, bundles,
`create --from` and `Case.from_caseroot()`.

## What

- **A create config is the arguments of `Case()` and of `configure_forcings()`.**
  `case:` names the grid files, as mom6_forge writes them: `ocn_grid` (the supergrid),
  `ocn_topo` and `ocn_vgrid`.
- **`read_grids()` reads them.** The grid takes the name written in its file (mom6_forge
  writes it), and the topography its `min_depth`. A case created from another so keeps
  the source's grid name, which its grid files and some forcing files are named after.
- **Removed:** `build_grid`, `build_topo`, `build_vgrid` and their type checks. A config
  with `grid:`, `topo:` or `vgrid:` sections is refused, with how to write the grid
  files instead.
- **`case_to_yaml()` (`crocodash dump`)** names the case's grid files in `case:`, and no
  longer reads `min_depth` itself.
- **Docs:** the YAML schema in `cli.md` shows the grid files and how to write them, and
  `sharing.md`'s note on old bundles is updated.

## Tests

- The grid files read back with the grid's own name (not its file's), its `min_depth`
  and its levels (`test_recipe_functions.py`). This replaces the 11 builder tests, which
  covered deleted code.
- The structure and dump tests check `case.ocn_grid`, `ocn_topo` and `ocn_vgrid`.

## Notes for reviewers

- **No backwards compatibility.** Configs with grid sections stop working. The ones we
  ship move to grid files in changes that merge with this one: crocontainer's demo,
  weekly tests and sample (CROCODILE-CESM/crocontainer#18), the gallery's starter config
  (CROCODILE-CESM/CrocoGallery#63), and the MCP server's `create_case`.
- A vertical grid file whose variable isn't `dz` (layer thickness) can't be named
  directly any more. Convert it once with
  `VGrid.from_file(path, variable_name=..., variable_type=...).write(new_path)`.
- Built on #342; it gets one rebase once that merges.
- About 120 lines added and 315 removed, most of the removals the builder tests.

Closes #343

🤖 Generated with [Claude Code](https://claude.com/claude-code)
