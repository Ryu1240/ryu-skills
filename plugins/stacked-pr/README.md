# スタック PR（`/stacked-pr`）

GitHub のスタック PR（下の PR の head ブランチを上の PR の base にして積む PR の連なり）を、作る・保つ・マージするためのスキルです。実際に詰まった事例（上の PR だけに main を入れて衝突し CI が止まった、`gh pr merge` が「part of a stack」で拒否された、上の段の Linear issue が Done にならなかった）を手順に織り込んでいます。

## 何をするか

| 操作 | やること |
|---|---|
| status | base/head を辿ってスタックを下から並べ、各 PR の CI・mergeable・mergeStateStatus・未解決スレッド数・本文の位置表記・Linear ID を一覧にする |
| create | 1 PR = 1 ストーリー（関連 issue のまとまり）に分け、下から順に `--base` を指定して PR を作る。本文の先頭に位置ブロック（`スタック 2/3　前: #101 ／ 次: #103`、Linear ID）を置き、GitHub のスタックとして登録する |
| sync | 下の PR の更新や main の取り込みを、一番下から上へ 1 段ずつ rebase（または merge）で伝える。上の PR だけに main を入れない |
| merge | 全段の CI・mergeable・未解決スレッド・本文と実装の一致を確かめてから、一番上（または止めたい位置）の PR に非同期マージ API（`merge-async`）を呼び、状態を追う。終わったら Linear の issue が Done になったかを確かめる |

- push、PR の作成・本文の更新、force push、マージ、Linear の状態変更は、内容を示して OK をもらってから行います
- `gh stack` 拡張（`gh extension install github/gh-stack`）があればそれも使えますが、無くても `git` と `gh api` だけで進められます

## 使い方

```text
/stacked-pr status 102
/stacked-pr create
/stacked-pr sync 101
/stacked-pr merge 103                 # 103 から下をまとめてマージ
/stacked-pr merge 103 --upto=102      # 102 から下だけマージし、103 は残す
```

同名のスキルが他にある環境では `/stacked-pr:stacked-pr` と名前空間付きで呼んでください。「この PR たちを積みたい」「下の PR を直したので上に伝えて」「スタックをまとめてマージして」のように頼むだけでも起動します。

## 押さえておくこと

- **main は下から入れる。** 上の PR だけに `origin/main` をマージすると、その base（下の PR のブランチ）との間で衝突（`CONFLICTING` / `DIRTY`）になり、`pull_request` の CI が走らなくなります
- **スタックのマージは merge-async で。** GitHub のスタックとして登録された PR は、`gh pr merge` も `PUT /pulls/{n}/merge` も拒否されます。`PUT /repos/{o}/{r}/pulls/{n}/merge-async`（`-f merge_method=merge -f sha=<head SHA>`、`X-GitHub-Api-Version: 2026-03-10`）を一番上の PR に呼ぶと、下の PR も含めて全か無かでマージされます。途中の PR に呼べば、そこから下だけがマージされ、上の PR は open のまま base が trunk に付け替わります
- **Linear の Done は確かめる。** base が main でない PR は、マージしても issue が自動で Done にならないことがあります
- **サンドボックスの中の gh は TLS エラーになることがある。** そのときはサンドボックスの外で再実行します

## 前提

| 依存 | 用途 |
|---|---|
| `git` | 必須 |
| `gh`（認証済み）・`jq` | 必須。PR の作成・状態の取得・merge-async の呼び出し |
| `python3` | `stack-status.sh` の本文照合 |
| GitHub の Stacked PRs 機能 | まとめてマージ・base の自動付け替えに必要（2026-07 から public preview）。使えないリポジトリでは、下から 1 段ずつ `gh pr merge` → base の付け替えで進める |
| Linear の MCP | 任意。あれば issue の状態確認と Done への変更（OK をもらってから）に使う |

## 構成

```
stacked-pr/
├── .claude-plugin/plugin.json
├── skills/stacked-pr/
│   ├── SKILL.md                   … 原則と、status / create / sync / マージ前の確認 / merge / Linear の要点
│   ├── references/
│   │   ├── create.md              … ストーリーの分け方、ブランチ名、--base、位置ブロックの書式、スタック登録
│   │   ├── maintain.md            … 下から順に伝える手順、main の取り込み、詰まった事例、gh stack
│   │   ├── merge.md               … merge-async の呼び方と状態、途中までのマージ、登録していないとき
│   │   └── linear.md              … issue の紐づけ、Done にならないときの対処
│   └── scripts/
│       └── stack-status.sh        … スタックを下から並べて各 PR の状態を一覧にする
├── README.md
└── LICENSE
```

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install stacked-pr@general-skills
```

## ライセンス

MIT
