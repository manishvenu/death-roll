#!/usr/bin/env bash
# Build `seen`: every open CrocoDash PR merged into one working tree.
#
# Named after git.git's own `seen` branch (formerly `pu`, "proposed updates"),
# which Junio rebuilds from scratch each day by merging every in-flight topic.
# linux-next does the same with ~200 subsystem trees. The rule those follow, and
# this does too: `seen` is GENERATED, never maintained. Do not commit to it, do
# not merge it into anything, do not open a PR from it. When it drifts, delete
# it and run this again.
#
# What it is for: developing against the combined state of the CrocoDash stack
# while that stack is still in review, without hand-merging branches every time
# one of them gains a commit.
#
# Deliberately short-lived. The PR list is read live from `gh`, so as PRs merge
# their entries simply stop appearing; when the last one lands, `seen` equals
# main and this script can be deleted along with crocontainer's
# INTEGRATION_BRANCHES.md.
#
# Usage:
#   dev/build_seen.sh            # rebuild the worktree from scratch
#   dev/build_seen.sh --keep     # reuse the existing worktree (keeps rerere cache warm)

set -euo pipefail

CROC_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
REPO="${CROC_ROOT}/regional_mom_workflows/CrocoDash"
WORKTREE="${CROC_ROOT}/regional_mom_workflows/CrocoDash-worktrees/seen"
GH_REPO="CROCODILE-CESM/CrocoDash"
BASE="origin/main"

command -v gh >/dev/null 2>&1 || { echo "gh not found -- run 'module load gh' first." >&2; exit 1; }

echo "Fetching ${GH_REPO}..."
git -C "${REPO}" fetch -q origin --prune

# Merge order is everything. These PRs form a stack four deep with fans at each
# level, and merging a descendant subsumes its ancestors -- so deepest first.
# Naive PR-number order produces 11 conflicts across this stack; depth order
# produces 7, most of them one or two files. This is the same reason linux-next
# keeps its tree order in a file rather than merging alphabetically.
ORDER=$(gh pr list --repo "${GH_REPO}" --state open --limit 100 \
          --json number,headRefName,baseRefName -q '.[] | [.number, .headRefName, .baseRefName] | @tsv' \
        | python3 -c '
import sys
rows = [l.rstrip("\n").split("\t") for l in sys.stdin if l.strip()]
base_of = {head: base for _, head, base in rows}

def depth(head, seen=None):
    seen = seen or set()
    d, cur = 0, head
    while cur in base_of and cur not in seen:
        seen.add(cur); cur = base_of[cur]; d += 1
    return d

for num, head, _ in sorted(rows, key=lambda r: (-depth(r[1]), int(r[0]))):
    print(f"{num}\t{head}")
')

[[ -n "${ORDER}" ]] || { echo "No open PRs -- main is the combined state. Delete this script."; exit 0; }

if [[ "${1:-}" != "--keep" ]]; then
    git -C "${REPO}" worktree remove --force "${WORKTREE}" 2>/dev/null || true
    rm -rf "${WORKTREE}"
    git -C "${REPO}" worktree add -q --detach "${WORKTREE}" "${BASE}"
fi
cd "${WORKTREE}"
git checkout -q --detach "${BASE}"

# Records each conflict resolution the first time and replays it on every later
# rebuild -- the thing that makes a regenerated branch cheap rather than a chore.
git config rerere.enabled true

echo
echo "Merging onto $(git rev-parse --short HEAD) (${BASE}), deepest first:"
merged=(); skipped=()
while IFS=$'\t' read -r num head; do
    [[ -n "${head}" ]] || continue
    if git merge --no-edit -q "origin/${head}" >/dev/null 2>&1; then
        printf '  ok        #%-4s %s\n' "${num}" "${head}"
        merged+=("#${num} ${head}")
    else
        files=$(git diff --name-only --diff-filter=U | tr '\n' ' ')
        printf '  CONFLICT  #%-4s %-40s %s\n' "${num}" "${head}" "${files}"
        git merge --abort 2>/dev/null || true
        skipped+=("#${num} ${head} -- ${files}")
    fi
done <<< "${ORDER}"

# Submodule pointers move independently of the merges above, so refresh them
# against whatever the combined tree now records.
git submodule update --init --recursive -q 2>/dev/null || \
    echo "  (submodule update reported problems -- check rm6/visualCaseGen by hand)"

echo
echo "seen is at $(git rev-parse --short HEAD) in ${WORKTREE}"
echo "  merged:  ${#merged[@]}"
if (( ${#skipped[@]} )); then
    echo "  SKIPPED: ${#skipped[@]} -- these PRs are NOT in this tree:"
    printf '    %s\n' "${skipped[@]}"
    echo
    echo "  Resolve one by hand to teach rerere:"
    echo "    cd ${WORKTREE} && git merge origin/<branch>"
    echo "    # fix conflicts, git add, git commit -- rerere records it"
    echo "  Later rebuilds replay that resolution automatically."
fi
