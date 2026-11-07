# Each Case() calls visualCaseGen.initialize(); do widgets / sys.path entries accumulate?
import sys, gc, resource
import ipywidgets
from visualCaseGen.initialize import initialize
R = "/glade/u/home/manishrv/work/installs/CESM_crocodash"
def nwidgets():
    reg = getattr(ipywidgets.Widget, "_active_widgets", None) or getattr(ipywidgets.Widget, "widgets", {})
    return len(reg)
print("ipywidgets", ipywidgets.__version__)
for i in range(4):
    initialize(R); gc.collect()
    print(f"after initialize #{i+1}: live widgets={nwidgets()}  maxrss={resource.getrusage(resource.RUSAGE_SELF).ru_maxrss/1024:.0f} MB  cime entries in sys.path={sum(p.endswith('/cime') for p in sys.path)}")
