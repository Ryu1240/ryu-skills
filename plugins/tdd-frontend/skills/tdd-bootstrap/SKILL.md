---
name: tdd-bootstrap
description: Detect the frontend project's stack/paths/tooling and generate a project-specific .claude/skills/_shared-tdd/ for the tdd-frontend skills
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
  - Bash(git check-ignore:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

フロントエンド（Vue/Vite 系）プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

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
| アプリ名 | `package.json` の `name` / 無ければ `cat README*` の H1 / 最終的に cwd 名 |
| フレームワーク | `package.json` の deps で `vue` / `react` / `svelte` を判定（本 plugin は Vue 前提。React 等なら警告） |
| ビルド | `vite.config.*` の有無（Vite） |
| TypeScript | `tsconfig.json` + `.ts`/`.vue` 件数 |
| テストランナー | `package.json` で `vitest`（+ `vitest.config.*` / `vite.config` の test 設定） |
| コンポーネント検証 | `package.json` で `@testing-library/vue` / `@vue/test-utils` |
| user-event | `package.json` で `@testing-library/user-event` |
| API モック | `package.json` で `msw` + `Glob src/**/mocks/**` / `**/handlers*` |
| 状態管理 | `package.json` で `pinia` / `vuex` |
| spec 配置 | `Glob src/**/*.spec.{ts,js}` / `**/*.test.{ts,js}` で件数と配置（co-located か `__tests__` か）を判定 |
| factory | `Glob src/**/testUtils/**` / `**/factory*` |
| カバレッジ | `package.json` で `@vitest/coverage-v8` / `--coverage` scripts |
| lint | `package.json` で `eslint` + `.eslintrc*` / `eslint.config.*`、`prettier` |
| 型チェック | `package.json` scripts で `vue-tsc` / `tsc --noEmit` |
| パッケージマネージャ | `yarn.lock` → yarn / `pnpm-lock.yaml` → pnpm / `package-lock.json` → npm |
| husky / lint-staged | `package.json` を Grep（`husky` / `lint-staged`） + `.husky/` |
| CI | `Glob .circleci/config.yml .github/workflows/*.yml` |
| Notion 連携 | この plugin の挙動として常に「任意」を表示 |

検出結果を以下の形式で提示：

```
🔍 storefront のプロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| アプリ名 | <name> |
| フレームワーク | Vue 3 / React / ... |
| ビルド | Vite / その他 |
| TypeScript | あり / なし |
| Vitest | あり (X spec files) |
| Testing Library | @testing-library/vue / @vue/test-utils / なし |
| MSW | あり / なし |
| 状態管理 | Pinia / Vuex / なし |
| spec 配置 | co-located *.spec.ts / __tests__ |
| カバレッジ | v8 / なし |
| lint | ESLint(+Prettier) / なし |
| パッケージマネージャ | yarn / pnpm / npm |
| husky/lint-staged | あり / なし |
| CI | GitHub Actions / CircleCI / なし |
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

下記テンプレを、Step 2 の検出結果で埋めて Write。「検出: なし」だった項目は対応行を **削除** するか「未導入」と明記する（推測で「あり」と書かない）。パッケージマネージャは検出値（`yarn`/`pnpm`/`npm run`）に統一する。

```markdown
# TDD スキル共通設定（Project Settings）— {app_name}

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。

## 構成とテスト

| | frontend |
|---|---|
| パッケージ | リポジトリ直下（{Vite 等} アプリ） |
| フレームワーク | {Vue 3 / React ...} + {TypeScript / JavaScript}。状態管理は {Pinia / Vuex / なし} |
| テスト | Vitest |
| コンポーネント検証 | {@testing-library/vue / @vue/test-utils} {+ user-event} |
| spec 配置 | {co-located `*.spec.ts` / `__tests__/`} |
| データ生成 | {factory あれば「ファクトリヘルパ（`<detected path>`）」/ なければ削除} |
| API モック | {MSW あれば「MSW（`<detected handlers path>`）」/ なければ「なし」} |
| カバレッジ | {v8 あれば「Vitest（v8）」/ なければ「未導入」} |

## テスト実行コマンド

**frontend（{framework} / Vitest）**（{pm} を使用）:
\`\`\`bash
{pm} test <file>                # 単一ファイル
{pm} test                       # 全件
{pm} test:ci  (または vitest run)  # 全件 1 回（CI 同様）
{coverage あれば: {pm} coverage}
{typecheck あれば: {pm} typecheck}
\`\`\`

## CI / hook（重要）

- {CI 検出結果: 「GitHub Actions がテストを走らせる」/ 「CircleCI がテストを走らせる」/ 「CI 未設定」}。
- {husky 検出時: 「pre-commit hook あり（husky + lint-staged）。`--no-verify` は禁止」/ 無ければ削除}
- lint: {ESLint あれば「ESLint（+ Prettier）」/ なければ「未導入」}

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。
2. **TDD メタ情報をコード/spec に残さない**。
3. **テストの独立性を必ず保つ**: {MSW 検出時: MSW handler を各テストでリセット（`afterEach(resetHandlers)`）。} {Pinia 検出時: Pinia は各テストで新規（`setActivePinia(createPinia())`）。} グローバル状態をテスト間で共有しない。
4. **Testing Library の作法**: 要素はロール/アクセシブルネームで取得（`getByRole`/`findByRole` 優先）、実装詳細に依存しない。`data-testid` は最後の手段。操作は user-event。
5. {MSW 検出時: **API 連携は MSW でモック**（正常系は共通 handler、異常系は各テストで `server.use(...)` 上書き）。実通信はしない。}
6. **Green は最小実装のみ**（YAGNI）。
7. **承認ゲートは Red 完了後と Commit 直前の2箇所**。
8. **ターン粒度**: 既定は各フェーズで停止。一気通貫は `--auto` でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
```

### 4-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`

plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read して Write する（プロジェクト固有差分は project-settings.md に集約）。ただし **3 ファイルの見出しのリポ名**（`— storefront`）は実プロジェクト名に置換し、`commit-convention.md` の「pre-commit hook あり（husky + lint-staged）」の段落は検出結果に合わせる（hook 無しなら「hook が無いため、コミット前に lint を手動実行する」に書き換える）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では、`plugins/tdd-frontend/skills/_shared-tdd/{filename}` を相対 Read する。

## Step 5: ワークフロー状態の git 追跡設定（確認）

`/tdd` は実行中に `.claude/tdd-workflow/` へ状態ファイルを書き出す（`workflow-{id}.json` / `current-cycle.json` / `notion-context-*.json` / `optimization-report-*.md`）。これらは**開発者ごとの進行中の作業状態**であり、コミットするとレビューのノイズや複数人作業時のコンフリクトの原因になる。Notion 連携を使う場合はタスク本文のキャッシュも含まれる。

### 5-1. 現状確認
```bash
git check-ignore -q .claude/tdd-workflow/
```
終了コードで判定する（`echo` を繋がない。128 を「未無視」と誤認しないため）:
- **0（既に無視されている）** → 何もせず次へ（サマリで「設定済み」と報告）。
- **1（無視されていない）** → 5-2 へ。
- **128（git 管理下でない）** → このステップをスキップ。

### 5-2. ユーザーに確認（AskUserQuestion・必須）
「TDD ワークフローの状態ファイルを git 管理から除外しますか？」として次を提示する:

- **`.gitignore` に追加（推奨）** — チーム全員に効く。`.gitignore` の変更自体はコミット対象になる。
- **`.git/info/exclude` に追加** — このクローンのみ。`.gitignore` を変更したくない場合に。他メンバーには効かない。
- **除外しない** — ワークフローの計画・進捗をチームで共有・レビューしたい場合。

### 5-3. 適用（承認された選択のみ）
対象ファイル（`.gitignore` または `.git/info/exclude`）を Read し、**同じ行が既にあれば何もしない**。無ければ末尾に追記して Write する:

```
# TDD ワークフローの進行状態（開発者ごとの一時ファイル）
.claude/tdd-workflow/
```

追記後に `git check-ignore -q .claude/tdd-workflow/` を再実行し、**実際に効いていることを確認**する。効いていなければ原因（別の否定パターン等）を提示する。

> ⚠️ `.claude/skills/_shared-tdd/` は**チームで共有すべき設定**なので絶対に ignore しない。このステップの対象は `.claude/tdd-workflow/` のみ。

## Step 6: サマリ提示

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

> サマリには**ワークフロー状態の git 追跡設定の結果**（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- `package.json` が存在しない → 「ここは JS/TS フロントエンドプロジェクトではないようです。中断します」と提示して終了。あわせて**汎用版 `tdd-universal` plugin**（任意の言語向け。対話型 bootstrap でスタックを聞き取って設定を構築）の利用を案内する。
- Vue 以外（React/Svelte）を検出 → 「この plugin は Vue + Vitest 前提です。テストランナーが Vitest なら概ね流用できますが、コンポーネント検証の記述は手動調整が必要です」と警告のうえ続行可否を確認。
- テストランナーが Vitest でない（Jest 等）→ 警告のみ出し、テスト実行コマンドを検出値で埋めて生成（ユーザーが手動で調整する前提）。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしてはいけない。
