"""Same repro with the proposed fix monkeypatched in (source rewritten in memory, worktree untouched)."""
import inspect, textwrap
import CrocoDash.forcing.bgc as bgc
src = textwrap.dedent(inspect.getsource(bgc.BGCRiverNutrientsConfigurator.process))
old = '''"don_riv_flux",
    "don_riv_flux",
    "dsi_riv_flux",
    "dsi_riv_flux",'''
assert old.replace("\n    ", "\n            ") in src.replace("\n        ", "\n    ") or True
import re
new_src = re.sub(r'"don_riv_flux",\s*"don_riv_flux",\s*"dsi_riv_flux",\s*"dsi_riv_flux",',
                 '"don_riv_flux", "dop_riv_flux", "dsi_riv_flux", "dfe_riv_flux",', src)
assert new_src != src
new_src = new_src.replace('"mmol/cm^2/s"', '"mmol/m^2/s"')
ns = {}
exec(compile(new_src, bgc.__file__, "exec"), bgc.__dict__, ns)
bgc.BGCRiverNutrientsConfigurator.process = ns["process"]
exec(open("riv_nut_units.py").read())
