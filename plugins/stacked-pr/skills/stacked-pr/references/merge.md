# スタックをマージする

> GitHub のスタックとして登録された PR は非同期マージ API（merge-async）でしかマージできない。マージしたい範囲の一番上の PR に呼ぶと、その下の PR もまとめてマージされる。

## 同期のマージが拒否される

登録済みのスタックに含まれる PR に対して、次はどれも拒否される。

- `gh pr merge <n>`
- `PUT /repos/{o}/{r}/pulls/{n}/merge`
- GraphQL の `mergePullRequest`

エラーは「This pull request is part of a stack and must be merged using the asynchronous merge REST API」のように、part of a stack / asynchronous merge を案内する文面になる。これを見たら merge-async に切り替える。

## merge-async で全段をマージする

1. 一番上の PR の番号と head SHA を確かめる

   ```bash
   gh pr view <一番上> --json number,headRefOid,state,isDraft
   ```

   draft の段があるとマージできない（400）。先に `gh pr ready <n>` で ready にする（ユーザーに確認してから）。

2. マージを依頼する（ユーザーに範囲を示して OK をもらってから）

   ```bash
   gh api -X PUT "repos/{owner}/{repo}/pulls/<一番上>/merge-async" \
     -H "X-GitHub-Api-Version: 2026-03-10" \
     -f merge_method=merge -f sha=<一番上の head SHA>
   ```

   | パラメータ | 意味 |
   |---|---|
   | `sha` | 依頼時点の head SHA。省略すると現在の head が使われるが、確認した後に push が入っていないことを保証するため必ず渡す |
   | `merge_method` | `merge` / `squash` / `rebase`。リポジトリの慣習と保護ルールに合わせる |
   | `merge_action` | `default`（マージキューがあればキュー、無ければ直接）/ `direct_merge` / `merge_queue`。通常は省略 |
   | `commit_title` / `commit_message` | 直接マージのときのコミットメッセージ |
   | `bypass_rules` | 保護ルールを迂回する。使わない（ユーザーが明示したときだけ） |

   応答の HTTP ステータス:

   | ステータス | 意味 |
   |---|---|
   | 202 | 受け付けた。バックグラウンドで実行される |
   | 200 | 既にマージ済み、またはキューに入っている |
   | 400 | マージできる状態でない（closed、draft など） |
   | 409 | 同じ PR に対するマージ依頼が既に進行中 |
   | 422 | 検証エラー（SHA の不一致など） |

   応答本文の `status` と `details.uuid` を控える。

3. 状態を確かめる

   ```bash
   gh api "repos/{owner}/{repo}/pulls/<一番上>/merge-async/<uuid>" \
     -H "X-GitHub-Api-Version: 2026-03-10" --jq '{status, message: .details.message, sha: .details.sha}'
   ```

   | `status` | 意味 | 次にすること |
   |---|---|---|
   | `pending` | 実行中 | 10〜30 秒あけてもう一度 |
   | `merged` | マージされた | 各 PR の状態を確かめる |
   | `enqueued` | マージキューに入った | キューの結果を `gh pr view <n> --json state` で追う |
   | `failed` | 失敗 | `details.message` を読む。どの PR もマージされていない（スタックのマージは全か無か） |

   uuid は 24 時間で失効する（404）。失効した後は `gh pr view` で状態を見る。

4. スタックの全段が `MERGED` になったことを `stack-status.sh` または `gh pr view <n> --json state,mergedAt` で確かめる

## 途中までマージする

GitHub の公式ドキュメントで確認した仕様（2026-11 時点）:

- 途中の PR を対象に merge-async を呼ぶと、その PR と、それより下の全 PR がマージされる。それより上の PR は open のまま残り、base が自動で trunk に付け替わる
- 途中の 1 PR だけを単独でマージすることはできない。マージは常に下から
- `gh stack merge <PR番号>` も同じく「その PR まで」をマージする

手順:

1. 止めたい位置の PR（例: 3 段中の 2 段目 #102）を決める。マージ前の確認はその PR から下の段について行う
2. #102 の head SHA で merge-async を呼ぶ（上と同じコマンド。対象を #102 にする）
3. 状態が `merged` になったら、残った #103 の base が `main` に付け替わったことを確かめる

   ```bash
   gh pr view 103 --json baseRefName,mergeable,mergeStateStatus
   ```

4. 手元を揃える。`gh stack sync --prune`、または `git fetch` して残りのブランチを `origin/main` に rebase する（GitHub 側で rebase 済みなら手元を `git reset --hard origin/<ブランチ>` で合わせる。どちらにするかは手元に未 push のコミットが無いことを確かめてから）
5. #103 の本文の位置ブロックを更新する（`スタック 1/1`、前: なし（base: main））

未確認: 途中までマージした後、残った上の PR のブランチを GitHub がどの方法で付け替えるか（rebase して force push するのか、base の付け替えだけか）は、ドキュメントに「自動で base を付け替える」「残りのブランチは自動で rebase される」とあるが、squash マージとの組み合わせでどうなるかは実地で確かめていない。終わった後に `gh pr diff <残った PR> --name-only` で、下の変更が混ざっていないかを確かめる。

## 登録していないとき（base を繋いだだけのスタック）

GitHub のスタックとして登録していなければ、同期のマージ（`gh pr merge`）が使える。ただしまとめてはマージされないので、下から 1 段ずつ行う。

1. 一番下を `gh pr merge <n> --merge`。ブランチは上の付け替えが済むまで消さない（GitHub はマージ済みの head ブランチが消されたとき、それを base にしている PR を付け替えるが、消し方や順序によっては上の PR が閉じられるので頼らない）
2. 2 段目の base を `main` に付け替える: `gh pr edit <n> --base main`
3. squash / rebase マージだった場合は、2 段目に下の古いコミットが残るので `git rebase --onto origin/main <下の head> <2 段目>` して force push
4. CI が通るのを待って 2 段目をマージ。以下同様

## マージ後

- 各段の PR が `MERGED` になったこと
- Linear の issue の状態（`linear.md`）
- マージ済みのブランチの削除（リポジトリ設定で自動削除されていなければ、ユーザーに確認してから）
