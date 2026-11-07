# Fix three small case-creator and WW3-widget defects

## Why

Three pre-existing defects found while reviewing #45:

1. **The WW3 Generate button stayed disabled.** `on_btn_generate_clicked` re-enables it only on its error paths, and `reset()` clears `WW3_INPUT_STATUS` without re-enabling it. Back on the Wave Grid stage after a successful run, the stage waits for a status that only that disabled button can set.
2. **An assert that can't fail.** `assert is_ccs_config_writeable or not add_grids_to_ccs_config` in `CaseCreator.__init__` tests the function object, not its result.
3. **Two datasets never closed** in `_apply_mom_namelist_changes`: the topog file and the vgrid file.

## What

1. `reset()` re-enables the button.
2. The assert is removed, and its hint moves into the `RuntimeError` that `_update_modelgrid_aliases` already raises when ccs_config isn't writeable. Calling the function in `__init__` instead would refuse every `CaseCreator` on a CESM install the user can't write to, including standard-grid cases and the GUI's own widget, which never write ccs_config.
3. Both datasets are opened with `with`.

## Tests

No new tests. (1) is widget state, (2) removes a check that never ran, and (3) changes no result.

Closes #47

🤖 Generated with [Claude Code](https://claude.com/claude-code)
