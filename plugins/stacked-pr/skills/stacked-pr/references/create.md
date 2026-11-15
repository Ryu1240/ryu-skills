# スタックを積む

> 1 PR = 1 ストーリー。下から順に作り、全段ができてから位置ブロックをまとめて書き、GitHub のスタックとして登録する。

## 1. ストーリーに分ける

1 PR に入れるのは、まとめてレビューすると意味が通る関連 issue のまとまり（ストーリー）。目安:

- 1 PR を読めば「何ができるようになったか」が 1 文で言える
- 下の PR だけをマージしても main が壊れない（上の PR が無くてもビルド・テストが通る）
- issue 1 つで 1 PR にすると、PR が細かすぎてスタックが長くなり、保つ手間（rebase の段数）が増える

分け方は表にしてユーザーに確認する。

| 段 | ストーリー | Linear issue | ブランチ |
|---|---|---|---|
| 1（下） | 返金 API の土台（モデルと保存） | TEC-121, TEC-122 | `alice/tec-121-refund-model` |
| 2 | 返金 API のエンドポイント | TEC-123 | `alice/tec-123-refund-endpoint` |
| 3（上） | 管理画面からの返金操作 | TEC-124, TEC-125 | `alice/tec-124-refund-admin-ui` |

## 2. ブランチ名

Linear の issue の「Copy git branch name」で得られる名前（`<user>/tec-123-<slug>`）をそのまま使ってよい。Linear はブランチ名に含まれる issue ID でも PR を紐づけるので、本文に ID を書き忘れたときの保険にもなる。1 PR に複数 issue を含むときは代表（一番中心の issue）のブランチ名を使い、残りの ID は本文に書く。

既存のブランチから積むときは、各ブランチが 1 つ下のブランチの先端を含んでいることを確かめる。

```bash
git merge-base --is-ancestor <下のブランチ> <上のブランチ> && echo ok
```

含んでいなければ、先に `git rebase <下のブランチ> <上のブランチ>` で積み直す（ユーザーに確認してから）。

## 3. 下から順に PR を作る

push と PR 作成はユーザーに一覧を見せて OK をもらってからまとめて行う。

```bash
git push -u origin alice/tec-121-refund-model
gh pr create --base main --head alice/tec-121-refund-model --title "..." --body-file <本文>

git push -u origin alice/tec-123-refund-endpoint
gh pr create --base alice/tec-121-refund-model --head alice/tec-123-refund-endpoint --title "..." --body-file <本文>
```

- 一番下の base だけが trunk（`main`）。それより上は 1 つ下の head ブランチ
- base を間違えると差分に下の PR の変更が混ざる。作った直後に `gh pr view <n> --json baseRefName,headRefName` と `gh pr diff <n> --name-only` で確かめる
- リポジトリの慣習が draft 始まりなら `--draft` を付ける

## 4. 本文の位置ブロック

本文の先頭に置く。リポジトリに PR テンプレートがあれば、テンプレートの先頭に差し込む。

```markdown
> **スタック 2/3**　前: #101 ／ 次: #103
>
> 1. #101 返金 API の土台（モデルと保存）
> 2. **#102 返金 API のエンドポイント** ← この PR
> 3. #103 管理画面からの返金操作
>
> Linear: TEC-123
```

- 一番下は `前: なし（base: main）`、一番上は `次: なし`
- Linear の ID はこの PR が受け持つ issue だけを書く（スタック全体の ID を全 PR に書くと、どの PR がどの issue を閉じるのかがぼやける）
- 上の PR を作るまで次の番号は決まらないので、全段を作り終えてから全 PR の位置ブロックをまとめて書き直す（`gh pr edit <n> --body-file <本文>`）

`stack-status.sh` は本文から `スタック i/n`・`前: #`・`次: #`・`TEC-\d+` を拾って、実際の並びと照らし合わせる。書式を変えるときはスクリプトの正規表現も合わせる。

## 5. GitHub のスタックとして登録する

base を繋いだだけでは GitHub の Stacked PRs 機能のスタックにはならない（登録は明示的に行う）。登録すると:

- 非同期マージ API でまとめて（または途中まで）マージできる
- 下がマージされると、上の PR の base が自動で trunk に付け替わり、ブランチも rebase される
- 下の PR の base に向けた CI ではなく、trunk に向けた pull_request の CI が全段で走る

登録の方法（どれか 1 つ）:

```bash
# gh stack 拡張（gh extension install github/gh-stack）
gh stack link --base main 101 102 103

# REST。pull_requests は下から上の順。各 PR の base は 1 つ前の PR の head と一致している必要がある
gh api -X POST "repos/{owner}/{repo}/stacks" -H "X-GitHub-Api-Version: 2026-03-10" \
  -F 'pull_requests[]=101' -F 'pull_requests[]=102' -F 'pull_requests[]=103'
```

既存のスタックの上に足すときは `POST /repos/{o}/{r}/stacks/{stack_number}/add`（または `gh stack link <stack_number> <pr>`）。外すときは `POST .../unstack`（または `gh stack unstack`）。

`gh stack` で最初から作る場合は `gh stack init` → `gh stack add` → `gh stack submit` が、ブランチ作成・push・PR 作成・登録をまとめて行う。既定では PR が draft で作られる（`--open` で ready）。

登録は外に出る操作なので、ユーザーの OK をもらってから行う。リポジトリで機能が有効でない（preview に参加していない）と 404 / 422 になる。そのときは登録せずに進め、マージ手順は `merge.md` の「登録していないとき」に従う。
