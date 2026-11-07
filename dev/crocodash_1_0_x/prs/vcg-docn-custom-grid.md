# Allow a custom ocean grid with a data ocean

## Why

A CICE case over a data ocean, such as `2000_DATM%JRA_SLND_CICE_DOCN%SOM_SROF_SGLC_SWAV`, can't use a custom ocean grid. Two constraints allow custom grids only with MOM6 (or CLM): "Custom grids can only be generated when MOM6 and/or CLM are selected." The reporter of CROCODILE-CESM/CrocoDash#232 added DOCN to both, then ran such a case for 5 days without trouble.

## What

- Both constraints also allow `docn`, as in the report.
- `_apply_mom_namelist_changes` returns early when the ocean isn't MOM6. Otherwise a DOCN case on a new ocean grid would get a `user_nl_mom` that nothing reads.

## Tests

- `test_a_data_ocean_can_take_a_custom_ocean_grid` (2_integration): a custom DATM/SLND/CICE/DOCN%SOM compset takes `GRID_MODE=Custom` and `OCN_GRID_MODE=Create New`. On main it fails with "Invalid assignment of GRID_MODE to Custom".
- `test_custom_compset.py` passes against a CESM with cime6.4.1.

## Not in this PR

In the GUI, a DOCN case on a new ocean grid still passes through the MOM6 "New Ocean Grid Initial Conditions" stage. Its answers are unused.

Part of CROCODILE-CESM/CrocoDash#232; CrocoDash takes it with a visualCaseGen pin bump.

🤖 Generated with [Claude Code](https://claude.com/claude-code)
