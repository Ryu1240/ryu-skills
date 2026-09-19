# TDD スキル共通設定（Project Settings）— shipment-api

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> shipment-api は **Go の HTTP API サーバー**（出荷管理）。テストは標準 `testing`。UI を持たない。

## 構成とテスト

| | backend（Go） |
|---|---|
| モジュール | リポジトリ直下の `go.mod`（マルチモジュール `go.work` なら対象モジュールを bootstrap が確定） |
| Go バージョン | Go 1.22+（modules） |
| ルーター | 標準 `net/http` ServeMux / chi / echo / gin のいずれか |
| テスト | 標準 `testing`（テーブル駆動 + `t.Run` サブテスト、`t.Helper()` / `t.Cleanup()` / `t.TempDir()`） |
| アサーション | `go-cmp`（`cmp.Diff`）を既定。testify（`require`/`assert`）のリポではそれに合わせる（bootstrap が検出） |
| HTTP テスト | `net/http/httptest`（`httptest.NewRecorder` でハンドラ直接呼び出し。ルーター経由は `httptest.NewServer`） |
| テスト配置 | 実装と同ディレクトリの `*_test.go`。公開 API は外部パッケージ `package foo_test`（ブラックボックス）、内部詳細は `package foo`。既存の多数派に合わせる |
| テストデータ | ビルダー/ファクトリ関数（`internal/testutil/factory/`）。固定入力・golden file は `testdata/` |
| モック | 利用側パッケージで定義した小さなインターフェイスに**手書きフェイク**を注入（`internal/testutil/` または `_test.go` 内）。gomock / mockery / moq（`go generate`）のリポではそれに従う |
| 外部 HTTP API | `httptest.NewServer` で応答を差し替え（`t.Cleanup(srv.Close)`）。**実通信はしない** |
| DB | `database/sql` + sqlc / sqlx / pgx（GORM / ent でも可）。テストは各ケースでトランザクション開始→`t.Cleanup(func() { _ = tx.Rollback() })`。純ユニットなら `go-sqlmock` |
| 時刻 / 乱数 | `func() time.Time` / `Clock` インターフェイスで注入 |
| カバレッジ | `go test -coverprofile` + `go tool cover -func` |

## レイヤー構成（この順に依存する。逆流禁止）

```
cmd/api/              … main のみ。依存の組み立て（DI）と起動
internal/handler/     … HTTP 層。デコード・バリデーション・ステータスコード変換のみ
internal/service/     … ビジネスロジック。net/http を知らない
internal/repository/  … データアクセス。database/sql・sqlc・sqlx をここに閉じ込める
internal/domain/      … 型・sentinel error。何にも依存しない（末端）
```

## テスト実行コマンド

```bash
go test ./internal/service/ -run '^TestInventoryService_Reserve$/^returns_ErrOutOfStock_when_stock_is_insufficient$' -count=1 -v   # 単一ケース（Red の失敗確認・独立性検証。要素ごとに ^…$ で完全一致）
go test ./internal/service/ -count=1                                       # 単一パッケージ（Green/Refactor の pass 確認）
go test ./... -count=1                                                     # 全件（CI 同様）
go test ./internal/service/ -count=1 -shuffle=on -race                     # ランダム順序 + レース検出（Optimize の独立性検証）
go test ./... -count=1 -coverprofile=coverage.out && go tool cover -func=coverage.out   # カバレッジ
go vet ./... && golangci-lint run ./...                                    # 静的解析
gofmt -l -w {files} && goimports -w {files}                                # フォーマット（変更ファイルに限定。`.` 全体だと vendor/ や testdata/ まで書き換える。goimports 未導入なら gofmt のみ）
```
> - Go のテスト実行単位は「ファイル」ではなく**パッケージ**。`{path}` にはテストファイルの**ディレクトリ**（`./internal/service/`）を渡す。
> - `-run` は**要素ごとに `^…$` で完全一致**させる（`-run '^TestX$/^sub_case$'`）。前方一致のままだと `TestXY` や `sub_case_extra` も走り「単独実行」にならない。サブテスト名の**空白は `_` に置換**される（`t.Run("returns ErrOutOfStock when stock is insufficient", ...)` → `^returns_ErrOutOfStock_when_stock_is_insufficient$`）。`(` `)` `+` `?` 等の正規表現メタ文字が名前に含まれる場合は `\` でエスケープする（テーブル駆動の `name` には最初から使わないのが安全）。同名の `name` を 2 行書くと `#01` が付いて別ケースになるので重複させない。
> - `-shuffle=on` が並べ替えるのは**トップレベルの `TestXxx` の順序だけ**（テーブル駆動のサブテストは定義順のまま）。サブテスト間の順序依存は `-run` での単独実行で炙り出す。
> - `-count=1` は**テストキャッシュを無効化**するため必須。`go test` は成功結果をキャッシュし、ソース変更は追跡するが**外部状態（DB の中身・環境変数・ファイル）の変化は追跡しない**。DB を触るテストは前回成功のキャッシュが返って「実行されずに ok」になりうる（失敗結果はキャッシュされないので Red には影響しないが、Green / Refactor / Optimize の再実行で効く）。
> - `Makefile` / `justfile` に `test` / `lint` ターゲットがあればそれを最優先で使う（bootstrap が検出して差し替える）。
> - DB を叩く integration テストを `//go:build integration` で分離しているリポでは `-tags=integration` を付ける。付け忘れると `ok … [no tests to run]`（他のテストが同居）または `?  … [no test files]`（タグ付きファイルだけのパッケージ）と出て、**走っていないのに終了コード 0** になる。

## CI / hook（重要）

- **CI がテストを走らせる**。push すれば `go test -race ./...` / `go vet` / `golangci-lint` が自動実行される。
- **pre-commit hook あり（lefthook / pre-commit）**: コミット時に `gofmt` / `go vet` / `golangci-lint` が走り、エラーがあるとコミットがブロックされる。→ `--no-verify` は**絶対禁止**。hook が無いリポでは Commit 前に `make lint`（無ければ `go vet ./... && golangci-lint run ./...`）を手動実行する。
- lint: `golangci-lint`（`.golangci.yml`）。フォーマット: `gofmt` / `goimports`。

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. **TDD メタ情報をコード/テストに残さない**（Red/Green/サイクル番号/PR番号/計画書§参照を書かない）。
3. **テストの独立性を必ず保つ（最重要）**:
   - DB を触るテストは**各ケースでトランザクションを開始し `t.Cleanup(func() { _ = tx.Rollback() })`**（または testcontainers-go / dockertest で使い捨て DB、テーブル truncate）。テスト間でレコードを共有しない。
   - `httptest.NewServer` は `t.Cleanup(srv.Close)`、一時ファイルは `t.TempDir()`。パッケージレベルの可変状態（グローバル変数・シングルトン・接続プール・`init()` の副作用）をテスト間で共有しない。
   - `t.Parallel()` は共有可変状態が無いと確認できたケースにだけ付ける。
4. **外部 I/O はインターフェイスで注入する**: DB・HTTP クライアント・時刻・乱数を実装内で直接掴まない（`time.Now()` / `http.DefaultClient` / `sql.Open` を service に書かない）。インターフェイスは**利用側パッケージで最小に定義**する（メソッド 1〜3 個）。コンストラクタ引数か関数引数で受け取り、テストで手書きフェイクに差し替える。
5. **エラーは値で返す**: `fmt.Errorf("reserve stock: %w", err)` でラップし、判定は `errors.Is` / `errors.As`。sentinel error（`domain.ErrOutOfStock`）・型付きエラーは `internal/domain/` に置く。`panic` しない、`_ = err` で捨てない、エラー文字列の比較で判定しない。
6. **`context.Context` を第一引数で伝搬する**: handler → service → repository の全経路で `ctx` を渡し、DB/HTTP 呼び出しは `ctx` 付き API（`QueryContext` / `http.NewRequestWithContext`）を使う。goroutine を起動したら終了を保証する（`errgroup` / `sync.WaitGroup`、`defer cancel()`）。**レイヤーの依存方向を守る**（handler → service → repository、domain は末端。service が `net/http` を import しない、repository 以外に SQL を書かない）。
7. **Green は最小実装のみ**（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出は Refactor で。
8. **承認ゲートは Red 完了後と Commit 直前の2箇所**。Green / Refactor の間は自動遷移してよい。
9. **ターン粒度**: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## ブランチ / コミット

- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
