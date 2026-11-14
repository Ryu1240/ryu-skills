---
name: tdd-bootstrap
description: Rust プロジェクトのクレート構成（ワークスペース対応）・Web フレームワーク・テストツール（cargo test / nextest / sqlx / wiremock / rstest）・lint 設定を走査し、tdd-rust 用の .claude/skills/_shared-tdd/ を生成する（承認制）。/tdd の初回起動時に自動で呼ばれるほか、「TDD の設定を作り直して」と頼まれたときに使う。
argument-hint: [--force]
model: opus
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(cat:*)
  - Bash(cargo:*)
  - Bash(git check-ignore:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

Rust プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（停止）。部分修正だけなら `/tdd-project-settings-update` が適切と併せて案内。
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

### 2-1. 対象クレートの特定（ワークスペース対応・最初にやる）
ルートの `Cargo.toml` を Read する。
- `[package]` のみ → 単一クレート。リポジトリ直下が対象。
- `[workspace]` あり（`members` に複数クレート）→ `cargo metadata --no-deps --format-version 1` でクレート名とパスを列挙する。どのクレートを TDD の対象にするかは Step 3 でユーザーに選ばせる（`axum` / `actix-web` / `clap` を依存に持つクレート＝サービス/バイナリ側を第一候補として提示。レイヤーがクレート分割されている場合（`crates/domain` / `crates/api` 等）は「複数クレートに跨る」旨を記録し、`-p` を跨いで使う）。

### 2-2. スタック検出（対象クレート配下）

| 検出項目 | 確認方法 |
|---|---|
| クレート名 / edition | `Cargo.toml` の `[package] name` / `edition` |
| ツールチェイン | `rust-toolchain.toml`（channel）。無ければ stable |
| lib / bin 分割 | `src/lib.rs` の有無、`[[bin]]` / `src/bin/*.rs`。bin のみなら「`lib.rs` 分割を推奨」を提示（`tests/` から公開 API を叩けない） |
| Web フレームワーク | 依存に `axum` / `actix-web` / `rocket` / `warp` |
| async ランタイム | 依存に `tokio` / `async-std`（→ `#[tokio::test]` か `#[async_std::test]` か） |
| CLI | 依存に `clap` / `argh`（Web フレームワークが無ければ CLI プロジェクトと判定） |
| HTTP テスト | 依存に `tower`（`oneshot`）/ `axum-test` / `reqwest`（統合テストで実サーバー起動） |
| 外部 API スタブ | `wiremock` / `mockito` / `httpmock` |
| DB | `sqlx` / `diesel` / `sea-orm` + `migrations/` + `.sqlx/`（オフラインクエリデータ） + `DATABASE_URL` の供給元（`.env` / CI 設定） |
| テスト補助 | `rstest` / `mockall` / `proptest` / `quickcheck` / `insta` / `pretty_assertions` / `testcontainers` / `assert_cmd` / `serial_test` |
| エラー | `thiserror` / `anyhow` / `eyre` |
| serde / 検証 | `serde` / `serde_json` / `validator` / `garde` |
| テスト配置 | `Grep "#\[cfg\(test\)\]" src/` の件数と `Glob tests/*.rs` の件数 → inline 主体か `tests/` 主体か |
| フェイク / ビルダー | `Grep "impl .* for Fake"` / `src/testutil` / `tests/common/mod.rs` |
| lint / format | `clippy.toml` / `Cargo.toml` の `[lints]` / `rustfmt.toml` / `.rustfmt.toml` |
| タスクランナー | `justfile` / `Makefile` / `.cargo/config.toml` の `[alias]` にある test / lint / cov レシピ（最優先で採用） |
| nextest / llvm-cov | `cargo nextest --version` / `cargo llvm-cov --version`（失敗＝未導入） |
| pre-commit hook | `.pre-commit-config.yaml` / `lefthook.yml` / `cargo-husky`（`[dev-dependencies]`。既定 feature は pre-push で `cargo test`。`precommit-hook` + `run-cargo-fmt` / `run-cargo-clippy` feature か `user-hooks` のときだけ pre-commit で fmt / clippy が走る。feature を Read して確定） |
| CI | `.github/workflows/*.yml` / `.circleci/config.yml` / `.gitlab-ci.yml` |

### 2-3. 実コマンドの抽出（最優先）
`justfile` / `Makefile` / `.cargo/config.toml` の `[alias]` に実際のテスト・lint コマンドがあればそれを最優先で採用する（`just test` / `make lint` / `cargo t` など）。推測より実物。無ければテンプレの `cargo test -p {crate} ...` を採用し、`-p` のクレート名は 2-1 の結果に置換する。

### 2-4. レイヤー構成の抽出
`src/` 配下のモジュール（ディレクトリ / `mod.rs` / 同名 `.rs`）を列挙し、実際の層の名前を把握する（`routes` / `handlers` / `api` / `services` / `usecases` / `application` / `repositories` / `infra` / `db` / `domain` / `model` など）。ワークスペースでレイヤーがクレートに分かれていればクレート名を層名として使う。テンプレの `routes/services/repositories/domain` を押し付けず、実態の名前を使う。

### 2-5. 独立性の担保方法の抽出
既存テストを 1〜2 件 Read し、実際にどう独立性を保っているか観察する（`#[sqlx::test]` / `pool.begin()` + rollback / testcontainers / `MockDatabase` / `MockServer::start()` をテストごとに呼ぶ / `serial_test` の `#[serial]`）。`#[serial]` や `--test-threads=1` に依存している場合は「順序依存の兆候」として記録する。

### 2-6. 検出結果の提示
```
🔍 プロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| クレート名 | <name>（edition <2021>） |
| 対象クレート | <path>（ワークスペースなら選択結果） |
| lib / bin | lib + bin / bin のみ（lib.rs 分割を推奨） |
| Web フレームワーク | axum / actix-web / rocket / なし（CLI: clap） |
| async ランタイム | tokio / async-std / なし |
| HTTP テスト | tower oneshot / axum-test / reqwest / なし |
| 外部 API スタブ | wiremock / mockito / なし |
| DB | sqlx（.sqlx/ あり・DATABASE_URL は .env）/ diesel / sea-orm / なし |
| テスト補助 | rstest / mockall / proptest / insta / ... |
| エラー | thiserror + anyhow / ... |
| テスト配置 | inline #[cfg(test)]（X 件）/ tests/*.rs（Y 件） |
| レイヤー構成 | <実際のモジュール名> |
| 独立性の担保 | <既存テストから抽出 / 不明> |
| lint / format | clippy(-D warnings) / rustfmt / 未設定 |
| タスクランナー | just / make / cargo alias / なし |
| nextest / llvm-cov | あり / なし |
| pre-commit hook | cargo-husky / pre-commit / lefthook / なし |
| CI | GitHub Actions / CircleCI / なし |

❓ 未確定の項目: <列挙>
```

## Step 3: 対話ヒアリング（未確定項目のみ）

未確定・推定の項目だけ AskUserQuestion で聞く（1回最大4問。多ければ優先度順に分割）。

- 対象クレート（ワークスペース検出時）: 候補を選択肢に。
- CLI プロジェクトだった場合（clap あり・Web フレームワークなし）: HTTP 前提の節（route 層・`oneshot`・ステータスコード）を CLI 向け（`cli` / `commands` 層・`assert_cmd` + `predicates` で stdout/exit code を検証）に読み替えて生成する旨を確認する。
- sqlx のコンパイル方式（`sqlx::query!` 使用時）: `DATABASE_URL` を必要とする（テスト DB が起動している前提）か、`SQLX_OFFLINE=true` + `.sqlx/` で回すか。Red/Green のコンパイルがこれで左右されるので確定させる。`#[sqlx::test]` を使う場合は実行時にも `DATABASE_URL`（テスト DB への接続と CREATEDB 権限）が必要なので、接続先が用意されているかも確定させる。
- 独立性の担保方法（既存テストから抽出できなかった場合）: 「`#[sqlx::test]`（テストごとに DB）」「トランザクションでロールバック」「testcontainers」「DB を使わない（フェイクのみ）」「その他」から選択（複数可）。
- レイヤー構成の呼び方（`src/` の構成が想定と違う場合）: 実際の層名と依存方向を確認。
- プロジェクト固有の追加不変条件（任意。例: `unsafe` を一部モジュールで許容、`clone()` の許容範囲）。

> 推測で埋めない。分からない項目は「未導入」「未対応」と明記する。

## Step 4: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```
- `[y]` → Step 5 へ / `[e]` → 変更項目を聞き自由入力で上書き、再確認 / `[n]` → 中断（何も生成しない）

承認を得るまで Write しない（停止）。

## Step 5: ファイル生成

`.claude/skills/_shared-tdd/` を作成し、以下 4 ファイルを Write：

### 5-1. `project-settings.md`
plugin 同梱テンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/project-settings.md`）を Read し、検出＋ヒアリング結果で置換して Write：
- 見出しのクレート名を実プロジェクト名に。
- 構成とテストの表を検出値に（検出「なし」の行は削除 or 「未導入」と明記。推測で「あり」と書かない）。actix-web なら HTTP テスト行を `actix_web::test::init_service` + `call_service` に、`rstest` 未導入ならパラメータ化行を「タプル配列ループ」に。
- レイヤー構成を実際のモジュール名に置換（Step 2-4 の結果）。CLI なら `routes` を `cli` / `commands` に差し替え、HTTP 前提の記述を CLI 向けに書き直す。
- テスト実行コマンドを `-p {crate}` と実レシピ（`just test` 等）に合わせる。nextest / llvm-cov 未導入なら「未導入」と明記。sqlx のコンパイル方式（`DATABASE_URL` / `SQLX_OFFLINE`）を注記に書く。
- 不変条件: DB を使わないなら 3 の `#[sqlx::test]` 記述を調整（diesel なら `test_transaction`、sea-orm なら `MockDatabase`）、`thiserror` 未導入なら 5 を実際のエラー表現に合わせる、レイヤー名は 6 を実態に合わせる。

### 5-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱のテンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read して Write する（プロジェクト固有差分は project-settings.md に集約）。ただし 3 ファイルの見出しのリポ名（`— ledger-core`）は実プロジェクト名に置換し、`commit-convention.md` の「pre-commit hook あり」の段落は検出結果に合わせる（hook 無しなら「hook が無いため、コミット前に `just lint` 等を手動実行する」に書き換える）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-rust/skills/_shared-tdd/{filename}` を相対 Read する。

### 5-3. 生成内容の検証
生成した `project-settings.md` を Read し直し、テスト実行コマンドが実在するかを確認する:
- `-p {crate}` のクレート名が `cargo metadata --no-deps --format-version 1` の出力に存在する。
- `just` / `make` のレシピ名が `justfile` / `Makefile` に存在する（Read で確認）。
- `cargo nextest` / `cargo llvm-cov` を書いたなら `--version` が成功する。

## Step 6: ワークフロー状態の git 追跡設定（確認）

`/tdd` は実行中に `.claude/tdd-workflow/` へ状態ファイルを書き出す（`workflow-{id}.json` / `current-cycle.json` / `notion-context-*.json` / `optimization-report-*.md`）。これらは開発者ごとの進行中の作業状態であり、コミットするとレビューのノイズや複数人作業時のコンフリクトの原因になる。Notion 連携を使う場合はタスク本文のキャッシュも含まれる。

### 6-1. 現状確認
```bash
git check-ignore -q .claude/tdd-workflow/
```
終了コードで判定する（`echo` を繋がない。128 を「未無視」と誤認しないため）:
- 0（既に無視されている） → 何もせず次へ（サマリで「設定済み」と報告）。
- 1（無視されていない） → 6-2 へ。
- 128（git 管理下でない） → このステップをスキップ。

### 6-2. ユーザーに確認（AskUserQuestion・必須）
「TDD ワークフローの状態ファイルを git 管理から除外しますか？」として次を提示する:

- `.gitignore` に追加（推奨） — チーム全員に効く。`.gitignore` の変更自体はコミット対象になる。
- `.git/info/exclude` に追加 — このクローンのみ。`.gitignore` を変更したくない場合に。他メンバーには効かない。
- 除外しない — ワークフローの計画・進捗をチームで共有・レビューしたい場合。

### 6-3. 適用（承認された選択のみ）
対象ファイル（`.gitignore` または `.git/info/exclude`）を Read し、同じ行が既にあれば何もしない。無ければ末尾に追記して Write する:

```
# TDD ワークフローの進行状態（開発者ごとの一時ファイル）
.claude/tdd-workflow/
```

追記後に `git check-ignore -q .claude/tdd-workflow/` を再実行し、実際に効いていることを確認する。効いていなければ原因（別の否定パターン等）を提示する。

> ⚠️ `.claude/skills/_shared-tdd/` はチームで共有すべき設定なので ignore しない。このステップの対象は `.claude/tdd-workflow/` のみ。

## Step 7: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
対象: {crate} / ランナー: cargo test（+ nextest）/ レイヤー: {layers} / DB: {db}

- project-settings.md  (走査 + ヒアリングから生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)

次のステップ:
1. project-settings.md を確認（特にテスト実行コマンドの -p クレート名・sqlx のコンパイル方式・レイヤー構成）
2. /tdd "<タスク>" で TDD ワークフロー開始
```

> サマリにはワークフロー状態の git 追跡設定の結果（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- `Cargo.toml` が存在しない → 「ここは Rust プロジェクトではないようです。中断します」と提示して終了。あわせて汎用版 `tdd-universal` plugin の利用を案内する。
- CLI プロジェクト（clap あり・Web フレームワークなし）→ Step 3 で CLI 向けに読み替えて続行（HTTP 前提のテンプレをそのまま出力しない）。
- フロントエンド / WASM 寄りだった場合（`yew` / `leptos` / `dioxus` / `wasm-bindgen` が主体）→ 「この plugin はサービス/ライブラリ前提です。`tdd-universal` が適切かもしれません」と提示し、続行可否を確認。
- bin のみのクレート（`src/lib.rs` なし）→ 警告のうえ続行。`tests/` の統合テストは書けないため `test_location` を inline のみにし、`lib.rs` 分割を次ステップとして案内。
- テストが 1 件も無い → 警告のうえ、最小限の project-settings.md を生成（ユーザーが手動で埋める前提）。「最初のテストがこのリポの流儀を決める」ことを伝える。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしない。
