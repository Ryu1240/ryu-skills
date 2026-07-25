---
name: tdd-bootstrap
description: Detect a monorepo's backend (Rails) and frontend (Vue/Vite) packages, paths and tooling, and generate a project-specific .claude/skills/_shared-tdd/ for the tdd-monorepo skills
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
    description: 初回セットアップ。モノレポを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

モノレポ（Rails backend + Vue frontend）を走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（**停止**）
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: モノレポ走査

### 2-1. パッケージディレクトリの特定（最重要）
モノレポは backend / frontend が別ディレクトリに分かれる。まず両者の場所を突き止める。

| 対象 | 確認方法 |
|---|---|
| backend パッケージ | `Glob **/Gemfile`（`node_modules`/`vendor` 除く）→ `Gemfile` があり `gem ['"]rails['"]` を含むディレクトリ（例 `api/`, `server/`, `backend/`） |
| frontend パッケージ | `Glob **/package.json`（`node_modules` 除く）→ deps に `vue`（または `react`）を含み `vite.config.*` があるディレクトリ（例 `web/`, `client/`, `frontend/`） |

- 両方見つかる → モノレポとして続行。
- 片方しか無い → 「これは単一スタックのようです。`tdd-rails` / `tdd-frontend` の単体プラグインの方が適切かもしれません」と伝え、続行可否を確認（片方だけのエコシステムで生成することは可能）。

### 2-2. 各パッケージのツール検出
特定したパッケージ配下で以下を検出する。

**backend（`{be}/`）**:

| 検出項目 | 確認方法 |
|---|---|
| アプリ名 | `{be}/config/application.rb` の `module` |
| RSpec | `{be}/Gemfile` の `rspec-rails` + `Glob {be}/spec/**/*_spec.rb` |
| spec サブディレクトリ | `Glob {be}/spec/*/` |
| FactoryBot / WebMock / Committee / Pundit / Bullet / SimpleCov / Rubocop | `{be}/Gemfile` を Grep |
| マルチテナント | `{be}/Gemfile` の `acts_as_tenant` OR Grep `ApplicationRecord.client` |

**frontend（`{fe}/`）**:

| 検出項目 | 確認方法 |
|---|---|
| フレームワーク | `{fe}/package.json` deps（`vue` / `react`） |
| Vitest / Testing Library / user-event / MSW / Pinia / coverage-v8 / ESLint | `{fe}/package.json` を Grep |
| spec 配置 | `Glob {fe}/src/**/*.spec.{ts,js}`（co-located か `__tests__` か） |
| factory | `Glob {fe}/src/**/testUtils/**` / `**/factory*` |
| パッケージマネージャ | `{fe}/yarn.lock`→yarn / `pnpm-lock.yaml`→pnpm / `package-lock.json`→npm |

**共通**: husky/lint-staged（ルート or 各パッケージの `package.json` + `.husky/`）、CI（`Glob .circleci/config.yml .github/workflows/*.yml`）、Notion 連携は常に「任意」。

検出結果を表で提示（backend パッケージ名・frontend パッケージ名・各ツールの有無・パッケージマネージャ）。

## Step 3: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```

- `[y]` → Step 4 へ / `[e]` → 変更項目を聞き自由入力で上書き、再確認 / `[n]` → 中断（何も生成しない）

承認なしに Write してはいけない（**停止**）。

## Step 4: ファイル生成

`.claude/skills/_shared-tdd/` を作成し、以下 4 ファイルを Write：

### 4-1. `project-settings.md`
plugin 同梱テンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/project-settings.md`）を土台に、検出結果で以下を置換して Write：
- 見出しのリポ名を実プロジェクト名に。
- **2つのエコシステム表**のパッケージパス（`api/`→検出した `{be}/`、`web/`→検出した `{fe}/`）・各ツール（検出「なし」の行は削除 or 「未導入」と明記。推測で「あり」と書かない）。
- **テスト実行コマンド**の `cd {be}` / `cd {fe}` を実パスに、パッケージマネージャを検出値（yarn/pnpm/npm run）に。
- **不変条件**: マルチテナント未検出なら backend の該当行を一般化、Committee 未検出なら OpenAPI 契約の行を削除、MSW 未検出なら frontend の該当行を調整。
- 片方のエコシステムのみのプロジェクトなら、もう一方の列・記述を削除する。

### 4-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read してそのまま Write する（プロジェクト固有の差分は project-settings.md に集約。パッケージパスの実値が必要なら state-machine.md の lint コマンド例だけ置換）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-monorepo/skills/_shared-tdd/{filename}` を相対 Read する。

## Step 5: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`（backend={be}/ , frontend={fe}/）
- project-settings.md  (走査結果から生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)

次のステップ:
1. project-settings.md を開いて検出に漏れた項目を補完
2. /tdd "<タスク>" で TDD ワークフロー開始（backend/frontend は自動判定）
```

## エラーハンドリング

- backend も frontend も見つからない → 「モノレポの backend(Rails)/frontend(Vue) を特定できませんでした。中断します」と提示して終了。あわせて**汎用版 `tdd-universal` plugin**（任意の言語・構成向け。対話型 bootstrap でスタックを聞き取って設定を構築）の利用を案内する。
- backend または frontend しか無い → 単体プラグイン（`tdd-rails` / `tdd-frontend`）の利用を案内しつつ、希望あれば片側のみで生成。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしてはいけない。
