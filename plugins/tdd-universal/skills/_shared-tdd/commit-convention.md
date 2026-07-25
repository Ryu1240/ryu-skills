# コミット規約（TDD スキル共通）— 汎用

> `tdd-commit` および `tdd-coverage-review` のコミット作成が従う規約。言語に依存しない。

## 署名（バージョンを焼かない）

すべてのコミットメッセージ末尾に：
```
Co-Authored-By: Claude <noreply@anthropic.com>
```
- **モデルバージョン（Sonnet 4.5 等）を署名に書かない**。スキルは将来別バージョン/別モデルで実行されるため陳腐化する。汎用 `Claude` で固定。

## メッセージ書式
- **日本語**で書く（`Co-Authored-By` 行のみ英語）。既存履歴が英語のリポでは既存に合わせる（`git log` を確認）。
- サマリー行: 型プレフィックス + 50〜72字目安。型: `feat / fix / test / refactor / perf / docs / chore`。
- 1サイクルの小さな変更は1行で可。複数変更を含む場合のみ詳細セクション（空行 + 箇条書き）。
- TDD メタ情報（Red/Green/サイクル番号/PR番号/計画書§参照）は**書かない**。

> 既存リポの規約（Conventional Commits / チケット番号プレフィックス等）が `git log` から読み取れる場合は**それを優先**する。

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
- **`--no-verify` 絶対禁止**: pre-commit hook がある場合（→ `project-settings.md` の `{{PRECOMMIT}}`）、hook をバイパスしてはいけない。
  - lint エラーでコミットがブロックされたら、エラーを修正して再コミット（`--no-verify` で回避しない）。
- **機密情報チェック**: `.env` / 認証情報 / APIキー / 外部サービスの認証情報 / PII を含むファイルはコミットしない（検出時は停止）。
- **生成物の扱い**: コード生成・スキーマ生成を伴う言語/ツールの場合、生成物が追跡対象なら忘れずステージングする（→ `project-settings.md` の「言語固有の慣習」）。
- コミット後 `git log -1 --format="%H %s"` で SHA とサマリーを取得し `completed_cycles` に記録（→ `workflow-schema.md`）。

## テスト / CI
- **CI がテストを走らせる**場合（→ `project-settings.md` の `{{CI}}`）、コミット前の「全件手動テスト必須」は不要。
- ただし各サイクルの Green/Refactor で**対象テストが pass していること**は必ずローカル確認する（→ `project-settings.md` の実行コマンド）。

## ブランチ
- `project-settings.md` の `{{MAIN_BRANCH}}` / `{{FEATURE_BRANCH}}` に従う。違反は warning のみ。
