#!/usr/bin/env bash
# stacked-pr 補助スクリプト
#
# 使い方:
#   bash stack-status.sh [-R <owner/repo>] <スタック内のどれかの PR 番号 | ブランチ名>
#
# やること:
#   1. open な PR の base/head の繋がりを辿り、trunk に近い側（下）から順に並べる
#   2. 各 PR の状態を 1 行ずつ出す
#   3. 本文の位置ブロック（スタック i/n・前: #・次: #）が実際の並びと合っているかを照らす
#
# 出力（タブ区切り。1 行目が見出し）:
#   pos       下から数えた段（1 が一番下）
#   pr        PR 番号
#   base      base ブランチ
#   head      head ブランチ
#   sha       head の SHA（先頭 10 桁。merge-async の sha にはフルの値を gh pr view で取る）
#   draft     draft なら yes
#   mergeable MERGEABLE / CONFLICTING / UNKNOWN（UNKNOWN は計算中。少し待って再実行）
#   state     mergeStateStatus（CLEAN / DIRTY / BLOCKED / BEHIND / UNSTABLE / HAS_HOOKS / UNKNOWN）
#   ci        statusCheckRollup の状態（SUCCESS / FAILURE / PENDING / ERROR / none=チェックが 1 件も無い）
#   threads   未解決のレビュースレッド数
#   gh_stack  GitHub のスタック登録上の位置（position/size）。未登録なら -
#   body      本文の位置表記の照合結果（ok / 食い違いの内容 / none=位置ブロックが無い）
#   linear    本文・ブランチ名・タイトルから拾った Linear issue ID。チームキーは環境変数 LINEAR_KEY
#             （拡張正規表現。既定は大文字 2〜7 文字）で絞れる。例: LINEAR_KEY=TEC bash stack-status.sh 101
#
# 注意:
#   - 辿れるのは open な PR だけ。マージ済みの段は出ない
#   - 1 つの head を base にする PR が複数ある（枝分かれ）ときは警告を出し、番号の小さい方を辿る
#   - サンドボックス内で gh が TLS エラーになるときは、サンドボックスの外で再実行する
set -euo pipefail

REPO_ARGS=()
if [ "${1:-}" = "-R" ]; then
  REPO_ARGS=(-R "$2")
  shift 2
fi
LINEAR_KEY="${LINEAR_KEY:-[A-Z][A-Z0-9]{1,6}}"
ARG="${1:?PR 番号かブランチ名を指定してください}"

command -v gh >/dev/null || { echo "gh が見つかりません" >&2; exit 1; }
command -v jq >/dev/null || { echo "jq が見つかりません" >&2; exit 1; }

REPO=$(gh repo view ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --json nameWithOwner -q .nameWithOwner)
TRUNK=$(gh repo view ${REPO_ARGS[@]+"${REPO_ARGS[@]}"} --json defaultBranchRef -q .defaultBranchRef.name)
OWNER=${REPO%%/*}
NAME=${REPO##*/}

OPEN=$(gh pr list -R "$REPO" --state open --limit 300 --json number,headRefName,baseRefName)
START=$(gh pr view -R "$REPO" "$ARG" --json number,headRefName,baseRefName,state)
if [ "$(jq -r .state <<<"$START")" != "OPEN" ]; then
  echo "warning: #$(jq -r .number <<<"$START") は open ではありません（$(jq -r .state <<<"$START")）。open な PR だけを辿ります" >&2
fi

# 下へ辿る: base を head に持つ PR を探す
chain=$(jq -r .number <<<"$START")
base=$(jq -r .baseRefName <<<"$START")
while [ "$base" != "$TRUNK" ]; do
  below=$(jq -r --arg b "$base" '[.[] | select(.headRefName == $b)] | sort_by(.number) | .[0].number // empty' <<<"$OPEN")
  [ -n "$below" ] || { echo "warning: base '$base' を head に持つ open な PR が無いため、ここを一番下とみなします" >&2; break; }
  chain="$below $chain"
  base=$(jq -r --argjson n "$below" '.[] | select(.number == $n) | .baseRefName' <<<"$OPEN")
done

# 上へ辿る: head を base に持つ PR を探す
head=$(jq -r .headRefName <<<"$START")
while :; do
  above=$(jq -r --arg h "$head" '[.[] | select(.baseRefName == $h)] | sort_by(.number) | map(.number)' <<<"$OPEN")
  count=$(jq length <<<"$above")
  [ "$count" -gt 0 ] || break
  if [ "$count" -gt 1 ]; then
    echo "warning: '$head' を base にする PR が複数あります: $(jq -r 'map("#\(.)") | join(" ")' <<<"$above")。#$(jq -r '.[0]' <<<"$above") を辿ります" >&2
  fi
  n=$(jq -r '.[0]' <<<"$above")
  chain="$chain $n"
  head=$(jq -r --argjson n "$n" '.[] | select(.number == $n) | .headRefName' <<<"$OPEN")
done

read -r -a PRS <<<"$chain"
TOTAL=${#PRS[@]}

QUERY='query($owner:String!,$name:String!,$n:Int!){repository(owner:$owner,name:$name){pullRequest(number:$n){
  number title body baseRefName headRefName headRefOid isDraft mergeable mergeStateStatus
  commits(last:1){nodes{commit{statusCheckRollup{state}}}}
  reviewThreads(first:100){nodes{isResolved}}
}}}'

printf 'pos\tpr\tbase\thead\tsha\tdraft\tmergeable\tstate\tci\tthreads\tgh_stack\tbody\tlinear\n'
i=0
for n in "${PRS[@]}"; do
  i=$((i + 1))
  pr=$(gh api graphql -f query="$QUERY" -F owner="$OWNER" -F name="$NAME" -F n="$n" --jq .data.repository.pullRequest)
  stack=$(gh api "repos/$REPO/pulls/$n" -H "X-GitHub-Api-Version: 2026-03-10" \
    --jq 'if .stack then "\(.stack.position)/\(.stack.size)" else "-" end' 2>/dev/null || echo "-")

  prev=""; next=""
  [ "$i" -gt 1 ] && prev=${PRS[$((i - 2))]}
  [ "$i" -lt "$TOTAL" ] && next=${PRS[$i]}

  body=$(jq -r '.body // ""' <<<"$pr")
  check=$(BODY="$body" python3 - "$i" "$TOTAL" "$prev" "$next" <<'PY'
import os, re, sys
pos, total, prev, nxt = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
body = os.environ["BODY"]
m_pos = re.search(r"スタック\s*(\d+)\s*/\s*(\d+)", body)
m_prev = re.search(r"前\s*[:：]\s*(#(\d+)|なし)", body)
m_next = re.search(r"次\s*[:：]\s*(#(\d+)|なし)", body)
if not (m_pos or m_prev or m_next):
    print("none"); sys.exit()
issues = []
if m_pos and (m_pos.group(1), m_pos.group(2)) != (pos, total):
    issues.append(f"位置 {m_pos.group(1)}/{m_pos.group(2)}→{pos}/{total}")
def cmp(label, m, want):
    got = m.group(2) if m and m.group(2) else ""
    if m is None:
        issues.append(f"{label}の記載なし")
    elif got != want:
        issues.append(f"{label} {('#' + got) if got else 'なし'}→{('#' + want) if want else 'なし'}")
cmp("前", m_prev, prev)
cmp("次", m_next, nxt)
print("ok" if not issues else "; ".join(issues))
PY
)
  linear=$({ jq -r '"\(.title) \(.body // "")"' <<<"$pr"; jq -r .headRefName <<<"$pr" | tr '[:lower:]' '[:upper:]'; } |
    grep -oE "\\b(${LINEAR_KEY})-[0-9]+\\b" | sort -u | paste -sd, - || true)

  jq -r --arg pos "$i" --arg stack "$stack" --arg body "$check" --arg linear "${linear:--}" '[
    $pos, "#\(.number)", .baseRefName, .headRefName, .headRefOid[0:10],
    (if .isDraft then "yes" else "no" end), .mergeable, .mergeStateStatus,
    (.commits.nodes[0].commit.statusCheckRollup.state // "none"),
    ([.reviewThreads.nodes[] | select(.isResolved | not)] | length | tostring),
    $stack, $body, $linear
  ] | @tsv' <<<"$pr"
done
