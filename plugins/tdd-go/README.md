# Go バックエンド TDD スイート（`/tdd`）

**Go のバックエンド**（HTTP API サーバー。CLI / ワーカーにも対応）向けの TDD ワークフロー自動化スキル群です。テストは標準 **`testing`** パッケージ（テーブル駆動 + `t.Run` サブテスト）を前提にしています。Plan → Red → Green → Refactor → Commit のサイクルをフェーズ単位で進め、Coverage Review と Test Optimize まで回します。

サンプルとして架空リポジトリ **`shipment-api`**（Go の出荷管理 API）を題材に記述しています。

## 前提スタック

| 項目 | 値 |
|---|---|
| 言語 | Go 1.22+（modules） |
| ルーター | 標準 `net/http` ServeMux / chi / echo / gin のいずれか |
| テスト | 標準 `testing`（`*_test.go` 併置。`package foo_test` / `package foo` は既存の多数派に合わせる） |
| アサーション | `go-cmp`（`cmp.Diff`）既定。testify のリポではそれに合わせる |
| HTTP テスト | `net/http/httptest`（`NewRecorder` / `NewServer`） |
| モック | 利用側で定義した小さなインターフェイス + 手書きフェイク（gomock / mockery / moq のリポではそれに従う） |
| 外部 API | `httptest.NewServer` で応答を差し替え。実通信はしない |
| DB | `database/sql` + sqlc / sqlx / pgx（GORM / ent 可）。テストはトランザクション + `t.Cleanup(func() { _ = tx.Rollback() })` |
| 時刻 / 乱数 | `Clock` インターフェイス / `func() time.Time` で注入 |
| lint / hook | `gofmt` / `goimports` + `go vet` + `golangci-lint`、lefthook / pre-commit |
| CI | GitHub Actions / CircleCI（`go test -race` / `golangci-lint`） |

これらの前提は [`_shared-tdd/project-settings.md`](skills/_shared-tdd/project-settings.md) に集約されています。**自分のプロジェクトに合わせて書き換えてください**（`/tdd-bootstrap` が自動生成します）。

## レイヤー構成を前提にした指示

このプラグインは**レイヤードアーキテクチャ**を前提に、各フェーズが具体的に踏み込みます。

```
cmd/api/              … main のみ。依存の組み立て（DI）と起動
internal/handler/     … HTTP 層。デコード・バリデーション・ステータスコード変換のみ
internal/service/     … ビジネスロジック。net/http を知らない
internal/repository/  … データアクセス。database/sql・sqlc をここに閉じ込める
internal/domain/      … 型・sentinel error。何にも依存しない
```

- **Red** はレイヤー別のテスト作法を指示（service=手書きフェイク注入 + `errors.Is`、handler=`httptest.NewRecorder`、repository=トランザクションロールバック、外部 API=`httptest.NewServer`）。単一ケース実行は `go test {pkg} -run '^TestX$/^sub_case$' -count=1`（要素ごとに完全一致。サブテスト名の空白は `_`）。
- **Refactor** は Go 固有の観点で改善（**レイヤー逆流**の解消 / **ループ内クエリの N+1** / **`%w` ラップと sentinel の集約** / **goroutine リーク・`defer cancel()` 漏れ・`ctx` の断絶** / インターフェイスの肥大と producer 側定義 / `any` と型アサーションの除去）
- **Coverage Review** は 400/401/403/404/409、sentinel error、外部 API 失敗、DB 制約違反、context キャンセル、`-race` まで含むマトリクスで抜けを埋めます
- **Optimize** はテーブル駆動化・`t.Helper()` ヘルパ抽出・`cmp.Diff` 集約を行い、`-shuffle=on` / `-race` / `-count=3` / `-p 1`・`-parallel 1` で独立性を検証します

> 実際のディレクトリ名が違っても構いません。`tdd-bootstrap` が `internal/` の実態（`usecase` / `store` / `transport` 等）を読み取って project-settings.md に反映します。**CLI プロジェクト**（cobra 等）や**ライブラリのみ**のモジュールでは、HTTP 前提の節を bootstrap が読み替えて生成します。

## 他プラグインとの使い分け

| 状況 | 使うもの |
|---|---|
| **Go バックエンド（API サーバー・CLI・ワーカー）** | **`tdd-go`** |
| TS/Node バックエンド | `tdd-node` |
| Vue + Vitest のフロントエンド | `tdd-frontend` |
| Rails + RSpec | `tdd-rails` |
| Python + pytest | `tdd-python` |
| Rails + Vue モノレポ | `tdd-monorepo` |
| 上記以外の言語 | `tdd-universal` |

1 リポジトリで有効化するプラグインは **1 つだけ**にしてください（同じ skill 名を提供するため）。

## インストール

```text
/plugin marketplace add Ryu1240/ryu-skills
/plugin install tdd-go@general-skills
```

導入後、初回 `/tdd` 実行時に Phase 0 が `.claude/skills/_shared-tdd/project-settings.md` の有無を判定し、無ければ `tdd-bootstrap` を提案します。手動なら `/tdd-bootstrap`（既存があれば確認）/ `/tdd-bootstrap --force`（上書き再生成）。

**マルチモジュール（`go.work`）にも対応**します。bootstrap が `go.work` の `use` を検出し、対象モジュールを選ばせたうえでコマンドに `cd {module_root}` を付けて生成します。

> `Makefile` / `justfile` に `test` / `lint` ターゲットがあれば bootstrap がそれを最優先で採用します（`-race` や `-tags=integration` などリポ固有のフラグを取りこぼさないため）。DB テストを `//go:build integration` で分離しているリポでは `-tags=integration` を自動で付けます。

## スキル一覧

- **[tdd](skills/tdd/SKILL.md)** — オーケストレーター。Phase 2 でレイヤーを判定し、Plan→サイクル→Coverage Review→Optimize を統括（Notion 連携は任意）。
- **[tdd-bootstrap](skills/tdd-bootstrap/SKILL.md)** — 初回セットアップ。マルチモジュール対応でモジュール・プロジェクト種別・レイヤー構成・アサーション/モックの流儀・独立性の担保方法を走査し、不明点は対話で確認して設定を生成（承認制）。あわせて `.claude/tdd-workflow/`（実行時の状態ファイル）を gitignore するかを確認します。
- **[tdd-project-settings-update](skills/tdd-project-settings-update/SKILL.md)** — 生成済み `project-settings.md` を自然言語指示で調整（コマンドは `Makefile` のターゲット / `go list` / 実際の `go test` で実在を裏取り）。
- **[tdd-red](skills/tdd-red/SKILL.md)** — Red。レイヤー別の作法で失敗するテストを 1 本だけ書く（コンパイルエラーも正しい Red）。
- **[tdd-green](skills/tdd-green/SKILL.md)** — Green。テストを通す最小実装（インターフェイス注入・`%w` ラップ・`ctx` 伝搬・レイヤー遵守。インターフェイス変更時はフェイクにも追従）。
- **[tdd-refactor](skills/tdd-refactor/SKILL.md)** — Refactor。レイヤー衛生 / N+1 / エラー処理 / 並行性・context / インターフェイスと型 をテスト緑のまま改善（`-race` 付きで確認）。
- **[tdd-commit](skills/tdd-commit/SKILL.md)** — Commit。pre-commit hook 準拠でコミット（マイグレーション・`go generate` 生成物・`go.mod`/`go.sum` も含める。hook が無ければ `make lint` を手動実行）。
- **[tdd-evacuator](skills/tdd-evacuator/SKILL.md)** — リファクタ候補・テスト妥当性（過剰モック・`errors.Is` 未使用・タグ漏れの指摘含む）に加え、サイクル境界で次サイクルの追加テストを提案（読み取り専用）。
- **[tdd-coverage-review](skills/tdd-coverage-review/SKILL.md)** — handler/service × テストカテゴリのマトリクスで不足を補完（`go tool cover -func` を手がかりに）。
- **[tdd-optimize](skills/tdd-optimize/SKILL.md)** — テストの最適化（テーブル駆動化・`t.Helper()` 抽出・`cmp.Diff` 集約・`t.Parallel()`）。`-shuffle=on` / `-race` / `-count=3` で独立性を検証。
- **[tdd-workflow-update](skills/tdd-workflow-update/SKILL.md)** — 進行中ワークフロー JSON を自然言語で動的更新。

## 共通契約（`_shared-tdd/`）

全スキルが単一情報源として参照します。

- `project-settings.md` — レイヤー構成・テストコマンド（`-count=1` 必須）・**不変条件**・CI/hook
- `workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定。`test_package_dir` / `test_name` は `go test` のディレクトリと `-run` 正規表現）
- `state-machine.md` — フェーズ遷移・2 モード・承認ゲート・停止条件
- `commit-convention.md` — コミット規約・署名・hook 準拠

## 使い方

```
# 自由テキストから計画
/tdd "出荷APIに在庫引当を追加し在庫不足なら409を返す"

# Notion タスクから計画
/tdd https://www.notion.so/<task-id>

# 既存ワークフローを実行（既定はフェーズ停止）/ 一気通貫
/tdd tdd-20260613-101500
/tdd tdd-20260613-101500 --auto

# 進行中ワークフローを動的更新
/tdd tdd-20260613-101500 -- サイクル5を削除
```

計画フェーズは状態 JSON を書き出すため、Plan モードではなく通常モードで実行してください。
