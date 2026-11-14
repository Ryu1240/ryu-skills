---
name: tdd-green
description: TDD の Green フェーズ。Red で追加した失敗テストを通す最小限の Go 実装を書く。通常は /tdd から呼ばれる。
argument-hint: <workflow_id>
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
  - Bash(date:*)
examples:
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す最小限の実装を行う。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` / `error_message` / `test_file_path` から、不足実装を特定（handler メソッド / service メソッド / repository クエリ / domain の型・sentinel error / インターフェイスのメソッド / DI 配線 / sqlc クエリ）。コンパイルエラーなら `undefined: xxx` / `missing method Xxx` の識別子がそのまま作るべきもの。

## 2. 実装（レイヤー別・最小）

### 必須パターン
- レイヤーの依存方向を守る（handler → service → repository、domain は末端）。service に `*http.Request` / `http.ResponseWriter` を渡さない。repository 以外に SQL / ORM 呼び出しを書かない。domain は標準ライブラリ以外を import しない。
- 外部 I/O はインターフェイスで受け取る: DB クライアント / HTTP クライアント / 時刻 / 乱数を実装内で直接掴まない（`time.Now()` / `http.DefaultClient` / `sql.Open` を service に書かない）。インターフェイスは利用側パッケージで最小に定義（今のテストが要求するメソッドだけ）。
- エラーは値で返す: 業務エラーは `domain.ErrOutOfStock` のような sentinel（または型付きエラー）を返し、handler で HTTP ステータスに変換。下位のエラーは `fmt.Errorf("reserve stock: %w", err)` でラップして返す（`%v` で包むと `errors.Is` が効かない）。`panic` しない、`_ = err` で捨てない。
- `ctx` を第一引数で受けて伝搬: `func (s *Service) Reserve(ctx context.Context, ...)`。DB/HTTP は `QueryContext` / `http.NewRequestWithContext` を使う。
- インターフェイスにメソッドを足したら、実装と手書きフェイクの両方に足す（フェイクが `does not implement` でコンパイルエラーになる）。
- DB スキーマ変更が要るならマイグレーションを生成して適用（生成物はコミット対象）。sqlc なら `.sql` を書いて `go generate ./...`（または `sqlc generate`）。

### 最小実装の線引き
テストが要求していない分岐・引数・設定・抽象化は作らない。共通化・インターフェイス抽出・キャッシュ・並行化は Refactor フェーズ以降で。「後で要るから」でインターフェイスにメソッドを足さない。

## 3. テスト pass 確認
```bash
go test {test_package_dir} -count=1
```
（integration タグがあれば `-tags=integration`。）対象パッケージ全件 pass を確認。最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

典型的失敗と対処:
- `X does not implement Y (missing method Z)` → フェイクと実装の両方にメソッドを追加（片方だけだと次で落ちる）。
- nil pointer dereference / assignment to entry in nil map → コンストラクタで初期化（`make(map...)`）、ポインタの nil チェック。
- `errors.Is` が false → `%v` で包んでいる / 別インスタンスの `errors.New` を返している。`%w` に直し、sentinel は `domain` の 1 か所で定義。
- `context.Canceled` / タイムアウトが伝搬しない → `ctx` を渡し忘れて `context.Background()` を内部で作っている箇所を直す。
- sqlc / mock の生成物が古い → `go generate ./...` を実行し忘れている。
- import cycle → domain が上位を import している。依存方向を直す（インターフェイスを利用側に移す）。

テストを都合よく書き換えて通してはいけない（Red で承認済み）。テスト側の誤りと判断した場合は停止して報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。マイグレーション・`go generate` 生成物・`go.mod`/`go.sum` の変更も含める), `retry_count`。

## 5. サマリ（簡潔）
実装した handler/service/repository/domain / インターフェイスの変更（フェイクへの追従含む）/ マイグレーション・生成物の有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- 依存モジュールの追加（`go get`）は設計判断: 新規ライブラリが必要になったら停止条件#2 として提示し承認を得る。
- `go vet {pkg}` と `gofmt -l {files}` を通しておくと Commit 時の hook で弾かれない。
