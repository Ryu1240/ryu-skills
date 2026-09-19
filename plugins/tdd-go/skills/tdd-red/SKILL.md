---
name: tdd-red
description: Red phase - Write ONE failing Go test (standard testing, table-driven subtest) for shipment-api, confirm it fails as expected
argument-hint: <workflow_id> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(go:*)
  - Bash(gofmt:*)
  - Bash(goimports:*)
  - Bash(make:*)
  - Grep
  - Glob
examples:
  - input: /tdd-red tdd-20260613-101500
    description: Execute Red phase for the current cycle
---

TDD の Red フェーズ。**今サイクルのテストを1つだけ**（1つのサブテスト、または 1 つの `TestXxx`）追加し、期待通り失敗することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（レイヤー構成・パス・**不変条件**・テストコマンド）
- `.claude/skills/_shared-tdd/workflow-schema.md` / `state-machine.md`

> 🔴 **一度に1テストケースのみ**。複数追加は不変条件違反。テーブル駆動テストに行を足す場合も **1 行だけ**。

## 入口ゲート（cycle 2 以降）
`current-cycle.json` が**存在しないこと**を Read で確認（存在＝前サイクル未完了 → `/tdd-commit {id}` 案内し中断）。`completed_cycles` 長 == `current_cycle - 1` を確認。

## 1. コンテキスト
`workflow-{id}.json` を Read（`target_files`, `patterns`(layer/test_kind/uses_db/uses_external_api/test_package/assert_lib), `current_cycle`, `user_instructions`）。`todo_task_id` で TaskGet し `cycle_plan` の該当エントリ（`title`, `kind`）を特定。

## 2. テストファイル決定
`$1` 指定があればそれ。無ければ**実装と同ディレクトリの `*_test.go`**（既存ファイルへの追記を優先、無ければ新規）。
- `internal/handler/shipment.go` → `internal/handler/shipment_test.go`、`internal/service/inventory.go` → `internal/service/inventory_test.go`。
- **パッケージ名の流儀**: `patterns.test_package` に従う（`package service_test` = 外部パッケージ・公開 API のブラックボックス、`package service` = 内部詳細）。既存ファイルに追記するときは**そのファイルの `package` 宣言に合わせる**（同ファイル内で混在はできない）。
- 既存の配置に揺れがあれば Glob で数え多数派に合わせる。

## 2-b. 既存テストへの影響確認（critical）
**公開インターフェイスの変更**は既存テストを壊す。変更する場合は参照箇所を Grep し、必要なら本サイクルで合わせて更新（振る舞いの意味は変えない）：
- エクスポート識別子（関数 / メソッド / 型 / 定数）のシグネチャ・名前
- **インターフェイスへのメソッド追加**（それを実装している**すべての手書きフェイク・モックが "does not implement" でコンパイルエラー**になる。`Grep "type fake.*struct"` で洗い出す）
- **構造体へのフィールド追加**（`cmp.Diff` / `reflect.DeepEqual` で期待値を丸ごと比較している既存テストがずれる）
- sqlc のクエリ変更（`go generate` で再生成が要る）、DB スキーマ（マイグレーションを伴う場合は既存の repository テストを確認）

## 3. テスト追加（レイヤー別の必須パターン）
既存の近いテストを Read し慣習に揃える（テーブル駆動か個別 `t.Run` か、`cmp.Diff` か testify か）。**shipment-api の必須パターンを守る**：

### domain / service spec（ロジック。手書きフェイクを注入し `errors.Is` で判定）
```go
func TestInventoryService_Reserve(t *testing.T) {
	tests := []struct {
		name    string
		stock   int
		wantErr error
	}{
		{name: "returns ErrOutOfStock when stock is insufficient", stock: 0, wantErr: domain.ErrOutOfStock},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			repo := &fakeStockRepo{stock: tt.stock}          // 利用側で定義した小さなインターフェイスのフェイク
			svc := service.NewInventoryService(repo)
			err := svc.Reserve(context.Background(), "sku-1", 1)
			if !errors.Is(err, tt.wantErr) {
				t.Fatalf("Reserve() error = %v, want %v", err, tt.wantErr)
			}
		})
	}
}
```
- **モジュールレベルのモック生成より、コンストラクタ/引数注入 + 手書きフェイク**を優先（不変条件#4）。gomock/mockery のリポではその流儀に従う。
- エラー判定は `errors.Is` / `errors.As`。**エラー文字列の比較はしない**。
- 時刻に依存するなら `Clock` / `func() time.Time` を注入し、テストでは固定値。

### handler spec（HTTP 契約。`httptest`）
```go
func TestShipmentHandler_Create(t *testing.T) {
	t.Run("returns 409 when stock is insufficient", func(t *testing.T) {
		svc := &fakeShipmentService{err: domain.ErrOutOfStock}
		h := handler.NewShipmentHandler(svc)
		req := httptest.NewRequest(http.MethodPost, "/shipments", strings.NewReader(`{"sku":"sku-1","quantity":1}`))
		rec := httptest.NewRecorder()

		h.Create(rec, req)

		if rec.Code != http.StatusConflict {
			t.Fatalf("status = %d, want %d", rec.Code, http.StatusConflict)
		}
		var body map[string]any
		if err := json.Unmarshal(rec.Body.Bytes(), &body); err != nil {
			t.Fatalf("invalid JSON body: %v", err)
		}
		if got := body["code"]; got != "OUT_OF_STOCK" {
			t.Errorf("code = %v, want OUT_OF_STOCK", got)
		}
	})
}
```
- ハンドラを直接呼ぶ（`rec` + `req`）。ルーティング・ミドルウェア込みの契約を見るときだけ `httptest.NewServer(router)` + `t.Cleanup(srv.Close)`。
- **正常系・デコード/バリデーション(400)・異常系(404/409)・認可(401/403)は別サイクル**に分ける。

### repository spec（実 DB）
実 DB に対して実行し、**各ケースでトランザクションを開始して `t.Cleanup(func() { _ = tx.Rollback() })`**。テスト間でレコードを共有しない。`//go:build integration` で分離しているリポではファイル先頭にタグを置き、実行時に `-tags=integration` を付ける。

### 外部 API を叩く場合
`httptest.NewServer(http.HandlerFunc(...))` で応答を差し替え、その `srv.URL` をクライアントに注入。`t.Cleanup(srv.Close)`。異常系（5xx / タイムアウト）はケースごとに別サーバーを立てる。**実通信はしない**。

### CLI（`patterns.test_kind == "cli"`）
`cmd.Execute()` / `RunE` に `bytes.Buffer` を `SetOut` / `SetErr` して stdout/stderr を捕捉。終了コード（返却エラー）と出力を契約として検証。

## 4. 失敗確認
```bash
go test {test_package_dir} -run '{TestFunc}/{サブテスト名（空白は _ に置換）}' -count=1 -v
```
（`Makefile` に単一ケース実行ターゲットがあれば project-settings に従う。integration タグがあれば `-tags=integration`。）

期待される失敗: **コンパイルエラー（未定義の関数 / 型 / メソッド / sentinel error）**、`status = 404, want 409`、`error = <nil>, want ErrOutOfStock`、`cmp.Diff` の差分、アサーション不一致。Go では「未定義でコンパイルが通らない」が最も典型的な Red であり、これは正しい失敗。
**予期しない失敗**（import cycle、`package` 名の不一致、`go mod tidy` 未実行で依存が解決しない、ビルドタグ漏れで `no tests to run`、`go vet` エラー、フェイクのメソッド漏れ）は**テスト側を修正して再実行**。実装を書き始めてはいけない。

> `-v` の出力に `--- FAIL: TestX/sub_case` が**実際に出ている**ことを確認する。`ok` / `no tests to run` は失敗ではない（`-run` の正規表現ミスかタグ漏れ）。

## 5. 状態更新
`current-cycle.json` を workflow-schema 準拠で Write（`phase:"red"`, `test_file_path`, **`test_package_dir`**（`go test` に渡すディレクトリ）, **`test_name`**（`-run` に渡す `TestFunc/sub_case` 正規表現）, `test_details`(error_type/message), `created_at`/`updated_at`）。
**自己検証**: Read で `phase=="red"`・`updated_at` 更新を確認。

## 6. サマリ（簡潔）
テストファイル / 追加した1ケース / 期待通りの失敗（コンパイルエラー or アサーション）/ 適用パターン（手書きフェイク注入・httptest・ロールバック・`errors.Is` 等）/ 次は Green。承認ゲート①は state-machine に従う（tdd 側が判断）。

## エラー
- テストファイル決定不能: `$1` 明示 or タスクに対象名（handler/service 名）追記を案内。
- フェイク / ファクトリ未定義: `internal/testutil/` を確認し、テストファイル内に最小の `type fakeXxx struct` を定義するか追加を促す。
- コンパイルエラーでテストが書けない: 実装側の型・関数が未定義なのが原因なら**それが期待される失敗**（そのまま Green へ）。設計上の型の矛盾（インターフェイスの循環・import cycle）なら停止条件#8 として報告。
