On a laptop, or any host CIME doesn't recognise, CrocoDash can't create a case or generate forcings unless `CIME_MACHINE` is set:

- visualCaseGen cuts the machine list to `["CESM_NOT_PORTED"]` (`cime_interface.py:829-830`);
- `Case(machine="ubuntu-latest")` then fails `init_args_check` with `machine must be one of ['CESM_NOT_PORTED']` (`case.py:362`);
- `Case(machine="CESM_NOT_PORTED")` fails in visualCaseGen's `CaseCreator`: "CESM is not ported to the current machine. Therefore, case creation is disabled."

The only way through today is `export CIME_MACHINE=ubuntu-latest`, so that CIME takes the host for that machine.

**Wanted:** on an unported host, `CESM_NOT_PORTED` means "configure, but don't create the case". visualCaseGen's show-commands behaviour is fine. CrocoDash still writes the grid files and generates the forcings, so they can be moved to a ported machine and the case created there.

**Fix:** re-cut the parked #271 (branch `cesm-not-ported-case`, commits c73e962d and 2cc6201c) onto main. CrocoDash derives `do_exec` from the machine and skips every xmlchange and user_nl write for `CESM_NOT_PORTED`, while forcing extraction runs as usual. Leave out #271's no-CESM-checkout mode and its test-suite changes.

Related: #372 (C14: `machine=` left out on a host CIME does recognise).
