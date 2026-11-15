---
name: stacked-pr
description: GitHub のスタック PR（下の PR の head ブランチを上の PR の base にして積む PR の連なり）を作る・保つ・マージするためのスキル。「PR を積みたい」「スタック PR にして」「下の PR を直したので上に伝えたい」「main を取り込みたい（スタックの途中で）」「スタックをまとめてマージして」「part of a stack と言われてマージできない」「merge-async」「stacked PR」"stack these PRs" など、依存する複数の PR を順番に作る・rebase で揃える・状態を確かめる・マージする場面で使う。1 PR = 1 ストーリー（関連 issue のまとまり）で積み、PR 本文にスタック上の位置と Linear の issue ID を書く。main の取り込みは下から順に揃え、上の PR だけに取り込まない。マージは一番上（または止めたい位置）の PR に対して非同期マージ API（merge-async）を呼び、状態を確かめる。単独の PR の作成・レビューや、PR の中身の解説（pr-tour）には使わない。
argument-hint: "<create | sync | status | merge> [<PR番号 | ブランチ名>] [--upto=<PR番号>] [--method=<merge|squash|rebase>]"
allowed-tools:
  - Read
  - Grep
  - Glob
  - Write
  - Edit
  - Bash(gh pr view:*)
  - Bash(gh pr list:*)
  - Bash(gh pr checks:*)
  - Bash(gh pr diff:*)
  - Bash(gh repo view:*)
  - Bash(gh auth status:*)
  - Bash(git status:*)
  - Bash(git diff:*)
  - Bash(git log:*)
  - Bash(git show:*)
  - Bash(git fetch:*)
  - Bash(git rev-parse:*)
  - Bash(git rev-list:*)
  - Bash(git merge-base:*)
  - Bash(git branch --show-current)
  - Bash(git for-each-ref:*)
  - Bash(git worktree list:*)
  - Bash(date:*)
  - ToolSearch
examples:
  - input: /stacked-pr create
    description: 現在のブランチ群から、1 PR = 1 ストーリーでスタック PR を下から順に作る（push と PR 作成は確認を経る）
  - input: /stacked-pr sync 101
    description: PR 101 を含むスタックを、main → 一番下 → … → 一番上の順に rebase で揃える
  - input: /stacked-pr status 103
    description: スタック全体の CI・mergeable・未解決スレッド・本文の位置表記を一覧にする
  - input: /stacked-pr merge 103
    description: 一番上の PR 103 に merge-async を呼び、下の PR も含めてまとめてマージする
  - input: /stacked-pr merge 103 --upto=102
    description: 102 から下だけをマージし、103 は open のまま残す
---

GitHub のスタック PR を作り、揃え、マージする作業を受け持つ。

以下、`$SKILL` はこのスキルのディレクトリ（`${CLAUDE_PLUGIN_ROOT}/skills/stacked-pr`。解決できない環境では、この SKILL.md を Read した場所）を指す。

`allowed-tools` で事前に許可しているのは、読み取り系の `gh` / `git` だけ。`git push`、`gh pr create` / `gh pr edit`、`gh api`（GET と PUT を区別できない）、`git rebase` / `git merge`、同梱スクリプトの実行は権限の確認を通る。push とマージは取り消しても通知と履歴が残るので、モデル側の確認とは別にハーネスの確認を残している。

## 用語

- **スタック**: PR の連なり。一番下の PR の base は trunk（通常 `main`）、それより上の PR の base は 1 つ下の PR の head ブランチ
- **下 / 上**: trunk に近い側が下。「上へ伝える」は下の変更を上のブランチへ順に取り込むこと
- **GitHub のスタック**: GitHub の Stacked PRs 機能（2026-07 public preview）で、スタックとして登録された PR。`gh stack submit` / `gh stack link` / `POST /repos/{o}/{r}/stacks` で登録される。base を繋げただけの PR は機能上のスタックとは限らない。PR の `stack` フィールド（`gh api repos/{o}/{r}/pulls/{n} --jq .stack`）が null でなければ登録済み

## 原則

1. **下から順に揃える**。下の PR を更新したら、その上を 1 段ずつ順に rebase（または merge）する。main を取り込むときも、一番下に取り込んでから上へ伝える。上の PR だけに `origin/main` を入れない（理由と事例は `references/maintain.md`）
2. **1 PR = 1 ストーリー**。関連する issue のまとまりを 1 PR にし、PR の境界をストーリーの境界に合わせる。1 issue ごとに細切れにしない
3. **マージは非同期マージ API で、上から指定する**。GitHub のスタックとして登録された PR は `gh pr merge` も同期の `PUT /pulls/{n}/merge` も拒否される。マージしたい範囲の一番上の PR に `merge-async` を呼ぶと、その下の PR もまとめてマージされる（`references/merge.md`）
4. **マージ前に全段を確かめる**。CI、mergeable、未解決のレビュースレッド、PR 本文の記述と今のコードの一致を、スタックの全 PR について見る。1 段でも欠けたらマージしない
5. **外に出る操作は確認してから**。push、PR の作成・本文の更新、force push、マージ、Linear の状態変更は、内容を示してユーザーの OK をもらってから実行する

## 状態を見る（status）

どの操作でも最初にスタックの形と各 PR の状態をつかむ。

```bash
bash "$SKILL/scripts/stack-status.sh" <スタック内のどれかの PR 番号 | ブランチ名>
```

base/head の繋がりを辿って一番下から一番上まで並べ、各 PR の base・head SHA・CI・mergeable・mergeStateStatus・未解決スレッド数・本文に書かれた位置表記と Linear ID を出す。GitHub のスタック登録があればその位置も出す。出力の見方はスクリプト冒頭のコメントにある。Linear ID の拾い漏れ・拾いすぎ（`UTF-8` など）を避けるには、チームキーを `LINEAR_KEY=TEC` のように渡す。

結果は表にしてユーザーに見せる。CONFLICTING / DIRTY の段があれば、その段と下の段の関係（どちらに何が入ったか）を `git log <下の head>..<上の head>` で確かめてから原因を説明する。

## 積む（create）

詳細は `references/create.md`。要点:

1. ストーリー単位に分ける。どの issue をどの PR に入れるかを表にして、ユーザーに確認する
2. ブランチ名は Linear の issue のブランチ名（Linear の「Copy git branch name」、`<user>/tec-123-<slug>`）をそのまま使ってよい。1 PR に複数 issue を含むときは代表の issue のものを使う
3. 一番下から順に作る。`gh pr create --base <1 つ下の head ブランチ> --head <このブランチ>`。一番下だけ `--base main`
4. PR 本文の先頭にスタックの位置ブロックを置く（書式は `references/create.md`）。`前: #101 / 次: #103`、全体の一覧、含む Linear issue ID（`TEC-123`）
5. 全段の PR ができたら、GitHub のスタックとして登録する（`gh stack link` または `POST /repos/{o}/{r}/stacks`）。登録すると非同期マージでまとめてマージでき、下がマージされたときに上の base が自動で付け替わる。登録しない場合はマージ手順が変わる（`references/merge.md` の「登録していないとき」）
6. 上の PR を作った後に下の PR 番号が確定するので、位置ブロックは全段を作り終えてから全 PR まとめて更新する

## 保つ（sync）

詳細は `references/maintain.md`。要点:

- 下の PR にコミットを足した・レビューで直した → その上を 1 段ずつ `git rebase <下の head>`（または `git merge`）し、各段を `git push --force-with-lease`（merge なら通常の push）
- main を取り込む → 一番下を `origin/main` に rebase し、上へ順に伝える。上の PR だけに main を入れない
- `gh stack` が入っていれば `gh stack rebase`（下から順のカスケード rebase）と `gh stack push` が同じことをする
- squash マージで下が先に入ったときは、上のブランチに下の古いコミットが残る。`git rebase --onto origin/main <下の古い head> <上>` で落とす
- 揃えた後に `stack-status.sh` をもう一度流し、全段が MERGEABLE で CI が走り出したことを確かめる

rebase と merge のどちらで伝えるかはリポジトリの慣習に合わせる。force push を避けたいリポジトリでは merge で伝える。どちらでも「下から順」は変わらない。

## マージ前の確認

`stack-status.sh` の結果に加えて、各 PR について次を確かめ、表で示す。

| 観点 | 見方 | マージしてよい状態 |
|---|---|---|
| CI | `gh pr checks <n>` | 全チェック成功（必須チェックが走っていない段があれば、衝突で pull_request の CI が起動していない可能性を疑う） |
| mergeable | `gh pr view <n> --json mergeable,mergeStateStatus` | `MERGEABLE` かつ `CLEAN`（または保護ルール上許される `UNSTABLE` / `HAS_HOOKS`） |
| レビュースレッド | スクリプトの未解決数（GraphQL `reviewThreads.isResolved`） | 0。残っていれば解決済みにするか、残す理由をユーザーと確認する |
| 本文と実装の一致 | PR 本文の「やったこと」「動作確認」と、その段の差分（`gh pr diff <n>`） | 本文に書いた変更が差分にあり、差分にある主な変更が本文にある。rebase やレビュー対応で後から変わった点が本文に反映されている |
| 位置表記 | 本文の位置ブロック | 前 / 次の PR 番号と全体の一覧が今のスタックと一致 |

食い違いがあれば直してから（本文の更新はユーザーに文面を見せてから）マージに進む。

## マージ（merge）

詳細は `references/merge.md`。要点:

1. 上の確認が全段で通っていることを確かめ、`stack-status.sh` の `linear` 列（含まれる Linear issue ID）を控えておく。マージ後は open でなくなるのでスクリプトに出ない
2. マージする範囲を決める。全部なら一番上の PR、途中までならそこで止めたい PR（`--upto`）を対象にする
3. 対象 PR の head SHA を取り、`merge-async` を呼ぶ。`merge_method` は `--method` の指定、無ければリポジトリの慣習（保護ルールで許された方法）に合わせる。呼ぶ前にコマンドと範囲（「#101〜#103 がまとめてマージされる」）をユーザーに示して OK をもらう

   ```bash
   gh api -X PUT "repos/{owner}/{repo}/pulls/<n>/merge-async" \
     -H "X-GitHub-Api-Version: 2026-03-10" \
     -f merge_method=merge -f sha=<head の SHA>
   ```

4. 返ってきた `details.uuid` で状態を確かめる。`pending` の間は間隔を空けて繰り返し、`merged` / `enqueued` / `failed` で止める

   ```bash
   gh api "repos/{owner}/{repo}/pulls/<n>/merge-async/<uuid>" -H "X-GitHub-Api-Version: 2026-03-10"
   ```

5. 終わったら `stack-status.sh` で各 PR が MERGED になったこと（途中までなら残りの PR の base が trunk に付け替わったこと）を確かめる
6. Linear の issue の状態を確かめる（次節）

## Linear 連携

詳細は `references/linear.md`。要点:

- PR 本文（またはブランチ名・タイトル）に `TEC-123` を書くと Linear の issue に PR が紐づく
- base が main でない PR は、マージしても issue が自動で Done にならないことがある（実際に、base が main でない PR に紐づいた issue が Done にならず、手で Done にした）
- マージ後に、スタックに含まれる全 issue ID の状態を確かめ、Done になっていないものを一覧にしてユーザーに示す。Linear の操作ができる環境なら、OK をもらってから Done にする。できない環境なら一覧を渡して手で Done にしてもらう

## gh とサンドボックス

サンドボックスの中で `gh` を呼ぶと、TLS のエラー（`x509: certificate signed by unknown authority`、`tls: failed to verify certificate` など）で失敗することがある。認証や API の問題ではないので、同じコマンドをサンドボックスの外で再実行する（Claude Code ならサンドボックス無効での再実行。権限の確認を通る）。`git fetch` / `git push` でも同様に失敗することがある。再実行しても失敗するなら `gh auth status` を確かめる。

## 終わり方

各操作の最後に、やったこと・確かめたこと（status の表）・残っていること（未解決スレッド、Done にしていない issue、手で確かめるべき点）を短くまとめて止まる。
