# コミット規約（TDD スキル共通）

> `tdd-commit` および `tdd-coverage-review` のコミット作成が従う規約。

## 署名（バージョンを焼かない）

すべてのコミットメッセージ末尾に以下を付ける：

```
Co-Authored-By: Claude <noreply@anthropic.com>
```

- モデルバージョン（4.7 / 4.8 等）を署名に書かない。スキルは将来別バージョン/別モデルで実行されるため、
  バージョンを焼くと陳腐化する。
- どのモデルが書いたかの記録が必要なら commit メタではなく別手段で（規約としては汎用 `Claude` で固定）。

## メッセージ書式

- 日本語で書く（既存 git log の大多数が日本語）。`Co-Authored-By` 行のみ英語。
- サマリー行: 型プレフィックス + 日本語、50〜72文字目安。
  型: `feat / fix / test / refactor / perf / docs / chore`。
- 1サイクルの小さな変更は1行で可。複数変更を含む場合のみ詳細セクション（空行 + 箇条書き）。
- TDD メタ情報（Red/Green/サイクル番号/PR番号/計画書§参照）は書かない（不変条件）。

例：
```
test: Task のラウンドトリップテストを追加
```
```
feat(task-schemas): Task を追加し roundtrip 契約をピン留め
```

## 実行ルール

- heredoc を使う（複数行を正しく整形）：
  ```bash
  git commit -m "$(cat <<'EOF'
  test: ...

  - ...

  Co-Authored-By: Claude <noreply@anthropic.com>
  EOF
  )"
  ```
- ステージングは個別 `git add <path>`。`git add .` / `git add -A` は使わない（意図しないファイル混入防止）。
- `--no-verify` は使わない（将来 hook が入っても習慣的にバイパスしないため）。
- 機密情報チェック: `.env` / 認証情報 / APIキー / PII / S3 鍵 / 個人特定可能パス を含むファイルはコミットしない（検出時は停止）。
- コミット後 `git log -1 --format="%H %s"` で SHA とサマリーを取得し、`completed_cycles` に記録（→ `workflow-schema.md`）。

## ブランチ

- 推奨: `feature/<TICKET-KEY>/<package>/<feature>`。違反は warning のみ（ブロックしない）。
- PR 作成前に手動で全件テスト（CI ではテストが走らないため。→ `project-settings.md`）。
