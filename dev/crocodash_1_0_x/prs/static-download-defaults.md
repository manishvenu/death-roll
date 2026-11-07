# Make the static download methods work on their defaults

## Why

These methods aren't on the forcing path, so nothing exercised them, and each failed on its defaults:
- `SeaWIFS.get_global_seawifs_script_for_cli` and `GEBCO.get_gebco_data_script` default `output_folder=None`, then call `Path(None)`. They would also have written `"None"` into the script.
- `GEBCO.get_gebco_data_with_python` returned `None` instead of the file it downloaded.
- `datasets.utils.write_bash_curl_script` opened the script inside `output_folder` before anything created that folder. The `mkdir -p` is inside the script itself.

## What

- Both script methods default to the working directory and create it if needed.
- `get_gebco_data_with_python` returns the extracted `.nc` file.
- `write_bash_curl_script` creates its folder before writing the script.

## Tests

- `test_script_methods_work_on_their_defaults`: both script methods, called with no arguments, write their script to the working directory, with no `"None"` in it.
- The existing `write_bash_curl_script` test now writes into a folder that doesn't exist yet.
- Against main's code, these three checks fail.
- `get_gebco_data_with_python` downloads a ~450 MB zip, so its return value isn't tested.

Closes #349

🤖 Generated with [Claude Code](https://claude.com/claude-code)
