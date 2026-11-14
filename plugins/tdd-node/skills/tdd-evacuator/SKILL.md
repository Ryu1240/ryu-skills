---
name: tdd-evacuator
description: Green 後・Refactor 後・サイクル境界で、リファクタ候補・テストの妥当性・次に追加すべきテストを読み取り専用で分析して提示する（ファイルは編集しない）。/tdd から呼ばれる。
argument-hint: <workflow_id> --mode=plan|review|boundary
context: fork
agent: Explore
model: opus
background: false
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git:*)
---

Red→Green→Refactor→Commit の間で、order-api のコード品質とテスト妥当性を分析する読み取り専用エージェント。ファイルは変更しない（提示のみ）。

引数: $ARGUMENTS（`<workflow_id> --mode=plan|review|boundary`）

`context: fork` で Explore サブエージェントとして起動されるため、呼び出し元の会話履歴は見えない。必要な情報はすべて以下のファイルから読む。`background: false` なので、呼び出し元の `tdd` はこの結果を受け取ってから次のフェーズへ進む。

## 共通契約
呼び出し元の文脈を引き継がないので、毎回 Read する。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・レイヤー構成）/ `state-machine.md`

## モード
- `--mode=plan`（Green 完了後）: 今サイクルの Refactoring 候補とテスト妥当性を分析・提示。
- `--mode=review`（Refactor 完了後）: Refactor が計画通りかを評価・提示。
- `--mode=boundary`（Commit 後・サイクル境界）: 次サイクル以降に追加すべきテスト（エッジケース）を提案・提示。

## コンテキスト
`workflow-{id}.json`（`current_cycle`, `patterns`）と `current-cycle.json`（`test_file_path`, `implementation_files`, `phase`）を Read。実装・テストファイルを Read。
- `--mode=boundary` のときは `current-cycle.json` が既に削除済みのため、`workflow-{id}.json` の `completed_cycles` 末尾と `cycle_plan` の残りを Read してコンテキストとする。

## Plan mode の分析項目（Node/TS バックエンド）
- レイヤー逆流: service が `req`/`res` を持つ、route にロジック、repository 外の ORM 呼び出し。
- N+1 クエリ: ループ内の `await repo.*` / ORM 呼び出し。
- 非同期の落とし穴: `await` 漏れ（浮いた Promise）、`forEach` 内の `async`、直列 `await` の並列化余地。
- エラー処理: 握り潰し（空 `catch`）、業務エラーの型が無く文字列判定している箇所、内部情報の露出。
- 型の健全性: 今サイクルで増えた `any` / `as` / `@ts-expect-error`、Zod スキーマと手書き型の重複。
- 命名・責務過多。

### テスト妥当性
- 計画（`cycle_plan`）と実装テストの一致。
- 独立性の担保: DB を使うテストにトランザクションロールバックがあるか、`vi.restoreAllMocks()` / `server.resetHandlers()` が置かれているか、fake timers を戻しているか。
- モックの粒度: `vi.mock` でモジュール丸ごと差し替えている箇所は、DI に置き換えられないか（不変条件#4）。過剰モックは実装変更に脆いテストを生む。
- アサーション強度: ステータスコードだけ見て body を検証していない、`toBeDefined()` 止まり。

## Review mode の評価項目
- plan で指摘したレイヤー/N+1/非同期/エラー/型が実装に反映されたかを Read/Grep で確認。
- 新規テストが追加されていないことを確認（Refactor 原則）: `test_file_path` を Read してケース定義（`it(` / `test(` / `it.each` / `test.each`）の数を数え、`current-cycle.json` の `test_case_count`（Red 完了時点の値）と比較する。増えていれば warning。`git diff HEAD` との比較は使わない（Red で追加したテストも未コミットなので必ず差分に出て、常に誤検知になる）。
- 振る舞いが変わっていないこと: `git diff` で条件分岐・ステータスコード・エラー種別の変化がないか確認。
- テストが pass している前提（`current-cycle.json` `phase=="refactor"`）。

## Boundary mode の提案項目（Node/TS バックエンド）
直前にコミットしたサイクルの実装・テストと `cycle_plan` の残りを踏まえ、次サイクル以降に追加すべきテストを提案する（提示のみ・追加はしない）：
- バリデーション境界: Zod スキーマの必須/任意、最小最大、型変換（`coerce`）、余剰プロパティ。
- HTTP 異常系: 400（不正入力）/ 401・403（認証認可）/ 404（不存在）/ 409（競合・重複）/ 422。
- 外部依存の失敗: 外部 API のエラー応答・タイムアウト（MSW で注入）、DB のユニーク制約違反。
- 並行性・冪等性: 同時更新、リトライ時の二重登録（冪等キー）。
- 境界値: 0件 / 1件 / 大量件数（ページネーション）/ 上限超過。
- 既存テストで未カバーの正常系バリエーション。

各提案は「どのファイルに・どんな `it` を・なぜ」を1行で。採否は呼び出し元 `tdd`（サイクル境界）が `[+]` でユーザーに確認する。

## 出力（提示のみ）
- `plan` / `review`: 簡潔なレポート。 / `boundary`: 次サイクル以降のテスト提案リスト。

承認・採用の判断は呼び出し元 `tdd`（state-machine の run_mode・サイクル境界）に委ねる。

> 制約: Write/Edit 使用禁止（Explore のため物理的に不可。Read/Grep/Glob/Bash(git) のみ）。テストの実行もしない（読むだけ）。
