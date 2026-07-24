---
name: tdd-bootstrap
description: Detect the Rails project's stack/paths/tooling and generate a project-specific .claude/skills/_shared-tdd/ for the tdd-rails skills
argument-hint: [--force]
model: opus
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(cat:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

Rails プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（**停止**）
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

以下を Glob / Grep / Bash(ls/find/cat) で確認し、検出結果を表にまとめる。

| 検出項目 | 確認方法 |
|---|---|
| アプリ名 | `Glob config/application.rb` → Grep `module .* < Rails::Application` / 無ければ `cat README*` の H1 / 最終的に cwd 名 |
| Rails | `Gemfile` で `gem ['"]rails['"]` |
| RSpec | `Gemfile` で `gem ['"]rspec-rails['"]` + `Glob spec/**/*_spec.rb` 件数 |
| spec サブディレクトリ | `Glob spec/*/` でディレクトリ列挙（models / requests / services / policies / workers / batch_workers / strategies / lib など） |
| FactoryBot | `Gemfile` で `factory_bot` + `Glob spec/factories/**/*.rb` |
| WebMock | `Gemfile` で `webmock` |
| Committee（OpenAPI 契約） | `Gemfile` で `committee` + `Glob doc/openapi/**/*.{yml,yaml,json}` |
| マルチテナント | `Gemfile` で `acts_as_tenant` OR Grep `ApplicationRecord.client` を `app/` 配下 |
| Pundit | `Gemfile` で `pundit` |
| Bullet | `Gemfile` で `bullet` |
| SimpleCov | `Gemfile` で `simplecov` |
| Rubocop | `Gemfile` で `rubocop` + `.rubocop.yml` |
| husky / lint-staged | `package.json` を Grep（`husky` / `lint-staged`） + `.husky/` |
| docker compose | `Glob docker-compose.yml compose.yml` |
| CI | `Glob .circleci/config.yml .github/workflows/*.yml` |
| Notion 連携 | この plugin の挙動として常に「任意」を表示 |

検出結果を以下の形式で提示：

```
🔍 sales-hub のプロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| アプリ名 | <name> |
| Rails | <version or 'unknown'> |
| RSpec | あり (X spec files) |
| spec 配置 | spec/{models,requests,services,...} |
| FactoryBot | あり |
| Committee | あり / なし |
| マルチテナント | acts_as_tenant / ApplicationRecord.client / なし |
| Pundit | あり / なし |
| Bullet | あり / なし |
| husky/lint-staged | あり / なし |
| docker compose | あり / なし |
| CI | CircleCI / GitHub Actions / なし |
```

## Step 3: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```

- `[y]` → Step 4 へ
- `[e]` → 「どの項目を変更しますか？」を聞き、自由入力で上書き。再度 `[y]/[e]/[n]` 確認。
- `[n]` → 中断（何も生成しない）

承認なしに Write してはいけない（**停止**）。

## Step 4: ファイル生成

`.claude/skills/_shared-tdd/` ディレクトリを作成し、以下 4 ファイルを Write：

### 4-1. `project-settings.md`

下記テンプレを、Step 2 の検出結果で埋めて Write。「検出: なし」だった項目は対応行を **削除** するか「未導入」と明記する（推測で「あり」と書かない）。

```markdown
# TDD スキル共通設定（Project Settings）— {app_name}

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。

## 構成とテスト

| | backend |
|---|---|
| パッケージ | リポジトリ直下（Rails アプリ） |
| テスト | RSpec |
| spec 配置 | `spec/{<detected_subdirs>}/` |
| データ生成 | {FactoryBot あれば「FactoryBot（`spec/factories/*.rb`）」/ なければ削除} |
| モック | {WebMock あれば「WebMock」/ なければ削除} |
| 契約検証 | {Committee あれば「Committee（`assert_response_schema_confirm(200)`、OpenAPI）」/ なければ「なし（contract test 不要）」} |
| カバレッジ | {SimpleCov あれば「SimpleCov」/ なければ「未導入」} |

## テスト実行コマンド

**backend（Rails / RSpec）**:
```bash
bundle exec rspec spec/path/to/foo_spec.rb           # 単一ファイル
bundle exec rspec spec/path/to/foo_spec.rb:42        # 行指定
{docker compose あれば: docker compose exec app bundle exec rspec spec/path/to/foo_spec.rb}
```

## CI / hook（重要）

- {CI 検出結果: 「CircleCI がテストを走らせる」/ 「GitHub Actions がテストを走らせる」/ 「CI 未設定」}。
- {husky 検出時: 「pre-commit hook あり（husky + lint-staged）。`--no-verify` は禁止」/ 無ければ削除}
- lint: {Rubocop あれば「Rubocop（`.rubocop.yml`）」/ なければ「未導入」}

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。
2. **TDD メタ情報をコード/spec に残さない**。
3. {マルチテナント検出時のみ: **multi-tenant scope を必ず張る**: モデル/サービスは `ApplicationRecord.client = client`（または `ActsAsTenant.with_tenant(client)`）でテナント文脈を設定。クエリは tenant scoped に。}
4. **RSpec の慣習を踏襲**: 明示的な `subject` 宣言は避ける（implicit subject）。{FactoryBot 検出時のみ: factory は適切にテナント等を渡す。}
5. {Committee 検出時のみ: **request spec は OpenAPI 契約を検証**: `assert_response_schema_confirm(200)` で response schema を担保。}
6. **Green は最小実装のみ**（YAGNI）。
7. **承認ゲートは Red 完了後と Commit 直前の2箇所**。
8. **ターン粒度**: 既定は各フェーズで停止。一気通貫は `--auto` でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
```

### 4-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`

plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read してそのまま Write する（プロジェクト固有変更なし）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では、`plugins/tdd-rails/skills/_shared-tdd/{filename}` を相対 Read する。

## Step 5: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
- project-settings.md  (走査結果から生成)
- commit-convention.md (テンプレからコピー)
- workflow-schema.md   (テンプレからコピー)
- state-machine.md     (テンプレからコピー)

次のステップ:
1. project-settings.md を開いて検出に漏れた項目を補完
2. /tdd "<タスク>" で TDD ワークフロー開始
```

## エラーハンドリング

- `Gemfile` が存在しない → 「ここは Rails プロジェクトではないようです。中断します」と提示して終了。
- 検出が極端に乏しい（spec/ 不在、Gemfile に RSpec 無し）→ 警告のみ出し、最小限の project-settings.md を生成（ユーザーが手動で埋める前提）。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしてはいけない。
