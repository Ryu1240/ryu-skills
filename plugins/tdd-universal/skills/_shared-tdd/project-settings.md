# TDD スキル共通設定（Project Settings）— {{PROJECT_NAME}}

> 全 TDD スキルの単一情報源。各スキルは `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。
> ⚠️ **このファイルは未設定のテンプレートです**（`{{...}}` が残っている＝未 bootstrap）。`/tdd-bootstrap` が検出と対話ヒアリングで埋める。

## スタック

| 項目 | 値 |
|---|---|
| 言語 / バージョン | {{LANGUAGE}} |
| フレームワーク | {{FRAMEWORK}} |
| テストランナー | {{TEST_RUNNER}} |
| 依存管理 | {{PACKAGE_MANAGER}} |
| 対象パッケージ | {{PACKAGE_ROOT}} |

## テスト実行コマンド（最重要）

各フェーズはこの節のコマンドだけを使う。**推測でコマンドを組み立ててはいけない。**
コマンド中の `{path}` / `{case}` / `{line}` は実行時に置換するプレースホルダ。

```bash
{{TEST_ONE_CASE}}     # 単一ケース（Red の失敗確認・独立性検証で使う）
{{TEST_ONE_FILE}}     # 単一ファイル（Green / Refactor の pass 確認）
{{TEST_ALL}}          # 全件
{{TEST_RANDOM}}       # ランダム順序（Optimize の独立性検証で必須。無ければ「未対応」）
{{TEST_COVERAGE}}     # カバレッジ（無ければ「未導入」）
{{STATIC_CHECK}}      # 型チェック / 静的解析（無ければ「未導入」）
{{LINT_FIX}}          # lint 自動修正（無ければ「未導入」）
```

## テスト配置と命名規則

- 配置: {{TEST_LAYOUT}}
- ファイル名: {{TEST_FILE_PATTERN}}
- ケース記述スタイル: {{TEST_CASE_STYLE}}
- テスト種別の区分: {{TEST_KINDS}}

## テストデータ / 外部依存

- データ生成: {{FIXTURE_STRATEGY}}
- 外部依存のモック: {{MOCK_STRATEGY}}
- 契約 / スキーマ検証: {{CONTRACT_CHECK}}

## テスト独立性の担保方法（スタック固有・最重要）

{{ISOLATION_STRATEGY}}

> 例: DB は各ケースでトランザクションロールバック / グローバル状態・シングルトンは teardown でリセット / HTTP スタブは各ケース後にリセット / 一時ディレクトリは毎回新規。
> **ここに書かれた手段を全フェーズが守る。** 順序依存・状態共有を作らない。

## 言語固有の慣習（イディオム）

{{LANGUAGE_IDIOMS}}

> bootstrap のヒアリングと既存コードの観察から記録する。Red のテスト作法・Green の最小実装・Refactor の観点で参照される。

## CI / hook

- CI: {{CI}}
- pre-commit hook: {{PRECOMMIT}}
- lint / format: {{LINTER}}

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。複数テストをまとめない、複数サイクルを1コミットにまとめない。
2. **TDD メタ情報をコード/テストに残さない**（Red/Green/サイクル番号/PR番号/計画書§参照を書かない）。
3. **テストの独立性を必ず保つ**: 上記「テスト独立性の担保方法」に従う。順序依存・グローバル状態の共有を作らない。
4. **既存テストの慣習を踏襲する（汎用版の最重要ルール）**: 新規テストは、対象に最も近い既存テストを Read し、その書式・命名・アサーションスタイル・セットアップ方法に揃える。**このリポの流儀が唯一の正解**であり、一般論の「ベストプラクティス」を持ち込まない。
5. **Green は最小実装のみ**（YAGNI）。後続サイクルが駆動するロジックを先回りしない。共通化・抽出は Refactor で。
6. **承認ゲートは Red 完了後と Commit 直前の2箇所**。Green / Refactor の間は自動遷移してよい。
7. **ターン粒度**: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。
8. {{EXTRA_INVARIANTS}}

## ブランチ / コミット

- main: {{MAIN_BRANCH}}。feature: {{FEATURE_BRANCH}}。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション（`tdd/SKILL.md` の Phase 1a 参照）。
