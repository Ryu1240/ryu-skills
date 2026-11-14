# 出力先（Phase 0 で読む）

> プラン（Markdown）・視覚ビュー（HTML）・敵対的レビューの結果・レビュー下書きの置き場所を決める。

## 既定

対象リポジトリのルートからの相対で `.claude/pr-tour/`。

| ファイル | パス |
|---|---|
| プラン（正） | `.claude/pr-tour/pr-<番号>.md`（PR が無いブランチは `branch-<ブランチ名をハイフン化>.md`） |
| 視覚ビュー | 同じ名前の `.html` |
| 敵対的レビューの結果 | `.claude/pr-tour/pr-<番号>-adversarial-review.md` |
| レビュー下書き（Phase 6） | `.claude/pr-tour/pr-<番号>-review-draft.md` |
| 図解の一時ファイル | スクラッチパッド（無ければ `.claude/pr-tour/tmp/`） |

## git 追跡外を保証する

これらはツアーの個人的な記録で、チームのリポジトリにコミットするものではない。リポジトリの `.gitignore` を書き換えるとその変更自体が差分になるので、そのクローン限定の `.git/info/exclude` に追記する。

```bash
mkdir -p .claude/pr-tour
git check-ignore -q .claude/pr-tour || echo "/.claude/pr-tour/" >> "$(git rev-parse --git-path info/exclude)"
```

`git rev-parse --git-path` を使うのは、worktree やサブモジュールでは `.git` がディレクトリではなくファイルで、`.git/info/exclude` を直接書けないため。

## ユーザーが別の置き場所を指定したとき

個人のメモ置き場など、ユーザーが別ディレクトリを指定したらそれに従い、同じ手順で追跡外を保証する。保存パスをチャットに表示するときは、決めたパスをそのまま使う（`.claude/pr-tour/` と決め打ちで書かない）。

## 対象リポジトリのクローンが手元に無いとき

書き込む先のリポジトリが無いので、プラン一式をスクラッチパッドに置き、その旨をプランの先頭に書く。スクラッチパッドはセッション固有なので、別セッションからの再開はできない（→ SKILL.md「再開」）。
