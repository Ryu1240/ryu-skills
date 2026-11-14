#!/usr/bin/env bash
# 別リポジトリ特有の情報がこのリポジトリに入るのを防ぐ検査。
# スキルは架空のサンプル（sales-hub / shipment-api など）だけで書く前提なので、
# 実在する他リポジトリ名・ローカルの絶対パス・個人のメール・実在の Notion ページを見つけたら止める。
#
#   scripts/check-foreign-info.sh --staged   # pre-commit から。ステージした追加行だけを見る（既定）
#   scripts/check-foreign-info.sh --all      # 追跡中の全ファイルを見る
#
# 他リポジトリ名の一覧はリポジトリに置かない（一覧そのものが別リポジトリの情報になるため）。
# `gh repo list <owner>` の結果を .git/info/foreign-repos に 1 日キャッシュする。
# 追加の禁止語は .git/info/foreign-denylist、誤検知の除外は .git/info/foreign-allowlist に
# 1 行 1 つの拡張正規表現で書く（どちらも追跡されない）。
set -euo pipefail

mode="${1:---staged}"
root=$(git rev-parse --show-toplevel)
info="$(git rev-parse --absolute-git-dir)/info"
cd "$root"
mkdir -p "$info"
cache="$info/foreign-repos"
deny="$info/foreign-denylist"
allow="$info/foreign-allowlist"

origin=$(git remote get-url origin 2>/dev/null || true)
slug=$(printf '%s' "$origin" | sed -E 's#\.git$##; s#^.*github\.com[:/]##')
owner=${slug%%/*}
self=${slug##*/}

if [ -n "$owner" ] && command -v gh >/dev/null 2>&1 &&
   { [ ! -s "$cache" ] || [ -n "$(find "$cache" -mtime +0 2>/dev/null)" ]; }; then
  if gh repo list "$owner" --limit 1000 --json name -q '.[].name' >"$cache.tmp" 2>/dev/null; then
    mv "$cache.tmp" "$cache"
  else
    rm -f "$cache.tmp"
  fi
fi
if [ ! -s "$cache" ]; then
  echo "warning: 他リポジトリ名の一覧を取得できなかったため、リポジトリ名の検査を飛ばします（gh auth status を確認）" >&2
fi

lines=$(mktemp)
patterns=$(mktemp)
hits=$(mktemp)
trap 'rm -f "$lines" "$patterns" "$hits"' EXIT

exclude=':!scripts/check-foreign-info.sh'
if [ "$mode" = "--all" ]; then
  git grep -n -I -e '' -- . "$exclude" >"$lines" || true
else
  git diff --cached -U0 --no-color --diff-filter=ACMR -- . "$exclude" | awk '
    /^\+\+\+ /   { f = substr($0, 7); next }
    /^@@/        { split($3, a, ","); n = substr(a[1], 2) + 0; next }
    /^\+/        { print f ":" n ":" substr($0, 2); n++ }
  ' >"$lines"
fi
[ -s "$lines" ] || exit 0

# ラベル<TAB>拡張正規表現
{
  if [ -s "$cache" ]; then
    grep -vixF "$self" "$cache" | while IFS= read -r name; do
      [ -n "$name" ] || continue
      esc=$(printf '%s' "$name" | sed 's/[.]/\\./g')
      printf '他リポジトリ名(%s)\t(^|[^A-Za-z0-9_-])%s([^A-Za-z0-9_-]|$)\n' "$name" "$esc"
    done || true
  fi
  printf 'ローカルの絶対パス\t/(Users|home)/[A-Za-z0-9._-]+/\n'
  printf 'メールアドレス\t[A-Za-z0-9._%%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,}\n'
  printf '実在の Notion ページ\tnotion\\.(so|site)/[^ )]*[0-9a-f]{32}\n'
  if [ -s "$deny" ]; then
    grep -v '^[[:space:]]*\(#\|$\)' "$deny" | while IFS= read -r re; do
      printf '禁止語(%s)\t%s\n' "$re" "$re"
    done || true
  fi
} >"$patterns"

# 既知の安全な値（プレースホルダや公開されている定型アドレス）
safe='noreply@anthropic\.com|@users\.noreply\.github\.com|@example\.(com|org|net)|git@github\.com|/(Users|home)/(<[^>]*>|user|username|you|me|runner)/'

while IFS="$(printf '\t')" read -r label re; do
  grep -iE -- "$re" "$lines" | grep -viE -- "$safe" | while IFS= read -r hit; do
    if [ -s "$allow" ] && printf '%s\n' "$hit" | grep -qE -f <(grep -v '^[[:space:]]*\(#\|$\)' "$allow"); then
      continue
    fi
    printf '  [%s] %s\n' "$label" "$hit"
  done || true  # 一致なし（grep の終了コード 1）は正常
done <"$patterns" >"$hits"

if [ -s "$hits" ]; then
  echo "別リポジトリ特有の情報らしきものが見つかりました:" >&2
  cat "$hits" >&2
  cat >&2 <<'MSG'

スキルとサンプルは架空の名前で書いてください（例: sales-hub / shipment-api）。
誤検知なら .git/info/foreign-allowlist に除外パターンを 1 行足してから、もう一度コミットしてください。
MSG
  exit 1
fi
