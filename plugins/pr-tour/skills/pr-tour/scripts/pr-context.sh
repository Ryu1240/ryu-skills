#!/usr/bin/env bash
# pr-tour 補助スクリプト
#
# 使い方:
#   bash pr-context.sh [-C <リポジトリのパス>] <PR番号 | PR URL | ブランチ名>
#
# やること:
#   1. gh で PR の base/head を解決する（PR が無いブランチ名なら base=origin の既定ブランチ）
#   2. base/head を refs/pr-tour/<id>/{base,head} に fetch する（作業ツリーには触れない）
#   3. PR メタ情報・既存プラン・コミット一覧・変更ファイルのレイヤー分類を出力する
#
# 出力の見方:
#   [meta]    PR 番号・タイトル・URL・base/head・SHA・作業ツリーとの一致
#   [plan]    既存プランの有無（更新時刻・セッション・記録 head とのズレ）
#   [body]    PR 本文（先頭 40 行）
#   [commits] head 側のコミット（merge-base 以降）
#   [files]   レイヤー順に並べた変更ファイル。列は  レイヤー<TAB>状態<TAB>+追加/-削除<TAB>パス
#             状態: A=追加 M=変更 D=削除 R=リネーム
#   [summary] git diff --shortstat
#
# レイヤー分類はパス名からの推測にすぎない。リポジトリの構成は CLAUDE.md や README で確かめること。
set -euo pipefail

if [ "${1:-}" = "-C" ]; then
  cd "$2"
  shift 2
fi
cd "$(git rev-parse --show-toplevel)"

ARG="${1:-}"
if [ -z "$ARG" ]; then
  echo "usage: pr-context.sh [-C <repo>] <PR番号 | PR URL | ブランチ名>" >&2
  exit 2
fi

GH=""
if command -v gh >/dev/null 2>&1; then GH="gh"
elif [ -x /opt/homebrew/bin/gh ]; then GH="/opt/homebrew/bin/gh"
fi

PR_NUMBER=""
case "$ARG" in
  *github.com/*/pull/*) PR_NUMBER="${ARG##*/pull/}"; PR_NUMBER="${PR_NUMBER%%[^0-9]*}" ;;
  ''|*[!0-9]*) ;;
  *) PR_NUMBER="$ARG" ;;
esac

DEFAULT_BRANCH="$(git symbolic-ref -q --short refs/remotes/origin/HEAD 2>/dev/null | sed 's#^origin/##' || true)"
DEFAULT_BRANCH="${DEFAULT_BRANCH:-main}"

TITLE=""; URL=""; BODY=""; BASE_REF="$DEFAULT_BRANCH"; HEAD_REF=""; STATE="NO_PR"; MERGE_COMMIT=""
FIELDS="number,title,url,body,baseRefName,headRefName,state,mergeCommit"

read_pr_json() {
  STATE="$(printf '%s' "$1" | jq -r '.state')"
  MERGE_COMMIT="$(printf '%s' "$1" | jq -r '.mergeCommit.oid // ""')"
  PR_NUMBER="$(printf '%s' "$1" | jq -r '.number')"
  TITLE="$(printf '%s' "$1" | jq -r '.title')"
  URL="$(printf '%s' "$1" | jq -r '.url')"
  BODY="$(printf '%s' "$1" | jq -r '.body // ""')"
  BASE_REF="$(printf '%s' "$1" | jq -r '.baseRefName')"
  HEAD_REF="$(printf '%s' "$1" | jq -r '.headRefName')"
}

if [ -n "$PR_NUMBER" ]; then
  if [ -z "$GH" ]; then
    echo "error: gh が見つからないため PR 番号を解決できません。ブランチ名で指定してください。" >&2
    exit 3
  fi
  read_pr_json "$($GH pr view "$PR_NUMBER" --json "$FIELDS")"
  ID="$PR_NUMBER"
else
  HEAD_REF="$ARG"
  ID="branch-$(printf '%s' "$ARG" | tr '/' '-' | tr -c 'A-Za-z0-9._-\n' '-')"
  if [ -n "$GH" ] && JSON="$($GH pr view "$ARG" --json "$FIELDS" 2>/dev/null)"; then
    read_pr_json "$JSON"
    ID="$PR_NUMBER"
  fi
fi

BASE_LOCAL="refs/pr-tour/$ID/base"
HEAD_LOCAL="refs/pr-tour/$ID/head"

git fetch -q origin "+refs/heads/$BASE_REF:$BASE_LOCAL"

if [ -n "$PR_NUMBER" ]; then
  git fetch -q origin "+refs/pull/$PR_NUMBER/head:$HEAD_LOCAL"
elif git fetch -q origin "+refs/heads/$HEAD_REF:$HEAD_LOCAL" 2>/dev/null; then
  :
elif git rev-parse -q --verify "$HEAD_REF" >/dev/null; then
  git update-ref "$HEAD_LOCAL" "$(git rev-parse "$HEAD_REF")"
else
  echo "error: ブランチ '$HEAD_REF' が origin にもローカルにも見つかりません" >&2
  exit 4
fi

# マージ済み PR は base の先端が head を含むので、そのままでは差分が空になる。
# マージコミットの第 1 親（マージ直前の base）を base に、第 2 親（PR head）を head に置き直す。
# squash / rebase マージ（親が 1 つ）なら base=親、head=マージコミット。
if [ "$STATE" = "MERGED" ] && [ -n "$MERGE_COMMIT" ]; then
  git rev-parse -q --verify "$MERGE_COMMIT^{commit}" >/dev/null 2>&1 || git fetch -q origin "$MERGE_COMMIT" || true
  PARENTS="$(git rev-list --parents -n1 "$MERGE_COMMIT" | wc -w | tr -d ' ')"
  if [ "$PARENTS" -ge 3 ]; then
    git update-ref "$BASE_LOCAL" "$(git rev-parse "$MERGE_COMMIT^1")"
    git update-ref "$HEAD_LOCAL" "$(git rev-parse "$MERGE_COMMIT^2")"
  elif [ "$PARENTS" -eq 2 ]; then
    git update-ref "$BASE_LOCAL" "$(git rev-parse "$MERGE_COMMIT^1")"
    git update-ref "$HEAD_LOCAL" "$(git rev-parse "$MERGE_COMMIT")"
  fi
fi

MERGE_BASE="$(git merge-base "$BASE_LOCAL" "$HEAD_LOCAL")"
CURRENT_BRANCH="$(git branch --show-current || true)"
HEAD_SHA="$(git rev-parse "$HEAD_LOCAL")"
LOCAL_SHA="$(git rev-parse HEAD)"

echo "[meta]"
echo "repo_root: $(pwd)"
echo "pr_number: ${PR_NUMBER:-（PR なし）}"
echo "title: ${TITLE:-（なし）}"
echo "url: ${URL:-（なし）}"
echo "state: $STATE${MERGE_COMMIT:+ (merge_commit=$MERGE_COMMIT)}"
echo "base_ref: $BASE_REF"
echo "head_ref: $HEAD_REF"
echo "head_sha: $HEAD_SHA"
echo "current_branch: ${CURRENT_BRANCH:-（detached）}"
echo "local_head_sha: $LOCAL_SHA"
# 同名ブランチでも、ローカルが遅れている・force push で履歴が差し替わっていると
# 作業ツリーの行番号は head と食い違う。SHA が一致するときだけ作業ツリーをそのまま読む。
if [ "$LOCAL_SHA" = "$HEAD_SHA" ]; then
  echo "working_tree_matches_head: yes（作業ツリーをそのまま読める）"
else
  BEHIND="$(git rev-list --count "HEAD..$HEAD_LOCAL" 2>/dev/null || echo '?')"
  AHEAD="$(git rev-list --count "$HEAD_LOCAL..HEAD" 2>/dev/null || echo '?')"
  if [ "$CURRENT_BRANCH" = "$HEAD_REF" ]; then
    echo "working_tree_matches_head: no（同名ブランチだが SHA が違う: head より ${BEHIND} コミット遅れ、ローカル固有 ${AHEAD} コミット。force push か未 pull。worktree を作ること）"
  else
    echo "working_tree_matches_head: no（別ブランチ。worktree を作ること）"
  fi
fi
echo "id: $ID"
echo "base_local_ref: $BASE_LOCAL"
echo "head_local_ref: $HEAD_LOCAL"
echo "merge_base: $MERGE_BASE"
echo "diff_cmd: git diff $BASE_LOCAL...$HEAD_LOCAL"
echo

# 別セッションが同じ PR を案内している最中に上書きすると、双方のプランと Artifact が壊れる。
# 更新時刻とセッション識別子を見せて、ユーザーが判断できるようにする。
echo "[plan]"
PLAN=".claude/pr-tour/pr-$ID.md"
[ "${ID#branch-}" != "$ID" ] && PLAN=".claude/pr-tour/$ID.md"
if [ -f "$PLAN" ]; then
  AGE_MIN=$(( ( $(date +%s) - $(stat -f %m "$PLAN" 2>/dev/null || stat -c %Y "$PLAN") ) / 60 ))
  SESSION_LINE="$(grep -m1 -E '^- session:' "$PLAN" || echo '- session: （記録なし）')"
  STEP_LINE="$(grep -m1 -E '^- 現在のステップ:' "$PLAN" || true)"
  RECORDED_HEAD="$(grep -m1 -oE 'head \(([0-9a-f]{7,40})' "$PLAN" | grep -oE '[0-9a-f]{7,40}' || true)"
  echo "existing: ${PLAN}（最終更新 ${AGE_MIN} 分前）"
  echo "  ${SESSION_LINE}"
  [ -n "$STEP_LINE" ] && echo "  ${STEP_LINE}"
  if [ -n "$RECORDED_HEAD" ] && [ "${HEAD_SHA#"$RECORDED_HEAD"}" = "$HEAD_SHA" ]; then
    echo "  head_changed_since_plan: yes（プランは ${RECORDED_HEAD} 基準。force push か追加コミット。差分を確認して file:line を見直すこと）"
  fi
  if [ "$AGE_MIN" -lt 30 ]; then
    echo "  warning: 30 分以内に更新されている。別セッションが進行中の可能性がある。上書きせずユーザーに確認すること"
  fi
else
  echo "existing: なし"
fi
echo

echo "[body]"
if [ -n "$BODY" ]; then printf '%s\n' "$BODY" | head -40; else echo "（PR 本文なし）"; fi
echo

echo "[commits]"
git log --no-merges --format='%h %s' "$MERGE_BASE..$HEAD_LOCAL"
echo

echo "[files]"
# 起点に近いもの（CI・IaC・エントリ）から、コア、設定、ドキュメント、テストの順に並べる
paste \
  <(git diff --name-status -M "$BASE_LOCAL...$HEAD_LOCAL" | awk -F'\t' '{ st=substr($1,1,1); print st "\t" $NF }') \
  <(git diff --numstat   -M "$BASE_LOCAL...$HEAD_LOCAL" | awk '{ print "+" $1 "/-" $2 }') \
| awk -F'\t' '
  function layer(p) {
    if (p ~ /(^|\/)(test|tests|spec|specs|__tests__|e2e)\// || p ~ /(_test\.go|_spec\.rb|\.test\.[jt]sx?|\.spec\.[jt]sx?|(^|\/)test_[^\/]*\.py|_test\.py)$/) return "90 test"
    if (p ~ /\.stories\.[jt]sx?$/)                                                    return "91 test:stories"
    if (p ~ /^\.github\/|^\.gitlab-ci|^\.circleci\/|(^|\/)Jenkinsfile$/)             return "10 ci"
    if (p ~ /(^|\/)(infra|terraform|cdk|deploy|k8s|helm|charts)\// || p ~ /\.tf$/ || p ~ /(^|\/)(Dockerfile|docker-compose[^\/]*\.ya?ml|compose\.ya?ml)$/) return "20 infra"
    if (p ~ /(^|\/)(routes?|router|urls)(\.[a-z]+)?$/ || p ~ /(^|\/)(routes|pages|app\/api|cmd|bin)\//) return "30 entry"
    if (p ~ /(^|\/)(controllers?|handlers?|api|views|resolvers|graphql)\//)          return "31 entry:handler"
    if (p ~ /(^|\/)(jobs|workers|consumers|listeners|subscribers|tasks|cron)\//)     return "32 entry:async"
    if (p ~ /(^|\/)(components|screens|hooks|composables|stores?)\//)                return "33 ui"
    if (p ~ /(^|\/)(services?|usecases?|use_cases|interactors|domain|core)\//)       return "40 core"
    if (p ~ /(^|\/)(models?|entities|repositories|repos|dao|queries)\//)             return "45 data"
    if (p ~ /(^|\/)(migrations?|migrate|schema)\// || p ~ /(^|\/)schema\.[a-z]+$/ || p ~ /\.sql$/ || p ~ /\.prisma$/) return "46 data:schema"
    if (p ~ /(^|\/)(adapters?|clients?|gateways?|integrations?|infrastructure)\//)  return "47 adapters"
    if (p ~ /(^|\/)(lib|pkg|internal|src|app)\//)                                    return "50 code"
    if (p ~ /(^|\/)(config|settings)\// || p ~ /(^|\/)\.env/)                        return "60 config"
    if (p ~ /(^|\/)(package\.json|package-lock\.json|pnpm-lock\.yaml|yarn\.lock|tsconfig[^\/]*\.json|Gemfile(\.lock)?|go\.(mod|sum)|Cargo\.(toml|lock)|pyproject\.toml|poetry\.lock|uv\.lock|requirements[^\/]*\.txt|Makefile|justfile)$/) return "61 config:tooling"
    if (p ~ /(^|\/)\.[a-z]*(lint|prettier|format|editorconfig)[^\/]*$/)             return "62 config:lint"
    if (p ~ /(^|\/)(locales?|i18n|translations)\//)                                  return "70 i18n"
    if (p ~ /(^|\/)(docs?|adr|adrs)\//)                                              return "80 docs"
    if (p ~ /(^|\/)(README|CHANGELOG|CLAUDE|AGENTS|CONTRIBUTING)[^\/]*\.md$/)        return "81 readme"
    return "99 other"
  }
  { l = layer($2); sub(/^[0-9]+ /, "", l); print layer($2) "\t" l "\t" $1 "\t" $3 "\t" $2 }
' | sort -t$'\t' -k1,1 -s | cut -f2-
echo
echo "[summary]"
git diff --shortstat "$BASE_LOCAL...$HEAD_LOCAL"
