---
name: tdd-red
description: Red phase - Write ONE failing Rust test (#[test] / #[tokio::test]) for ledger-core, confirm it fails as expected (including compile errors caused by the not-yet-defined target)
argument-hint: <workflow_id> [test_file_path]
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
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。**今サイクルのテストを1つだけ**（1つのテスト関数）追加し、期待通り失敗することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（レイヤー構成・パス・**不変条件**・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 **一度に1テストケースのみ**。複数追加は不変条件違反。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が**存在しないこと**を Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`(layer/test_kind/test_location/is_async/uses_db/uses_external_api/assert_lib), `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストの置き場所決定
`$1` 指定があればそれ。無ければ `patterns.test_location` と既存の慣習に従う：
- **ユニット（domain / service / repository）**: 実装ファイル末尾の `#[cfg(test)] mod tests { use super::*; ... }`（既存 `mod tests` への追記を優先、無ければ新規作成）。`src/services/inventory.rs` → 同ファイル内。`mod.rs` 分割や `#[cfg(test)] mod tests;` + `tests.rs` の慣習があればそれに従う。
- **統合（route の契約テスト・公開 API）**: `tests/{name}.rs`（lib の公開 API 経由。`tests/common/mod.rs` にヘルパ）。既存の配置に揺れがあれば Glob で数え多数派に合わせる。

## 2-b. 既存テストへの影響確認（critical）
**公開インターフェイスの変更**は既存テスト・フェイクを壊す。変更する場合は参照箇所を Grep し、必要なら本サイクルで合わせて更新（振る舞いの意味は変えない）：
- **トレイトへのメソッド追加** → **全フェイク実装（`impl XxxRepo for FakeRepo`）がコンパイルできなくなる**。フェイクも同時に更新（`mockall` なら自動）。
- **公開 struct へのフィールド追加** → struct リテラルで構築している全テストが壊れる。`Default` 導出かビルダー関数（`testutil`）への寄せ替えを検討。
- **enum variant の追加** → 網羅 `match` が壊れる（`_ =>` で潰さず各腕を追加）。
- **関数シグネチャ / 型名 / `pub` の変更** → `tests/` の統合テストを Grep。
- **DB スキーマ変更** → `sqlx::query!` のオフラインデータ再生成（`cargo sqlx prepare`）が要る。既存 repository テストも確認。

## 3. テスト追加（レイヤー別の必須パターン）
既存の近いテストを Read し慣習（アサーションライブラリ・フェイクの書き方・ヘルパ名）に揃える。**ledger-core の必須パターンを守る**：

### domain spec（純粋関数・値オブジェクト。同期）
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn rejects_negative_amount() {
        let err = Amount::new(-1).unwrap_err();
        assert!(matches!(err, LedgerError::InvalidAmount { .. }));
    }
}
```
- エラーは `matches!` で **variant を判定**する（`to_string()` の文字列比較で判定しない）。
- `?` を使いたいテストは `-> Result<(), Box<dyn std::error::Error>>` を返す。

### service spec（ロジック。トレイトに手書きフェイクを注入）
```rust
#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::Arc;

    struct FakeRepo { stock: i64 }

    #[async_trait::async_trait]                     // Arc<dyn Trait> で async メソッドを持つ場合（既存の慣習に従う）
    impl InventoryRepo for FakeRepo {
        async fn find_stock(&self, _sku: &str) -> Result<i64, LedgerError> { Ok(self.stock) }
    }

    #[tokio::test]
    async fn returns_out_of_stock_when_stock_is_insufficient() {
        let service = InventoryService::new(Arc::new(FakeRepo { stock: 0 }));
        let err = service.reserve("sku-1", 1).await.unwrap_err();
        assert!(matches!(err, LedgerError::OutOfStock { .. }));
    }
}
```
- **`mockall` より手書きフェイクを優先**（不変条件#4。既に `mockall` を使うリポではそれに従う）。フェイクが複数モジュールで要るなら `#[cfg(test)] pub mod testutil` に置く。
- 時刻・乱数は `Clock` などのトレイトで注入し、テストでは固定値を返すフェイクを渡す。

### route spec（HTTP 契約。`oneshot`）
```rust
#[tokio::test]
async fn returns_409_when_stock_is_insufficient() {
    let app = test_app(FakeRepo { stock: 0 });      // Router を組み立てるヘルパ（testutil / tests/common）
    let req = Request::builder()
        .method("POST").uri("/orders")
        .header("content-type", "application/json")
        .body(Body::from(json!({ "sku": "sku-1", "quantity": 1 }).to_string()))
        .unwrap();
    let res = app.oneshot(req).await.unwrap();
    assert_eq!(res.status(), StatusCode::CONFLICT);
    let bytes = to_bytes(res.into_body(), usize::MAX).await.unwrap();
    let body: serde_json::Value = serde_json::from_slice(&bytes).unwrap();
    assert_eq!(body["code"], "OUT_OF_STOCK");
}
```
- **正常系・デシリアライズ/検証(400/422)・異常系(404/409)・認可(401/403)は別サイクル**に分ける。
- `axum-test` 導入時は `TestServer` を使う。actix-web なら `test::init_service` + `call_service`。

### repository spec（DB。`#[sqlx::test]`）
```rust
#[sqlx::test(migrations = "./migrations")]
async fn find_stock_returns_zero_for_unknown_sku(pool: PgPool) {
    let repo = PgInventoryRepo::new(pool);
    assert_eq!(repo.find_stock("unknown").await.unwrap(), 0);
}
```
- **テストごとに DB が作られる**ので他テストとレコードを共有しない。`#[sqlx::test]` が使えないリポでは `pool.begin()` でトランザクションを開き末尾でロールバック。diesel は `test_transaction`。

### 外部 API を叩く場合（`wiremock`）
```rust
#[tokio::test]
async fn maps_upstream_500_to_pricing_unavailable() {
    let server = MockServer::start().await;         // テストごとに起動（共有しない）
    Mock::given(method("GET")).and(path("/prices/sku-1"))
        .respond_with(ResponseTemplate::new(500))
        .mount(&server).await;
    let client = HttpPricingClient::new(server.uri());
    let err = client.price_of("sku-1").await.unwrap_err();
    assert!(matches!(err, LedgerError::PricingUnavailable));
}
```
**実通信はしない**。

### パラメータ化が要る場合
`rstest` 導入時は `#[rstest] #[case(...)]`。未導入なら 1 テスト内でタプル配列をループし、`assert!(..., "case: {name}")` のように失敗メッセージにケース名を含める（それでも **1 サイクル = 1 テスト関数**）。

## 4. 失敗確認
```bash
cargo test -p {crate} {test_name} -- --exact          # test_name はモジュールパス込み（services::inventory::tests::case_name）
cargo test -p {crate} --test {file} {case} -- --exact  # tests/{file}.rs の統合テストの場合
```
期待される失敗:
- **テストが要求する型・関数・トレイトメソッド・enum variant が未定義でコンパイルできない**（Rust では**これが正規の Red**。Green で定義する。`error_type: compile_error_undefined`）。
- アサーション不一致（`assertion failed` / `left != right`）、`matches!` が false、ステータスコード不一致、`unwrap_err()` が `Ok` で panic。

**予期しない失敗**は**テスト側を修正して再実行**。実装を書き始めてはいけない：
- 対象の未定義**以外**の理由によるコンパイルエラー（`use` 漏れ、テスト内の `Send` 境界不足、lifetime、型推論不能）。
- `#[tokio::test]` 忘れ（`await` is only allowed inside `async` functions）。
- `sqlx::query!` が `DATABASE_URL` 未設定 / `.sqlx/` 不在でコンパイル不能（project-settings のコンパイル方式を確認）。
- feature flag 未指定、dev-dependency 未追加（追加は停止条件#2 の設計判断として確認）。
- **`running 0 tests`** と出る → `test_name` のモジュールパスが誤っている（`--exact` はフィルタ完全一致）。パスを直す。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, **`test_name`**（`-- --exact` に渡す完全名）, `test_details`(error_type/message), `created_at`/`updated_at`）。
**自己検証**: Read で `phase=="red"`・`updated_at` 更新を確認。

## 6. サマリ（簡潔）
テストの場所（inline / tests/）/ 追加した1ケース / 期待通りの失敗（コンパイルエラーか実行時か）/ 適用パターン（フェイク注入・oneshot・`#[sqlx::test]`・wiremock 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストの置き場所決定不能: `$1` 明示 or タスクに対象名（route/service 名）追記を案内。
- ビルダー / フェイク未定義: `testutil` / `tests/common` を確認し追加を促す（テストと同じサイクルで追加してよい）。
- コンパイルエラーでテストが書けない: 対象の型・関数が未定義なのが原因なら**それが期待される失敗**（そのまま Green へ）。borrow checker がモジュール構造の変更を要求するなど設計上の矛盾なら停止条件#8 として報告。
