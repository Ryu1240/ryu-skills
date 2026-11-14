# TDD スキル共通設定（Project Settings）— sales-hub

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> sales-hub は Rails(RSpec) バックエンドの単一スタック（マルチテナント Rails API）。

## 構成とテスト

| | backend |
|---|---|
| パッケージ | リポジトリ直下（Rails アプリ） |
| テスト | RSpec |
| spec 配置 | `spec/{models,requests,services,resources,workers,batch_workers,policies,mailers,strategies,lib,...}/` |
| データ生成 | FactoryBot（`spec/factories/*.rb`、trait あり） |
| モック | WebMock / shared context（`spec/support/`） |
| 契約検証 | Committee（`assert_response_schema_confirm(200)`、OpenAPI） |
| カバレッジ | SimpleCov |

## テスト実行コマンド

backend（Rails / RSpec）:
```bash
bundle exec rspec spec/path/to/foo_spec.rb           # 単一ファイル
bundle exec rspec spec/path/to/foo_spec.rb:42        # 行指定
bundle exec parallel_rspec -n 4                       # 全件並列
# Docker 経由（起動中コンテナに exec。環境差異を避けたい場合）
docker compose exec app bundle exec rspec spec/path/to/foo_spec.rb
```

## CI / hook

- CircleCI がテストを走らせる。push すれば RSpec / lint / brakeman が自動実行される。
- pre-commit hook あり（husky + lint-staged）: コミット時に自動 format、lint エラーがあるとコミットがブロックされる。→ `--no-verify` は使わない（→ `commit-convention.md`）。
- lint: backend=Rubocop（`.rubocop.yml`）。

## 不変条件（全スキル共通・破ってはいけない線）

1. 1サイクル = 1テスト = 1コミット。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. TDD メタ情報をコード/spec に残さない（Red/Green/PR番号/サイクル番号/計画書§参照を書かない）。
3. multi-tenant scope を張る（不変条件の中で最も優先する。漏れると他テナントのデータが見える・書ける不具合になり、テストも他テナントのレコードを拾って信号が信用できなくなる）: モデル/サービスは `ApplicationRecord.client = client`（または `ActsAsTenant.with_tenant(client)`）でテナント文脈を設定。クエリは tenant scoped に。request spec は `include_context 'with current user'` を使う。
4. RSpec の慣習を踏襲: 明示的な `subject` 宣言は避ける（implicit subject）。factory は `create(:x, client: current_client)` でテナントを渡す。shoulda matchers を活用。
5. request spec は OpenAPI 契約を検証: `assert_response_schema_confirm(200)`（Committee）で response schema を担保。
6. Green は最小実装のみ（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出・N+1対策は Refactor で。
7. 承認ゲートは Red 完了後と Commit 直前の2箇所。Green / Refactor の間は自動遷移してよい。
8. ターン粒度: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
