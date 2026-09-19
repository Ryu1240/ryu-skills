# Universal TDD スイート（`/tdd`）

**任意の言語・テストフレームワーク**向けの汎用 TDD ワークフロー自動化スキル群です。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

専用プラグイン（`tdd-rails` / `tdd-python` / `tdd-frontend` / `tdd-node` / `tdd-go` / `tdd-monorepo`）が用意されていないスタック — Rust, Java/Kotlin, PHP, C#, Elixir, Swift, Dart, Scala, Ruby(非Rails), React, その他 — はこれを使います。

## 設計: 言語知識をスキル本体から追い出す

専用プラグインはスキル本文に言語固有の手順（`bundle exec rspec`、implicit subject、Bullet の N+1 …）を持っています。汎用版はそれを**一切持ちません**。代わりに:

1. **`project-settings.md` が言語知識のすべてを保持する** — テスト実行コマンド（単一ケース/単一ファイル/全件/ランダム順序/カバレッジ/lint/静的解析）、テスト配置と命名規則、テストデータとモックの手段、**テスト独立性の担保方法**、**言語固有の慣習（イディオム）**。フェーズスキルは推測せずここだけを読みます。書かれていなければ**推測せず停止**します。
2. **不変条件に「既存テストの慣習を踏襲する」を据える** — 新規テストは対象に最も近い既存テストを読み、その書式・命名・アサーションスタイル・セットアップ方法に揃えます。**このリポの流儀が唯一の正解**であり、一般論の「ベストプラクティス」を持ち込みません。これが言語非依存で最も効く汎用機構です。

つまり、状態機械・承認ゲート・1サイクル=1テスト=1コミットの規律・JSON 永続化という**言語に関係ない価値**をそのまま享受しつつ、言語依存部分は設定と実物観察で埋めます。

## bootstrap は対話式

`/tdd-bootstrap` が:

1. **走査** — マニフェスト（`go.mod` / `Cargo.toml` / `pom.xml` / `composer.json` / `mix.exs` / `pubspec.yaml` / `*.csproj` / `build.sbt` …）から言語とテストランナーを判定。スクリプト定義（`package.json` の `scripts` / `Makefile` / `justfile` / CI 設定）に**実際のコマンドがあればそれを最優先**。既存テストを実際に Read してケース記述スタイルと独立性の担保方法を抽出。
2. **ヒアリング** — 検出できなかった項目・推定止まりの項目**だけ**を対話で確認（AskUserQuestion）。優先度1（テストランナー・単一ケース/単一ファイル実行コマンド・対象パッケージ）は必ず確定させます。優先度2（独立性の担保方法・ランダム順序・言語固有の慣習）で品質を、優先度3（lint・カバレッジ・追加不変条件）で仕上げを。
3. **生成** — 承認後に `project-settings.md` の `{{...}}` をすべて埋めて `.claude/skills/_shared-tdd/` を作成。

**マニフェストが1つも見つからない場合でも、対話だけで成立します。** 分からない項目は「未導入」「未対応」と明記され、推測で捏造されません。

> 未設定の判定はプレースホルダの残存（`{{`）で行います。`/tdd` は Phase 0 で `{{` が残っていれば bootstrap を促して停止し、テストコマンド不明のまま走り出すことを防ぎます。

## 専用プラグインとの使い分け

| 状況 | 使うもの |
|---|---|
| Rails + RSpec | `tdd-rails`（multi-tenant / OpenAPI 契約 / Bullet まで踏み込む） |
| Python + pytest | `tdd-python` |
| Vue + Vitest | `tdd-frontend`（role 取得 / MSW まで踏み込む） |
| TS/Node バックエンド | `tdd-node`（レイヤー衛生 / DI / Zod まで踏み込む） |
| Go バックエンド | `tdd-go`（テーブル駆動 / httptest / `-race` まで踏み込む） |
| Rails + Vue モノレポ | `tdd-monorepo` |
| **上記以外のすべて** | **`tdd-universal`** |

専用版の方が言語固有の作法まで指示できるので、該当するなら専用版を推奨します（bootstrap も検出時にその旨を案内します）。1 リポジトリで有効化するプラグインは **1 つだけ**にしてください（同じ skill 名を提供するため）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-universal@general-skills
```

> ⚠️ **権限について**: 汎用版はテスト実行コマンドを事前に特定できないため、フェーズスキルの `allowed-tools` は `Bash` をパターン限定できません（専用版は `Bash(bundle:*)` 等に絞っています）。権限を絞りたい場合は、bootstrap 後に判明したコマンドに合わせて各 SKILL.md の `allowed-tools` を編集するか、`.claude/settings.json` の permissions で制御してください。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。Phase 0 で project-settings の未設定を検出し bootstrap を呼ぶ。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — **対話型**初回セットアップ。走査＋ヒアリングで `.claude/skills/_shared-tdd/` を生成（承認制）。言語検出表・ランナー別コマンド表を内蔵。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整・追記・修正（diff 提案→承認→適用。コマンドは実在を裏取り）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。**既存テストの慣習を抽出**してから、失敗するテストを 1 本だけ書く。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（既存実装の慣習も踏襲）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。重複除去・命名・責務分解・データアクセス効率・エラー処理の一貫性・lint をテスト緑のまま。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を pre-commit hook 準拠でコミットし、状態をアーカイブ（既存 `git log` の規約を優先）。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用・編集しない）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — 公開インターフェイス × テストカテゴリ（境界値/空/異常系/外部依存失敗/認可/契約/冪等性）で不足を補完。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — テストの最適化（セットアップ巻き上げ・パラメータ化・アサーション集約）。独立性を担保し、検証できなかった項目は明記。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — **言語知識のすべて**（テストコマンド・配置/命名・独立性・イディオム・不変条件）
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# 初回（設定が無ければ bootstrap が対話で立ち上がる）
/tdd "在庫チェックを在庫サービスに切り出して境界値も検証する"

# 手動で設定を作る / 作り直す
/tdd-bootstrap
/tdd-bootstrap --force

# 設定をあとから直す
/tdd-project-settings-update "テストは make test で走らせる"

# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 既存ワークフローを実行（既定はフェーズ停止）/ 一気通貫
/tdd tdd-20260613-101500
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
