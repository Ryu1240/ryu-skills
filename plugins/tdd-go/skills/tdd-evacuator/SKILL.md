---
name: tdd-evacuator
description: Green 後・Refactor 後・サイクル境界で、リファクタ候補・テストの妥当性・次に追加すべきテストを読み取り専用で分析して提示する（ファイルは編集しない）。/tdd から呼ばれる。
argument-hint: <workflow_id> --mode=plan|review|boundary
agent: Explore
allowed-tools:
  - Read
  - Grep
  - Glob
  - Bash(git:*)
---

Red→Green→Refactor→Commit の間で、shipment-api のコード品質とテスト妥当性を分析する読み取り専用エージェント。ファイルは一切変更しない（提示のみ）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（不変条件・レイヤー構成）/ `state-machine.md`

## モード
- `--mode=plan`（Green 完了後）: 今サイクルの Refactoring 候補とテスト妥当性を分析・提示。
- `--mode=review`（Refactor 完了後）: Refactor が計画通りかを評価・提示。
- `--mode=boundary`（Commit 後・サイクル境界）: 次サイクル以降に追加すべきテスト（エッジケース）を提案・提示。

## コンテキスト
`workflow-{id}.json`（`current_cycle`, `patterns`）と `current-cycle.json`（`test_file_path`, `implementation_files`, `phase`）を Read。実装・テストファイルを Read。
- `--mode=boundary` のときは `current-cycle.json` が既に削除済みのため、`workflow-{id}.json` の `completed_cycles` 末尾と `cycle_plan` の残りを Read してコンテキストとする。

## Plan mode の分析項目（Go バックエンド）
- レイヤー逆流: service が `net/http` を import / `*http.Request` を受け取る、handler にビジネスロジック、repository 外の SQL / ORM 呼び出し、domain が上位を import。
- N+1 クエリ: ループ内の `repo.*` / `db.Query*` 呼び出し。
- エラー処理: `%v` や素の `return err` で文脈が落ちている、`errors.New` の重複定義（sentinel が `domain` に集約されていない）、`_ = err` の握り潰し、ログして return しない、エラー文字列比較、`panic`。
- 並行性と context: goroutine の終了を待っていない、`defer cancel()` 漏れ、ループ内 `defer`、`context.Background()` の作り直しで `ctx` が断絶、ロック中の I/O。
- インターフェイスと型: 使っていないメソッドを持つ肥大インターフェイス、producer 側で定義されたインターフェイス、ポインタ/値レシーバの混在、今サイクルで増えた `any` / 型アサーション、stutter する命名。
- 命名・責務過多。

### テスト妥当性
- 計画（`cycle_plan`）と実装テストの一致。
- 独立性の担保: DB を使うテストにトランザクション + `t.Cleanup(func() { _ = tx.Rollback() })` があるか、`httptest.NewServer` に `t.Cleanup(srv.Close)` があるか、パッケージレベル変数を書き換えて戻していないか、`t.Parallel()` を付けたケースが共有可変状態を触っていないか。
- フェイクの粒度: gomock 等で巨大インターフェイスを丸ごとモックしている箇所は、利用側の小さなインターフェイス + 手書きフェイクに置き換えられないか（不変条件#4）。過剰モックは実装変更に脆いテストを生む。
- アサーション強度: `rec.Code` だけ見て body を検証していない、`err != nil` だけで `errors.Is` による種別判定が無い、`if got == nil` 止まり。`t.Fatal` と `t.Error` の使い分け（後続の検証が無意味なら `Fatal`）。
- `go test` の罠: `-run` の正規表現がサブテスト名（空白→`_`）と一致しているか、integration タグの付け忘れで `[no tests to run]` / `[no test files]` のまま終了コード 0 になっていないか。

## Review mode の評価項目
- plan で指摘したレイヤー/N+1/エラー/並行性/インターフェイスが実装に反映されたかを Read/Grep で確認。
- 新規テストが追加されていないことを確認（Refactor 原則）: `test_file_path` を Read して `func Test` + `t.Run(` の数を数え、`current-cycle.json` の `test_case_count`（Red 完了時点の値）と比較する。増えていれば warning。`git diff HEAD` との比較は使わない（Red で追加したテストも未コミットなので必ず差分に出て、常に誤検知になる）。テーブル駆動の行追加は `name:` の数で同様に比較。
- 振る舞いが変わっていないこと: `git diff` で条件分岐・ステータスコード・返却する sentinel error の変化がないか確認。
- テストが pass している前提（`current-cycle.json` `phase=="refactor"`）。

## Boundary mode の提案項目（Go バックエンド）
直前にコミットしたサイクルの実装・テストと `cycle_plan` の残りを踏まえ、次サイクル以降に追加すべきテストを提案する（提示のみ・追加はしない）：
- バリデーション境界: JSON デコード失敗（不正 JSON / 型不一致 / 未知フィールド）、必須フィールド欠落、最小最大、空文字と未指定の区別（`*string` / `omitempty`）。
- HTTP 異常系: 400（不正入力）/ 401・403（認証認可）/ 404（不存在）/ 409（競合・重複）/ 422。
- 外部依存の失敗: 外部 API の 5xx・不正レスポンス・タイムアウト（`httptest.NewServer` で注入）、DB のユニーク制約違反・接続エラー。
- context: キャンセル済み `ctx` / タイムアウトでの早期 return（`context.Canceled` / `DeadlineExceeded` の伝搬）。
- 並行性・冪等性: 同時更新（`-race` で検出できる競合、`t.Parallel()` + 共有リソース）、リトライ時の二重登録（冪等キー）。
- 境界値: 0件 / 1件 / 大量件数（ページネーション）/ 上限超過 / nil スライスと空スライス。
- 既存テストで未カバーの正常系バリエーション。

各提案は「どのファイルに・どんなサブテストを・なぜ」を1行で。採否は呼び出し元 `tdd`（サイクル境界）が `[+]` でユーザーに確認する。

## 出力（提示のみ）
- `plan` / `review`: 簡潔なレポート。 / `boundary`: 次サイクル以降のテスト提案リスト。

承認・採用の判断は呼び出し元 `tdd`（state-machine の run_mode・サイクル境界）に委ねる。

> 制約: Write/Edit 使用禁止（Explore のため物理的に不可。Read/Grep/Glob/Bash(git) のみ）。テストの実行もしない（読むだけ）。
