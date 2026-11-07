# Replace a leftover file when fetching GLORYS from Copernicus Marine

## Why

copernicusmarine doesn't overwrite a file that's already there. When a partial `glorys.nc` from an interrupted download is in the way, it writes the new data to `glorys_(1).nc`. `get_glorys_data_from_cds_api` still returns `glorys.nc`, so the caller reads the old or partial file. Seen as `NetCDF: HDF error` on a 9 KB leftover after a retry.

## What

`get_glorys_data_from_cds_api` passes `overwrite=True`, so the file it returns is always the one it just downloaded.

## Tests

- `test_get_glorys_data_from_cds_api` (marked slow) now leaves a partial `temp.nc` in place first. It checks that the result is the only file there and holds the requested data.
- That test fails on main and passes here, run against the real service.

Closes #355

🤖 Generated with [Claude Code](https://claude.com/claude-code)
