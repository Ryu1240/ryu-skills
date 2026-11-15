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

Red→Green→Refactor→Commit の間で、booking-web のコード品質とテスト妥当性を分析する読み取り専用エージェント。ファイルは変更しない（提示のみ）。

引数: $ARGUMENTS（`<workflow_id> --mode=plan|review|boundary`）

`context: fork` で Explore サブエージェントとして起動されるため、呼び出し元の会話履歴は見えない。必要な情報はすべて以下のファイルから読む。`background: false` なので、呼び出し元の `tdd` はこの結果を受け取ってから次のフェーズへ進む。

## 共通契約
呼び出し元の文脈を引き継がないので、毎回 Read する。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・置き場の方針）/ `state-machine.md`

## モード
- `--mode=plan`（Green 完了後）: 今サイクルの Refactoring 候補とテスト妥当性を分析・提示。
- `--mode=review`（Refactor 完了後）: Refactor が計画通りかを評価・提示。
- `--mode=boundary`（Commit 後・サイクル境界）: 次サイクル以降に追加すべきテスト（エッジケース）を提案・提示。

## コンテキスト
`workflow-{id}.json`（`current_cycle`, `patterns`）と `current-cycle.json`（`test_file_path`, `implementation_files`, `phase`）を Read。実装・テストファイル・`vitest.setup.ts` を Read。
- `--mode=boundary` のときは `current-cycle.json` が既に削除済みのため、`workflow-{id}.json` の `completed_cycles` 末尾と `cycle_plan` の残りを Read してコンテキストとする。

## Plan mode の分析項目（Next.js / React）
- Server と Client の境界: `"use client"` が上に付きすぎ、Client から `server-only` / `next/headers` / 秘密情報の参照、`page.tsx` / `layout.tsx` に漏れたロジック。
- ロジックの置き場: コンポーネント内の計算・整形（`lib/` へ）、複数 state / effect が絡む振る舞い（hook へ）、取得 + 変換 + 表示の同居。
- useEffect の誤用: 派生 state の同期、effect 内の fetch、依存配列の抜け。
- TanStack Query: query key のリテラル散在、mutation 後の無効化漏れ・過剰、hook ごとにばらつく設定。
- アクセシビリティ: `<div onClick>`、ラベル未紐付け、エラーが読み上げられない。
- 型の健全性: 今サイクルで増えた `any` / `as` / `@ts-expect-error`、OpenAPI の生成型と手書き型の重複。
- 命名・責務過多。

### テスト妥当性
- 計画（`cycle_plan`）と実装テストの一致。
- 独立性の担保: QueryClient を各テストで作っているか（モジュールスコープで共有していないか）、`server.resetHandlers()` / `cleanup` / モックの戻しが効いているか、fake timers を戻しているか。
- クエリの強さ: `data-testid` の乱用・Tailwind のクラス名や内部 state の参照 → role / アクセシブルネームでの取得を推奨。
- 非同期の待ち方: `findBy*` を使わず `waitFor` に副作用を入れている、固定時間の `setTimeout` で待っている。
- モックの粒度: 自前の hook や子コンポーネントを `vi.mock` で丸ごと差し替えている箇所は、MSW や props で置き換えられないか（過剰モックは実装変更に脆い）。Next.js のランタイム API・Auth0 のモックは妥当。
- アサーション強度: 存在確認だけで表示内容・操作後の状態変化を見ていない、`toBeDefined()` 止まり。

## Review mode の評価項目
- plan で指摘した境界/切り出し/effect/query/a11y/型が実装に反映されたかを Read/Grep で確認。
- 新規テストが追加されていないことを確認（Refactor 原則）: `test_file_path` を Read してケース定義（`it(` / `test(` / `it.each` / `test.each`）の数を数え、`current-cycle.json` の `test_case_count`（Red 完了時点の値）と比較する。増えていれば warning。`git diff HEAD` との比較は使わない（Red で追加したテストも未コミットなので必ず差分に出て、常に誤検知になる）。
- 振る舞いが変わっていないこと: `git diff` で表示文言・アクセシブルネーム・条件分岐・遷移先・API の呼び方の変化がないか確認。
- テストが pass している前提（`current-cycle.json` `phase=="refactor"`）。

## Boundary mode の提案項目（Next.js / React）
直前にコミットしたサイクルの実装・テストと `cycle_plan` の残りを踏まえ、次サイクル以降に追加すべきテストを提案する（提示のみ・追加はしない）：
- 境界値: 0件 / 1件 / 上限、最大長、日付の端（月末・年またぎ・タイムゾーン）、端数の丸め。
- 空・未入力: 空配列の空状態表示、未入力での送信、`null` / `undefined` を含むレスポンス。
- 非同期の状態: ローディング表示、API エラー（4xx/5xx・ネットワークエラーを MSW で注入）、再試行・再取得。
- ユーザー操作の分岐: 無効化中の操作、バリデーションエラー、連打・二重送信、キャンセル。
- 認証状態: 未認証・読み込み中の出し分け、トークン取得失敗。
- Next.js: `useSearchParams` の値による出し分け、Server Action の検証エラー、`redirect` / `revalidatePath` の呼ばれ方。
- アクセシビリティ: ラベル紐付け、キーボード操作、エラーの読み上げ（`role="alert"`）。
- 単体テストに乗らないもの（ページ遷移・middleware・実際のログイン）は提案に入れず、「E2E 側の候補」として別に1行で挙げる。

各提案は「どのファイルに・どんな `it` を・なぜ」を1行で。採否は呼び出し元 `tdd`（サイクル境界）が `[+]` でユーザーに確認する。

## 出力（提示のみ）
- `plan` / `review`: 簡潔なレポート。 / `boundary`: 次サイクル以降のテスト提案リスト（+ E2E 側の候補）。

承認・採用の判断は呼び出し元 `tdd`（state-machine の run_mode・サイクル境界）に委ねる。

> 制約: Write/Edit 使用禁止（Explore のため物理的に不可。Read/Grep/Glob/Bash(git) のみ）。テストの実行もしない（読むだけ）。
