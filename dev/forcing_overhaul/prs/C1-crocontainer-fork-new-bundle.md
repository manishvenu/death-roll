# Create the case from a bundle with crocodash create --from

## Why

CrocoDash drops `crocodash fork` and `crocodash duplicate`
(CROCODILE-CESM/CrocoDash#340). A case is now created from a bundle, or a caseroot,
with `crocodash create --from`, which:
- carries the bundled case's own changes, leaving out the ones specific to its machine;
- copies its forcing files whose settings still match.

The bundle also changed: `crocodash bundle` writes `bundle.json` plus `caseroot/` and
`inputdir/`, instead of `crocodash_case.yaml`.

## What

- **`run_case.sh` creates the case from a non-empty `/workspace/bundle`:**
  `crocodash create --from /workspace/bundle --caseroot /workspace/case --inputdir
  /workspace/inputdir ... --configure-only --no-input`.
  - `--configure-only`: the container can't download data, so the forcings aren't
    processed. The bundle's matching forcing files are copied in.
  - `--no-input`: a run with a TTY (`docker run -it`) doesn't stop to ask.
- **An old bundle stops the script.** A bundle without `bundle.json` (the format
  CrocoDash wrote before) ends with a message to bundle the case again. Before, it would
  have fallen through to the Panama demo, because the image always creates an empty
  `/workspace/bundle`, so only a non-empty one counts as a bundle.
- **The smoke test no longer checks `crocodash fork`.** The next line already checks
  `crocodash create`.

## Tests

CrocoDash's container CI job (`run_cesm_crocontainer`) runs this script on a bundle once
its testing.yml tag points at an image built from this.

## Notes for reviewers

- The image's CrocoDash is this repo's `CrocoDash` submodule, which doesn't have
  `create --from` yet. Until it is bumped past CROCODILE-CESM/CrocoDash#340, running a
  bundle in an image built from this fails at `crocodash create --from`. The Panama demo
  and `case_config.yaml` runs are unchanged.
- The bundled case's xmlchanges are now carried too. On another machine (here
  `ubuntu-latest`), CrocoDash leaves out its PE layout, batch job, project and
  directories.

Closes #16

🤖 Generated with [Claude Code](https://claude.com/claude-code)
