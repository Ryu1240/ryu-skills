# TDD スキル共通設定（Project Settings）— storefront

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> storefront は **Vue 3 + Vite + TypeScript** の SPA フロントエンド（Vitest でテスト）。

## 構成とテスト

| | frontend |
|---|---|
| パッケージ | リポジトリ直下（Vite アプリ） |
| フレームワーク | Vue 3（Composition API）+ TypeScript。状態管理は Pinia |
| テスト | Vitest |
| コンポーネント検証 | Vue Testing Library（`@testing-library/vue`）+ `@testing-library/user-event` |
| spec 配置 | 実装と同ディレクトリの `*.spec.ts`（`src/**/*.spec.ts`） |
| データ生成 | ファクトリヘルパ（`src/testUtils/factory/`） |
| API モック | MSW（handlers: `src/testUtils/mocks/handlers/`、server: `src/testUtils/mocks/server.ts`） |
| カバレッジ | Vitest（v8 provider、`yarn coverage`） |

## テスト実行コマンド

**frontend（Vue / Vitest）**:
```bash
yarn test src/path/to/foo.spec.ts        # 単一ファイル（Vitest は該当ファイルのみ実行）
yarn test                                # 全件（watch）
yarn test:ci                             # 全件 1 回（vitest run。CI 同様）
yarn coverage                            # カバレッジ（vitest run --coverage）
yarn typecheck                           # 型チェック（vue-tsc --noEmit）
```
> パッケージマネージャは yarn を既定とする。npm/pnpm のプロジェクトでは `npm run` / `pnpm` に読み替える（bootstrap が検出）。

## CI / hook（重要）

- **CI がテストを走らせる**。push すれば Vitest / ESLint / type-check が自動実行される。
- **pre-commit hook あり（husky + lint-staged）**: コミット時に自動 format、lint エラーがあるとコミットがブロックされる。→ `--no-verify` は**絶対禁止**（hook を無効化しない）。
- lint: ESLint（+ Prettier）。`yarn lint --fix`。

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. **TDD メタ情報をコード/spec に残さない**（Red/Green/PR番号/サイクル番号/計画書§参照を書かない）。
3. **テストの独立性を必ず保つ（最重要）**: MSW handler は各テストでリセット（`afterEach(() => server.resetHandlers())`）。Pinia は各テストで新規（`setActivePinia(createPinia())`）。グローバル状態・モジュールキャッシュをテスト間で共有しない。
4. **Testing Library の作法を踏襲**: 要素はロール/アクセシブルネームで取得（`getByRole` / `findByRole` 優先）、実装詳細（内部 state・CSS クラス・コンポーネント内部）に依存しない。`data-testid` は最後の手段。ユーザー操作は `user-event`（`fireEvent` より優先）。
5. **API 連携は MSW でモック**: 正常系は共通 handler（`src/testUtils/mocks/handlers/`）、異常系は各テストで `server.use(...)` で上書き。実際の通信はしない。
6. **Green は最小実装のみ**（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・composable 抽出・コンポーネント分割は Refactor で。
7. **承認ゲートは Red 完了後と Commit 直前の2箇所**。Green / Refactor の間は自動遷移してよい。
8. **ターン粒度**: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
