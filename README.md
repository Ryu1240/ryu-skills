# general-skills

Claude Code 向け **TDD ワークフロー自動化スキル**の plugin マーケットプレイスです。Plan → Red → Green → Refactor → Commit のサイクルを、状態を永続化しながらフェーズ単位で進め、最後に Coverage Review と Test Optimize まで回すオーケストレーションを提供します。

スタックごとに 4 つの plugin に分かれています（うち `tdd-monorepo` は複数スタック混在向け）。

| Plugin | 対象スタック | スラッシュコマンド | ディレクトリ |
|---|---|---|---|
| **`tdd-rails`** | Ruby on Rails + RSpec（マルチテナント API） | `/tdd …` | [`plugins/tdd-rails/`](plugins/tdd-rails/) |
| **`tdd-python`** | Python + pytest + pydantic（CLI ツール） | `/tdd …` | [`plugins/tdd-python/`](plugins/tdd-python/) |
| **`tdd-frontend`** | Vue 3 + Vite + Vitest（SPA フロントエンド） | `/tdd …` | [`plugins/tdd-frontend/`](plugins/tdd-frontend/) |
| **`tdd-monorepo`** | Rails backend + Vue frontend のモノレポ（エコシステム自動判定） | `/tdd …` | [`plugins/tdd-monorepo/`](plugins/tdd-monorepo/) |

> 各 plugin の skill はプロジェクト固有の前提を `skills/_shared-tdd/project-settings.md` に集約しています。サンプルとして架空リポジトリ **`sales-hub`**（Rails）/ **`taskcli`**（Python）/ **`storefront`**（フロントエンド）/ **`retail-hub`**（モノレポ）を題材に記述してあるので、自分のプロジェクトに合わせて `project-settings.md` を書き換えて使ってください。

## インストール

Claude Code の plugin マーケットプレイスとして登録し、使いたい plugin をインストールします。

```text
# 1. マーケットプレイスを追加（1 度だけ）
/plugin marketplace add SC-Ryu1240/general-skills

# 2. 使いたい plugin を導入
/plugin install tdd-rails@general-skills      # Rails プロジェクト用
/plugin install tdd-python@general-skills     # Python プロジェクト用
/plugin install tdd-frontend@general-skills   # Vue/Vite フロントエンド用
/plugin install tdd-monorepo@general-skills   # Rails+Vue モノレポ用
```

各 plugin は同じ skill 名（`/tdd`, `/tdd-red`, `/tdd-green`, …）を提供します。**プロジェクトごとに 1 つだけを `.claude/settings.json` で有効化するのが推奨運用**です。単体スタックのリポジトリはスタックに対応する plugin を、**Rails+Vue のモノレポでは `tdd-monorepo` を選びます**（`tdd-monorepo` は 1 スキルセットで backend/frontend をエコシステム自動判定するため、単体プラグインの同時有効化＝skill 名衝突を避けられます）。単体プラグインを複数同時に有効化すると skill 名が衝突するので避けてください。

導入後はオーケストレーターを起動するだけで計画から実装までを進められます。初回起動時はプロジェクト固有の TDD 設定が無いことを検出すると、`tdd-bootstrap` が呼び出されてプロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md などを生成します（承認制）。

```text
# 初回（または .claude/skills/_shared-tdd/ が無いとき）
/tdd "Lead に status カラムを追加し API で返す"
# → 走査結果が提示されるので承認すると _shared-tdd/ が生成され、その後ワークフロー開始

# 手動で再生成する場合
/tdd-bootstrap          # 既存があれば確認 / 無ければ生成
/tdd-bootstrap --force  # 上書き再生成
```

## Plugin 一覧

### `tdd-rails`（`/tdd`）

Ruby on Rails + RSpec バックエンド向け。マルチテナント scope・OpenAPI 契約検証（Committee）・FactoryBot・Bullet（N+1）・Pundit・husky/lint-staged を前提にしています。詳細は [`plugins/tdd-rails/README.md`](plugins/tdd-rails/README.md) を参照。

- **[tdd](plugins/tdd-rails/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-rails/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。Rails プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。
- **[tdd-project-settings-update](plugins/tdd-rails/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-rails/skills/tdd-red/SKILL.md)** — Red。失敗するテストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-green](plugins/tdd-rails/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装。
- **[tdd-refactor](plugins/tdd-rails/skills/tdd-refactor/SKILL.md)** — Refactor。N+1/dependent/サービス抽出などをテスト緑のまま改善。
- **[tdd-commit](plugins/tdd-rails/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-rails/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-rails/skills/tdd-coverage-review/SKILL.md)** — endpoint/model × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-rails/skills/tdd-optimize/SKILL.md)** — RSpec テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-rails/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-python`（`/tdd`）

Python + pytest + pydantic 向け。`StrictModel`（`extra="forbid"`）・コマンド別モジュール・docker compose 経由のテスト実行を前提にしています。詳細は [`plugins/tdd-python/README.md`](plugins/tdd-python/README.md) を参照。

- **[tdd](plugins/tdd-python/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-python/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。Python プロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。
- **[tdd-project-settings-update](plugins/tdd-python/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-python/skills/tdd-red/SKILL.md)** — Red。失敗する pytest テストを 1 本だけ書く（schema roundtrip / logic / validation）。
- **[tdd-green](plugins/tdd-python/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（`schemas/` の pydantic モデル等）。
- **[tdd-refactor](plugins/tdd-python/skills/tdd-refactor/SKILL.md)** — Refactor。挙動を変えずにコード品質を改善。
- **[tdd-commit](plugins/tdd-python/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分をコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-python/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・pytest テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-python/skills/tdd-coverage-review/SKILL.md)** — pydantic モデル/関数 × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-coverage-overlap](plugins/tdd-python/skills/tdd-coverage-overlap/SKILL.md)** — pytest-cov の coverage-context で意味的なテスト重複を検出（削除/統合候補を提示）。
- **[tdd-optimize](plugins/tdd-python/skills/tdd-optimize/SKILL.md)** — pytest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-python/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-frontend`（`/tdd`）

Vue 3 + Vite + Vitest フロントエンド向け。Vue Testing Library（role 取得）・MSW（API モック）・Pinia・ESLint/Prettier・husky/lint-staged を前提にしています。詳細は [`plugins/tdd-frontend/README.md`](plugins/tdd-frontend/README.md) を参照。

- **[tdd](plugins/tdd-frontend/skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](plugins/tdd-frontend/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。フロントエンドプロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。
- **[tdd-project-settings-update](plugins/tdd-frontend/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-frontend/skills/tdd-red/SKILL.md)** — Red。失敗する Vitest テストを 1 本だけ書く（component/composable/store/util）。
- **[tdd-green](plugins/tdd-frontend/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（Composition API・MSW handler 等）。
- **[tdd-refactor](plugins/tdd-frontend/skills/tdd-refactor/SKILL.md)** — Refactor。composable 抽出/コンポーネント分割/再レンダリング衛生などをテスト緑のまま改善。
- **[tdd-commit](plugins/tdd-frontend/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-frontend/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-frontend/skills/tdd-coverage-review/SKILL.md)** — component/composable × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-frontend/skills/tdd-optimize/SKILL.md)** — Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-frontend/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### `tdd-monorepo`（`/tdd`）

Rails/RSpec backend + Vue/Vitest frontend の**モノレポ**向け。1 スキルセットで `ecosystem`（backend/frontend）を自動判定して各フェーズを分岐します。単体プラグインを複数同時有効化する際の skill 名衝突を避けるため、モノレポでは**これ 1 つだけ**を有効化します。詳細は [`plugins/tdd-monorepo/README.md`](plugins/tdd-monorepo/README.md) を参照。

- **[tdd](plugins/tdd-monorepo/skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 で backend/frontend を自動判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](plugins/tdd-monorepo/skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。モノレポの backend/frontend パッケージを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。
- **[tdd-project-settings-update](plugins/tdd-monorepo/skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](plugins/tdd-monorepo/skills/tdd-red/SKILL.md)** — Red。ecosystem に応じて失敗する RSpec / Vitest テストを 1 本だけ書く。
- **[tdd-green](plugins/tdd-monorepo/skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（Rails or Vue/TS）。
- **[tdd-refactor](plugins/tdd-monorepo/skills/tdd-refactor/SKILL.md)** — Refactor。backend=N+1/dependent/サービス抽出、frontend=composable 抽出/コンポーネント分割。
- **[tdd-commit](plugins/tdd-monorepo/skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](plugins/tdd-monorepo/skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](plugins/tdd-monorepo/skills/tdd-coverage-review/SKILL.md)** — ecosystem 別の（対象 × テストカテゴリ）マトリクスで不足テストを補完。
- **[tdd-optimize](plugins/tdd-monorepo/skills/tdd-optimize/SKILL.md)** — RSpec / Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](plugins/tdd-monorepo/skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新（`ecosystem` は保護）。

## 設計のポイント

- **1 サイクル = 1 テスト = 1 コミット**。粒度を固定し、TDD メタ情報はコードに残しません。
- **状態の永続化**: 進行状態を `.claude/tdd-workflow/` の JSON に保存し、いつでも中断・再開できます。
- **承認ゲートは 2 箇所**（Red 完了後・Commit 直前）。既定はフェーズ停止、`--auto` で一気通貫。
- **共通契約は単一情報源**: パス・テストコマンド・不変条件・状態スキーマ・コミット規約を `_shared-tdd/` にまとめ、全 skill が参照します。
