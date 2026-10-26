"""Board issues for the grid-paths work (run only with the user's OK):
CrocoDash Q19, crocontainer C2 and CrocoGallery G1 in project 9's Backlog,
with blocked-by links, and the stale crocontainer#16 <- CrocoDash#340 link
removed (#16 closed when crocontainer #17 merged)."""

import json
import subprocess

PROJECT, STATUS, BACKLOG = "PVT_kwDOCrNdQM4Boz_Y", "PVTSSF_lADOCrNdQM4Boz_YzhnSU9M", "f75ad846"


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


def create(repo, title, body):
    url = gh("issue", "create", "-R", repo, "--title", title, "--body", body)
    item = json.loads(
        gh("project", "item-add", "9", "--owner", "CROCODILE-CESM", "--url", url, "--format", "json")
    )["id"]
    gh("project", "item-edit", "--id", item, "--project-id", PROJECT, "--field-id", STATUS,
       "--single-select-option-id", BACKLOG)
    return url, int(url.rsplit("/", 1)[1])


def blocked_by(repo, number, blockers):
    for brepo, bnum in blockers:
        graphql(
            "mutation($i: ID!, $b: ID!) { addBlockedBy(input: {issueId: $i, blockingIssueId: $b}) { clientMutationId } }",
            i=node(repo, number), b=node(brepo, bnum),
        )


CD, CC, CG = "CROCODILE-CESM/CrocoDash", "CROCODILE-CESM/crocontainer", "CROCODILE-CESM/CrocoGallery"
q19_url, q19 = create(
    CD, "Name the grid files in the create config instead of building grids",
    "Makes a create config the arguments of `Case()` and of `configure_forcings()`: `case:` names "
    "the grid files (`ocn_grid`, `ocn_topo`, `ocn_vgrid`), and the `grid:`, `topo:` and `vgrid:` "
    "sections go, so the YAML no longer changes with mom6_forge's API. About 120 lines added and "
    "315 removed.\n\n**Repo:** CrocoDash\n**Branch:** [`yaml-grid-paths`]"
    "(https://github.com/CROCODILE-CESM/CrocoDash/tree/yaml-grid-paths) (built and pushed)\n"
    "**Depends on:** CROCODILE-CESM/CrocoDash#342\n"
    "**Goes with:** the crocontainer and CrocoGallery changes that write and name grid files "
    "(their issues are blocked by this one), and the CrocoDash MCP server's `create_case` "
    "writing grid files first",
)
print("Q19", q19_url)
c2_url, c2 = create(
    CC, "Write the grid files the case configs name, instead of grids in YAML",
    "The Panama demo, YAML config mode, the weekly tests and the NYF sample write their grid files "
    "with short CrocoDash (mom6_forge) scripts, and their configs name them, for CrocoDash's new "
    "create config.\n\n**Repo:** crocontainer\n**Branch:** [`grid-files`]"
    "(https://github.com/CROCODILE-CESM/crocontainer/tree/grid-files) (built and pushed)\n"
    f"**Depends on:** CROCODILE-CESM/CrocoDash#{q19}. Merge the two together: the weekly tests "
    "follow both repos' branch tips.",
)
print("C2", c2_url)
g1_url, g1 = create(
    CG, "Update the CLI page and starter config for CrocoDash's new create",
    "The starter config (`crocodash template --output x.yaml`) names the grid files; the CLI page "
    "covers `create --from`, `configure` and the forcing prompts, without `fork` and `duplicate`; "
    "the tutorials link to CrocoDash's `sharing` page.\n\n**Repo:** CrocoGallery\n**Branch:** "
    "[`crocodash-cli-overhaul`](https://github.com/CROCODILE-CESM/CrocoGallery/tree/crocodash-cli-overhaul) "
    f"(built and pushed)\n**Depends on:** CROCODILE-CESM/CrocoDash#340, #341 and #{q19} (it "
    "describes them as merged)",
)
print("G1", g1_url)
blocked_by(CD, q19, [(CD, 342)])
blocked_by(CC, c2, [(CD, q19)])
blocked_by(CG, g1, [(CD, 340), (CD, 341), (CD, q19)])
graphql(
    "mutation($i: ID!, $b: ID!) { removeBlockedBy(input: {issueId: $i, blockingIssueId: $b}) { clientMutationId } }",
    i=node(CC, 16), b=node(CD, 340),
)
print("linked; removed crocontainer#16 <- CrocoDash#340")
