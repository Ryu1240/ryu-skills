# Next.js TDD スイート（`/tdd`）

**Next.js（App Router）+ React + TypeScript** のフロントエンド向けの TDD ワークフロー自動化スキル群です。テストは **Vitest + React Testing Library** を前提にしています。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`booking-web`**（Next.js App Router の予約アプリ）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| フレームワーク | Next.js（App Router）+ React + TypeScript |
| テスト | Vitest（`*.test.ts(x)` 併置。`@vitejs/plugin-react` + `vite-tsconfig-paths`） |
| DOM 環境 | jsdom（DOM を使わないテストは `// @vitest-environment node`） |
| コンポーネント検証 | React Testing Library + user-event + jest-dom |
| API モック | MSW |
| サーバー状態 | TanStack Query（各テストで新しい `QueryClient`） |
| API の型 | OpenAPI から生成（`openapi-typescript`） |
| 認証 | Auth0 SPA（`useAuth0` をモック） |
| スタイル | Tailwind CSS（クラス名は検証しない） |
| lint / hook | ESLint（`eslint-config-next`）+ husky/lint-staged |
| CI | GitHub Actions / CircleCI |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせて書き換えてください**（`/tdd-bootstrap` が自動生成します）。TanStack Query・Auth0・MSW が無いプロジェクトでは、bootstrap が該当の記述を外すか、実際に使っているもの（SWR・NextAuth など）に置き換えます。

## 何をどこでテストするか

App Router では Server Component（特に async なもの）を React Testing Library で描画できません。そこでこのプラグインは、**Server Component を薄く保ち、ロジックをテストできる場所に寄せる**ことを前提に各フェーズが判断します。

```
app/**/page.tsx, layout.tsx  … Server Component。単体テストしない（データ取得と子への受け渡しだけ）
app/**/actions.ts            … Server Action。async 関数として node 環境でテスト
app/api/**/route.ts          … Route Handler。Request を渡して直接呼ぶ
features/<name>/components/  … Client Component。React Testing Library でテスト
features/<name>/hooks/       … custom hook（TanStack Query）。renderHook + QueryClient wrapper
lib/                         … 純粋関数・API クライアント。node 環境でテスト
```

- **Plan** はタスクから「どこでテストするか」（`lib` / `hook` / `component` / `server-action` / `route-handler` / `api-client`）を判定し、1 サイクル 1 種別で分解します。Server Component にしか置き場が無いロジックは、切り出す前提で計画します。
- **Red** はテスト種別ごとの書き方を指示します（role で引く・`findBy*` で待つ・`userEvent.setup()`・MSW の上書き・`next/navigation` / `next/cache` / Auth0 のモック・`vi.hoisted`）。
- **Refactor** は Next.js / React 固有の観点で改善します（**Server と Client の境界** / ロジックの `lib`・hook への切り出し / **`useEffect` の誤用** / query key と無効化 / アクセシビリティ / 型）。
- **Coverage Review** はローディング・API エラー・空状態・認証状態・mutation 後の再取得まで含むマトリクスで抜けを埋めます。

> 実際のディレクトリ名が違っても構いません。`tdd-bootstrap` が実態（`src/` の有無、`features/` の代わりに `components/` + `hooks/` など）を読み取って project-settings.md に反映します。

## 範囲外: E2E

ページをまたぐ遷移・middleware・async Server Component の結合・実際の Auth0 ログインは **E2E（Playwright など）の範囲**で、このプラグインでは扱いません。計画・境界の提案・Coverage Review でこれらに当たったときは、テストを追加せずに「E2E 側の候補」として列挙するだけにします。

## 他プラグインとの使い分け

| 状況 | 使うもの |
|---|---|
| **Next.js（App Router）+ React** | **`tdd-nextjs`** |
| Vue + Vite + Vitest のフロントエンド | `tdd-frontend` |
| TS/Node バックエンド（API サーバー・ワーカー） | `tdd-node` |
| Rails + RSpec | `tdd-rails` |
| Python + pytest | `tdd-python` |
| Go バックエンド | `tdd-go` |
| Rust | `tdd-rust` |
| Rails + Vue モノレポ | `tdd-monorepo` |
| 上記以外の言語 | `tdd-universal` |

1 リポジトリで有効化するプラグインは **1 つだけ**にしてください（同じ skill 名を提供するため）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-nextjs@general-skills
```

導入後、初回 `/tdd` 実行時に Phase 0 が `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します。手動なら `/tdd-bootstrap`（既存があれば確認）/ `/tdd-bootstrap --force`（上書き再生成）。

- **テスト基盤が未整備でも始められます。** bootstrap が React Testing Library・jsdom・`vitest.config.mts`・`vitest.setup.ts`・MSW・`renderWithProviders` の不足を洗い出し、承認すれば追加します（コミットはしません。`chore: テスト基盤を追加` として最初のサイクルの前にコミットするよう案内します）。
- **`frontend/` のようなサブディレクトリにも対応します。** bootstrap が `next` を依存に持つパッケージを探し、コマンドに `cd {package_root}` を付けて生成します。`.claude/` は git のルートに置きます。

> Jest のプロジェクトでも使えます。bootstrap が検出し、単一ケース実行を `jest -t`、ランダム順序を `--randomize` に読み替えてコマンド節を差し替えます。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でテスト種別（どこでテストするか）を判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。Next.js のバージョンと Router、テスト基盤、TanStack Query・認証・OpenAPI 型の有無を走査し、不明点は対話で確認して設定を生成（承認制）。テスト基盤が足りなければセットアップ案を出し、承認後に追加します。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整（コマンドは `package.json` の scripts で実在を裏取り）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。テスト種別ごとの作法で失敗する Vitest テストを 1 本だけ書く。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（境界の遵守・アクセシブルな markup・TanStack Query・OpenAPI の型）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。Server/Client の境界 / ロジックの切り出し / `useEffect` / query key / a11y / 型 をテスト緑のまま改善。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミット（再生成した OpenAPI の型も含める）。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性（クエリの強さ・非同期の待ち方・過剰モック）に加え、サイクル境界で次サイクルの追加テストと E2E 側の候補を提案（読み取り専用）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — 対象（lib / hook / component / server action / route handler）× テストカテゴリのマトリクスで不足を補完。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — `it.each` 化・render ヘルパへの集約・DOM 不要なテストの node 環境化。`-t` 単独実行と `--sequence.shuffle` で独立性を検証。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — 置き場の方針・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# 自由テキストから計画 → 承認すれば同じセッションのまま Red へ進む
/tdd "予約フォームに日付の重複チェックを追加し、重複時はエラーを表示する"

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
