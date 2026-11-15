---
name: tdd-green
description: TDD の Green フェーズ。Red で追加した失敗テストを通す最小限の Next.js / React / TypeScript 実装を書く。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(yarn:*)
  - Bash(npx:*)
  - Bash(npm:*)
  - Bash(pnpm:*)
  - Grep
  - Glob
  - Bash(date:*)
examples:
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す最小限の実装を行う。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・置き場の方針）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` / `error_message` / `test_file_path` から、不足実装を特定（lib の関数 / hook / Client Component / Server Action / Route Handler / API クライアント / 正常系 MSW handler / ファクトリ）。

## 2. 実装（テスト種別ごと・最小）

### 必須パターン
- Server と Client の境界: 状態・イベント・ブラウザ API を使うコンポーネントだけに `"use client"` を付ける。`page.tsx` / `layout.tsx` にロジックを書かない（テストが `lib/` や hook を指しているなら、そこに書く）。
- `lib/` は React も Next.js も import しない純粋関数にする。時刻・乱数は引数で受け取る。
- データ取得は TanStack Query の hook に閉じ込める（`useEffect` + `fetch` + `useState` で手書きしない）。query key は配列で、引数を含める（`['reservations', { date }]`）。
- API 呼び出しは API クライアント経由。レスポンスの型は OpenAPI の生成型（`components['schemas'][...]` / `paths[...]`）を使い、手書きの型を重ねない。生成ファイルは手で編集しない。
- トークンは API クライアントに注入する（クライアント内部で `useAuth0` を呼ばない。hook 側で `getAccessTokenSilently` を渡す）。
- アクセシブルな markup で書く: ボタンは `<button>`、入力には `<label>` を紐付ける、エラーは `role="alert"`、見た目だけの状態は `aria-pressed` / `aria-current` / `aria-invalid` / `disabled` で表に出す。テストが role で引けないのは markup の問題として直す（テストに `data-testid` を足して逃げない）。
- Server Action は入力（`FormData`）を検証してから使う。`revalidatePath` / `redirect` はテストが要求したものだけ呼ぶ。
- テストを通すための正常系 MSW handler が無ければ `test/msw/handlers.ts` に追加する（OpenAPI の型に合わせる）。

### 最小実装の線引き
テストが要求していない props・分岐・ローディング表示・エラー表示・楽観的更新・メモ化は作らない。それぞれ後続サイクルが駆動する。共通化・hook 抽出・コンポーネント分割は Refactor フェーズ以降で。

## 3. テスト pass 確認
```bash
pnpm vitest run {test_file_path}
```
全件 pass を確認。最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

典型的失敗と対処:
- role / label が見つからない → markup をアクセシブルにする（`<div onClick>` を `<button>` に、`<label htmlFor>` の紐付け）。
- 非同期の表示が出ない → テスト側が `findBy*` で待っているか、hook が `enabled` 条件で止まっていないか、MSW handler の URL が合っているか。
- `Invalid hook call` / `No QueryClient set` → hook を Server Component から呼んでいる、または wrapper を通していない。
- `server-only` / `next/headers` を Client から import している → 境界の誤り。サーバー専用の処理を Client Component から切り離す。
- 型エラー → 実装の型を直す。`any`/`as`/`@ts-expect-error` で通さない（停止条件#8）。
- 前のテストの状態が残る → QueryClient の共有・モックの戻し忘れ（不変条件#3）。

テストを都合よく書き換えて通してはいけない（Red で承認済み）。テスト側の誤りと判断した場合は停止して報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。追加した MSW handler・ファクトリも含める), `retry_count`。

## 5. サマリ（簡潔）
実装した lib / hook / component / server action / handler / MSW handler の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- 依存パッケージの追加は設計判断: 新規ライブラリ（UI ライブラリ・日付ライブラリ・フォームライブラリ等）が必要になったら停止条件#2 として提示し承認を得る。
- API 契約（OpenAPI）の変更が必要になったら停止条件#2（バックエンドとの合意が要る）。
- `pnpm typecheck` で型崩れがないことも確認しておくと Commit 時の hook で弾かれない。
