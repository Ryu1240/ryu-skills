# general-skills

Claude Code 向け **TDD ワークフロー自動化スキル**の plugin マーケットプレイスです。Plan → Red → Green → Refactor → Commit のサイクルを、状態を永続化しながらフェーズ単位で進め、最後に Coverage Review と Test Optimize まで回すオーケストレーションを提供します。

スタックごとに 8 つの plugin に分かれています（`tdd-monorepo` は複数スタック混在向け、`tdd-universal` はそれ以外のあらゆる言語向け）。

| Plugin | 対象スタック | スラッシュコマンド | ディレクトリ |
|---|---|---|---|
| **`tdd-rails`** | Ruby on Rails + RSpec（マルチテナント API） | `/tdd …` | [`plugins/tdd-rails/`](plugins/tdd-rails/) |
| **`tdd-python`** | Python + pytest + pydantic（CLI ツール） | `/tdd …` | [`plugins/tdd-python/`](plugins/tdd-python/) |
| **`tdd-frontend`** | Vue 3 + Vite + Vitest（SPA フロントエンド） | `/tdd …` | [`plugins/tdd-frontend/`](plugins/tdd-frontend/) |
| **`tdd-node`** | TypeScript + Node.js バックエンド（Vitest） | `/tdd …` | [`plugins/tdd-node/`](plugins/tdd-node/) |
| **`tdd-go`** | Go バックエンド（標準 `testing` + テーブル駆動 + `httptest`） | `/tdd …` | [`plugins/tdd-go/`](plugins/tdd-go/) |
| **`tdd-rust`** | Rust（`cargo test` + axum + sqlx。ワークスペース対応） | `/tdd …` | [`plugins/tdd-rust/`](plugins/tdd-rust/) |
| **`tdd-monorepo`** | Rails backend + Vue frontend のモノレポ（エコシステム自動判定） | `/tdd …` | [`plugins/tdd-monorepo/`](plugins/tdd-monorepo/) |
| **`tdd-universal`** | **上記以外のあらゆる言語**（Java / Kotlin / PHP / C# / Elixir / Swift …）。対話型 bootstrap で設定を構築 | `/tdd …` | [`plugins/tdd-universal/`](plugins/tdd-universal/) |
| **`pr-tour`** | 言語非依存。**PR をエントリーポイントから実行順にツアー形式で解説**（TDD ではありません） | `/pr-tour …` | [`plugins/pr-tour/`](plugins/pr-tour/) |

> 専用 plugin（`tdd-universal` 以外）の skill はプロジェクト固有の前提を `skills/_shared-tdd/project-settings.md` に集約しています。サンプルとして架空リポジトリ **`sales-hub`**（Rails）/ **`taskcli`**（Python）/ **`storefront`**（フロントエンド）/ **`order-api`**（Node バックエンド）/ **`shipment-api`**（Go）/ **`ledger-core`**（Rust）/ **`retail-hub`**（モノレポ）を題材に記述してあるので、自分のプロジェクトに合わせて `project-settings.md` を書き換えて使ってください（`tdd-bootstrap` が自動生成します）。
>
> **`tdd-universal` は言語固有の知識をスキル本体に持たず**、すべて `project-settings.md` から読みます。未対応言語では bootstrap が走査＋**対話ヒアリング**で設定を構築するため、マニフェストが検出できない環境でも成立します。

## インストール

Claude Code の plugin マーケットプレイスとして登録し、使いたい plugin をインストールします。

```text
# 1. マーケットプレイスを追加（1 度だけ）
/plugin marketplace add Ryu1240/ryu-skills

# 2. 使いたい plugin を導入
/plugin install tdd-rails@general-skills      # Rails プロジェクト用
/plugin install tdd-python@general-skills     # Python プロジェクト用
/plugin install tdd-frontend@general-skills   # Vue/Vite フロントエンド用
/plugin install tdd-node@general-skills       # TS/Node バックエンド用
/plugin install tdd-go@general-skills         # Go バックエンド用
/plugin install tdd-rust@general-skills       # Rust 用
/plugin install tdd-monorepo@general-skills   # Rails+Vue モノレポ用
/plugin install tdd-universal@general-skills  # それ以外のあらゆる言語用
/plugin install pr-tour@general-skills        # PR をツアー形式で解説（TDD とは独立。併用可）
```

各 plugin は同じ skill 名（`/tdd`, `/tdd-red`, `/tdd-green`, …）を提供します。**プロジェクトごとに 1 つだけを `.claude/settings.json` で有効化するのが推奨運用**です。選び方:

- 単体スタック（Rails / Python / Vue / TS・Node バックエンド / Go / Rust）→ 対応する専用 plugin
- **Rails+Vue のモノレポ** → `tdd-monorepo`（1 スキルセットで backend/frontend をエコシステム自動判定するため、単体プラグインの同時有効化＝skill 名衝突を避けられます）
- **上記以外の言語** → `tdd-universal`（bootstrap が対話でスタックを聞き取って設定を構築）

複数を同時に有効化すると skill 名が衝突するので避けてください。

導入後はオーケストレーターを起動するだけで計画から実装までを進められます。初回起動時はプロジェクト固有の TDD 設定が無いことを検出すると、`tdd-bootstrap` が呼び出されてプロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md などを生成します（承認制）。

```text
# 初回（または .claude/skills/_shared-tdd/ が無いとき）
/tdd "Lead に status カラムを追加し API で返す"
# → 走査結果が提示されるので承認すると _shared-tdd/ が生成され、その後ワークフロー開始

# 手動で再生成する場合
/tdd-bootstrap          # 既存があれば確認 / 無ければ生成
/tdd-bootstrap --force  # 上書き再生成
```

## Plugin 一覧

### `tdd-rails`（`/tdd`）

Ruby on Rails + RSpec バックエンド向け。マルチテナント scope・OpenAPI 契約検証（Committee）・FactoryBot・Bullet（N+1）・Pundit・husky/lint-staged を前提にしています。詳細は [`plugins/tdd-rails/README.md`](plugins/tdd-rails/README.md) を参照。

- **[tdd](plugins/tdd-rails/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-rails/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。Rails プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-rails/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-rails/skills/tdd-red/SKILL.md)** — Red。失敗するテストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-green](plugins/tdd-rails/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装。
- **[tdd-refactor](plugins/tdd-rails/skills/tdd-refactor/SKILL.md)** — Refactor。N+1/dependent/サービス抽出などをテスト緑のまま改善。
- **[tdd-commit](plugins/tdd-rails/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-rails/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-rails/skills/tdd-coverage-review/SKILL.md)** — endpoint/model × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-rails/skills/tdd-optimize/SKILL.md)** — RSpec テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-rails/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-python`（`/tdd`）

Python + pytest + pydantic 向け。`StrictModel`（`extra="forbid"`）・コマンド別モジュール・docker compose 経由のテスト実行を前提にしています。詳細は [`plugins/tdd-python/README.md`](plugins/tdd-python/README.md) を参照。

- **[tdd](plugins/tdd-python/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-python/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。Python プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-python/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-python/skills/tdd-red/SKILL.md)** — Red。失敗する pytest テストを 1 本だけ書く（schema roundtrip / logic / validation）。
- **[tdd-green](plugins/tdd-python/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（`schemas/` の pydantic モデル等）。
- **[tdd-refactor](plugins/tdd-python/skills/tdd-refactor/SKILL.md)** — Refactor。挙動を変えずにコード品質を改善。
- **[tdd-commit](plugins/tdd-python/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分をコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-python/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・pytest テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-python/skills/tdd-coverage-review/SKILL.md)** — pydantic モデル/関数 × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-coverage-overlap](plugins/tdd-python/skills/tdd-coverage-overlap/SKILL.md)** — pytest-cov の coverage-context で意味的なテスト重複を検出（削除/統合候補を提示）。
- **[tdd-optimize](plugins/tdd-python/skills/tdd-optimize/SKILL.md)** — pytest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-python/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-frontend`（`/tdd`）

Vue 3 + Vite + Vitest フロントエンド向け。Vue Testing Library（role 取得）・MSW（API モック）・Pinia・ESLint/Prettier・husky/lint-staged を前提にしています。詳細は [`plugins/tdd-frontend/README.md`](plugins/tdd-frontend/README.md) を参照。

- **[tdd](plugins/tdd-frontend/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-frontend/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。フロントエンドプロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-frontend/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-frontend/skills/tdd-red/SKILL.md)** — Red。失敗する Vitest テストを 1 本だけ書く（component/composable/store/util）。
- **[tdd-green](plugins/tdd-frontend/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（Composition API・MSW handler 等）。
- **[tdd-refactor](plugins/tdd-frontend/skills/tdd-refactor/SKILL.md)** — Refactor。composable 抽出/コンポーネント分割/再レンダリング衛生などをテスト緑のまま改善。
- **[tdd-commit](plugins/tdd-frontend/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-frontend/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-frontend/skills/tdd-coverage-review/SKILL.md)** — component/composable × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-frontend/skills/tdd-optimize/SKILL.md)** — Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-frontend/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-node`（`/tdd`）

TypeScript + Node.js バックエンド向け（Vitest）。**レイヤードアーキテクチャ**（routes → services → repositories → schemas）を前提に、DI での依存差し替え・Zod による境界検証・Supertest・トランザクションロールバックまで踏み込んで指示します。Refactor では**レイヤー逆流 / ループ内 await の N+1 / `await` 漏れ / `any`・`as` の混入**を検出します。モノレポ（workspaces / turborepo / nx）と Jest にも bootstrap が対応。詳細は [`plugins/tdd-node/README.md`](plugins/tdd-node/README.md) を参照。

- **[tdd](plugins/tdd-node/skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括。
- **[tdd-bootstrap](plugins/tdd-node/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。パッケージ・ランナー・レイヤー構成・独立性の担保方法を走査し、不明点は対話で確認（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-node/skills/tdd-project-settings-update/SKILL.md)** — 生成済み設定を自然言語で調整（コマンドは `package.json` の scripts で裏取り）。
- **[tdd-red](plugins/tdd-node/skills/tdd-red/SKILL.md)** — Red。レイヤー別の作法（schema/service/route/repository）で失敗する Vitest テストを 1 本だけ書く。
- **[tdd-green](plugins/tdd-node/skills/tdd-green/SKILL.md)** — Green。最小実装（DI・Zod 検証・エラークラス・レイヤー遵守）。
- **[tdd-refactor](plugins/tdd-node/skills/tdd-refactor/SKILL.md)** — Refactor。レイヤー衛生 / N+1 / 非同期の落とし穴 / エラー処理 / 型の健全性。
- **[tdd-commit](plugins/tdd-node/skills/tdd-commit/SKILL.md)** — Commit。husky/lint-staged 準拠でコミット（マイグレーションも含める）。
- **[tdd-evacuator](plugins/tdd-node/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性（過剰モックの指摘含む）・サイクル境界の追加テスト提案（読み取り専用）。
- **[tdd-coverage-review](plugins/tdd-node/skills/tdd-coverage-review/SKILL.md)** — 400/401/403/404/409・外部API失敗・DB制約・冪等性まで含むマトリクスで補完。
- **[tdd-optimize](plugins/tdd-node/skills/tdd-optimize/SKILL.md)** — `it.each` 化・セットアップ巻き上げ。`--sequence.shuffle` と並列実行で独立性を検証。
- **[tdd-workflow-update](plugins/tdd-node/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-go`（`/tdd`）

Go バックエンド向け（標準 `testing`）。**`cmd/` + `internal/` のレイヤー構成**（handler → service → repository → domain）を前提に、利用側で定義する小さなインターフェイスと手書きフェイクによる DI・テーブル駆動 + `t.Run` サブテスト・`net/http/httptest`・トランザクションロールバック（`t.Cleanup`）まで踏み込んで指示します。Refactor では**レイヤー逆流 / ループ内クエリの N+1 / `%w` ラップ漏れ・エラー握り潰し / goroutine リーク・`ctx` 伝搬漏れ / インターフェイス肥大**を検出し、Optimize は `-shuffle=on` と `-race` で独立性を検証します。マルチモジュール（`go.work`）と CLI（cobra）にも bootstrap が対応。詳細は [`plugins/tdd-go/README.md`](plugins/tdd-go/README.md) を参照。

- **[tdd](plugins/tdd-go/skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括。
- **[tdd-bootstrap](plugins/tdd-go/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。`go.mod`/`go.work`・ルーター・アサーション/モックライブラリ・DB と独立性の担保方法・`Makefile` ターゲットを走査し、不明点は対話で確認（承認制）。あわせて `.claude/tdd-workflow/` を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-go/skills/tdd-project-settings-update/SKILL.md)** — 生成済み設定を自然言語で調整（コマンドは `Makefile` / 実際の `go test` で裏取り）。
- **[tdd-red](plugins/tdd-go/skills/tdd-red/SKILL.md)** — Red。レイヤー別の作法（domain/service/handler/repository）でテーブル駆動の失敗するテストを 1 本だけ書く。
- **[tdd-green](plugins/tdd-go/skills/tdd-green/SKILL.md)** — Green。最小実装（インターフェイス注入・`%w` ラップ・`ctx` 伝搬・レイヤー遵守）。
- **[tdd-refactor](plugins/tdd-go/skills/tdd-refactor/SKILL.md)** — Refactor。レイヤー衛生 / N+1 / エラー処理 / 並行性と context / インターフェイスと型 / `gofmt`・`go vet`・`golangci-lint`。
- **[tdd-commit](plugins/tdd-go/skills/tdd-commit/SKILL.md)** — Commit。pre-commit hook 準拠でコミット（マイグレーション・`go generate` 生成物・`go.mod`/`go.sum` も含める）。
- **[tdd-evacuator](plugins/tdd-go/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性・サイクル境界の追加テスト提案（読み取り専用）。
- **[tdd-coverage-review](plugins/tdd-go/skills/tdd-coverage-review/SKILL.md)** — 400/401/403/404/409・外部 API 失敗・DB 制約・sentinel error・context キャンセルまで含むマトリクスで補完。
- **[tdd-optimize](plugins/tdd-go/skills/tdd-optimize/SKILL.md)** — テーブル駆動化・`t.Helper()` ヘルパ抽出・`t.Parallel()`。`-shuffle=on` / `-race` / `-count=3` で独立性を検証。
- **[tdd-workflow-update](plugins/tdd-go/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-rust`（`/tdd`）

Rust 向け（`cargo test`）。**lib + bin 分割のレイヤー構成**（routes → services → repositories → domain）を前提に、トレイト + 手書きフェイクによる DI・`#[cfg(test)] mod tests` / `tests/` の使い分け・axum の `oneshot`・`#[sqlx::test]` によるテスト毎の DB 分離・`thiserror` の型付きエラーまで踏み込んで指示します。Refactor では**レイヤー逆流 / N+1 / 非テストコードの `unwrap()` / 不要な `clone()` / async 内のブロッキング呼び出し・`MutexGuard` の `.await` 跨ぎ / `#[allow(clippy)]` の増加**を検出します。stable ではテストのランダム順序が使えないため、Optimize は `--test-threads=1` と既定並列の両方・`cargo nextest` で独立性を検証します。ワークスペース（`[workspace]`）と CLI（clap）にも bootstrap が対応。詳細は [`plugins/tdd-rust/README.md`](plugins/tdd-rust/README.md) を参照。

- **[tdd](plugins/tdd-rust/skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括。
- **[tdd-bootstrap](plugins/tdd-rust/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。`Cargo.toml`（ワークスペース）・Web フレームワーク・テスト補助クレート・DB と独立性の担保方法・`justfile`/`Makefile` レシピを走査し、不明点は対話で確認（承認制）。あわせて `.claude/tdd-workflow/` を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-rust/skills/tdd-project-settings-update/SKILL.md)** — 生成済み設定を自然言語で調整（コマンドは `justfile`/`Makefile` / 実際の `cargo test` で裏取り）。
- **[tdd-red](plugins/tdd-rust/skills/tdd-red/SKILL.md)** — Red。レイヤー別の作法（domain/service/route/repository）で失敗するテストを 1 本だけ書く。型未定義によるコンパイルエラーも期待される失敗として扱う。
- **[tdd-green](plugins/tdd-rust/skills/tdd-green/SKILL.md)** — Green。最小実装（トレイト注入・`?` 伝搬・`From` 実装・レイヤー遵守。`clone()` で借用エラーを握りつぶさない）。
- **[tdd-refactor](plugins/tdd-rust/skills/tdd-refactor/SKILL.md)** — Refactor。レイヤー衛生 / N+1 / エラー処理 / 所有権と借用 / async の落とし穴 / 型駆動設計 / `cargo fmt`・`clippy -D warnings`。
- **[tdd-commit](plugins/tdd-rust/skills/tdd-commit/SKILL.md)** — Commit。pre-commit hook 準拠でコミット（マイグレーション・`.sqlx/`・`Cargo.lock`・`insta` スナップショットも含める）。
- **[tdd-evacuator](plugins/tdd-rust/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性・サイクル境界の追加テスト提案（読み取り専用）。
- **[tdd-coverage-review](plugins/tdd-rust/skills/tdd-coverage-review/SKILL.md)** — 400/401/403/404/409/422・外部 API 失敗・DB 制約・エラー variant・整数境界・`None`/空コレクションまで含むマトリクスで補完。
- **[tdd-optimize](plugins/tdd-rust/skills/tdd-optimize/SKILL.md)** — `rstest` パラメータ化・ヘルパ抽出・`#[sqlx::test]` fixtures。`--exact` 単独実行 / `--test-threads=1` / `cargo nextest` で独立性を検証。
- **[tdd-workflow-update](plugins/tdd-rust/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-monorepo`（`/tdd`）

Rails/RSpec backend + Vue/Vitest frontend の**モノレポ**向け。1 スキルセットで `ecosystem`（backend/frontend）を自動判定して各フェーズを分岐します。単体プラグインを複数同時有効化する際の skill 名衝突を避けるため、モノレポでは**これ 1 つだけ**を有効化します。詳細は [`plugins/tdd-monorepo/README.md`](plugins/tdd-monorepo/README.md) を参照。

- **[tdd](plugins/tdd-monorepo/skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 で backend/frontend を自動判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](plugins/tdd-monorepo/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。モノレポの backend/frontend パッケージを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-monorepo/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-monorepo/skills/tdd-red/SKILL.md)** — Red。ecosystem に応じて失敗する RSpec / Vitest テストを 1 本だけ書く。
- **[tdd-green](plugins/tdd-monorepo/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（Rails or Vue/TS）。
- **[tdd-refactor](plugins/tdd-monorepo/skills/tdd-refactor/SKILL.md)** — Refactor。backend=N+1/dependent/サービス抽出、frontend=composable 抽出/コンポーネント分割。
- **[tdd-commit](plugins/tdd-monorepo/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-monorepo/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-monorepo/skills/tdd-coverage-review/SKILL.md)** — ecosystem 別の（対象 × テストカテゴリ）マトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-monorepo/skills/tdd-optimize/SKILL.md)** — RSpec / Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-monorepo/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新（`ecosystem` は保護）。

### `tdd-universal`（`/tdd`）

**専用 plugin が無いあらゆる言語**向け（Java / Kotlin / PHP / C# / Elixir / Swift / Dart / Scala / Ruby(非Rails) / React …）。スキル本体は言語知識を持たず、テストコマンド・配置・独立性の担保方法・言語固有イディオムをすべて `project-settings.md` から読みます。加えて不変条件に「**既存テストの慣習を踏襲する**」を据えることで、言語非依存のまま各リポの流儀に適応します。詳細は [`plugins/tdd-universal/README.md`](plugins/tdd-universal/README.md) を参照。

- **[tdd](plugins/tdd-universal/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括。Phase 0 で未設定（`{{...}}` の残存）を検出し bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-universal/skills/tdd-bootstrap/SKILL.md)** — **対話型**初回セットアップ。言語検出表とランナー別コマンド表で走査し、検出できない項目はヒアリングして設定を構築（承認制）。マニフェスト検出ゼロでも対話だけで成立。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](plugins/tdd-universal/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整（コマンドは実在を裏取りしてから提案）。
- **[tdd-red](plugins/tdd-universal/skills/tdd-red/SKILL.md)** — Red。既存テストの慣習を抽出してから失敗するテストを 1 本だけ書く。
- **[tdd-green](plugins/tdd-universal/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（既存実装の慣習も踏襲）。
- **[tdd-refactor](plugins/tdd-universal/skills/tdd-refactor/SKILL.md)** — Refactor。重複除去・命名・責務分解・データアクセス効率・エラー処理の一貫性・lint。
- **[tdd-commit](plugins/tdd-universal/skills/tdd-commit/SKILL.md)** — Commit。pre-commit hook 準拠でコミット（既存 `git log` の規約を優先）。
- **[tdd-evacuator](plugins/tdd-universal/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用）。
- **[tdd-coverage-review](plugins/tdd-universal/skills/tdd-coverage-review/SKILL.md)** — 公開インターフェイス × カテゴリ（境界値/空/異常系/外部依存失敗/認可/契約/冪等性）で不足を補完。
- **[tdd-optimize](plugins/tdd-universal/skills/tdd-optimize/SKILL.md)** — テスト最適化（セットアップ巻き上げ・パラメータ化・アサーション集約）。検証できなかった項目は明記。
- **[tdd-workflow-update](plugins/tdd-universal/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `pr-tour`（`/pr-tour`）

TDD 系とは独立した、**PR を理解するための**スキルです（skill 名が衝突しないので TDD 系プラグインと同時に有効化できます）。差分の外にある起点（ルーティング・画面・cron・ジョブの起動元）を探し、起点から差分を貫く案内プランを Markdown と視覚ビューで保存・公開してから、1 ターン 1 ステップで「見る場所 / ここは何をしている場所か / 変更点 / なぜ / 対応するテスト / 次へのつながり」を解説します。詳細は [`plugins/pr-tour/README.md`](plugins/pr-tour/README.md) を参照。

> [!WARNING]
> 公式マーケットプレースの **`code-review` プラグイン（別物）** は PR に `gh pr comment` で公開コメントを投稿します。pr-tour はレビュー結果を手元に返す effort 付きの `code-review` スキルを併走させる前提で、判別できないときは起動しませんが、公式プラグインを入れている環境ではツアー前に無効化を推奨します。

- **[pr-tour](plugins/pr-tour/skills/pr-tour/SKILL.md)** — 本体。対象の解決 → 全体把握 → 起点の探索 → テスト対応 → プラン承認 → 1 ステップずつ解説 → 完了。effort 付き `code-review` があればバックグラウンドで並走させ、指摘を該当ステップに添える。
- **[references/](plugins/pr-tour/skills/pr-tour/references/)** — 起点の辿り方、プランの書式、code-review の並走、テストの実測、保存先、レビューコメント下書き。
- **[scripts/](plugins/pr-tour/skills/pr-tour/scripts/)** — base/head の fetch と変更ファイルのレイヤー分類、プランと視覚ビューの同時更新、図解用 SVG ヘルパー。

## 設計のポイント

- **1 サイクル = 1 テスト = 1 コミット**。粒度を固定し、TDD メタ情報はコードに残しません。
- **状態の永続化**: 進行状態を `.claude/tdd-workflow/` の JSON に保存し、いつでも中断・再開できます。
- **承認ゲートは 2 箇所**（Red 完了後・Commit 直前）。既定はフェーズ停止、`--auto` で一気通貫。
- **共通契約は単一情報源**: パス・テストコマンド・不変条件・状態スキーマ・コミット規約を `_shared-tdd/` にまとめ、全 skill が参照します。

## このリポジトリで開発する場合

クローンしたら、まず同梱の git hook を有効にしてください。

```text
git config core.hooksPath .githooks
```

pre-commit で次の 2 点を検査します。

- **作者メールが GitHub の noreply アドレスか**（`<ID>+<ユーザー名>@users.noreply.github.com`）。個人のアドレスを公開履歴に残さないためです。
- **別リポジトリ特有の情報が混ざっていないか**（[`scripts/check-foreign-info.sh`](scripts/check-foreign-info.sh)）。スキルとサンプルは架空の名前（`sales-hub` / `shipment-api` など）で書く前提なので、オーナーの他リポジトリ名・ローカルの絶対パス・個人のメール・実在の Notion ページを検出したらコミットを止めます。
  - 他リポジトリ名の一覧は `gh repo list` から取得して `.git/info/` に 1 日キャッシュします。一覧そのものをリポジトリに置かないためです。
  - 社名などの追加の禁止語は `.git/info/foreign-denylist`、誤検知の除外は `.git/info/foreign-allowlist` に 1 行 1 つの正規表現で書きます（どちらも追跡されません）。
  - `scripts/check-foreign-info.sh --all` で、追跡中の全ファイルをまとめて検査できます。
