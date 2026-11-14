# Frontend TDD スイート（`/tdd`）

Vue 3 + Vite + Vitest フロントエンド向けの TDD ワークフロー自動化スキル群です。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`storefront`**（Vue 3 + Vite + TypeScript の SPA）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| アプリ | リポジトリ直下の Vite アプリ |
| フレームワーク | Vue 3（Composition API）+ TypeScript |
| テスト | Vitest（`src/**/*.spec.ts` 併置） |
| コンポーネント検証 | Vue Testing Library（`@testing-library/vue`）+ user-event |
| API モック | MSW（`src/testUtils/mocks/`） |
| 状態管理 | Pinia |
| データ生成 | ファクトリヘルパ（`src/testUtils/factory/`） |
| カバレッジ | Vitest（v8 provider） |
| lint / hook | ESLint(+Prettier) + husky/lint-staged |
| CI | GitHub Actions / CircleCI |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせてこのファイルを書き換えてください**（`/tdd-bootstrap` が自動生成します）。

## インストール

Claude Code のマーケットプレイス経由で導入します。

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-frontend@general-skills
```

導入後、フロントエンドプロジェクトの `.claude/settings.json` で本 plugin を有効化してください（他スタックのプロジェクトでは無効化しておくと skill 名の衝突を避けられます）。

plugin 同梱の `_shared-tdd/project-settings.md` は架空リポ `storefront` を題材にしたテンプレです。**初めて `/tdd` を実行すると Phase 0 で `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します**。承認するとプロジェクトを走査してプロジェクト固有の設定を `.claude/skills/_shared-tdd/` に生成するので、事前準備は不要です。手動で走らせたい場合は `/tdd-bootstrap`（既存があれば確認）または `/tdd-bootstrap --force`（上書き再生成）を実行してください。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の有無を判定し、未生成なら tdd-bootstrap を呼ぶ。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。フロントエンドプロジェクトを走査し、`.claude/skills/_shared-tdd/` にプロジェクト固有設定（`project-settings.md` + テンプレ 3 ファイル）を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。手編集を潰さず、メモリ同期も提案）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。失敗する Vitest テストを 1 本だけ書き、意図通り失敗することを確認。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（component/composable/store/util）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。composable 抽出/コンポーネント分割/再レンダリング衛生などをテスト緑のまま改善。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミットし、状態をアーカイブ。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — component/composable × テストカテゴリのマトリクスで不足テストを補完。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — Vitest テストの最適化（独立性を担保。承認後に適用）。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — パス・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 自由テキストから計画 → 承認すれば同じセッションのまま Red へ進む
/tdd "商品一覧に在庫フィルタを追加し composable で状態管理"

# 中断したワークフローを別セッションで再開（既定はフェーズ停止）
/tdd tdd-20260613-101500

# 一気通貫モード
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。

1 つのワークフローは計画から最適化まで同じセッションで進めるのが基本です（計画時の分析や判断の経緯が次のフェーズに活きるため）。状態 JSON は中断・compact からの再開用に書き出されます。
