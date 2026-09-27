---
name: tdd-green
description: Green phase - Minimal implementation in order-api (TypeScript/Node backend) to pass the failing Vitest test
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
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す**最小限の実装**を行う。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**不変条件**・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` / `error_message` / `test_file_path` から、不足実装を特定（route ハンドラ / service メソッド / repository クエリ / Zod スキーマ / エラークラス / DI 配線）。

## 2. 実装（レイヤー別・最小）

### 必須パターン
- **レイヤーの依存方向を守る**（routes → services → repositories）。service に `req`/`res` を渡さない。repository 以外に SQL/ORM 呼び出しを書かない。
- **外部 I/O は DI で受け取る**: `fetch` / DB クライアント / 時刻 / ランダム を実装内で直接掴まない（コンストラクタ引数か関数引数）。
- **境界は Zod で検証**: route はリクエストを `parse`/`safeParse` してから service に渡す。`as` で検証を迂回しない。
- **エラーは型で表現**: 業務エラーは専用クラス（`OutOfStockError` 等）を投げ、route 層で HTTP ステータスに変換。`catch` で握り潰さない。
- **DB スキーマ変更が要るならマイグレーションを生成**して適用（生成物はコミット対象）。

### 最小実装の線引き
テストが要求していない分岐・引数・設定・抽象化は**作らない**。共通化・インターフェース抽出・キャッシュは Refactor フェーズ以降で。

## 3. テスト pass 確認
```bash
yarn vitest run {test_file_path}
```
全件 pass を確認。最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

典型的失敗と対処:
- **型エラー** → 実装の型を直す。`any`/`as`/`@ts-expect-error` で通さない（停止条件#8）。
- **DI 未配線** → route/service の生成箇所で依存を渡す。
- **Zod の検証が想定と違う** → スキーマの定義（`optional`/`nullable`/`coerce`）を確認。
- **await 漏れ** → Promise がテストに解決されず落ちる典型。
- **DB のロールバック漏れ** → 前のケースのデータが残って件数が合わない。

**テストを都合よく書き換えて通してはいけない**（Red で承認済み）。テスト側の誤りと判断した場合は停止して報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。マイグレーション生成物も含める), `retry_count`。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
実装した route/service/repository/schema / マイグレーションの有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- **依存パッケージの追加は設計判断**: 新規ライブラリが必要になったら停止条件#2 として提示し承認を得る。
- `yarn typecheck` で型崩れがないことも確認しておくと Commit 時の hook で弾かれない。
