"""Board changes for the space/time work (SPACE_TIME.md), run once with the user's OK
(2026-10-30: "Do it all", "Feel free to change the board"):
- #335 becomes Q5 (TimeRequest); new issues Q20-Q23 with blocked-by links;
- Sprints 11-12 added; the sharing tail moves after the data-access PRs;
- #327's description posted; #328 (duplicate of #329) and ESMCI #53 (superseded by
  CDEPS#3) closed; #344 and a new static-download bug issue go to Backlog.
Prints each step; stops on the first gh error."""

import json
import subprocess
from pathlib import Path

HERE = Path(__file__).parent
PROJECT, STATUS, BACKLOG = "PVT_kwDOCrNdQM4Boz_Y", "PVTSSF_lADOCrNdQM4Boz_YzhnSU9M", "f75ad846"
SPRINT = "PVTIF_lADOCrNdQM4Boz_Yzhnc1zk"
CD, ESMCI, CC, CG = (
    "CROCODILE-CESM/CrocoDash",
    "ESMCI/visualCaseGen",
    "CROCODILE-CESM/crocontainer",
    "CROCODILE-CESM/CrocoGallery",
)


def gh(*args):
    res = subprocess.run(["gh", *args], capture_output=True, text=True)
    if res.returncode:
        raise SystemExit(f"gh {' '.join(args[:3])}: {res.stderr}")
    return res.stdout.strip()


def graphql(query, **variables):
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += ["-f", f"{k}={v}"]
    return json.loads(gh(*args))


def node(repo, number):
    return json.loads(gh("issue", "view", str(number), "-R", repo, "--json", "id"))["id"]


def items():
    """{(repo name, number): project item id}"""
    data = json.loads(
        gh("project", "item-list", "9", "--owner", "CROCODILE-CESM", "--format", "json", "--limit", "300")
    )
    return {
        (it["content"]["repository"].split("/")[-1], it["content"]["number"]): it["id"]
        for it in data["items"]
        if it.get("content", {}).get("number")
    }


def sprints():
    q = graphql(
        "query { node(id: \"%s\") { ... on ProjectV2IterationField { configuration {"
        " iterations { id title startDate duration } completedIterations { id title startDate duration } } } } }"
        % SPRINT
    )
    conf = q["data"]["node"]["configuration"]
    return conf["iterations"] + conf["completedIterations"]


def add_sprints(new):
    """Add iterations, passing every existing one back by id (keeps them and their items)."""
    its = sprints()
    have = {i["title"] for i in its}
    todo = [(t, d) for t, d in new if t not in have]
    if not todo:
        return
    rows = [
        '{id: "%s", title: "%s", startDate: "%s", duration: %d}' % (i["id"], i["title"], i["startDate"], i["duration"])
        for i in sorted(its, key=lambda i: i["startDate"])
    ] + ['{title: "%s", startDate: "%s", duration: 7}' % (t, d) for t, d in todo]
    graphql(
        'mutation { updateProjectV2Field(input: {fieldId: "%s", iterationConfiguration: '
        '{startDate: "2026-10-27", duration: 7, iterations: [%s]}}) { clientMutationId } }'
        % (SPRINT, ", ".join(rows))
    )
    after = {i["title"]: i["id"] for i in sprints()}
    for i in its:
        assert after.get(i["title"]) == i["id"], f"iteration {i['title']} changed id"
    print("sprints added:", [t for t, _ in todo])


def set_sprint(item_id, title):
    it = {i["title"]: i["id"] for i in sprints()}[title]
    gh("project", "item-edit", "--id", item_id, "--project-id", PROJECT, "--field-id", SPRINT, "--iteration-id", it)


def backlog(item_id):
    gh("project", "item-edit", "--id", item_id, "--project-id", PROJECT, "--field-id", STATUS,
       "--single-select-option-id", BACKLOG)


def create(repo, title, body, sprint=None, assign=True):
    args = ["issue", "create", "-R", repo, "--title", title, "--body", body]
    if assign:
        args += ["--assignee", "manishvenu"]
    url = gh(*args)
    item = json.loads(
        gh("project", "item-add", "9", "--owner", "CROCODILE-CESM", "--url", url, "--format", "json")
    )["id"]
    backlog(item)
    if sprint:
        set_sprint(item, sprint)
    number = int(url.rsplit("/", 1)[1])
    print("created", url, sprint or "")
    return number


def blocked_by(repo, number, blockers):
    for brepo, bnum in blockers:
        graphql(
            "mutation($i: ID!, $b: ID!) { addBlockedBy(input: {issueId: $i, blockingIssueId: $b}) { clientMutationId } }",
            i=node(repo, number), b=node(brepo, bnum),
        )
        print(f"{repo.split('/')[-1]}#{number} blocked by {brepo.split('/')[-1]}#{bnum}")


def body(scope, branch, depends, check=None):
    text = (
        f"{scope}\n\nPart of one way for every forcing product to handle space and time: a `Region` "
        "for the box and a `TimeRequest` for the dates.\n\n"
        f"**Repo:** CrocoDash\n**Branch:** `{branch}` (being built)\n**Depends on:** {depends}"
    )
    return text + (f"\n**Real-case check:** {check}" if check else "")


# 1. Sprints 11-12, then #335 becomes Q5.
add_sprints([("Sprint 11", "2027-01-05"), ("Sprint 12", "2027-01-12")])
gh("issue", "edit", "335", "-R", CD, "--title", "Describe each fetch's dates with a TimeRequest", "--body", body(
    "Every dated fetch gets one `TimeRequest`: the window (whole days, end day included) and, when "
    "the data is thinned, the dates to keep. The dates are worked out once for the whole window, so "
    "every chunk thins on the same dates. The CESM readers keep only the window's records through it; "
    "the initial condition takes the record at or before the start and is never thinned; and a run "
    "outside the product's data fails at configure. Replaces the `tseries-time-slice` re-cut of "
    "CROCODILE-CESM/CrocoDash#306.",
    "time-request",
    "CROCODILE-CESM/CrocoDash#332, CROCODILE-CESM/CrocoDash#333",
    "process a monthly CESM-POP case starting on the 1st and check the initial-condition record.",
))
print("edited #335")

# 2. New issues Q20-Q23.
q20 = create(CD, "Fetch every box as a Region and pad it once", body(
    "Every dated fetch gets one `Region`: a lat/lon box whose longitudes run east from `lon_min`, so a "
    "box across 180E is 170..190 and a 360-wide box is every longitude. `@accessmethod` adds the "
    "product's buffer (`buf`) once. Open-boundary edge boxes go the short way round the globe instead "
    "of taking a plain min/max, which fetches a whole latitude band for grids split at ±180 and for "
    "polar edges. CICE's extra ±1 degree goes.",
    "region", "CROCODILE-CESM/CrocoDash#335",
), "Sprint 7")
q21 = create(CD, "Fetch GLORYS and the reference products by Region and TimeRequest", body(
    "GLORYS (RDA, Copernicus API, CLI script) and the reference ocean, ice and wave products take "
    "`region` and `when`. The CLI script keeps every request: today a second request overwrites the "
    "first, because the check looks for `.sh` while regional-mom6 writes `.pbs`.",
    "glorys-reference-requests", f"CROCODILE-CESM/CrocoDash#{q20}",
), "Sprint 8")
q22 = create(CD, "Cut CESM output, CICE restarts and CESM-WW3-JRA spectra with Region.select", body(
    "The CESM-POP and CESM-MOM readers, the CICE restart subset and the CESM-WW3-JRA spectra cut their "
    "box with `Region.select`: columns run west to east across the source's own seam, and a box "
    "reaching a tripole fold keeps every column of its rows. Also: CICE grid units come from the file; "
    "WW3-JRA's coverage includes its spin-up and is checked at configure; a YYYYMM file end is read as "
    "the end of that month.",
    "cesm-cice-ww3jra-windows", f"CROCODILE-CESM/CrocoDash#{q20}",
), "Sprint 8")
q23 = create(CD, "Fetch ERA5 and GLOFAS by Region and TimeRequest, and drop the loose box and date arguments", body(
    "ERA5 asks for one area, two across 180E, or the globe; GLOFAS takes `when`. After this no dated "
    "access method takes `lat_min`/`lat_max`/`lon_min`/`lon_max` or `dates`: the temporary adapters, "
    "`make_dates_end_inclusive`, `convert_lons_to_180_range` and the per-product `validate_method` "
    "overrides go, and `adding_data_access.md` describes `Region` and `TimeRequest`.",
    "drop-loose-access-args", f"CROCODILE-CESM/CrocoDash#{q21}, CROCODILE-CESM/CrocoDash#{q22}",
), "Sprint 9")
blocked_by(CD, 335, [(CD, 332)])
blocked_by(CD, q20, [(CD, 335)])
blocked_by(CD, q21, [(CD, q20)])
blocked_by(CD, q22, [(CD, q20)])
blocked_by(CD, q23, [(CD, q21), (CD, q22)])
blocked_by(CD, 338, [(CD, q20)])
blocked_by(CD, 339, [(CD, q20)])

# 3. Sprint moves: the sharing tail goes after the data-access PRs.
ids = items()
for (repo, number), sprint in {
    ("CrocoDash", 341): "Sprint 9",
    ("CrocoDash", 340): "Sprint 10",
    ("CrocoDash", 338): "Sprint 10",
    ("CrocoDash", 342): "Sprint 11",
    ("CrocoDash", 339): "Sprint 11",
    ("CrocoDash", 343): "Sprint 12",
    ("crocontainer", 18): "Sprint 12",
    ("CrocoGallery", 63): "Sprint 12",
}.items():
    set_sprint(ids[(repo, number)], sprint)
    print(f"{repo}#{number} -> {sprint}")

# 4. #327's description.
gh("pr", "edit", "327", "-R", CD, "--body-file", str(HERE / "prs" / "Q03-time-sampling.md"))
print("posted #327 description")

# 5. Housekeeping.
gh("issue", "close", "328", "-R", CD, "--reason", "not planned", "--comment", "Duplicate of #329.")
print("closed #328")
gh("pr", "close", "53", "-R", ESMCI, "--comment",
   "Closing: CrocoDash now aligns the stream years through CDEPS, whose JRA, CORE2 IAF and GLOFAS "
   "streams read DATM_YR_*/DROF_YR_* (CROCODILE-CESM/CDEPS#3, used by CROCODILE-CESM/CrocoDash#326), "
   "so this planner isn't needed.")
print("closed ESMCI #53")
item = json.loads(gh("project", "item-add", "9", "--owner", "CROCODILE-CESM",
                     "--url", "https://github.com/CROCODILE-CESM/CrocoDash/issues/344", "--format", "json"))["id"]
backlog(item)
print("#344 -> Backlog")
create(CD, "Static download script methods fail on their defaults", (
    "Found while surveying the data products for the space/time work (2026-10-30):\n"
    "- `seawifs.get_global_seawifs_script_for_cli` and `gebco.get_gebco_data_script` default "
    "`output_folder=None`, then call `Path(output_folder)`, which raises `TypeError`.\n"
    "- `get_gebco_data_with_python` returns `None` instead of the extracted file's path.\n"
    "- `datasets/utils.write_bash_curl_script` opens the script inside `output_folder` before "
    "anything creates that folder (the `mkdir -p` is inside the script).\n\n"
    "None of these is on the forcing path (bathymetry and chlorophyll are fetched by hand)."
), assign=False)
print("done")
