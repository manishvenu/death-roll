import sys, os, glob, copy, shutil, tempfile, logging
sys.path.insert(0, os.path.expanduser("~/work/installs/CESM_crocodash/components/mom/cime_config/MOM_RPS"))
from pathlib import Path
from uuid import uuid4
from contextlib import redirect_stdout, redirect_stderr
import CrocoDash.shareable as sh
from CrocoDash.shareable import CaseBundle
from CrocoDash.recipe import create_case_from_yaml

def patched(self, cesmroot, machine, project_number):
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        caseroot_tmp = tmp_path / f"temp_case-{uuid4().hex}"
        inputdir = tmp_path / "temp_inputdir"
        config = copy.deepcopy(self.case_yaml)
        config["case"].update(cesmroot=str(cesmroot), machine=machine, project=project_number,
                              caseroot=str(caseroot_tmp), inputdir=str(inputdir))
        ref = None
        try:
            with open(os.devnull, "w") as devnull, redirect_stdout(devnull), redirect_stderr(devnull):
                create_case_from_yaml(config, override=True, configure_only=True)
            ref = CaseBundle(caseroot_tmp)
            self.non_standard_case_info = self.diff(ref)
            return self.non_standard_case_info
        finally:
            # FIX: the temp case's EXEROOT/RUNDIR live under CIME_OUTPUT_ROOT/<case>, outside tmp_dir
            out_root = ref._case.get_value("CIME_OUTPUT_ROOT") if ref is not None else None
            if out_root:
                shutil.rmtree(Path(out_root) / caseroot_tmp.name, ignore_errors=True)

sh.CaseBundle.identify_non_standard_case_info = patched
OUT = "/glade/derecho/scratch/manishrv"
before = set(glob.glob(OUT + "/temp_case-*"))
S = Path(__file__).resolve().parent
info = CaseBundle(S/"cases/audit_v_a13_1").identify_non_standard_case_info(
    Path("~/work/installs/CESM_crocodash").expanduser(), "derecho", "ncgd0011")
print("info:", info)
print("NEW leftover dirs with fix:", sorted(set(glob.glob(OUT + "/temp_case-*")) - before))
