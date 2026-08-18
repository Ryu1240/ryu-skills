# Node/TypeScript バックエンド TDD スイート（`/tdd`）

**TypeScript + Node.js のバックエンド**（HTTP API サーバー）向けの TDD ワークフロー自動化スキル群です。テストランナーは **Vitest** を前提にしています。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`order-api`**（TypeScript + Node.js の注文 API）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| ランタイム | Node.js 20+ / TypeScript（ESM） |
| Web フレームワーク | Express / Fastify / Hono / NestJS のいずれか |
| テスト | Vitest（`src/**/*.test.ts` 併置） |
| HTTP テスト | Supertest（またはフレームワークの inject） |
| データ生成 | ファクトリ関数（`src/testUtils/factory/`） |
| モック | `vi.mock` / `vi.spyOn`（内部）、MSW（外部 HTTP API） |
| DB | Prisma / Drizzle / TypeORM 等。テストはトランザクションロールバック |
| スキーマ検証 | Zod（境界で `parse`） |
| lint / hook | ESLint(+Prettier) + husky/lint-staged |
| CI | GitHub Actions / CircleCI |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせて書き換えてください**（`/tdd-bootstrap` が自動生成します）。

## レイヤー構成を前提にした指示

このプラグインは**レイヤードアーキテクチャ**を前提に、各フェーズが具体的に踏み込みます。

```
src/routes/       … HTTP 層。Zod での検証とレスポンス整形のみ
src/services/     … ビジネスロジック。HTTP を知らない
src/repositories/ … データアクセス。SQL/ORM をここに閉じ込める
src/schemas/      … Zod スキーマと型
```

- **Red** はレイヤー別のテスト作法を指示（schema=`safeParse`、service=DI でモック注入、route=Supertest、repository=トランザクションロールバック）
- **Refactor** は Node/TS 固有の観点で改善（**レイヤー逆流**の解消 / **ループ内 await の N+1** / **`await` 漏れ・浮いた Promise** / エラークラスへの統一 / `any`・`as` の除去）
- **Coverage Review** は 400/401/403/404/409、外部 API 失敗、DB 制約違反、冪等性まで含むマトリクスで抜けを埋めます

> 実際のディレクトリ名が違っても構いません。`tdd-bootstrap` が `src/` の実態（`controllers` / `usecases` / `handlers` 等）を読み取って project-settings.md に反映します。

## 他プラグインとの使い分け

| 状況 | 使うもの |
|---|---|
| **TS/Node バックエンド（API サーバー・ワーカー）** | **`tdd-node`** |
| Vue + Vitest のフロントエンド | `tdd-frontend` |
| Rails + RSpec | `tdd-rails` |
| Python + pytest | `tdd-python` |
| Rails + Vue モノレポ | `tdd-monorepo` |
| 上記以外の言語 | `tdd-universal` |

1 リポジトリで有効化するプラグインは **1 つだけ**にしてください（同じ skill 名を提供するため）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-node@general-skills
```

導入後、初回 `/tdd` 実行時に Phase 0 が `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します。手動なら `/tdd-bootstrap`（既存があれば確認）/ `/tdd-bootstrap --force`（上書き再生成）。

**モノレポにも対応**します。bootstrap が workspaces / turborepo / nx を検出し、対象パッケージを選ばせたうえでコマンドに `cd {package_root}` を付けて生成します。

> Jest のプロジェクトでも使えます。bootstrap が検出し、単一ケース実行を `jest -t`、ランダム順序を `--randomize` に読み替えてコマンド節を差し替えます。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。モノレポ対応でパッケージ・ランナー・レイヤー構成・独立性の担保方法を走査し、不明点は対話で確認して設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整（コマンドは `package.json` の scripts で実在を裏取り）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。レイヤー別の作法で失敗する Vitest テストを 1 本だけ書く。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（DI・Zod 検証・エラークラス・レイヤー遵守）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。レイヤー衛生 / N+1 / 非同期 / エラー処理 / 型の健全性 をテスト緑のまま改善。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。1 サイクル分を husky/lint-staged 準拠でコミット（マイグレーションも含める）。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性（過剰モックの指摘含む）に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — エンドポイント/サービス × テストカテゴリのマトリクスで不足を補完。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — Vitest テストの最適化（`it.each` 化・セットアップ巻き上げ）。`--sequence.shuffle` と並列実行で独立性を検証。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — レイヤー構成・テストコマンド・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# 自由テキストから計画
/tdd "注文APIに在庫チェックを追加し在庫不足なら409を返す"

# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 既存ワークフローを実行（既定はフェーズ停止）/ 一気通貫
/tdd tdd-20260613-101500
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
