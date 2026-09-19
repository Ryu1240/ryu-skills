---
name: tdd-refactor
description: Refactor phase - Improve shipment-api Go code quality (layer hygiene / N+1 queries / error wrapping / context & goroutine hygiene / interface design) while keeping tests green
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(go:*)
  - Bash(gofmt:*)
  - Bash(goimports:*)
  - Bash(golangci-lint:*)
  - Bash(make:*)
  - Grep
  - Glob
examples:
  - input: /tdd-refactor tdd-20260613-101500
    description: Execute Refactor phase for the current cycle
---

TDD の Refactor フェーズ。**動作を変えずに**コード品質を改善し、テストが引き続き pass することを確認する。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（lint・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅内部改善 ❌新機能 ❌動作変更 ❌**新規テスト追加**（次サイクルの Red で）。

## 入口ゲート
`current-cycle.json` を Read。`phase=="green"`、`implementation_files` 非空、`updated_at` 非空。違反なら `/tdd-green {id}` 案内し中断。

## 1. 対象読み込み
`implementation_files` と `test_file_path` を Read。

## 2. 改善（該当時のみ・Go バックエンド固有）

### 2-1. レイヤー衛生（最優先）
- **依存方向の逆流**を解消: service が `*http.Request` / `http.ResponseWriter` を受け取っていないか（`Grep "net/http" internal/service/`）、handler にビジネスロジック（在庫判定・金額計算）が漏れていないか、repository 以外に SQL / ORM 呼び出しが無いか、domain が上位パッケージを import していないか。
- 見つかった場合は正しい層へ移動する（テストが緑のまま動くこと）。

### 2-2. N+1 クエリ（必須確認）
ループ内での DB 呼び出しを Grep で探す。
```go
for _, id := range ids { item, err := repo.FindByID(ctx, id) }   // ❌ N+1
items, err := repo.FindByIDs(ctx, ids)                          // ✅ 一括取得（WHERE id = ANY($1)）
```
sqlc なら一括取得クエリ（`= ANY(sqlc.slice(...))` / `IN`）を追加、GORM/ent なら `Preload` / `With...` でまとめる。**ループ内のクエリ呼び出しはレビュー対象**。

### 2-3. エラー処理の一貫性
- **`%w` ラップの一貫性**: 下位エラーを返す箇所が `%v` / 素の `return err`（文脈なし）/ 独自の `errors.New` で情報を落としていないか。文脈（何をしようとして失敗したか）を付けて `%w` で包む。
- **sentinel / 型付きエラーの集約**: 同じ意味のエラーが複数箇所で `errors.New` されていれば `domain` の 1 定義に寄せる。handler の `errors.Is` → HTTP ステータス変換を 1 か所（`writeError` 等）に集約。
- **握り潰し・二重処理**: `_ = err`、`if err != nil { log.Println(err) }` だけで return しない箇所、ログして更に return して上位でもログする二重処理を解消。
- エラーメッセージに内部情報（SQL・DSN・スタック）を載せない。`panic` を `error` 返却に直す。

### 2-4. 並行性と context
- **goroutine リーク**: 起動した goroutine の終了を待っていない / `ctx` キャンセルで抜けない箇所。`errgroup.Group` か `sync.WaitGroup` に統一。
- **`defer cancel()` 漏れ**: `context.WithTimeout` / `WithCancel` の直後に `defer cancel()` が無い。
- **ループ内 `defer`**: 関数終了まで解放されない（`rows.Close()` / `tx.Rollback()` / ファイル）。ループ本体を関数に切り出す。
- **mutex の保持範囲**: I/O をロック中に行っていないか。保持区間を最小に。`-race` で検出されたレースは停止条件#8。
- **`ctx` の断絶**: 途中で `context.Background()` を作り直している箇所を、引数の `ctx` に繋ぎ直す。

### 2-5. インターフェイスと型
- **インターフェイスの肥大**: 今サイクルで使っていないメソッドを持つインターフェイスを分割（メソッド 1〜3 個が目安）。**producer 側で定義しているインターフェイスは利用側へ移す**。
- **レシーバの混在**: 同じ型でポインタ / 値レシーバが混在していれば統一（状態を持つならポインタ）。
- **`any` / `interface{}` と型アサーション**: 今サイクルで増えていれば具体型かジェネリクスで解消（解消できなければ停止条件#8 として報告）。
- **stutter する命名**: `shipment.ShipmentService` → `shipment.Service`。パッケージ名と型名の重複を除く。
- 構造体のゼロ値が安全か（`New...` なしで使われても nil map / nil chan に書き込まない）。

### 2-6. 関数の分解と命名
- 責務過多（デコード・検証・取得・変換・永続化が同居）な関数を分割。深いネストは early return へ（`if err != nil { return }` を先に）。
- `MixedCaps`、頭字語は `ID` / `URL` / `HTTP`。短い変数名（`i`, `n`, `tx`）は狭いスコープでのみ。`data` / `info` / `tmp` 等の無意味名を役割名に。
- 不要なエクスポート（パッケージ外から使われていない大文字識別子）を小文字に。

### 2-7. フォーマット / 静的解析
```bash
gofmt -l -w {files} && goimports -w {files}     # goimports 未導入なら gofmt のみ
go vet {pkg}
golangci-lint run {pkg}                          # 未導入なら go vet のみ
```
警告は `//nolint` で黙らせず解消する（停止条件#8）。

## 3. テスト維持確認
```bash
go test {test_package_dir} -count=1 -race
```
（integration タグがあれば `-tags=integration`。）対象パッケージ全件 pass を維持し、`-race` でレースが出ないことを確認。失敗したら参照ミス（移動したパッケージの import、インターフェイス移動後のフェイク、命名変更）を修正、または `[r]修正 / [u]ロールバック / [s]停止`。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"refactor"`, `refactor_details`（`layer_fixes` / `n_plus_one` / `error_handling` / `concurrency_ctx` / `interfaces_types` / `decomposition` / `naming` / `linter`。空オブジェクト不可。何もなければ `{"note":"no refactor needed"}`）, `updated_at`。
**自己検証**: `phase=="refactor"` かつ `refactor_details` 非空を Read で確認。

## 5. サマリ（簡潔）
実施した改善（レイヤー/N+1/エラー/並行性・ctx/インターフェイス・型/命名/lint 件数）/ 全件 pass（`-race` 含む）/ 次は Evac(review)→Commit。→ 自動遷移（承認ゲート②は tdd 側）。

## 注意
- **振る舞いを変える改善は Refactor ではない**。仕様変更に踏み込む必要が見えたら停止条件#2（設計判断）として報告する。
- **レイヤー構成そのものの変更**（新しい層の追加、依存の向きの変更、パッケージ分割の再編）はスコープ外。提案として報告し別タスクに分ける。
- 実装ファイルの `package` 名やディレクトリを動かすと**テストの import も追従**が要る。動かすなら同サイクル内で整合させる。
