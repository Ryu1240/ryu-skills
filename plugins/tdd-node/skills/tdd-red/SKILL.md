---
name: tdd-red
description: TDD の Red フェーズ。失敗する Vitest テスト（`it` 1つ）を1つだけ追加し、期待どおりに失敗することを確認する。通常は /tdd から呼ばれる。単独では「失敗するテストを1つ書いて」と頼まれたときに使う。
argument-hint: <workflow_id> [test_file_path]
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
  - TaskGet
  - Bash(date:*)
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。今サイクルのテストを1つだけ（1つの `it`）追加し、期待通り失敗することを確認する。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（レイヤー構成・パス・不変条件・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 一度に1テストケースのみ。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が存在しないことを Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`(layer/test_kind/uses_db/uses_external_api), `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ実装と同ディレクトリの `*.test.ts`（既存ファイルへの追記を優先、無ければ新規）。
- `src/routes/orders.ts` → `src/routes/orders.test.ts`、`src/services/inventory.ts` → `src/services/inventory.test.ts`。
- 既存の配置に揺れがあれば Glob で数え多数派に合わせる（`__tests__/` や `tests/` 別ツリーの慣習があればそちらに従う）。

## 2-b. 既存テストへの影響確認
公開インターフェイスの変更は既存テストを壊す。変更する場合は参照箇所を Grep し、必要なら本サイクルで合わせて更新（振る舞いの意味は変えない）：
- 関数/メソッドのシグネチャ、エクスポート名
- Zod スキーマ（フィールド追加は `.strict()` なスキーマのテストを壊す。既存の `parse` テストを Grep）
- DI で渡すオブジェクトの形（モックの型も直す必要がある）
- DB スキーマ（マイグレーションを伴う場合は既存の repository テストを確認）

## 3. テスト追加（レイヤー別の必須パターン）
既存の近いテストを Read し慣習に揃える。order-api の必須パターンを守る：

### schema spec（Zod）
```ts
describe('createOrderSchema', () => {
  it('rejects a negative quantity', () => {
    const result = createOrderSchema.safeParse({ ...validInput, quantity: -1 });
    expect(result.success).toBe(false);
  });
});
```

### service spec（ロジック。DI で依存を差し替える）
```ts
describe('InventoryService', () => {
  it('throws OutOfStockError when stock is insufficient', async () => {
    const repo = { findStock: vi.fn().mockResolvedValue(0) };      // DI で注入
    const service = new InventoryService(repo);
    await expect(service.reserve('sku-1', 1)).rejects.toThrow(OutOfStockError);
  });
});
```
- `vi.mock` によるモジュール丸ごとモックより、コンストラクタ/引数注入を優先（不変条件#4）。
- `afterEach(() => { vi.restoreAllMocks() })` を置く（戻し忘れたモックが後続のテストに漏れ、独立性が崩れる）。

### route spec（HTTP 契約。Supertest）
```ts
describe('POST /orders', () => {
  it('returns 409 when stock is insufficient', async () => {
    const res = await request(app).post('/orders').send(validBody);
    expect(res.status).toBe(409);
    expect(res.body).toMatchObject({ code: 'OUT_OF_STOCK' });
  });
});
```
- 正常系・バリデーション(400)・異常系(404/409)・認可(401/403)は別サイクルに分ける。

### repository spec（DB）
実 DB に対して実行し、各ケースでトランザクションロールバック（`beforeEach` で開始、`afterEach` でロールバック）。テスト間でレコードを共有しない。

### 外部 API を叩く場合
MSW handler（`src/testUtils/mocks/handlers/`）でモック。異常系は各テストで `server.use(...)` 上書き。`afterEach(() => server.resetHandlers())`。実通信はしない。

## 4. 失敗確認
```bash
yarn vitest run {test_file_path} -t "{テストケース名}"
```
期待される失敗: 未定義（関数/エクスポート/ルート）、`expected 409 got 404/500`、Zod の検証が通ってしまう、アサーション不一致。
予期しない失敗（import パス誤り、型エラー、DI 未配線、DB 未接続、MSW 未起動）はテスト側を修正して再実行。実装を書き始めてはいけない。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, `test_name`（`-t` に渡すケース名）, `test_case_count`（`test_file_path` 内の `it(` / `test(` / `it.each` / `test.each` の定義数。Evac(review) の基準値）, `test_details`(error_type/message), `created_at`/`updated_at`）。

## 6. サマリ（簡潔）
テストファイル / 追加した1ケース / 期待通りの失敗 / 適用パターン（DI・Supertest・ロールバック・MSW 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（route/service 名）追記を案内。
- ファクトリ未定義: `src/testUtils/factory/` を確認し追加を促す。
- 型エラーでテストが書けない: 実装側の型が未定義なのが原因ならそれが期待される失敗（そのまま Green へ）。設計上の型の矛盾なら停止条件#8 として報告。
