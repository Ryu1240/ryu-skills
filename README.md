# general-skills

Claude Code 向けの **TDD ワークフロー自動化スキル**集です。Plan → Red → Green → Refactor → Commit のサイクルを、状態を永続化しながらフェーズ単位で進め、最後に Coverage Review と Test Optimize まで回すオーケストレーションを提供します。

スタックごとに 2 つのスイートに分かれています。

| スイート | 対象スタック | スラッシュコマンド | ディレクトリ |
|---|---|---|---|
| **Rails TDD** | Ruby on Rails + RSpec（マルチテナント API） | `/tdd-rails …` | [`skills/tdd-rails/`](skills/tdd-rails/) |
| **Python TDD** | Python + pytest + pydantic（CLI ツール） | `/tdd-py …` | [`skills/tdd-python/`](skills/tdd-python/) |

> 各スイートのスキルはプロジェクト固有の前提を `_shared-tdd-*/project-settings.md` に集約しています。サンプルとして架空リポジトリ **`sales-hub`**（Rails）/ **`taskcli`**（Python）を題材に記述してあるので、自分のプロジェクトに合わせて `project-settings.md` を書き換えて使ってください。

## インストール

使いたいスイートのスキルフォルダと共通契約フォルダ（`_shared-tdd-*/`）を、対象プロジェクトの `.claude/skills/` 直下にコピーします。各スキルは `.claude/skills/_shared-tdd-rails/...` のようなパスで共通契約を参照するため、コピー後もそのまま動きます。

```bash
# 例: Rails スイートを導入
cp -r skills/tdd-rails/tdd-rails* skills/tdd-rails/_shared-tdd-rails ~/your-project/.claude/skills/

# 例: Python スイートを導入
cp -r skills/tdd-python/tdd-py* skills/tdd-python/_shared-tdd-python ~/your-project/.claude/skills/
```

導入後、オーケストレーターを起動するだけで計画から実装までを進められます。

```
/tdd-rails "Lead に status カラムを追加し API で返す"
/tdd-py "Task に priority フィールドを追加"
```

2 つのスイートはスキル名・共通契約フォルダ名がすべて接頭辞（`tdd-rails*` / `tdd-py*`）で分離されているため、同じプロジェクトに同時導入しても衝突しません。

## スキル一覧

### Rails TDD（`/tdd-rails`）

Ruby on Rails + RSpec バックエンド向け。マルチテナント scope・OpenAPI 契約検証（Committee）・FactoryBot・Bullet（N+1）・Pundit・husky/lint-staged を前提にしています。

- **[tdd-rails](skills/tdd-rails/tdd-rails/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-rails-red](skills/tdd-rails/tdd-rails-red/SKILL.md)** — Red。失敗するテストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-rails-green](skills/tdd-rails/tdd-rails-green/SKILL.md)** — Green。テストを通す最小実装。
- **[tdd-rails-refactor](skills/tdd-rails/tdd-rails-refactor/SKILL.md)** — Refactor。N+1/dependent/サービス抽出などをテスト緑のまま改善。
- **[tdd-rails-commit](skills/tdd-rails/tdd-rails-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-rails-evacuator](skills/tdd-rails/tdd-rails-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-rails-coverage-review](skills/tdd-rails/tdd-rails-coverage-review/SKILL.md)** — endpoint/model × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-rails-optimize](skills/tdd-rails/tdd-rails-optimize/SKILL.md)** — RSpec テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-rails-workflow-update](skills/tdd-rails/tdd-rails-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

### Python TDD（`/tdd-py`）

Python + pytest + pydantic 向け。`StrictModel`（`extra="forbid"`）・コマンド別モジュール・docker compose 経由のテスト実行を前提にしています。

- **[tdd-py](skills/tdd-python/tdd-py/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-py-red](skills/tdd-python/tdd-py-red/SKILL.md)** — Red。失敗する pytest テストを 1 本だけ書く（schema roundtrip / logic / validation）。
- **[tdd-py-green](skills/tdd-python/tdd-py-green/SKILL.md)** — Green。テストを通す最小実装（`schemas/` の pydantic モデル等）。
- **[tdd-py-refactor](skills/tdd-python/tdd-py-refactor/SKILL.md)** — Refactor。挙動を変えずにコード品質を改善。
- **[tdd-py-commit](skills/tdd-python/tdd-py-commit/SKILL.md)** — Commit。1 サイクル分をコミットし、状態をアーカイブ。
- **[tdd-py-evacuator](skills/tdd-python/tdd-py-evacuator/SKILL.md)** — リファクタ候補・pytest テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-py-coverage-review](skills/tdd-python/tdd-py-coverage-review/SKILL.md)** — pydantic モデル/関数 × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-py-coverage-overlap](skills/tdd-python/tdd-py-coverage-overlap/SKILL.md)** — pytest-cov の coverage-context で意味的なテスト重複を検出（削除/統合候補を提示）。
- **[tdd-py-optimize](skills/tdd-python/tdd-py-optimize/SKILL.md)** — pytest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-py-workflow-update](skills/tdd-python/tdd-py-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 設計のポイント

- **1 サイクル = 1 テスト = 1 コミット**。粒度を固定し、TDD メタ情報はコードに残しません。
- **状態の永続化**: 進行状態を `.claude/tdd-workflow/` の JSON に保存し、いつでも中断・再開できます。
- **承認ゲートは 2 箇所**（Red 完了後・Commit 直前）。既定はフェーズ停止、`--auto` で一気通貫。
- **共通契約は単一情報源**: パス・テストコマンド・不変条件・状態スキーマ・コミット規約を `_shared-tdd-*/` にまとめ、全スキルが参照します。
