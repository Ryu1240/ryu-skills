# コミット規約（TDD スキル共通）— order-api

> `tdd-commit` および `tdd-coverage-review` のコミット作成が従う規約。

## 署名（バージョンを焼かない）

すべてのコミットメッセージ末尾に：
```
Co-Authored-By: Claude <noreply@anthropic.com>
```
- モデルバージョン（Sonnet 4.5 等）を署名に書かない。スキルは将来別バージョン/別モデルで実行されるため陳腐化する。汎用 `Claude` で固定。

## メッセージ書式
- 日本語で書く（`Co-Authored-By` 行のみ英語）。
- サマリー行: 型プレフィックス + 日本語、50〜72字目安。型: `feat / fix / test / refactor / perf / docs / chore`。
- 1サイクルの小さな変更は1行で可。複数変更を含む場合のみ詳細セクション（空行 + 箇条書き）。
- TDD メタ情報（Red/Green/サイクル番号/PR番号/計画書§参照）は書かない。

## 実行ルール
- heredoc を使う:
  ```bash
  git commit -m "$(cat <<'EOF'
  test: ...

  - ...

  Co-Authored-By: Claude <noreply@anthropic.com>
  EOF
  )"
  ```
- ステージングは個別 `git add <path>`。`git add .` / `-A` は使わない。
- `--no-verify` は使わない: order-api は husky + lint-staged の pre-commit hook があり、自動 format と lint チェックが走る。hook を迂回すると、CI で初めて落ちる変更がチームに流れる。
  - lint / type エラーでコミットがブロックされたら、エラーを修正して再コミット（`--no-verify` で回避しない）。
- 機密情報チェック: `.env` / 認証情報 / APIキー / 接続文字列 / PII を含むファイルはコミットしない（検出時は停止）。
- DB マイグレーションを伴う場合: 生成されたマイグレーションファイルを忘れずステージングする（実装だけコミットするとチームで壊れる）。
- コミット後 `git log -1 --format="%H %s"` で SHA とサマリーを取得し `completed_cycles` に記録（→ `workflow-schema.md`）。

## テスト / CI
- CI がテストを走らせるので、コミット前の「全件手動テスト必須」は不要（push で Vitest / ESLint / type-check が自動実行）。
- ただし各サイクルの Green/Refactor で対象テストが pass していることはローカルで確認する（→ `project-settings.md` のコマンド）。

## ブランチ
- main: `main`。feature: `feature/{description}`（例 `feature/<TICKET-KEY>/<short-desc>`）。違反は warning のみ。
