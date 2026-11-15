---
name: tdd-refactor
description: TDD の Refactor フェーズ。テストを緑に保ったまま、Server と Client の境界・hook と純粋関数への切り出し・useEffect の誤用・query key とキャッシュ無効化・アクセシビリティ・型の健全性を改善する。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
model: opus
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
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。動作を変えずにコード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（lint・置き場の方針）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌新規テスト追加（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ・Next.js / React 固有）

### 2-1. Server と Client の境界（最優先）
- `"use client"` が必要以上に上（ページ全体・レイアウト）に付いていないか。状態やイベントを持つ部分だけを子コンポーネントに切り出し、親は Server Component のまま保つ。
- Client Component から `server-only` のモジュール・`next/headers`・秘密情報を参照していないか（Grep で確認）。`NEXT_PUBLIC_` に秘密が入っていないか。
- `page.tsx` / `layout.tsx` に分岐・整形・計算が漏れていれば `lib/` の関数へ移す（テストが緑のまま動くこと）。

### 2-2. ロジックの置き場
- コンポーネント内の計算・整形・判定は `lib/` の純粋関数へ。複数の state / effect が絡む振る舞いは custom hook へ。単純な表示ロジックまで抽出しない。
- 責務過多（取得 + 変換 + 表示が同居）なコンポーネントは、データを持つ側と表示する側に分ける。

### 2-3. useEffect の誤用
- props / state から計算できる値を `useEffect` + `setState` で同期していれば、レンダー中の計算に置き換える。
- `useEffect` 内の `fetch` はデータ取得の hook（TanStack Query）へ。イベントで起きる処理はイベントハンドラへ。
- 依存配列の抜け・オブジェクト/関数の毎回生成による無限ループに注意。

### 2-4. TanStack Query の衛生
- query key をリテラルで散らばらせず、key factory（`reservationKeys.list({ date })`）に集約する。
- mutation 成功時の無効化が、影響する query key を過不足なく対象にしているか。
- `staleTime` / `enabled` / `select` の設定がコンポーネントごとにばらついていれば hook 側に寄せる。

### 2-5. 再レンダーとメモ化
- 計測なしの `useMemo` / `useCallback` / `React.memo` を増やさない（React Compiler を使っている場合は不要）。逆に、明らかに重い計算・大きなリストの `key` に index を使っている箇所は直す。

### 2-6. アクセシビリティ
- `<div onClick>` → `<button>`、入力の `<label>` 紐付け、見出し階層、エラーの `role="alert"` / `aria-describedby`。テストが role で引けているかは改善の手がかりになる。

### 2-7. 型の健全性
- `any` / `as` / `@ts-expect-error` が今サイクルで増えていないか。増えていれば型定義で解消する（解消できなければ停止条件#8 として報告）。
- OpenAPI の生成型と手書きの型が重複していれば生成型に寄せる。props の型は `ComponentProps` などで導出できるなら導出する。

### 2-8. Tailwind とテストヘルパ
- 同じクラスの長い並びが複数箇所にあれば、コンポーネントか variant に寄せる（`cn` / `clsx` などプロジェクトの慣習に従う）。
- テスト側で重複している render の配線（QueryClient・認証モック）は `renderWithProviders` に寄せる。ただしテストケースの追加・削除はしない。

### 2-9. 命名
- 1文字変数・`data`/`info`/`tmp` 等の無意味名を役割名に。イベントハンドラは `handleX` / props は `onX` の慣習に揃える。

### 2-10. lint / 型チェック
```bash
pnpm lint --fix {files}
pnpm typecheck
```

## 3. テスト維持確認
```bash
pnpm vitest run {test_file_path}
```
全件 pass を維持していることを確認。失敗したら参照ミス（移動したモジュールの import、`"use client"` の付け忘れ、props の受け渡し）を修正、または `[r]修正 / [u]ロールバック / [s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（`client_boundary` / `logic_extraction` / `effect_fixes` / `query_hygiene` / `memoization` / `a11y` / `type_safety` / `styling` / `naming` / `linter`。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。

## 5. サマリ（簡潔）
実施した改善（境界/切り出し/effect/query/a11y/型/命名/lint 件数）/ 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。

## 注意
- 振る舞いを変える改善は Refactor ではない。表示やアクセシブルネームが変わる変更（テストの `getByRole` の name が変わるなど）は仕様変更なので、停止条件#2（設計判断）として報告する。
- ディレクトリ構成そのものの変更（`features/` の切り方の変更など）はスコープ外。提案として報告し別タスクに分ける。
