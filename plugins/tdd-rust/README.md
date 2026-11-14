# Rust TDD スイート（`/tdd`）

Rust のサービス / ライブラリ（HTTP API サーバー・CLI・ライブラリクレート）向けの TDD ワークフロー自動化スキル群です。テストランナーは標準の `cargo test`（`#[test]` / `#[tokio::test]`）を前提にしています。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ `ledger-core`（Rust の台帳サービス。lib + bin 分割の単一クレート、axum + tokio + sqlx）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| ツールチェイン | Rust stable（edition 2021）/ tokio |
| クレート構成 | `src/main.rs` は起動のみ、`src/lib.rs` がモジュールを公開（ワークスペース対応） |
| Web フレームワーク | axum（actix-web / rocket は bootstrap が読み替え） |
| テスト | 標準 `#[test]` / `#[tokio::test]`。ユニットは `#[cfg(test)] mod tests`、統合は `tests/*.rs` |
| HTTP テスト | `tower::ServiceExt::oneshot`（`axum-test` 導入時はそれ） |
| モック | トレイト + 手書きフェイク構造体（`mockall` 導入時はそれ）。外部 HTTP は `wiremock` |
| DB | sqlx。テストは `#[sqlx::test]`（テストごとに DB 作成 + マイグレーション） |
| エラー | `thiserror` の enum（domain）。`anyhow` は `main.rs` のみ |
| パラメータ化 | `rstest`（導入時） |
| lint / hook | `cargo fmt` + `cargo clippy -- -D warnings` + pre-commit / lefthook（または cargo-husky の precommit-hook feature） |
| CI | GitHub Actions / CircleCI |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。自分のプロジェクトに合わせて書き換えてください（`/tdd-bootstrap` が自動生成します）。

## レイヤー構成を前提にした指示

このプラグインはレイヤードアーキテクチャを前提に、各フェーズが Rust 固有の観点で踏み込みます。

```
src/routes/       … HTTP 層。extractor でデコードし、IntoResponse でステータス変換するだけ
src/services/     … ビジネスロジック。axum / http の型を知らない
src/repositories/ … データアクセス。sqlx をここに閉じ込める
src/domain/       … 型・値オブジェクト・エラー enum。I/O を知らない（末端）
```

- Red はレイヤー別のテスト作法を指示（domain=`matches!` で variant 判定、service=トレイトに手書きフェイクを注入、route=`oneshot`、repository=`#[sqlx::test]`、外部 API=`wiremock`）。テストが要求する型・関数が未定義でコンパイルできないのが Rust の正規の Red であることを明記しています。
- Refactor は Rust 固有の観点で改善（レイヤー逆流の解消 / ループ内 `.await` の N+1 / 非テストコードの `unwrap()`・不要な `clone()`（`unsafe` の増加は Evac が検出し、導入は設計判断として停止）/ `Box<dyn Error>` → 型付き enum / `.await` 跨ぎの `MutexGuard`・async 内のブロッキング / newtype と enum による型駆動設計 / `#[allow]` の増加検出）
- Coverage Review は 400/401/403/404/409/422、外部 API 失敗、DB 制約違反、整数オーバーフロー・`None`/空コレクション経路・エラー variant ごとの返却まで含むマトリクスで抜けを埋めます
- Optimize は `rstest` パラメータ化・ビルダー抽出・`#[sqlx::test]` の fixtures 活用。ランダム順序が stable で使えない代わりに `--test-threads=1` と既定並列の双方・`cargo nextest`・反復実行で独立性を検証します

> 実際のモジュール名が違っても構いません。`tdd-bootstrap` が `src/` の実態（`handlers` / `usecases` / `infra` 等）やワークスペースのクレート分割を読み取って project-settings.md に反映します。

## 他プラグインとの使い分け

| 状況 | 使うもの |
|---|---|
| Rust のサービス / CLI / ライブラリ | `tdd-rust` |
| Go のバックエンド | `tdd-go` |
| TS/Node バックエンド | `tdd-node` |
| Vue + Vitest のフロントエンド | `tdd-frontend` |
| Rails + RSpec | `tdd-rails` |
| Python + pytest | `tdd-python` |
| Rails + Vue モノレポ | `tdd-monorepo` |
| 上記以外の言語 | `tdd-universal` |

1 リポジトリで有効化するプラグインは 1 つだけにしてください（同じ skill 名を提供するため）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-rust@general-skills
```

導入後、初回 `/tdd` 実行時に Phase 0 が `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します。手動なら `/tdd-bootstrap`（既存があれば確認）/ `/tdd-bootstrap --force`（上書き再生成）。

ワークスペース（`[workspace]`）にも対応します。bootstrap が `cargo metadata` でクレートを列挙し、対象クレートを選ばせたうえでコマンドに `-p {crate}` を付けて生成します（ワークスペース全体のコンパイル時間を避けるため）。

> CLI プロジェクト（clap）でも使えます。 bootstrap が検出し、HTTP 前提の route 層を `cli` / `commands` 層に、`oneshot` による契約テストを `assert_cmd` + `predicates` による stdout / exit code 検証に読み替えて設定を生成します。

> sqlx を使うリポでは `sqlx::query!` のコンパイル方式（`DATABASE_URL` を要求するか、`SQLX_OFFLINE=true` + `.sqlx/` で回すか）を bootstrap が確定します。Red/Green のコンパイル可否がこれで左右されるためです。

## スキル一覧

- [tdd](skills/tdd/SKILL.md) — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- [tdd-bootstrap](skills/tdd-bootstrap/SKILL.md) — 初回セットアップ。ワークスペース対応でクレート・Web/CLI・テスト補助クレート・sqlx のコンパイル方式・独立性の担保方法を走査し、不明点は対話で確認して設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- [tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md) — 生成済み `project-settings.md` を自然言語指示で調整（コマンドは `justfile` / `Makefile` / `Cargo.toml` と実際の `cargo` 実行で裏取り）。
- [tdd-red](skills/tdd-red/SKILL.md) — Red。レイヤー別の作法で失敗するテストを 1 本だけ書く（未定義によるコンパイルエラーも期待される Red として扱う）。
- [tdd-green](skills/tdd-green/SKILL.md) — Green。テストを通す最小実装（トレイト注入・型付きエラー・`?` 伝搬・レイヤー遵守。`unwrap()` / `clone()` で逃げない）。
- [tdd-refactor](skills/tdd-refactor/SKILL.md) — Refactor。レイヤー衛生 / N+1 / エラー処理 / 所有権と借用 / async の落とし穴 / 型駆動設計 をテスト緑のまま改善。
- [tdd-commit](skills/tdd-commit/SKILL.md) — Commit。fmt / clippy の pre-commit hook 準拠でコミット（マイグレーション・`.sqlx/`・`Cargo.lock`・スナップショットも含める）。
- [tdd-evacuator](skills/tdd-evacuator/SKILL.md) — リファクタ候補・テスト妥当性（`is_err()` 止まりのアサーション・`mockall` の呼び出し回数結合の指摘含む）に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用）。
- [tdd-coverage-review](skills/tdd-coverage-review/SKILL.md) — エンドポイント/サービス/エラー variant × テストカテゴリのマトリクスで不足を補完。
- [tdd-optimize](skills/tdd-optimize/SKILL.md) — テストの最適化（`rstest` 化・ビルダー抽出・fixtures）。`--test-threads=1` と並列・`nextest`・反復実行で独立性を検証。
- [tdd-workflow-update](skills/tdd-workflow-update/SKILL.md) — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — レイヤー構成・テストコマンド・不変条件・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# 自由テキストから計画 → 承認すれば同じセッションのまま Red へ進む
/tdd "台帳APIに残高チェックを追加し残高不足なら409を返す"

# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 中断したワークフローを別セッションで再開（既定はフェーズ停止）/ 一気通貫
/tdd tdd-20260613-101500
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。

1 つのワークフローは計画から最適化まで同じセッションで進めるのが基本です（計画時の分析や判断の経緯が次のフェーズに活きるため）。状態 JSON は中断・compact からの再開用に書き出されます。
