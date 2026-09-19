# TDD スキル共通設定（Project Settings）— ledger-core

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> ledger-core は **Rust の台帳サービス**（HTTP API サーバー）。lib + bin 分割の単一クレート。axum + tokio + sqlx。UI を持たない。

## 構成とテスト

| | backend（Rust） |
|---|---|
| クレート | リポジトリ直下の単一クレート（ワークスペースなら `crates/api/` 等。bootstrap が確定） |
| ツールチェイン | Rust stable（edition 2021）。`rust-toolchain.toml` があればそれ |
| lib / bin | `src/main.rs` は起動のみ。`src/lib.rs` がモジュールを公開し、テストは lib 経由で書く |
| async ランタイム | tokio |
| Web フレームワーク | axum（actix-web / rocket なら bootstrap が読み替え） |
| テスト | 標準 `#[test]` / `#[tokio::test]` |
| HTTP テスト | `Router` + `tower::ServiceExt::oneshot`（`axum-test` 導入時はそれ） |
| テスト配置 | ユニット: 同一ファイル末尾の `#[cfg(test)] mod tests { use super::*; }` / 統合: `tests/*.rs`（lib の公開 API 経由） |
| アサーション | `assert!` / `assert_eq!` / `matches!`（`pretty_assertions` / `insta` 導入時はそれに合わせる） |
| パラメータ化 | `rstest`（導入時）。無ければ 1 テスト内でタプル配列をループし、失敗メッセージにケース名を含める |
| データ生成 | ビルダー関数。ユニット用は `#[cfg(test)] pub mod testutil`、**`tests/*.rs` から使うものは `tests/common/mod.rs`**（`cfg(test)` のモジュールは統合テストバイナリから見えない） |
| モック | トレイト + 手書きフェイク構造体を注入（`mockall` 導入時はそれ）。外部 HTTP は `wiremock` |
| DB | sqlx（PostgreSQL）。テストは `#[sqlx::test]`（テストごとに DB を作成しマイグレーション適用） |
| デシリアライズ / 検証 | serde（境界の `Json<T>` extractor）+ ドメイン型のコンストラクタで検証 |
| エラー | `thiserror` の enum（`src/domain/error.rs`）。`anyhow` は `main.rs` のみ |
| カバレッジ | `cargo llvm-cov`（未導入なら「未導入」） |

## レイヤー構成（この順に依存する。逆流禁止）

```
src/routes/       … HTTP 層。extractor でデコードし、IntoResponse でステータス変換するだけ
src/services/     … ビジネスロジック。axum / http の型を知らない
src/repositories/ … データアクセス。sqlx をここに閉じ込める
src/domain/       … 型・値オブジェクト・エラー enum。I/O を知らない（末端）
```

## テスト実行コマンド

```bash
cargo test -p ledger-core --lib services::inventory::tests::case_name -- --exact   # 単一ケース（Red の失敗確認・独立性検証。--lib でハーネスを 1 つに絞る）
cargo test -p ledger-core --lib services::inventory::                        # モジュール単位（Green の pass 確認。Rust は「ファイル」≒「モジュールパス」）
cargo test -p ledger-core                                                    # クレート単位（Refactor の pass 確認。モジュールを跨ぐ移動の回帰を統合テスト含めて拾う）
cargo test --workspace                                                       # 全件（CI 同様）
cargo test -p ledger-core -- --test-threads=1                                # 直列実行（並列既定との差分で順序依存・共有状態を炙り出す）
cargo nextest run -p ledger-core                                             # プロセス分離実行（導入済みなら。未導入なら「未導入」）
cargo llvm-cov -p ledger-core --show-missing-lines                           # カバレッジ（未到達行つき。既定出力は行番号が出ない。未導入なら「未導入」。tarpaulin でも可）
cargo clippy --all-targets -- -D warnings                                    # 静的解析（clippy はコンパイルも兼ねる。全フェーズ・hook・CI で同じ引数に揃える）
cargo fmt --all                                                              # フォーマット
```
> `justfile` / `Makefile` に `test` / `lint` レシピがあれば**それを最優先**（bootstrap が検出して差し替える）。
> `-p <crate>` で対象を絞るのはワークスペース全体のコンパイルを避けるため。**名前フィルタは実行対象を絞るだけでコンパイル量は減らない**。`--lib` / `--test {file}` を付けるとテストハーネスが 1 つになり、統合テストバイナリと doc-test のビルドも省ける。
> **ランダム順序は stable の `cargo test` では未対応**（nightly の `-Z unstable-options --shuffle` のみ）。独立性検証は「`--test-threads=1` と既定並列の両方で pass」「nextest でプロセス分離」「同じコマンドを 3 回連続実行」で代替する。
> 統合テスト（`tests/foo.rs`）の単一ケースは `cargo test -p ledger-core --test foo case_name -- --exact`。
> `sqlx::query!` マクロは `DATABASE_URL` か `SQLX_OFFLINE=true` + `.sqlx/` が無いとコンパイルできない（bootstrap が確認）。**`#[sqlx::test]` は実行時にも `DATABASE_URL` が必須**（テストごとに `_sqlx_test_*` DB を作るため接続先と CREATEDB 権限が要る。オフラインコンパイルでもこれは省けない）。

## CI / hook（重要）

- **CI がテストを走らせる**。push すれば `cargo test` / `cargo clippy -- -D warnings` / `cargo fmt --check` が自動実行される。
- **pre-commit hook あり（pre-commit / lefthook、または cargo-husky を `precommit-hook` + `run-cargo-fmt` / `run-cargo-clippy` feature で設定）**: コミット時に `cargo fmt --check` と `cargo clippy -- -D warnings` が走り、警告があるとコミットがブロックされる。→ `--no-verify` は**絶対禁止**。hook が無いリポでは `just lint`（または上記の静的解析コマンド）をコミット前に手動実行する。
- lint: clippy（`-D warnings`）。format: rustfmt。型検査はコンパイル自体（`cargo check --all-targets`）。

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. **TDD メタ情報をコード/テストに残さない**（Red/Green/サイクル番号/PR番号/計画書§参照を書かない）。
3. **テストの独立性を必ず保つ（最重要）**:
   - DB を触るテストは **`#[sqlx::test]` でテストごとに DB を作る**（またはトランザクションを開いて末尾でロールバック）。テスト間でレコードを共有しない。
   - `static` の可変状態（`OnceLock` / `LazyLock` / `once_cell::sync::Lazy` / `lazy_static!` / `static Mutex` / atomics）・環境変数（`std::env::set_var` はプロセス共有）をテスト間で共有しない。
   - `wiremock::MockServer` はテストごとに起動する（共有しない）。
   - `cargo test` は**既定で並列**。並列で壊れるテストは独立性が壊れている（`--test-threads=1` や `serial_test` で隠さない）。
4. **外部 I/O はトレイトで抽象化して注入する**: DB・HTTP クライアント・時刻（`Clock`）・乱数 を実装内で直接掴まない（`Utc::now()` / `SystemTime::now()` をドメインコードで呼ばない）。ジェネリクス（`S: InventoryRepo`）か `Arc<dyn InventoryRepo>` で受け取り、テストでは手書きフェイクを渡す。外部 HTTP は `wiremock` でスタブし**実通信はしない**。
5. **エラーは型で表現し `?` で伝搬する**: `thiserror` の enum を `domain` に置き、`anyhow` は bin の境界（`main.rs`）のみ。**非テストコードで `unwrap()` / `expect()` / `panic!` を使わない**（不変条件の表明として `expect("理由")` のみ可、理由を添える）。`Result` を `let _ =` で捨てない。
6. **`unsafe` を書かない**（必要なら停止条件#2 の設計判断として停止）。所有権・借用の問題を `clone()` で握りつぶさない。**レイヤーの依存方向を守る**（routes → services → repositories、domain は末端）。services が `axum::` / `http::` の型を知らない。repositories 以外に `sqlx::query` を書かない。
7. **Green は最小実装のみ**（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出は Refactor で。
8. **承認ゲートは Red 完了後と Commit 直前の2箇所**。Green / Refactor の間は自動遷移してよい。
9. **ターン粒度**: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
