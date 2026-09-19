# コミット規約（TDD スキル共通）— shipment-api

> `tdd-commit` および `tdd-coverage-review` のコミット作成が従う規約。

## 署名（バージョンを焼かない）

すべてのコミットメッセージ末尾に：
```
Co-Authored-By: Claude <noreply@anthropic.com>
```
- **モデルバージョン（Sonnet 4.5 等）を署名に書かない**。スキルは将来別バージョン/別モデルで実行されるため陳腐化する。汎用 `Claude` で固定。

## メッセージ書式
- **日本語**で書く（`Co-Authored-By` 行のみ英語）。
- サマリー行: 型プレフィックス + 日本語、50〜72字目安。型: `feat / fix / test / refactor / perf / docs / chore`。
- 1サイクルの小さな変更は1行で可。複数変更を含む場合のみ詳細セクション（空行 + 箇条書き）。
- TDD メタ情報（Red/Green/サイクル番号/PR番号/計画書§参照）は**書かない**。

## 実行ルール
- **heredoc を使う**:
  ```bash
  git commit -m "$(cat <<'EOF'
  test: ...

  - ...

  Co-Authored-By: Claude <noreply@anthropic.com>
  EOF
  )"
  ```
- **ステージングは個別 `git add <path>`**。`git add .` / `-A` は使わない。
- **`--no-verify` 絶対禁止**: shipment-api は **lefthook / pre-commit の pre-commit hook** があり、`gofmt` / `go vet` / `golangci-lint` が走る。hook をバイパスしてはいけない。
  - lint / vet エラーでコミットがブロックされたら、エラーを修正して再コミット（`--no-verify` で回避しない。`//nolint` で黙らせない）。
  - hook が無いリポでは、コミット前に `make lint`（無ければ `go vet ./... && golangci-lint run ./...`）を手動実行して同等の検査を通す。
- **機密情報チェック**: `.env` / 認証情報 / APIキー / DB 接続文字列（DSN）/ PII を含むファイルはコミットしない（検出時は停止）。
- **生成物・依存の変更を忘れない**: DB マイグレーション（`db/migrations/`）、`go generate` の生成物（sqlc の `*.sql.go` / gomock・mockery・moq のモック）、`go.mod` / `go.sum` の変更は実装と同じコミットに含める（実装だけコミットするとチームでビルドが壊れる）。
- コミット後 `git log -1 --format="%H %s"` で SHA とサマリーを取得し `completed_cycles` に記録（→ `workflow-schema.md`）。

## テスト / CI
- **CI がテストを走らせる**ので、コミット前の「全件手動テスト必須」は不要（push で `go test -race ./...` / `go vet` / `golangci-lint` が自動実行）。
- ただし各サイクルの Green/Refactor で**対象パッケージのテストが pass していること**は必ずローカル確認する（→ `project-settings.md` のコマンド。`-count=1` を忘れない）。

## ブランチ
- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。違反は warning のみ。
