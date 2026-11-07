# Write every GLORYS request in one process_forcings pass

## Why

With `function_name="get_glorys_data_script_for_cli"`:

- `process_forcings()` wrote the IC request, then failed reading the IC file, which doesn't exist until the script runs. The boundary requests only came on the next pass, so it took process → script → process → script → process.
- On main the script also kept only one request. `regional_mom6.get_glorys_data` writes `get_glorys_data.pbs`, but CrocoDash looked for `get_glorys_data.sh` to decide whether to add to the script. So every request replaced the last, and only the final boundary chunk was ever downloaded.

## What

- **One script:** `get_glorys_data_script_for_cli` writes `get_glorys_data.sh` itself, the name its usage text and the tutorials use. It adds one `copernicusmarine subset` line per request and skips a request already in the script. Each line is the same as regional_mom6's: the same 0.24° pad and depth range.
- **No regridding while data is missing:** after a script-type method has only written requests, the IC and boundary steps stop before regridding. They raise `DownloadScriptWritten`, naming the script.
- **One stop:** the driver catches that, runs the remaining components, then raises once: "Wrote the download requests to …/get_glorys_data.sh. Run it, then run process_forcings() again."
- After the script has run, `process_forcings()` finds every raw file and processes as before.
- **Quoted paths:** the `-o` folder and `-f` file are shell-quoted, so an inputdir with a space works. regional_mom6's script left them bare.

## Tests

- `test_the_glorys_script_gets_every_request_in_one_pass`: on a new case with two boundaries, one `process_forcings()` stops with that message. The script then holds the IC and both boundaries, each request once. A second pass before the script has run adds nothing. It fails on main.

- `test_get_glorys_data_script_for_cli` now writes into a folder with a space and checks that the script's `-o` reads back as that folder.

## Merge note

1.1's #346 (Q21) rewrites the same script method for `Region`/`TimeRequest`; when it rebases, keep its version.

Closes #356

🤖 Generated with [Claude Code](https://claude.com/claude-code)
