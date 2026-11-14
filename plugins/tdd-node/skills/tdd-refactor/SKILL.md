---
name: tdd-refactor
description: TDD の Refactor フェーズ。テストを緑に保ったまま、レイヤーの依存方向・N+1・非同期の落とし穴・エラークラス・型の健全性を改善する。通常は /tdd から呼ばれる。
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
- `.claude/skills/_shared-tdd/project-settings.md`（lint・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌新規テスト追加（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ・Node/TS バックエンド固有）

### 2-1. レイヤー衛生（最優先）
- 依存方向の逆流を解消: service が `req`/`res` を受け取っていないか、route にビジネスロジックが漏れていないか、repository 以外に ORM 呼び出しが無いか（Grep で確認）。
- 見つかった場合は正しい層へ移動する（テストが緑のまま動くこと）。

### 2-2. N+1 クエリ（必須確認）
ループ内での DB 呼び出し・`await` を Grep で探す。
```ts
for (const id of ids) { await repo.findById(id) }   // ❌ N+1
const rows = await repo.findByIds(ids)              // ✅ 一括取得
```
ORM の関連取得（Prisma の `include`、Drizzle の join、TypeORM の `relations`）でまとめる。ループ内 await はレビュー対象。

### 2-3. 非同期の落とし穴
- `await` 漏れ: Promise を返す関数の呼び出しに `await`/`return` が無い箇所（浮いた Promise は例外を握り潰す）。
- `Promise.all` 化: 独立した非同期処理が直列に `await` されていれば並列化（順序依存・DB トランザクション内は除く）。
- `forEach` 内の `async` は待たれない → `for...of` + `await` か `Promise.all(map)` に。

### 2-4. エラー処理の一貫性
- 業務エラーは専用クラスに統一し、route 層で HTTP ステータスへ変換する箇所を1か所に集約。
- `catch (e) {}` の握り潰し・`catch` して同じ内容を再 throw するだけの冗長を解消。
- エラーメッセージに内部情報（SQL・スタック・接続文字列）を載せない。

### 2-5. 型の健全性
- `any` / `as` / `@ts-expect-error` が今サイクルで増えていないか。増えていれば型定義で解消する（解消できなければ停止条件#8 として報告）。
- Zod スキーマから型を導出できる箇所で手書き型を重複定義していれば `z.infer` に寄せる。

### 2-6. 関数の分解と命名
- 責務過多（検証・取得・変換・永続化が同居）な関数を分割。深いネストは early return へ。
- 1文字変数・`data`/`info`/`tmp` 等の無意味名を役割名に。

### 2-7. lint / 型チェック
```bash
yarn lint --fix {files}
yarn typecheck
```

## 3. テスト維持確認
```bash
yarn vitest run {test_file_path}
```
全件 pass を維持していることを確認。失敗したら参照ミス（移動したモジュールの import、DI の配線、命名）を修正、または `[r]修正 / [u]ロールバック / [s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（`layer_fixes` / `n_plus_one` / `async_fixes` / `error_handling` / `type_safety` / `decomposition` / `naming` / `linter`。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。

## 5. サマリ（簡潔）
実施した改善（レイヤー/N+1/非同期/エラー/型/命名/lint 件数）/ 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。

## 注意
- 振る舞いを変える改善は Refactor ではない。仕様変更に踏み込む必要が見えたら停止条件#2（設計判断）として報告する。
- レイヤー構成そのものの変更（新しい層の追加、依存の向きの変更）はスコープ外。提案として報告し別タスクに分ける。
