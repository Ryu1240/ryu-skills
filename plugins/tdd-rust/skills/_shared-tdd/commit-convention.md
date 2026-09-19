# コミット規約（TDD スキル共通）— ledger-core

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
- **`--no-verify` 絶対禁止**: ledger-core は **pre-commit hook（pre-commit / lefthook、または cargo-husky の precommit-hook feature）** で `cargo fmt --check` と `cargo clippy -- -D warnings` が走る。hook をバイパスしてはいけない。
  - fmt / clippy でコミットがブロックされたら、`cargo fmt --all` と警告の修正で解消して再コミット（`--no-verify` で回避しない。`#[allow(clippy::...)]` で黙らせない）。
  - hook が無いリポでは、コミット前に `just lint`（または project-settings の静的解析コマンド）を手動実行する。
- **機密情報チェック**: `.env` / 認証情報 / APIキー / `DATABASE_URL` などの接続文字列 / PII を含むファイルはコミットしない（検出時は停止）。
- **忘れやすい生成物を必ずステージングする**:
  - DB マイグレーション（`migrations/`）と **`.sqlx/` のオフラインクエリデータ**（`cargo sqlx prepare` の生成物。実装だけコミットすると CI の `SQLX_OFFLINE` ビルドが壊れる）
  - **`Cargo.lock`** の変更（依存の追加・更新を伴う場合）
  - `insta` のスナップショット（`*.snap`。`.snap.new` は残さない）
- コミット後 `git log -1 --format="%H %s"` で SHA とサマリーを取得し `completed_cycles` に記録（→ `workflow-schema.md`）。

## テスト / CI
- **CI がテストを走らせる**ので、コミット前の「全件手動テスト必須」は不要（push で `cargo test` / `cargo clippy` / `cargo fmt --check` が自動実行）。
- ただし各サイクルの Green/Refactor で**対象テストが pass していること**は必ずローカル確認する（→ `project-settings.md` のコマンド）。

## ブランチ
- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。違反は warning のみ。
