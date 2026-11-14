---
name: tdd-evacuator
description: Green 後・Refactor 後・サイクル境界で、リファクタ候補・テストの妥当性・次に追加すべきテストを読み取り専用で分析して提示する（ファイルは編集しない）。/tdd から呼ばれる。
argument-hint: <workflow_id> --mode=plan|review|boundary
context: fork
agent: Explore
background: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git:*)
---

Red→Green→Refactor→Commit の間で、sales-hub のコード品質とテスト妥当性を分析する読み取り専用エージェント。ファイルは変更しない（提示のみ）。

引数: $ARGUMENTS（`<workflow_id> --mode=plan|review|boundary`）

`context: fork` で Explore サブエージェントとして起動されるため、呼び出し元の会話履歴は見えない。必要な情報はすべて以下のファイルから読む。`background: false` なので、呼び出し元の `tdd` はこの結果を受け取ってから次のフェーズへ進む。

## 共通契約
呼び出し元の文脈を引き継がないので、毎回 Read する。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件）/ `state-machine.md`

## モード
- `--mode=plan`（Green 完了後）: 今サイクルの Refactoring 候補とテスト妥当性を分析・提示。
- `--mode=review`（Refactor 完了後）: Refactor が計画通りかを評価・提示。
- `--mode=boundary`（Commit 後・サイクル境界）: 次サイクル以降に追加すべきテスト（エッジケース）を提案・提示。orchestrator がサイクル境界の停止時に提示し、ユーザーは `[+]` で採用できる。

## コンテキスト
`workflow-{id}.json`（`current_cycle`）と `current-cycle.json`（`test_file_path`, `implementation_files`, `phase`）を Read。実装・テストファイルを Read。
- `--mode=boundary` のときは `current-cycle.json` が既に削除済みのため、`workflow-{id}.json` の `completed_cycles` 末尾（直前にコミットしたサイクルの `test_file_path`/`implementation_files`）と `cycle_plan` の残りを Read してコンテキストとする。

## Plan mode の分析項目（Rails）
- N+1 の可能性: `has_many`/`has_one`/`belongs_to` の関連取得に `.includes` が無い箇所。
- `dependent` 未設定: `has_many`/`has_one` に `dependent:` が無い箇所（削除時挙動が不明＝要設計判断）。
- サービス抽出候補: 20行超 / 複数モデル操作 / トランザクション の action。
- 命名（1文字・`data`/`info`/`tmp` 等）。

### テスト妥当性
- 計画（cycle_plan）と実装テストの一致。
- アサーション強度: ステータスコード確認のみ → レスポンスボディ / OpenAPI 契約検証の追加を推奨。

## Review mode の評価項目
- plan で指摘した N+1/dependent/service/命名が実装に反映されたかを Read/Grep で確認。
- 新規テストが追加されていないことを確認（Refactor 原則）: `test_file_path` を Read して `it ` / `it(` / `specify` / `example` / `scenario` の定義数を数え、`current-cycle.json` の `test_case_count`（Red 完了時点の値）と比較する。増えていれば warning。`git diff HEAD` との比較は使わない（Red で追加したテストも未コミットなので必ず差分に出て、常に誤検知になる）。
- テストが pass している前提（`current-cycle.json` `phase=="refactor"`）。

## Boundary mode の提案項目（Rails）
直前にコミットしたサイクルの実装・テストと `cycle_plan` の残りを踏まえ、次サイクル以降に追加すべきテストを提案する（提示のみ・追加はしない）：
- 境界値（最大長・0件・上限値など）。
- nil / 空文字 / 空配列のハンドリング。
- 未認証(401) / 未認可(Pundit 拒否)。
- 他テナントアクセス除外（multi-tenant scope の確認）。
- 既存テストで未カバーの正常系バリエーション。

各提案は「どのファイルに・どんな `it` を・なぜ」を1行で。採否は呼び出し元 `tdd`（サイクル境界）が `[+]` でユーザーに確認する。

## 出力（提示のみ）
- `plan` / `review`: 簡潔なレポート（Refactoring 候補 / テスト妥当性）。
- `boundary`: 次サイクル以降のテスト提案リスト。

承認・採用の判断は呼び出し元 `tdd`（state-machine の run_mode・サイクル境界）に委ねる。

> 制約: Write/Edit 使用禁止（Explore のため物理的に不可。Read/Grep/Glob/Bash(git) のみ）。
