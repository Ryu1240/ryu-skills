# TDD スキル共通設定（Project Settings）— booking-web

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> booking-web は Next.js（App Router）+ React + TypeScript のフロントエンド（予約アプリ）。テストは Vitest + React Testing Library。E2E（Playwright）はこのスキルの範囲外。

## 構成とテスト

| | frontend（Next.js App Router） |
|---|---|
| パッケージ | リポジトリ直下（モノレポなら `frontend/` 等。bootstrap が確定） |
| フレームワーク | Next.js（App Router）+ React + TypeScript。パスエイリアス `@/*` |
| テスト | Vitest（`vitest.config.mts`。`@vitejs/plugin-react` + `vite-tsconfig-paths`） |
| DOM 環境 | jsdom（既定）。DOM を使わないテストはファイル先頭の `// @vitest-environment node` で node に切り替える |
| コンポーネント検証 | React Testing Library（`@testing-library/react`）+ `@testing-library/user-event` + `@testing-library/jest-dom` |
| テスト配置 | 実装と同ディレクトリの `*.test.ts(x)`（`lib/price.test.ts` / `features/reservations/components/ReservationForm.test.tsx`） |
| セットアップ | `vitest.setup.ts`（jest-dom・`cleanup`・MSW server の起動/リセット・`next/font` などのスタブ） |
| サーバー状態 | TanStack Query（`@tanstack/react-query`）。テストは各ケースで新しい `QueryClient` |
| API | OpenAPI から生成した型（`lib/api/schema.d.ts`。`openapi-typescript`）+ API クライアント（`lib/api/client.ts`） |
| API モック | MSW（handlers: `test/msw/handlers.ts`、server: `test/msw/server.ts`） |
| 認証 | Auth0 SPA（`@auth0/auth0-react`）。テストでは `useAuth0` をモックし、トークン取得は API クライアントへの注入で差し替える |
| スタイル | Tailwind CSS（テストではクラス名を検証しない） |
| テストヘルパ | `test/render.tsx` の `renderWithProviders`（QueryClient + 認証モックを配線） |
| データ生成 | ファクトリ関数（`test/factories/`。OpenAPI の型で書く） |
| カバレッジ | Vitest（v8 provider） |

## 置き場の方針（何をどこでテストするか）

```
app/**/page.tsx, layout.tsx  … Server Component。薄く保ち、単体テストしない（データ取得と子への受け渡しだけ）
app/**/actions.ts            … Server Action。普通の async 関数として node 環境でテスト
app/api/**/route.ts          … Route Handler。GET/POST を Request で直接呼んで node 環境でテスト
features/<name>/components/  … Client Component（"use client"）。RTL でテスト
features/<name>/hooks/       … custom hook（TanStack Query を含む）。renderHook + QueryClient wrapper でテスト
lib/                         … 純粋関数・API クライアント。node 環境でテスト（UI を知らない）
```

- Server Component にロジックを置かない。分岐・整形・計算は `lib/` の純粋関数か Client Component / hook に寄せて、そちらをテストする（async Server Component は RTL で描画できない）。
- ページをまたぐ遷移・middleware・async Server Component の結合・実際の Auth0 ログインは E2E の範囲。このスキルでは扱わず、必要ならサマリで「E2E 側で確認」と書くだけにする。

## テスト実行コマンド

```bash
pnpm vitest run lib/price.test.ts -t "ケース名"         # 単一ケース（Red の失敗確認・独立性検証）
pnpm vitest run lib/price.test.ts                       # 単一ファイル（Green/Refactor の pass 確認）
pnpm vitest run                                         # 全件（CI 同様）
pnpm vitest run lib/price.test.ts --sequence.shuffle    # ランダム順序（Optimize の独立性検証）
pnpm vitest run --coverage                              # カバレッジ
pnpm typecheck                                          # tsc --noEmit
pnpm lint --fix                                         # ESLint（eslint-config-next）自動修正
pnpm gen:api                                            # OpenAPI から型を再生成（手で編集しない）
```
> パッケージマネージャは pnpm を既定とする。yarn/npm のプロジェクトでは読み替える（bootstrap が検出）。
> モノレポでは `cd {package_root} && ...` を付けて実行する。状態 JSON のパスはリポジトリルート基準で記録し、実行時は `{package_root}/` を外して渡す。

## CI / hook

- CI がテストを走らせる。push すれば Vitest / ESLint / type-check が自動実行される。
- pre-commit hook あり（husky + lint-staged）: コミット時に自動 format、lint エラーがあるとコミットがブロックされる。→ `--no-verify` は使わない（→ `commit-convention.md`）。
- lint: ESLint（`eslint-config-next`）。型: `tsc --noEmit`。

## 不変条件（全スキル共通・破ってはいけない線）

1. 1サイクル = 1テスト = 1コミット。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. TDD メタ情報をコード/テストに残さない（Red/Green/サイクル番号/PR番号/計画書§参照を書かない）。
3. テストの独立性を保つ（不変条件の中で最も優先する。崩れるとフレークや順序依存で Red/Green の信号そのものが信用できなくなる）:
   - `QueryClient` は各テストで新規に作る（`retry: false`）。キャッシュをテスト間で共有しない。
   - MSW は `afterEach(() => server.resetHandlers())`。`onUnhandledRequest: 'error'` で未定義の通信を落とす。
   - DOM は各テスト後に `cleanup()`（Vitest の `globals: true` なら RTL が自動で行う。そうでなければ `vitest.setup.ts` で明示）。
   - モックは各テスト後に戻す（`vi.clearAllMocks()` / `vi.restoreAllMocks()`、または config の `clearMocks` / `restoreMocks`）。fake timers を使ったら `vi.useRealTimers()` で戻す。
   - モジュールレベルの可変状態（シングルトンのストア・キャッシュ）をテスト間で共有しない。
4. Testing Library の作法: 要素はロール/アクセシブルネームで取得（`getByRole` / `findByRole` 優先）。非同期の表示は `findBy*` で待つ。`data-testid` は最後の手段。操作は `userEvent.setup()` で作った `user` を `await` して使う（`fireEvent` より優先）。実装詳細（state・Tailwind のクラス名・コンポーネント内部）に依存しない。見た目だけの状態は `aria-pressed` / `aria-current` / `aria-invalid` / `disabled` として表に出して検証する。
5. API 連携は MSW でモックする: 正常系は共通 handler、異常系は各テストで `server.use(...)` で上書き。実通信はしない。レスポンスは OpenAPI の型（`components['schemas'][...]`）に合わせ、生成された型ファイルは手で編集しない。
6. Server と Client の境界を守る: Server Component にロジックを置かない（`lib/` か Client Component / hook へ）。`"use client"` はできるだけ葉に寄せる。Client から `server-only` のモジュールを import しない。秘密情報を `NEXT_PUBLIC_` で露出しない。
7. Next.js のランタイム API はテストで差し替える: `next/navigation`（`useRouter` / `usePathname` / `useSearchParams` / `redirect`）・`next/cache`（`revalidatePath` 等）・`next/headers` は `vi.mock` でモックし、呼ばれ方を検証する。`next/font` は `vitest.setup.ts` でスタブする。
8. Green は最小実装のみ（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・hook 抽出・コンポーネント分割は Refactor で。
9. 承認ゲートは Red 完了後と Commit 直前の2箇所。Green / Refactor の間は自動遷移してよい。
10. ターン粒度: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
