---
name: tdd-refactor
description: Refactor phase - Improve ledger-core Rust code quality (layer hygiene / N+1 queries / typed errors / ownership & borrowing / async pitfalls / type-driven design) while keeping cargo test green
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cargo:*)
  - Bash(rustup:*)
  - Bash(make:*)
  - Bash(just:*)
  - Grep
  - Glob
examples:
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。**動作を変えずに**コード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（lint・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌**新規テスト追加**（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ・Rust 固有）

### 2-1. レイヤー衛生（最優先）
- **依存方向の逆流**を解消: service が `axum::` / `http::` / `StatusCode` を持っていないか、route にビジネスロジックが漏れていないか、repository 以外に `sqlx::query` が無いか（Grep で確認）。
- 見つかった場合は正しい層へ移動する（テストが緑のまま動くこと）。

### 2-2. N+1 クエリ（必須確認）
ループ内での DB 呼び出し・`.await` を Grep で探す。
```rust
for id in ids { repo.find_by_id(id).await?; }            // ❌ N+1
let rows = repo.find_by_ids(&ids).await?;                 // ✅ 一括取得（WHERE id = ANY($1)）
```
`futures::future::join_all` で並列化しても **N 本のクエリは N 本のまま**（N+1 の解決ではない）。JOIN / `ANY($1)` / バッチで 1 クエリに。**ループ内 `.await` はレビュー対象**。

### 2-3. エラー処理の一貫性
- 非テストコードの **`unwrap()` / `expect()` / `panic!`** を `?` と variant に置換（不変条件#5）。
- `Box<dyn Error>` / `anyhow` がドメイン・サービス層に漏れていれば型付き enum に。
- 同じ `map_err(|e| LedgerError::Db(e))` の繰り返しは `#[from]` / `impl From` に集約。
- `let _ = fallible();` の握り潰し、`if let Err(_) = ... {}` の空腕を解消。
- エラーメッセージ・`Display` に接続文字列・SQL・スタックなど内部情報を載せない。

### 2-4. 所有権と借用
- 不要な **`clone()`**（借用で済む・`Arc` の clone で済む・`into()` で所有権を渡せる）を除去。
- 引数は `String` → `&str`、`Vec<T>` → `&[T]`、`Box<T>` → `&T` に（呼び出し側が所有権を渡す必要が無いなら）。
- `Rc<RefCell<_>>` の濫用、`Arc<Mutex<_>>` の保持範囲が広すぎる（ロックを関数全体で握る）箇所を狭める。
- `String` を都度 `format!` で作っている定数は `&'static str` / `const` に。

### 2-5. async の落とし穴
- async 関数内の **`std::thread::sleep` / `std::fs` / ブロッキング I/O** → `tokio::time::sleep` / `tokio::fs` / `spawn_blocking`。
- **`MutexGuard` を `.await` 跨ぎで保持**（`std::sync::Mutex`）→ スコープを切る、または `tokio::sync::Mutex`。
- `tokio::spawn` の `JoinHandle` を捨てている（エラーが消える）→ `await` するか `JoinSet` で回収。
- 独立した非同期処理が直列 `.await` → `tokio::join!` / `try_join!` で並列化（**順序依存・同一トランザクション内は除く**）。

### 2-6. 型駆動設計と命名
- ID・金額・SKU などのプリミティブを newtype（`struct Sku(String)`）に。文字列で持っている状態を enum に。
- `Option<Option<T>>`、`Result<Option<T>, E>` と `Option<Result<T, E>>` の混在、`bool` 引数の羅列を解消。
- getter に `get_` 接頭辞を付けない、`snake_case` / `CamelCase` / `SCREAMING_SNAKE_CASE` の規約を守る。1文字変数・`data` / `tmp` を役割名に。
- 責務過多（検証・取得・変換・永続化が同居）な関数を分割。深いネストは early return / `let else` / `?` へ。

### 2-7. フォーマット / lint
```bash
cargo fmt --all
cargo clippy --all-targets --all-features -- -D warnings
```
今サイクルで **`#[allow(clippy::...)]` / `#[allow(dead_code)]` が増えていないか** Grep で確認。増えていれば根本を直す（直せなければ停止条件#8 として報告）。

## 3. テスト維持確認
```bash
cargo test -p {crate} {module_path}::
```
モジュール内の全件 pass を維持していることを確認。失敗したら参照ミス（移動したモジュールの `use`、トレイト境界、フェイクの更新漏れ）を修正、または `[r]修正 / [u]ロールバック / [s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（`layer_fixes` / `n_plus_one` / `error_handling` / `ownership` / `async_fixes` / `type_design` / `naming` / `linter`。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。
**自己検証**: `phase=="refactor"` かつ `refactor_details` 非空を Read で確認。

## 5. サマリ（簡潔）
実施した改善（レイヤー/N+1/エラー/所有権/async/型/命名/lint 件数）/ 全件 pass / 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。

## 注意
- **振る舞いを変える改善は Refactor ではない**。仕様変更に踏み込む必要が見えたら停止条件#2（設計判断）として報告する。
- **レイヤー構成そのものの変更**（新しい層・クレートの追加、依存の向きの変更）や **`unsafe` の導入**はスコープ外。提案として報告し別タスクに分ける。
- **公開 API（`pub`）のシグネチャ変更**は `tests/` の統合テストと下流クレートを壊す。今サイクルの実装に閉じた変更に留める。
