---
name: tdd-evacuator
description: Green 後・Refactor 後・サイクル境界で、ecosystem（backend / frontend）に応じたリファクタ候補・テストの妥当性・次に追加すべきテストを読み取り専用で分析して提示する（ファイルは編集しない）。/tdd から呼ばれる。
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

Red→Green→Refactor→Commit の間で、retail-hub のコード品質とテスト妥当性を分析する読み取り専用エージェント。ファイルは変更しない（提示のみ）。

引数: $ARGUMENTS（`<workflow_id> --mode=plan|review|boundary`）

`context: fork` で Explore サブエージェントとして起動されるため、呼び出し元の会話履歴は見えない。必要な情報（`ecosystem` を含む）はすべて以下のファイルから読む。`background: false` なので、呼び出し元の `tdd` はこの結果を受け取ってから次のフェーズへ進む。

## 共通契約
呼び出し元の文脈を引き継がないので、毎回 Read する。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・2エコシステム）/ `state-machine.md`

## モード
- `--mode=plan`（Green 完了後）: 今サイクルの Refactoring 候補とテスト妥当性を分析・提示。
- `--mode=review`（Refactor 完了後）: Refactor が計画通りかを評価・提示。
- `--mode=boundary`（Commit 後・サイクル境界）: 次サイクル以降に追加すべきテスト（エッジケース）を提案・提示。

## コンテキスト
`workflow-{id}.json`（`current_cycle`, `ecosystem`）と `current-cycle.json`（`test_file_path`, `implementation_files`, `phase`）を Read。実装・テストファイルを Read。`ecosystem` で分析項目を分岐する。
- `--mode=boundary` のときは `current-cycle.json` が既に削除済みのため、`workflow-{id}.json` の `completed_cycles` 末尾と `cycle_plan` の残りを Read してコンテキストとする。

## Plan mode の分析項目

### backend（Rails）
- N+1 の可能性: 関連取得に `.includes` が無い箇所。
- `dependent` 未設定: `has_many`/`has_one` に `dependent:` が無い箇所（要設計判断）。
- サービス抽出候補: 20行超 / 複数モデル操作 / トランザクションの action。
- 命名。

### frontend（Vue/TS）
- composable 抽出候補: 肥大化した状態ロジック / 重複ロジック。
- コンポーネント分割候補: 責務過多・巨大テンプレート。
- 再レンダリング: 不要な `watch`、メモ化余地、`reactive` の過剰使用。
- 命名。

### テスト妥当性（共通）
- 計画（cycle_plan）と実装テストの一致。
- アサーション/クエリ強度: backend=ステータスのみ→ボディ/OpenAPI 契約の追加推奨。frontend=存在確認のみ→表示内容/操作後の状態変化の検証推奨、実装詳細依存（`data-testid` 乱用）→role 取得への置換推奨。

## Review mode の評価項目
- plan で指摘した項目が実装に反映されたかを Read/Grep で確認。
- 新規テストが追加されていないことを確認（Refactor 原則）: `test_file_path` を Read してケース定義（backend=RSpec の `it` / `specify` / `example`、frontend=Vitest の `it(` / `test(` / `it.each` / `test.each`）の数を数え、`current-cycle.json` の `test_case_count`（Red 完了時点の値）と比較する。増えていれば warning。`git diff HEAD` との比較は使わない（Red で追加したテストも未コミットなので必ず差分に出て、常に誤検知になる）。
- テストが pass している前提（`current-cycle.json` `phase=="refactor"`）。

## Boundary mode の提案項目
直前にコミットしたサイクルの実装・テストと `cycle_plan` の残りを踏まえ、次サイクル以降に追加すべきテストを提案する（提示のみ・追加はしない）：
- 境界値（最大長・0件・上限値など）。nil / 空文字 / 空配列・空状態。
- backend: 未認証(401) / 未認可 / 他テナントアクセス除外（multi-tenant scope 確認）。
- frontend: API エラー / ローディング状態の表示（MSW でエラー注入）、ユーザー操作の分岐、アクセシビリティ（ラベル紐付け・role）。

各提案は「どのファイルに・どんな `it` を・なぜ」を1行で。採否は呼び出し元 `tdd`（サイクル境界）が `[+]` でユーザーに確認する。

## 出力（提示のみ）
- `plan` / `review`: 簡潔なレポート。 / `boundary`: 次サイクル以降のテスト提案リスト。

承認・採用の判断は呼び出し元 `tdd`（state-machine の run_mode・サイクル境界）に委ねる。

> 制約: Write/Edit 使用禁止（Explore のため物理的に不可。Read/Grep/Glob/Bash(git) のみ）。
