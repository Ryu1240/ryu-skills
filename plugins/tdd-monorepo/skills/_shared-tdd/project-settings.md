# TDD スキル共通設定（Project Settings）— retail-hub

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> retail-hub は Rails(RSpec) バックエンド + Vue3/TypeScript(Vitest) フロントエンド のモノレポ。

## 2つのエコシステム

| | backend | frontend |
|---|---|---|
| パッケージ | `api/`（Rails） | `web/`（Vue 3 + Vite） |
| テスト | RSpec | Vitest + Vue Testing Library + user-event |
| spec 配置 | `api/spec/{models,requests,services,resources,workers,policies,...}/` | 実装と同ディレクトリの `*.spec.ts`（`web/src/**/*.spec.ts`） |
| データ生成 | FactoryBot（`api/spec/factories/*.rb`、trait あり） | ファクトリヘルパ（`web/src/testUtils/factory/`） |
| モック | WebMock / shared context（`api/spec/support/`） | MSW（`web/src/testUtils/mocks/handlers/`） |
| 契約検証 | Committee（`assert_response_schema_confirm(200)`、OpenAPI） | OpenAPI 由来の型を利用（MSW handler を schema と整合させる） |
| 状態管理 | — | Pinia |
| カバレッジ | SimpleCov | Vitest（v8 provider、`yarn coverage`） |

## テスト実行コマンド

backend（Rails / RSpec）:
```bash
cd api && bundle exec rspec spec/path/to/foo_spec.rb           # 単一ファイル
cd api && bundle exec rspec spec/path/to/foo_spec.rb:42        # 行指定
cd api && bundle exec parallel_rspec -n 4                       # 全件並列
# Docker 経由（起動中コンテナに exec。環境差異を避けたい場合）
docker compose exec api bundle exec rspec spec/path/to/foo_spec.rb
```

frontend（Vue / Vitest）（yarn を既定。npm/pnpm のプロジェクトでは読み替え）:
```bash
cd web && yarn test src/path/to/foo.spec.ts     # 単一ファイル
cd web && yarn test                              # 全件（watch）
cd web && yarn test:ci                           # 全件 1 回（vitest run。CI 同様）
cd web && yarn coverage                          # カバレッジ
cd web && yarn typecheck                         # 型チェック（vue-tsc --noEmit）
```

## CI / hook

- CI がテストを走らせる。push すれば backend/frontend それぞれのテスト・lint が（変更パスに応じて）自動実行される。
- pre-commit hook あり（husky + lint-staged）: コミット時に自動 format、lint エラーがあるとコミットがブロックされる。→ `--no-verify` は使わない（→ `commit-convention.md`）。
- lint: backend=Rubocop（`api/.rubocop.yml`）/ frontend=ESLint(+Prettier)（`web/`）。

## 不変条件（全スキル共通・破ってはいけない線）

1. 1サイクル = 1テスト = 1コミット。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. TDD メタ情報をコード/spec に残さない（Red/Green/PR番号/サイクル番号/計画書§参照を書かない）。
3. テストの独立性を保つ（不変条件の中で最も優先する。崩れるとフレークや順序依存で Red/Green の信号そのものが信用できなくなる）:
   - backend: multi-tenant scope を張る（`ApplicationRecord.client = client` / `ActsAsTenant.with_tenant(client)`。request spec は `include_context 'with current user'`）。
   - frontend: MSW handler を各テストでリセット（`afterEach(resetHandlers)`）、Pinia は各テスト新規（`setActivePinia(createPinia())`）。グローバル状態を共有しない。
4. 各エコシステムの慣習を踏襲:
   - backend: 明示的な `subject` 宣言を避ける（implicit subject）。factory は `create(:x, client: current_client)`。shoulda matchers。
   - frontend: 要素はロール/アクセシブルネームで取得（`getByRole`/`findByRole` 優先、実装詳細に依存しない。`data-testid` は最後の手段）。操作は user-event。
5. API 連携の契約検証:
   - backend: request spec は `assert_response_schema_confirm(200)`（Committee）で OpenAPI response schema を担保。
   - frontend: API 連携は MSW でモック（正常系は共通 handler、異常系は各テストで `server.use(...)` 上書き）。実通信はしない。
6. Green は最小実装のみ（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出は Refactor で。
7. 承認ゲートは Red 完了後と Commit 直前の2箇所。Green / Refactor の間は自動遷移してよい。
8. ターン粒度: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
