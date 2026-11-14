# TDD スキル共通設定（Project Settings）— order-api

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> order-api は TypeScript + Node.js のバックエンド（HTTP API サーバー）。テストは Vitest。UI を持たない。

## 構成とテスト

| | backend（Node / TypeScript） |
|---|---|
| パッケージ | リポジトリ直下（モノレポなら `packages/api/` 等。bootstrap が確定） |
| ランタイム | Node.js 20+ / TypeScript（ESM） |
| Web フレームワーク | Express / Fastify / Hono / NestJS のいずれか |
| テスト | Vitest |
| HTTP テスト | Supertest（またはフレームワークの inject/テストクライアント） |
| テスト配置 | 実装と同ディレクトリの `*.test.ts`（`src/**/*.test.ts`） |
| データ生成 | ファクトリ関数（`src/testUtils/factory/`） |
| モック | `vi.mock` / `vi.spyOn`（内部依存）、MSW（外部 HTTP API） |
| DB | Prisma / Drizzle / TypeORM 等。テストはトランザクションロールバック |
| スキーマ検証 | Zod（リクエスト/レスポンスの境界で検証） |
| カバレッジ | Vitest（v8 provider） |

## レイヤー構成（この順に依存する。逆流禁止）

```
src/routes/       … HTTP 層。リクエスト検証（Zod）とレスポンス整形のみ
src/services/     … ビジネスロジック。HTTP を知らない
src/repositories/ … データアクセス。SQL/ORM をここに閉じ込める
src/schemas/      … Zod スキーマと型
```

## テスト実行コマンド

```bash
yarn vitest run src/path/to/foo.test.ts -t "ケース名"   # 単一ケース（Red の失敗確認・独立性検証）
yarn vitest run src/path/to/foo.test.ts                 # 単一ファイル（Green/Refactor の pass 確認）
yarn vitest run                                          # 全件（CI 同様）
yarn vitest run src/path/to/foo.test.ts --sequence.shuffle  # ランダム順序（Optimize の独立性検証）
yarn coverage                                            # カバレッジ
yarn typecheck                                           # tsc --noEmit
yarn lint --fix                                          # ESLint(+Prettier) 自動修正
```
> パッケージマネージャは yarn を既定とする。npm/pnpm のプロジェクトでは読み替える（bootstrap が検出）。

## CI / hook

- CI がテストを走らせる。push すれば Vitest / ESLint / type-check が自動実行される。
- pre-commit hook あり（husky + lint-staged）: コミット時に自動 format、lint エラーがあるとコミットがブロックされる。→ `--no-verify` は使わない（→ `commit-convention.md`）。
- lint: ESLint（+ Prettier）。型: `tsc --noEmit`。

## 不変条件（全スキル共通・破ってはいけない線）

1. 1サイクル = 1テスト = 1コミット。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. TDD メタ情報をコード/テストに残さない（Red/Green/サイクル番号/PR番号/計画書§参照を書かない）。
3. テストの独立性を保つ（不変条件の中で最も優先する。崩れるとフレークや順序依存で Red/Green の信号そのものが信用できなくなる）:
   - DB を触るテストは各ケースでトランザクションロールバック（またはテーブル truncate）。テスト間でレコードを共有しない。
   - `afterEach(() => { vi.restoreAllMocks() })` でモックを戻す。fake timers を使ったら `vi.useRealTimers()` で戻す。
   - モジュールレベルの可変状態（シングルトン・キャッシュ・接続プール）をテスト間で共有しない。
4. 外部 I/O は依存注入で差し替える: `fetch` / DB クライアント / 時刻 / ランダム を実装内で直接掴まない。コンストラクタ引数か関数引数で受け取り、テストで差し替える。外部 HTTP は MSW でモックし実通信はしない。
5. 境界は Zod で検証する: HTTP リクエスト・外部 API レスポンスは `parse` / `safeParse` を通してから内部へ渡す。`as` による型アサーションで検証を迂回しない。
6. レイヤーの依存方向を守る: routes → services → repositories。services が HTTP（req/res）を知らない。repositories 以外に SQL/ORM 呼び出しを書かない。
7. Green は最小実装のみ（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出は Refactor で。
8. 承認ゲートは Red 完了後と Commit 直前の2箇所。Green / Refactor の間は自動遷移してよい。
9. ターン粒度: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
