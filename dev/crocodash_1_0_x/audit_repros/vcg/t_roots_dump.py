import sys, json
from visualCaseGen.initialize import initialize
cime = initialize(sys.argv[1])
out = {"compsets": sorted(cime.compsets), "machines": sorted(cime.machines), "ocnice": sorted(cime.domains["ocnice"])}
json.dump(out, open(sys.argv[2], "w"))
