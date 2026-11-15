---
name: tdd-bootstrap
description: Next.js（App Router）+ React + TypeScript プロジェクトのスタック・テスト基盤（Vitest / React Testing Library / jsdom / MSW）・データ取得・認証・OpenAPI 型を走査し、tdd-nextjs 用の .claude/skills/_shared-tdd/ を生成する（承認制）。テスト基盤が足りなければセットアップ案も出す。/tdd の初回起動時に自動で呼ばれるほか、「TDD の設定を作り直して」と頼まれたときに使う。
argument-hint: [--force]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Glob
  - Grep
  - AskUserQuestion
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(cat:*)
  - Bash(git check-ignore:*)
  - Bash(pnpm:*)
  - Bash(yarn:*)
  - Bash(npm:*)
  - Bash(npx:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、_shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

Next.js（App Router）プロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → そのまま Step 2 へ
- 存在し、`--force` なし → 「既に存在します。再生成しますか？ [o]上書き / [n]中断」を確認（停止）。部分修正だけなら `/tdd-project-settings-update` が適切と併せて案内。
- 存在し、`--force` あり → そのまま Step 2 へ（上書き）

## Step 2: プロジェクト走査

### 2-1. 対象パッケージの特定（モノレポ対応・最初にやる）
`Glob **/package.json`（`node_modules` 除外）で候補を列挙する。
- 1つだけ → そのディレクトリが対象（リポジトリ直下とは限らない。`frontend/` だけに `package.json` がある構成もある）。
- 複数（workspaces / turborepo / nx / 単にディレクトリが分かれている）→ 依存に `next` を持つものを第一候補として Step 3 でユーザーに選ばせる。
- `.claude/` と状態ファイルは git のルートに置く。対象パッケージがルートでなければ `package_root`（例 `frontend`）として記録し、コマンドに `cd {package_root} && ...` を付ける。

### 2-2. スタック検出（対象パッケージ配下）

| 検出項目 | 確認方法 |
|---|---|
| プロジェクト名 | `package.json` の `name` |
| Next.js | 依存の `next` のバージョン。`app/` / `src/app/` があれば App Router、`pages/` だけなら Pages Router（→ エラーハンドリング） |
| ソースの置き場 | `src/` の有無。`tsconfig.json` の `paths`（`@/*` の向き先） |
| ディレクトリ構成 | `app/` `components/` `features/` `hooks/` `lib/` などの実際の名前（テンプレの `features/<name>/` を押し付けない） |
| TypeScript | `tsconfig.json` + `typescript` 依存 |
| テストランナー | 依存に `vitest` / `jest`。設定ファイル `vitest.config.*` / `jest.config.*` |
| DOM 環境 | 依存に `jsdom` / `happy-dom`、`vitest.config.*` の `environment` |
| Vite プラグイン | `@vitejs/plugin-react`、`vite-tsconfig-paths`（またはパスエイリアスの設定） |
| セットアップファイル | `vitest.config.*` の `setupFiles` とその中身（jest-dom・cleanup・MSW の配線）、`globals` の値 |
| Testing Library | `@testing-library/react` / `@testing-library/user-event` / `@testing-library/jest-dom` |
| API モック | `msw` + `Glob **/mocks/** **/msw/**`、`openapi-msw` |
| サーバー状態 | `@tanstack/react-query` / `swr` |
| API の型 | `openapi-typescript` / `openapi-fetch` / `orval` と、`scripts` の生成コマンド（`gen:api` 等）と生成先 |
| 認証 | `@auth0/auth0-react` / `@auth0/nextjs-auth0` / `next-auth` / `@clerk/nextjs` |
| スタイル | `tailwindcss` / CSS Modules |
| テストヘルパ | `Glob **/test/** **/testUtils/** **/test-utils*`（`renderWithProviders` 等） |
| テスト配置 | `Glob **/*.{test,spec}.{ts,tsx}` で件数と配置（co-located / `__tests__/`）を判定 |
| E2E | `@playwright/test` / `cypress`（範囲外だが、E2E 側へ回す先があるかとして記録） |
| lint / format | `eslint.config.*` / `.eslintrc*`（`eslint-config-next`）/ `prettier` / `biome` |
| 型チェック | `scripts` の `typecheck` / `tsc --noEmit` |
| パッケージマネージャ | `pnpm-lock.yaml` → pnpm / `yarn.lock` → yarn / `package-lock.json` → npm（`packageManager` フィールドも見る） |
| husky / lint-staged | `package.json` を Grep + `.husky/` / `lefthook.yml`（git のルートも見る） |
| CI | `.github/workflows/*.yml` / `.circleci/config.yml`（git のルート） |

### 2-3. 実コマンドの抽出（最優先）
`package.json` の `scripts` に実際のコマンドがあればそれを最優先で採用する（`test` / `typecheck` / `lint` / `gen:api` / `coverage`）。推測より実物。`test` が `vitest run` なら `pnpm test {path} -t "{case}"` も使える。

### 2-4. 既存テストの作法の抽出
既存テストを 1〜3 件 Read し、実際の書き方を観察する（environment の指定、render ヘルパ、QueryClient の作り方、MSW の使い方、`next/navigation` のモック、`describe` の粒度と言語）。

### 2-5. テスト基盤の不足の洗い出し
App Router のコンポーネントと hook を TDD するのに要るものが揃っているかを判定する。足りないものを列挙する（無いものを「あり」と書かない）：
- `@testing-library/react` / `@testing-library/user-event` / `@testing-library/jest-dom`
- `jsdom`（または `happy-dom`）
- `@vitejs/plugin-react` / `vite-tsconfig-paths`
- `vitest.config.mts` / `vitest.setup.ts`
- `msw`（API 連携があるなら）
- `renderWithProviders` / `createWrapper`（TanStack Query・認証を使っているなら）

### 2-6. 検出結果の提示
```
🔍 プロジェクト走査結果

| 項目 | 検出値 |
|---|---|
| プロジェクト名 | <name> |
| 対象パッケージ | <path>（package_root: <frontend / なし>） |
| Next.js | <version>（App Router / Pages Router） |
| ソースの置き場 | src/ あり・なし / `@/*` → <path> |
| ディレクトリ構成 | <実際の名前> |
| テストランナー | Vitest <version> / Jest / なし |
| DOM 環境 | jsdom / happy-dom / なし |
| Testing Library | react / user-event / jest-dom（不足: <列挙>） |
| セットアップ | vitest.config.* / vitest.setup.ts / なし（globals: true/false） |
| API モック | MSW / なし |
| サーバー状態 | TanStack Query / SWR / なし |
| API の型 | openapi-typescript（<生成先>, `<script>`）/ なし |
| 認証 | Auth0 SPA / ... / なし |
| スタイル | Tailwind / ... |
| テスト配置 | co-located *.test.ts(x)（X 件） |
| E2E | Playwright / なし（範囲外） |
| lint / 型 | <cmd> / 未導入 |
| パッケージマネージャ | pnpm / yarn / npm |
| husky/lint-staged | あり / なし |
| CI | GitHub Actions / CircleCI / なし |

⚠️ テスト基盤の不足: <列挙 / なし>
❓ 未確定の項目: <列挙>
```

## Step 3: 対話ヒアリング（未確定項目のみ）

未確定・推定の項目だけ AskUserQuestion で聞く（1回最大4問。多ければ優先度順に分割）。

- 対象パッケージ（モノレポ検出時）: 候補を選択肢に。
- テスト基盤の不足がある場合（2-5）: 「足りないものを今セットアップする（推奨。依存追加と設定ファイルを1コミットにまとめる）」「設定ファイルの生成だけ行い、セットアップは自分でやる」「中断」。セットアップを選んだら Step 5-4 で行う。
- API のモック方法（MSW 未導入で API 連携がある場合）: 「MSW（推奨。fetch の層で差し替えるので、API クライアントや TanStack Query の実装を変えても壊れにくい）」「API クライアントのモジュールを `vi.mock` で差し替える（依存が増えないが、実装の形に結びつく）」。
- DOM 環境（未導入の場合）: 「jsdom（推奨。Testing Library の標準で、ブラウザ API の再現が広い）」「happy-dom（速いが、一部の API の挙動が違う）」。
- テストランナーが Jest だった場合: 単一ケース実行を `jest {path} -t "{case}"`、ランダム順序を `--randomize` に読み替えて確定する（テンプレは Vitest 前提なのでコマンド節を全面的に書き換える。`next/jest` の設定があればそれに従う）。
- ディレクトリ構成の呼び方（`features/` が無い等）: 実際の置き場（hook・Client Component・純粋関数・API クライアント）を確認。
- プロジェクト固有の追加不変条件（任意）。

> 推測で埋めない。分からない項目は「未導入」「未対応」と明記する。

## Step 4: 承認ゲート

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？（テスト基盤のセットアップ: する / しない）
[y] 生成 / [e] 個別編集 / [n] 中断
```
- `[y]` → Step 5 へ / `[e]` → 変更項目を聞き自由入力で上書き、再確認 / `[n]` → 中断（何も生成しない）

承認を得るまで Write しない・依存を追加しない（停止）。

## Step 5: ファイル生成

`.claude/skills/_shared-tdd/` を作成し、以下 4 ファイルを Write：

### 5-1. `project-settings.md`
plugin 同梱テンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/project-settings.md`）を Read し、検出＋ヒアリング結果で置換して Write：
- 見出しのリポ名を実プロジェクト名に。
- 構成とテストの表を検出値に（検出「なし」の行は削除 or 「未導入」と明記。推測で「あり」と書かない）。
- 置き場の方針を実際のディレクトリ名に置換（Step 2-2 の結果。`src/` があれば `src/` 付きに）。
- テスト実行コマンドをパッケージマネージャと実 scripts に合わせる。`package_root` があれば `cd {package_root} && ...` を付ける。Jest なら Vitest 用コマンドを全面差し替え。
- 不変条件: MSW 未導入なら 5 を実際のモック方法に置換、TanStack Query 未導入なら 3 の QueryClient の行を削除（SWR なら `SWRConfig` の `provider: () => new Map()` に置換）、認証ライブラリに合わせて表の認証の行を置換、`globals` の値に合わせて 3 の `cleanup` の記述を調整。

### 5-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱のテンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read して Write する（プロジェクト固有差分は project-settings.md に集約）。ただし 3 ファイルの見出しのリポ名（`— booking-web`）は実プロジェクト名に置換し、`commit-convention.md` の「pre-commit hook あり（husky + lint-staged）」の段落は検出結果に合わせる（hook 無しなら「hook が無いため、コミット前に lint / typecheck を手動実行する」に書き換える）。OpenAPI の型生成が無ければ生成ファイルの段落を削除する。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-nextjs/skills/_shared-tdd/{filename}` を相対 Read する。

### 5-3. 生成内容の検証
生成した `project-settings.md` を Read し直し、テスト実行コマンドが実在するか（`package.json` の `scripts` と整合するか）を確認する。

### 5-4. テスト基盤のセットアップ（Step 3 で選ばれた場合のみ）
足りないものだけを追加する（既にあるものは触らない）。
1. 依存追加: `{pm} add -D <不足パッケージ>`（`package_root` で実行）。
2. 設定ファイル（無い場合のみ Write。ある場合は差分を提示して Edit の承認を取る）：
   ```ts
   // vitest.config.mts
   import react from '@vitejs/plugin-react'
   import tsconfigPaths from 'vite-tsconfig-paths'
   import { defineConfig } from 'vitest/config'

   export default defineConfig({
     plugins: [tsconfigPaths(), react()],
     test: {
       environment: 'jsdom',
       setupFiles: ['./vitest.setup.ts'],
       clearMocks: true,     // vi.fn() の呼び出し履歴を各テスト前に消す（restoreMocks だけでは消えない）
       restoreMocks: true,   // vi.spyOn を元に戻す
       exclude: ['**/node_modules/**', '**/e2e/**'],   // Playwright のテストを拾わない
     },
   })
   ```
   ```ts
   // vitest.setup.ts
   import '@testing-library/jest-dom/vitest'
   import { cleanup } from '@testing-library/react'
   import { afterAll, afterEach, beforeAll, vi } from 'vitest'
   import { server } from './test/msw/server'

   beforeAll(() => server.listen({ onUnhandledRequest: 'error' }))
   afterEach(() => {
     server.resetHandlers()
     cleanup()   // globals: false のため RTL の自動 cleanup が効かない
   })
   afterAll(() => server.close())

   vi.mock('server-only', () => ({}))
   vi.mock('next/font/google', () => ({ Inter: () => ({ className: 'font', variable: '--font' }) }))   // 使っているフォントに合わせる
   ```
   `test/msw/server.ts`（`setupServer(...handlers)`）、`test/msw/handlers.ts`（空配列から始める）、`test/render.tsx`（`renderWithProviders` と `createWrapper`。どちらも呼ぶたびに `new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })` を作る）も、該当ライブラリがある場合だけ用意する。
3. `package.json` の `scripts` に `test` が無ければ `"test": "vitest run"` を足す（あれば変えない）。
4. 検証: 既存テストがあれば `{pm} vitest run` で全件 pass、`{pm} typecheck` が通ることを確認。落ちたら原因を提示して停止。
5. コミットはしない。変更ファイルを一覧で提示し、「`chore: テスト基盤を追加` として最初のサイクルの前にコミットする」ことを推奨する（TDD のサイクルのコミットと混ぜない）。

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
対象ファイル（git のルートの `.gitignore` または `.git/info/exclude`）を Read し、同じ行が既にあれば何もしない。無ければ末尾に追記して Write する:

```
# TDD ワークフローの進行状態（開発者ごとの一時ファイル）
.claude/tdd-workflow/
```

追記後に `git check-ignore -q .claude/tdd-workflow/` を再実行し、実際に効いていることを確認する。効いていなければ原因（別の否定パターン等）を提示する。

> ⚠️ `.claude/skills/_shared-tdd/` はチームで共有すべき設定なので ignore しない。このステップの対象は `.claude/tdd-workflow/` のみ。

## Step 7: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
対象: {package_root} / Next.js {version} / ランナー: {runner} / DOM: {environment}

- project-settings.md  (走査 + ヒアリングから生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)
- テスト基盤: {追加したもの / 変更なし}（未コミット。`chore: テスト基盤を追加` で先にコミットを推奨）

次のステップ:
1. project-settings.md を確認（特にテスト実行コマンドと置き場の方針）
2. /tdd "<タスク>" で TDD ワークフロー開始
```

> サマリにはワークフロー状態の git 追跡設定の結果（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- `package.json` が存在しない → 「ここは JS/TS プロジェクトではないようです。中断します」と提示して終了。あわせて汎用版 `tdd-universal` plugin の利用を案内する。
- `next` が依存に無い → React だけ（Vite 等）なら「この plugin は Next.js 前提です。Server Component / Next.js のランタイム API に関する記述を除けば流用できます」と警告し続行可否を確認。Vue なら `tdd-frontend`、バックエンドなら `tdd-node` を案内。
- Pages Router だけ → 「この plugin は App Router 前提です。`getServerSideProps` などはテンプレの置き場の方針に載っていません」と警告し続行可否を確認（続行時は置き場の方針から Server Component / Server Action の行を外し、`pages/api` を Route Handler の行に置き換える）。
- テストランナーが未導入 → Step 3 のセットアップの選択肢を出す。セットアップしない場合も最小限の project-settings.md を生成し、「最初のテストがこのリポの流儀を決める」ことを伝える。
- 既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定 → 承認なしに上書きしない。
