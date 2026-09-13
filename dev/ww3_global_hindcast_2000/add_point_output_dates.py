"""
Add the missing date%point%{start,stride,stop} namelist entries to a
SourceMods override of namelist_definition_ww3.xml.

Why this is needed (found while writing setup_case.ipynb, not assumed):
CESM's WW3 cime_config exposes `type%point%file` (default 'points.list') so
point output CAN be turned on, but its namelist_definition_ww3.xml never
defines `date_percent_point_percent_start/stride/stop` -- only the field and
restart groups get those. Confirmed by grepping every "point"-related entry
in the file: the only hit is `type_percent_point_percent_file`.

That matters because the underlying Fortran (model/src/w3nmlshelmd.F90,
READ_OUTPUT_DATE_NML) defaults DATE%POINT%STRIDE to '0' when it's absent from
the namelist -- WW3's own stride=0 convention for "off". So without this fix,
point output stays silently disabled even with points.list wired up and
staged in $RUNDIR.

buildnml (components/ww3/cime_config/buildnml) explicitly supports overriding
the whole namelist definition via $CASEROOT/SourceMods/src.ww3/
namelist_definition_ww3.xml -- "user definition *replaces* existing
definition" (its own comment) -- so this script copies the real file and
adds the three missing entries, rather than patching the checked-out
component's cime_config in place.

Usage:
    python add_point_output_dates.py <caseroot>
"""

import re
import sys
from pathlib import Path

DEFAULT_DEFINITION = Path(
    "~/work/installs/cesm3_0_beta08_gui/components/ww3/cime_config/"
    "namelist_definition_ww3.xml"
).expanduser()

NEW_ENTRIES = """
  <entry id="date_percent_point_percent_start">
    <type>char</type>
    <group>output_date_nml</group>
    <category>setup</category>
    <values>
      <value>unset</value>
    </values>
  </entry>
  <entry id="date_percent_point_percent_stride">
    <type>char</type>
    <group>output_date_nml</group>
    <category>setup</category>
    <values>
      <value>unset</value>
    </values>
  </entry>
  <entry id="date_percent_point_percent_stop">
    <type>char</type>
    <group>output_date_nml</group>
    <category>setup</category>
    <values>
      <value>99990101 0</value>
    </values>
  </entry>
"""


def build_override(source_path=DEFAULT_DEFINITION):
    text = source_path.read_text()
    anchor = '<entry id="date_percent_field_percent_stop">'
    idx = text.index(anchor)
    close_idx = text.index("</entry>", idx) + len("</entry>")
    return text[:close_idx] + "\n" + NEW_ENTRIES.strip("\n") + text[close_idx:]


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python add_point_output_dates.py <caseroot>")

    caseroot = Path(sys.argv[1]).expanduser()
    out_dir = caseroot / "SourceMods" / "src.ww3"
    if not out_dir.is_dir():
        raise SystemExit(
            f"{out_dir} does not exist -- run create_newcase first "
            "(SourceMods/src.<comp> is created as part of standard case setup)."
        )

    out_path = out_dir / "namelist_definition_ww3.xml"
    out_path.write_text(build_override())

    assert "date_percent_point_percent_stride" in out_path.read_text()
    print(f"Wrote {out_path}")
