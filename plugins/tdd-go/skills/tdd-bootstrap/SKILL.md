---
name: tdd-bootstrap
description: Go プロジェクトのモジュール構成・レイヤー・テストの流儀・ツールを走査し、tdd-go 用の .claude/skills/_shared-tdd/ を生成する（承認制）。/tdd の初回起動時に自動で呼ばれるほか、「TDD の設定を作り直して」と頼まれたときに使う。
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
  - Bash(go:*)
  - Bash(git check-ignore:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

Go プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（停止）。部分修正だけなら `/tdd-project-settings-update` が適切と併せて案内。
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

### 2-1. 対象モジュールの特定（マルチモジュール対応・最初にやる）
`Glob **/go.mod`（`vendor/` 除外）と `go.work` の有無で候補を列挙する。
- `go.mod` が1つだけ → リポジトリ直下が対象。
- 複数（`go.work` あり / サブディレクトリに `go.mod`） → `go.work` の `use` ディレクティブを確認。どのモジュールを TDD の対象にするかは Step 3 でユーザーに選ばせる（HTTP サーバーらしい候補＝`cmd/*/main.go` を持ち、chi / gin / echo / net/http を import しているものを第一候補として提示）。
- `go version` で Go のバージョン、`go list ./...`（対象モジュール内）でパッケージ一覧を取得する。

### 2-2. スタック検出（対象モジュール配下）

| 検出項目 | 確認方法 |
|---|---|
| モジュール名 / Go バージョン | `go.mod` の `module` / `go` ディレクティブ（`go version` で実行環境も確認） |
| プロジェクト種別 | `cmd/*/main.go` を Read。`net/http` / ルーターの起動なら HTTP サーバー、`cobra` / `urfave/cli` / `flag` 主体なら CLI、`lambda` / `pubsub` ならワーカー |
| ルーター | `go.mod` の require に `go-chi/chi` / `gin-gonic/gin` / `labstack/echo` / `gofiber/fiber` / `gorilla/mux`。無ければ標準 `net/http` ServeMux |
| アサーション | `google/go-cmp` / `stretchr/testify` / 標準のみ（既存 `_test.go` を Grep して実際の使用を確認） |
| モック | `golang/mock` or `uber-go/mock`（gomock）/ `vektra/mockery` / `matryer/moq` の `//go:generate` 行。無ければ手書きフェイク（`internal/testutil/` や `_test.go` 内の `type fakeXxx struct`） |
| DB / ORM | `database/sql` + `sqlc.yaml` / `jmoiron/sqlx` / `jackc/pgx` / `gorm.io/gorm` / `entgo.io/ent` |
| マイグレーション | `golang-migrate/migrate` / `pressly/goose` / `ariga.io/atlas` + ディレクトリ（`db/migrations/` / `migrations/`） |
| 外部 API スタブ | 既存テストの `httptest.NewServer` / `h2non/gock` / `jarcoal/httpmock` |
| 独立性の担保 | 既存テストの `tx.Rollback` / `t.Cleanup` / `testcontainers-go` / `ory/dockertest` / `DATA-DOG/go-sqlmock` / truncate ヘルパ |
| integration タグ | `Grep "//go:build integration"` の有無（あれば DB テストは `-tags=integration` が要る） |
| テスト配置 | `Glob **/*_test.go` で件数と、`package foo` / `package foo_test` の比率（`Grep "^package .*_test$"`） |
| テストデータ | `Glob **/testdata/**` / `internal/testutil/**` / `**/factory/**` |
| lint / format | `.golangci.yml` / `.golangci.yaml`、`goimports` / `gofumpt` の使用（Makefile や CI を Grep） |
| ビルドスクリプト | `Makefile` / `justfile` / `Taskfile.yml` / `mage` の `test` / `lint` / `cover` ターゲット |
| pre-commit hook | `lefthook.yml` / `.pre-commit-config.yaml` / `.husky/` / `.git/hooks/pre-commit` |
| CI | `.github/workflows/*.yml` / `.circleci/config.yml` / `.gitlab-ci.yml` |

### 2-3. 実コマンドの抽出（最優先）
`Makefile` / `justfile` / `Taskfile.yml` に実際の `test` / `lint` / `cover` ターゲットがあればそれを最優先で採用する（`make test` が `-race -tags=integration` を付けている等、リポ固有のフラグを取りこぼさないため）。無ければ CI 設定の `run:` 行から実コマンドを拾う。推測より実物。

### 2-4. レイヤー構成の抽出
`internal/` と `pkg/` 配下のディレクトリを列挙し、実際の層の名前を把握する（`handler` / `controller` / `api` / `transport` / `service` / `usecase` / `app` / `repository` / `store` / `infra` / `domain` / `model` / `entity` など）。テンプレの `handler/service/repository/domain` を押し付けず、実態の名前を使う。フラットな構成（`internal/` 直下にパッケージが並ぶ）ならそのまま記録する。

### 2-5. 独立性の担保方法の抽出
既存テストのセットアップを 1〜2 件 Read し、実際にどう独立性を保っているか観察する（トランザクション + `t.Cleanup(func() { _ = tx.Rollback() })` / truncate / testcontainers-go / dockertest / sqlmock / `TestMain` での DB 準備 / `t.TempDir()`）。`TestMain` がある場合はその中身も Read する（グローバル共有の有無）。

### 2-6. 検出結果の提示
```
🔍 プロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| モジュール名 | <module path>（Go <version>） |
| 対象モジュール | <path>（マルチモジュールなら選択結果） |
| プロジェクト種別 | HTTP サーバー / CLI / ワーカー |
| ルーター | chi / gin / echo / 標準 net/http / なし |
| アサーション | go-cmp / testify / 標準 |
| モック | 手書きフェイク / gomock / mockery / moq |
| DB / ORM | sqlc / sqlx / pgx / GORM / ent / なし |
| マイグレーション | golang-migrate / goose / atlas / なし |
| 独立性の担保 | <既存テストから抽出 / 不明> |
| integration タグ | あり（-tags=integration 必須）/ なし |
| テスト配置 | co-located *_test.go（X 件。package foo_test: Y 件） |
| レイヤー構成 | <実際のディレクトリ名と依存方向> |
| test/lint コマンド | make test / make lint（Makefile）/ 直接 go test |
| lint | golangci-lint（.golangci.yml）/ go vet のみ |
| pre-commit hook | lefthook / pre-commit / なし |
| CI | GitHub Actions / CircleCI / なし |

❓ 未確定の項目: <列挙>
```

## Step 3: 対話ヒアリング（未確定項目のみ）

未確定・推定の項目だけ AskUserQuestion で聞く（1回最大4問。多ければ優先度順に分割）。

- 対象モジュール（マルチモジュール検出時）: 候補を選択肢に。
- プロジェクト種別が CLI だった場合: HTTP 前提の節（handler 層・`httptest`・ステータスコード）を CLI 向けに読み替えて生成する旨を確認する。読み替え内容: レイヤーは `cmd/` + `internal/cli/`（コマンド定義）→ `internal/app` or `service`（ロジック）、テストは `cmd.Execute()` / `RunE` を `bytes.Buffer` で stdout/stderr を捕捉して検証、終了コードとエラーメッセージを契約とみなす。
- 独立性の担保方法（既存テストから抽出できなかった場合）: 「トランザクション + `t.Cleanup(func() { _ = tx.Rollback() })`」「各ケースで truncate」「testcontainers-go / dockertest」「sqlmock（DB を使わない）」「DB を使わない（フェイクのみ）」「その他」から選択（複数可）。
- テストパッケージの流儀（`package foo` と `package foo_test` が混在する場合）: 新規テストをどちらで書くか確認。
- アサーションライブラリ（go-cmp と testify が混在する場合）: 新規テストで使う方を確認。
- レイヤー構成の呼び方（`internal/` の構成が想定と違う場合）: 実際の層名と依存方向を確認。
- プロジェクト固有の追加不変条件（任意）。

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
- 見出しのリポ名を実モジュール名（`go.mod` の `module` 末尾）に。
- 構成とテストの表を検出値に（検出「なし」の行は削除 or 「未導入」と明記。推測で「あり」と書かない）。アサーション / モック / テストパッケージの流儀は Step 3 の確定値。
- レイヤー構成を実際のディレクトリ名に置換（Step 2-4 の結果）。CLI なら CLI 向けの構成に差し替え。
- テスト実行コマンドを実物に合わせる。`Makefile` のターゲットがあれば `make test` 系を先頭に置き、その下に等価な `go test` 直接実行を残す（単一ケース `-run` 実行は Makefile に無いことが多いので `go test` 直接で書く）。マルチモジュールなら `cd {module_root} && ...` を付ける。integration タグがあれば DB テストのコマンドに `-tags=integration` を付ける。
- 不変条件: DB を使わないなら 3 のロールバック記述を調整、レイヤー名は 6 を実態に合わせる。CLI なら 6 の「handler → service → repository」を CLI の依存方向に書き換える。

### 5-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱のテンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read して Write する（プロジェクト固有差分は project-settings.md に集約）。ただし 3 ファイルの見出しのリポ名（`— shipment-api`）は実プロジェクト名に置換し、`commit-convention.md` の「pre-commit hook あり」の段落は検出結果に合わせる（hook 無しなら「hook が無いため、コミット前に `make lint` 等を手動実行する」に書き換える）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-go/skills/_shared-tdd/{filename}` を相対 Read する。

### 5-3. 生成内容の検証
生成した `project-settings.md` を Read し直し、テスト実行コマンドが実在するかを確認する：`Makefile` のターゲット名と整合するか、`go list ./...` の出力にコマンド中のパッケージパスが含まれるか。可能なら `go vet ./...` を実行し、`_test.go` を含めて型検査が通ることを確認する（`go test -run '^$'` は `TestMain` を実行してしまい DB 接続等が走るので使わない）。

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
対象: {module_root} / 種別: {HTTP|CLI} / アサーション: {assert_lib} / レイヤー: {layers}

- project-settings.md  (走査 + ヒアリングから生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)

次のステップ:
1. project-settings.md を確認（特にテスト実行コマンド・integration タグ・レイヤー構成）
2. /tdd "<タスク>" で TDD ワークフロー開始
```

> サマリにはワークフロー状態の git 追跡設定の結果（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- `go.mod` が存在しない → 「ここは Go モジュールではないようです。中断します」と提示して終了。あわせて汎用版 `tdd-universal` plugin の利用を案内する（GOPATH モードの古いプロジェクトも同様）。
- CLI プロジェクトだった場合（cobra / urfave/cli 主体で HTTP サーバーを持たない）→ Step 3 で読み替えを確認したうえで続行する。ライブラリのみ（`cmd/` が無い）なら「handler 層は存在しない」として service/domain 中心の設定を生成する。
- テストが 1 件も無い → 警告のうえ、最小限の project-settings.md を生成（ユーザーが手動で埋める前提）。「最初のテストがこのリポの流儀（`package foo_test` か否か・アサーションライブラリ）を決める」ことを伝える。
- `go list ./...` がビルドエラーで失敗する → エラーを提示し、ビルドが通る状態にしてから再実行するよう案内（壊れたツリーに対して設定を生成しても検証できない）。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしない。
