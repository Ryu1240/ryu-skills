---
name: tdd-bootstrap
description: Detect the TypeScript/Node backend project's stack, layout, test runner and tooling, and generate a project-specific .claude/skills/_shared-tdd/ for the tdd-node skills
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

TypeScript / Node.js バックエンドプロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（**停止**）。部分修正だけなら `/tdd-project-settings-update` が適切と併せて案内。
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

### 2-1. 対象パッケージの特定（モノレポ対応・最初にやる）
`Glob **/package.json`（`node_modules` 除外）で候補を列挙する。
- **1つだけ** → リポジトリ直下が対象。
- **複数**（workspaces / turborepo / nx）→ ルートの `package.json` の `workspaces`、`pnpm-workspace.yaml`、`turbo.json`、`nx.json` を確認。**どのパッケージを TDD の対象にするかは Step 3 でユーザーに選ばせる**（バックエンドらしい候補＝`express`/`fastify`/`hono`/`@nestjs/core` を依存に持つものを第一候補として提示）。

### 2-2. スタック検出（対象パッケージ配下）

| 検出項目 | 確認方法 |
|---|---|
| プロジェクト名 | `package.json` の `name` |
| TypeScript | `tsconfig.json` + `typescript` 依存。ESM/CJS は `"type"` と `tsconfig` の `module` で判定 |
| テストランナー | 依存に `vitest` / `jest` / `mocha`。設定ファイル `vitest.config.*` / `jest.config.*` |
| Web フレームワーク | 依存に `express` / `fastify` / `hono` / `@nestjs/core` |
| HTTP テスト | 依存に `supertest` / `light-my-request`（Fastify inject）/ NestJS の `@nestjs/testing` |
| ORM / DB | `prisma` / `drizzle-orm` / `typeorm` / `knex` / `mongoose` + マイグレーションディレクトリ |
| スキーマ検証 | `zod` / `valibot` / `yup` / `class-validator` |
| 外部 API モック | `msw` / `nock` |
| テスト配置 | `Glob **/*.{test,spec}.ts` で件数と配置（co-located / `tests/` / `__tests__/`）を判定 |
| ファクトリ | `Glob **/testUtils/**` / `**/factories/**` / `@faker-js/faker` |
| lint / format | `.eslintrc*` / `eslint.config.*` / `prettier` |
| 型チェック | `scripts` の `typecheck` / `tsc --noEmit` |
| パッケージマネージャ | `yarn.lock` → yarn / `pnpm-lock.yaml` → pnpm / `package-lock.json` → npm |
| husky / lint-staged | `package.json` を Grep + `.husky/` / `lefthook.yml` |
| CI | `.github/workflows/*.yml` / `.circleci/config.yml` |

### 2-3. 実コマンドの抽出（最優先）
`package.json` の `scripts` に実際のコマンドがあれば**それを最優先**で採用する（`test` / `test:unit` / `typecheck` / `lint` / `coverage`）。推測より実物。

### 2-4. レイヤー構成の抽出
`src/` 配下のディレクトリを列挙し、実際の層の名前を把握する（`routes` / `controllers` / `handlers` / `services` / `usecases` / `repositories` / `models` / `schemas` など）。**テンプレの `routes/services/repositories` を押し付けず、実態の名前を使う**。

### 2-5. 独立性の担保方法の抽出
既存テストのセットアップを 1〜2 件 Read し、実際にどう独立性を保っているか観察する（トランザクションロールバック / truncate / testcontainers / インメモリ DB / `vi.restoreAllMocks` / `server.resetHandlers`）。

### 2-6. 検出結果の提示
```
🔍 プロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| プロジェクト名 | <name> |
| 対象パッケージ | <path>（モノレポなら選択結果） |
| TypeScript | あり（ESM/CJS） |
| テストランナー | Vitest / Jest / なし |
| Web フレームワーク | Express / Fastify / Hono / NestJS / なし |
| HTTP テスト | supertest / inject / なし |
| ORM / DB | Prisma / Drizzle / ... / なし |
| スキーマ検証 | Zod / ... / なし |
| 外部 API モック | MSW / nock / なし |
| テスト配置 | co-located *.test.ts（X 件） |
| レイヤー構成 | <実際のディレクトリ名> |
| 独立性の担保 | <既存テストから抽出 / 不明> |
| lint / 型 | <cmd> / 未導入 |
| パッケージマネージャ | yarn / pnpm / npm |
| husky/lint-staged | あり / なし |
| CI | GitHub Actions / CircleCI / なし |

❓ 未確定の項目: <列挙>
```

## Step 3: 対話ヒアリング（未確定項目のみ）

**未確定・推定の項目だけ** AskUserQuestion で聞く（1回最大4問。多ければ優先度順に分割）。

- **対象パッケージ**（モノレポ検出時）: 候補を選択肢に。
- **テストランナーが Jest だった場合**: 単一ケース実行を `jest {path} -t "{case}"`、ランダム順序を `--randomize` に読み替えて確定する（テンプレは Vitest 前提なので**コマンド節を全面的に書き換える**）。
- **独立性の担保方法**（既存テストから抽出できなかった場合）: 「トランザクションロールバック」「各ケースで truncate」「testcontainers」「DB を使わない（モックのみ）」「その他」から選択（複数可）。
- **レイヤー構成の呼び方**（`src/` の構成が想定と違う場合）: 実際の層名と依存方向を確認。
- **プロジェクト固有の追加不変条件**（任意）。

> **推測で埋めない**。分からない項目は「未導入」「未対応」と明記する。

## Step 4: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```
- `[y]` → Step 5 へ / `[e]` → 変更項目を聞き自由入力で上書き、再確認 / `[n]` → 中断（何も生成しない）

承認なしに Write してはいけない（**停止**）。

## Step 5: ファイル生成

`.claude/skills/_shared-tdd/` を作成し、以下 4 ファイルを Write：

### 5-1. `project-settings.md`
plugin 同梱テンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/project-settings.md`）を Read し、検出＋ヒアリング結果で置換して Write：
- 見出しのリポ名を実プロジェクト名に。
- **構成とテスト**の表を検出値に（検出「なし」の行は削除 or 「未導入」と明記。推測で「あり」と書かない）。
- **レイヤー構成**を実際のディレクトリ名に置換（Step 2-4 の結果）。
- **テスト実行コマンド**をパッケージマネージャと実 scripts に合わせる。モノレポなら `cd {package_root} && ...` を付ける。**Jest なら Vitest 用コマンドを全面差し替え**。
- **不変条件**: DB を使わないなら 3 のロールバック記述を調整、Zod 未導入なら 5 を実際のスキーマ検証手段に置換（無ければ削除）、レイヤー名は 6 を実態に合わせる。

### 5-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read してそのまま Write する（プロジェクト固有差分は project-settings.md に集約）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-node/skills/_shared-tdd/{filename}` を相対 Read する。

### 5-3. 自己検証（必須）
生成した `project-settings.md` を Read し直し、テスト実行コマンドが実在するか（`package.json` の `scripts` と整合するか）を確認する。

## Step 6: ワークフロー状態の git 追跡設定（確認）

`/tdd` は実行中に `.claude/tdd-workflow/` へ状態ファイルを書き出す（`workflow-{id}.json` / `current-cycle.json` / `notion-context-*.json` / `optimization-report-*.md`）。これらは**開発者ごとの進行中の作業状態**であり、コミットするとレビューのノイズや複数人作業時のコンフリクトの原因になる。Notion 連携を使う場合はタスク本文のキャッシュも含まれる。

### 6-1. 現状確認
```bash
git check-ignore -q .claude/tdd-workflow/ && echo ignored || echo not-ignored
```
- **既に無視されている** → 何もせず次へ（サマリで「設定済み」と報告）。
- **無視されていない** → 6-2 へ。
- git 管理下でない（コマンドが失敗する）→ このステップをスキップ。

### 6-2. ユーザーに確認（AskUserQuestion・必須）
「TDD ワークフローの状態ファイルを git 管理から除外しますか？」として次を提示する:

- **`.gitignore` に追加（推奨）** — チーム全員に効く。`.gitignore` の変更自体はコミット対象になる。
- **`.git/info/exclude` に追加** — このクローンのみ。`.gitignore` を変更したくない場合に。他メンバーには効かない。
- **除外しない** — ワークフローの計画・進捗をチームで共有・レビューしたい場合。

### 6-3. 適用（承認された選択のみ）
対象ファイル（`.gitignore` または `.git/info/exclude`）を Read し、**同じ行が既にあれば何もしない**。無ければ末尾に追記して Write する:

```
# TDD ワークフローの進行状態（開発者ごとの一時ファイル）
.claude/tdd-workflow/
```

追記後に `git check-ignore -q .claude/tdd-workflow/` を再実行し、**実際に効いていることを確認**する。効いていなければ原因（別の否定パターン等）を提示する。

> ⚠️ `.claude/skills/_shared-tdd/` は**チームで共有すべき設定**なので絶対に ignore しない。このステップの対象は `.claude/tdd-workflow/` のみ。

## Step 7: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
対象: {package_root} / ランナー: {runner} / レイヤー: {layers}

- project-settings.md  (走査 + ヒアリングから生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)

次のステップ:
1. project-settings.md を確認（特にテスト実行コマンドとレイヤー構成）
2. /tdd "<タスク>" で TDD ワークフロー開始
```

> サマリには**ワークフロー状態の git 追跡設定の結果**（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- `package.json` が存在しない → 「ここは Node.js プロジェクトではないようです。中断します」と提示して終了。あわせて**汎用版 `tdd-universal` plugin** の利用を案内する。
- **フロントエンド寄りだった場合**（`vue` / `react` / `svelte` を依存に持ち、`src/components/` が主体）→ 「この plugin はバックエンド前提です。Vue なら `tdd-frontend`、それ以外は `tdd-universal` が適切かもしれません」と提示し、続行可否を確認。
- **テストランナーが未導入** → 警告のうえ、最小限の project-settings.md を生成（ユーザーが手動で埋める前提）。「最初のテストがこのリポの流儀を決める」ことを伝える。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしてはいけない。
