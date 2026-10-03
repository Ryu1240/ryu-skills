# PR ツアーガイド（`/pr-tour`）

> [!WARNING]
> **公式マーケットプレースの `code-review` プラグインと併用するときは注意してください。**
>
> このスキルは、レビュー結果を**手元に返す** `code-review` スキル（effort レベル `low` / `medium` / `high` … と `--comment` / `--fix` を受け取るもの）をバックグラウンドで併走させる前提で書かれています。
> 公式マーケットプレース（`claude-plugins-official`）には **同じ名前の別物** の `code-review` プラグインがあり、そちらは PR を受け取ると **`gh pr comment` で GitHub にレビューコメントを投稿します**。ツアー中にそちらが起動すると、**解説のつもりで PR に公開コメントが付きます**（削除しても通知は残ります）。
>
> スキル側では、利用可能な `code-review` の説明文を見て effort 付きのものだと判別できない限り起動しない（レビュー併走を省いてツアーを続ける）ようにしてあります。それでも、公式の `code-review` プラグインを入れている環境では、ツアーを始める前に次のどちらかをおすすめします。
>
> - ツアーを行うリポジトリでは公式 `code-review` プラグインを無効化する（`/plugin` から、または `.claude/settings.json` の `enabledPlugins`）
> - `--no-review` を付けて起動する

PR の差分を **「処理の流れ」に沿って、エントリーポイントから順に** 案内するスキルです。差分ファイルを上から読むのではなく、差分の外にある起点（ルーティング・画面・cron・ジョブの起動元）を探し、起点から差分を貫く「案内プラン」を作ってから、1 ターン 1 ステップで解説します。

## 何をするか

| Phase | やること |
|---|---|
| 0. 対象の解決 | PR / ブランチ / 別リポジトリを判別し、base と head を確定。既存プランがあれば再開を提案 |
| 1. 全体把握 | base・head を専用 ref に fetch し、変更ファイルをレイヤー別に一覧。ツアーが成立するかを判断し、code-review をバックグラウンドで起動 |
| 2. 読み取り環境 | 作業ツリーが head と SHA で一致しなければ、読み取り専用の worktree を作る（checkout・stash はしない） |
| 3. 起点の探索 | リポジトリの文書から起点カタログを組み立て、変更シンボルの呼び出し元を起点まで辿る |
| 3.5 テスト対応 | 追加・変更されたテストがどの変更を固定しているかを対応付け、依存が軽ければ scratchpad で実行して実測を添える |
| 4. プラン | Markdown のプラン（正）と HTML の視覚ビュー（俯瞰）を保存・公開し、承認を待つ |
| 5. ステップ実行 | 1 ターン 1 ステップ。見る場所 → ここは何をしている場所か → 変更点 → なぜこの変更か → 対応するテスト → レビューの指摘 → 次へのつながり。図解を Artifact に追記し、選択肢を出して止まる |
| 完了 | 流れの振り返り、テストの有無、レビュー指摘の確定／仮説／撤回、未確認事項。worktree と ref を片付ける |
| 6. 任意 | 質問ログを材料に、本人の文体でレビューコメントの下書きを作り Pending review として置く（公開は明示的な OK の後だけ） |

- **プランはファイルに残す**（既定は `.claude/pr-tour/`。`.git/info/exclude` で追跡外にする）。文脈が要約されても、別セッションからでも、プランを読めば位置を復元できます
- **文章はチャット、図解は Artifact**。視覚ビューはルートごとの縦ステッパーで、各ステップに到達した時点で手書き SVG の図（シーケンス／流れ図）を追記します
- **差分の外から差分へ到達できるか**（直接呼び出し／フレームワークの規約による結線）を file:line の根拠付きで確かめ、存在しない経路を捏造して線を繋ぐことはしません

## 使い方

```text
/pr-tour 123
/pr-tour https://github.com/<owner>/<repo>/pull/123 -- 返金処理の失敗時の扱いを重点的に
/pr-tour feat/cancel-order
/pr-tour 123 --no-review
/pr-tour 123 --review-level=high
/pr-tour                       # 現在のブランチの PR。進行中のプランがあれば再開
```

同名のスキルが他にある環境では `/pr-tour:pr-tour` と名前空間付きで呼んでください。「この PR を解説して」「PR #123 の中身を理解したい」「walk me through this PR」のように頼むだけでも起動します。

## 前提と縮退

| 依存 | 無いときの挙動 |
|---|---|
| `git` | 必須 |
| `gh`（認証済み）・`jq` | PR 番号・URL の解決に使う。無い／GitHub 以外なら、ブランチ差分と `git log` のコミットメッセージで代える |
| `python3` | プランと視覚ビューの同時更新・図解の生成に使う |
| Artifact ツール | 無ければ視覚ビューをローカルの HTML として保存し、ブラウザで開いてもらう |
| effort 付きの `code-review` スキル | 無い／別物と判断したら **レビュー併走を省いてツアーを続ける**。プランに「併走なし（理由）」と明記する |
| 対象リポジトリのクローン | 無ければ `gh api` で読む。worktree とテスト実行は使えず、プランはスクラッチパッドに置く |

ツアー自身はレビュー（良し悪しの判定）をしません。`code-review` の指摘は出典付きで該当ステップに添えるだけで、PR へのコメント投稿は Phase 6 でユーザーの承認を経たときだけ行います。

## 構成

```
pr-tour/
├── .claude-plugin/plugin.json
├── skills/pr-tour/
│   ├── SKILL.md                         … 進め方（原則、Phase 0〜5、質問、再開、完了）
│   ├── references/
│   │   ├── entry-points.md              … 起点カタログの作り方と、差分から外側へ辿るレシピ
│   │   ├── plan-template.md             … プランファイルの書式
│   │   ├── adversarial-review.md        … code-review の見分け・並走・指摘の配り方
│   │   ├── verification.md              … テストを scratchpad で実行する手順
│   │   ├── output-paths.md              … 保存先と追跡外の保証
│   │   └── review-handoff.md            … レビューコメント下書き・Pending review
│   ├── assets/plan-view.html            … 視覚ビューのテンプレート
│   └── scripts/
│       ├── pr-context.sh                … base/head の fetch、変更ファイルのレイヤー分類、既存プランの検出
│       ├── plan-step.py                 … ステップ進行を Markdown と HTML に同時反映
│       └── fig.py                       … 図解用 SVG ヘルパーと整形式チェック
├── README.md
└── LICENSE
```

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install pr-tour@general-skills
```

## ライセンス

MIT
