# Monorepo TDD スイート（`/tdd`）

**Rails/RSpec バックエンド + Vue/Vitest フロントエンドのモノレポ**向けの TDD ワークフロー自動化スキル群です。1 スキルセットで **backend / frontend をエコシステム自動判定**しながら、Plan → Red → Green → Refactor → Commit のサイクルを回し、Coverage Review と Test Optimize まで進めます。

サンプルとして架空モノレポ **`retail-hub`**（`api/` = Rails、`web/` = Vue 3 + Vite）を題材に記述しています。

## なぜ専用プラグインなのか

単体スタック用の `tdd-rails` / `tdd-frontend` / `tdd-python` は同じ skill 名（`/tdd`, `/tdd-red`, …）を提供するため、**モノレポで複数を同時有効化すると skill 名が衝突**します（orchestrator の内部呼び出しがどのプラグインの skill を呼ぶか未定義になる）。

`tdd-monorepo` は **1 プラグインに backend/frontend 両対応を集約**し、`workflow-{id}.json` の `ecosystem` フィールドで各フェーズが分岐します。**モノレポではこれ 1 つだけを有効化**すれば、`/tdd` がタスク内容から backend(Rails) / frontend(Vue) を判定して適切なフローを実行します（1 ワークフロー = 1 エコシステム）。

## 前提スタック

| 項目 | backend | frontend |
|---|---|---|
| パッケージ | `api/`（Rails） | `web/`（Vue 3 + Vite） |
| テスト | RSpec | Vitest + Vue Testing Library + user-event |
| データ生成 | FactoryBot | ファクトリヘルパ（`web/src/testUtils/factory/`） |
| モック | WebMock / shared context | MSW（`web/src/testUtils/mocks/`） |
| 契約検証 | Committee（OpenAPI） | OpenAPI 型 + MSW handler 整合 |
| 状態管理 / N+1 / 権限 | multi-tenant, Bullet, Pundit | Pinia |
| lint / hook | Rubocop + husky/lint-staged | ESLint(+Prettier) + husky/lint-staged |
| CI | 変更パスに応じ backend/frontend を自動実行 | 同左 |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。**自分のモノレポに合わせてこのファイルを書き換えてください**（`/tdd-bootstrap` が backend/frontend パッケージを走査して自動生成します）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-monorepo@general-skills
```

モノレポの `.claude/settings.json` で **`tdd-monorepo` だけを有効化**してください（`tdd-rails` / `tdd-frontend` は無効化。同時有効化は skill 名衝突の原因になります）。

初回 `/tdd` 実行時、Phase 0 で `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します。承認すると backend(Rails) / frontend(Vue) の両パッケージを走査してプロジェクト固有設定を生成します。手動なら `/tdd-bootstrap`（既存があれば確認）/ `/tdd-bootstrap --force`（上書き再生成）。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 で backend/frontend を自動判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。モノレポの backend/frontend パッケージを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定を生成（承認制）。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。ecosystem に応じて失敗する RSpec / Vitest テストを 1 本だけ書く。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（Rails or Vue/TS）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。backend=N+1/dependent/サービス抽出、frontend=composable 抽出/コンポーネント分割 をテスト緑のまま。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — ecosystem 別の（対象 × テストカテゴリ）マトリクスで不足テストを補完。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — RSpec / Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新（`ecosystem` は保護）。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — 2 エコシステムのパス・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定・`ecosystem` 含む）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# Notion タスクから計画（backend/frontend は自動判定）
/tdd https://www.notion.so/<task-id>

# 自由テキストから計画
/tdd "商品一覧に在庫フィルタを追加し composable で状態管理"   # → frontend と判定
/tdd "Lead に status カラムを追加し API で返す"                # → backend と判定

# 既存ワークフローを実行（既定はフェーズ停止）
/tdd tdd-20260613-101500

# 一気通貫モード
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
