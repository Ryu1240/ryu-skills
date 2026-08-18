---
name: tdd-bootstrap
description: Detect any project's language, test runner, layout and tooling - and interactively interview the user for whatever cannot be detected - to generate a project-specific .claude/skills/_shared-tdd/ for the tdd-universal skills
argument-hint: [--force]
model: opus
allowed-tools:
  - Read
  - Write
  - Glob
  - Grep
  - AskUserQuestion
  - Bash(ls:*)
  - Bash(find:*)
  - Bash(cat:*)
  - Bash(git check-ignore:*)
  - Bash(git log:*)
examples:
  - input: /tdd-bootstrap
    description: 初回セットアップ。プロジェクトを走査し、不明な項目は対話で確認して _shared-tdd/ を生成する。
  - input: /tdd-bootstrap --force
    description: 既に _shared-tdd/ がある場合でも再生成（上書き）する。
---

**任意の言語**のプロジェクトを走査し、`.claude/skills/_shared-tdd/` 配下に project-settings.md を含む 4 ファイルを生成する。

このスキルの役割は「**検出できるものは自動で埋め、できないものはユーザーに聞く**」こと。専用プラグイン（tdd-rails / tdd-python / tdd-frontend / tdd-monorepo）が無いスタックでも TDD ワークフローを成立させるための入口。`/tdd` の Phase 0 から自動呼び出しされるほか、単独でも実行できる。

> 原則: **推測で埋めない**。検出できた項目は「検出値」として提示し、できなかった項目は必ず聞く。捏造した値を書くと以降の全フェーズが空振りする。

## 引数

- `--force`: 既存の `.claude/skills/_shared-tdd/` を上書きする。未指定で既存ファイルがある場合は確認のうえ中断（または `[o]` で上書き）。

## Step 1: 上書き判定

`.claude/skills/_shared-tdd/project-settings.md` を Read：

- 存在しない → Step 2 へ
- 存在するが `{{` プレースホルダが残る（未 bootstrap のテンプレ）→ Step 2 へ（埋めに行く）
- 存在し設定済み、`--force` なし → 「既に設定済みです。再生成しますか？ [o]上書き / [n]中断」を確認（**停止**）
  - 部分的な修正だけなら `/tdd-project-settings-update` の方が適切、と併せて案内する。
- 存在し設定済み、`--force` あり → Step 2 へ（上書き）

## Step 2: スタック検出

### 2-1. マニフェストからの言語・ランナー判定
`Glob`（`node_modules` / `vendor` / `.git` / ビルド出力は除外）でマニフェストを探し、下表で当たりを付ける。**複数ヒットしたらモノレポ/多言語**なので、対象パッケージをユーザーに選ばせる（Step 3 で質問）。

| マニフェスト | 言語 | 主なテストランナー（依存ファイルを Grep して確定） |
|---|---|---|
| `Gemfile` | Ruby | RSpec / Minitest |
| `pyproject.toml` / `setup.py` / `requirements*.txt` / `Pipfile` | Python | pytest / unittest |
| `package.json` | JS / TS | Vitest / Jest / Mocha / `node:test` / Playwright(e2e) |
| `go.mod` | Go | 標準 `testing`（+ testify） |
| `Cargo.toml` | Rust | 標準 `#[test]`（+ nextest） |
| `pom.xml` / `build.gradle(.kts)` | Java / Kotlin | JUnit 5 / JUnit 4 / Spock / Kotest |
| `composer.json` | PHP | PHPUnit / Pest |
| `*.csproj` / `*.sln` | C# / .NET | xUnit / NUnit / MSTest |
| `mix.exs` | Elixir | ExUnit |
| `Package.swift` / `*.xcodeproj` | Swift | XCTest / Swift Testing |
| `pubspec.yaml` | Dart / Flutter | `package:test` / `flutter_test` |
| `build.sbt` | Scala | ScalaTest / MUnit |
| `*.cabal` / `stack.yaml` | Haskell | Hspec / tasty |
| `CMakeLists.txt` / `Makefile` | C / C++ | GoogleTest / Catch2 / CTest |

### 2-2. テスト実行コマンドの候補
ランナーが確定したら、下表を**候補**として提示する（確定はユーザー承認 or スクリプト定義の実物優先）。
`package.json` の `scripts` / `Makefile` のターゲット / `Rakefile` / `justfile` / CI 設定に**実際のコマンドがある場合はそれを最優先**する（プロジェクトの正解はそこに書かれている）。

| ランナー | 単一ケース | 単一ファイル | ランダム順序 |
|---|---|---|---|
| RSpec | `bundle exec rspec {path}:{line}` | `bundle exec rspec {path}` | `--order random` |
| Minitest | `bin/rails test {path}:{line}` | `bin/rails test {path}` | `--seed N` |
| pytest | `pytest "{path}::{case}"` | `pytest {path}` | `-p randomly`（pytest-randomly） |
| Vitest | `vitest run {path} -t "{case}"` | `vitest run {path}` | `--sequence.shuffle` |
| Jest | `jest {path} -t "{case}"` | `jest {path}` | `--randomize` |
| `node:test` | `node --test --test-name-pattern "{case}"` | `node --test {path}` | （標準では未対応） |
| Go testing | `go test {pkg} -run '^{case}$'` | `go test {pkg}` | `-shuffle=on` |
| Rust | `cargo test {module}::{case}` | `cargo test {module}` | （nextest: `--shuffle`） |
| JUnit(Maven) | `mvn test -Dtest={Class}#{case}` | `mvn test -Dtest={Class}` | （順序は `@TestMethodOrder` 依存） |
| JUnit(Gradle) | `gradle test --tests '{Class}.{case}'` | `gradle test --tests '{Class}'` | 同上 |
| PHPUnit | `vendor/bin/phpunit --filter '{case}'` | `vendor/bin/phpunit {path}` | `--order-by=random` |
| Pest | `vendor/bin/pest --filter '{case}'` | `vendor/bin/pest {path}` | `--order-by=random` |
| .NET | `dotnet test --filter 'FullyQualifiedName~{case}'` | `dotnet test --filter '...'` | （ランナー依存） |
| ExUnit | `mix test {path}:{line}` | `mix test {path}` | `--seed N`（既定でランダム） |
| XCTest | `swift test --filter '{case}'` | `swift test --filter '{Suite}'` | （未対応） |
| Dart/Flutter | `flutter test {path} --plain-name '{case}'` | `flutter test {path}` | `--test-randomize-ordering-seed random` |

> **表に無いランナー / 表と実態が違う場合は、必ず Step 3 で聞く**。表は当て推量の材料であって、正解ではない。

### 2-3. 周辺ツールの検出
| 項目 | 確認方法 |
|---|---|
| プロジェクト名 | マニフェストの name / `git remote get-url origin` の末尾 / cwd 名 |
| テスト配置・命名 | `Glob` で既存テストを列挙 → co-located か別ツリーか、ファイル名パターン、件数 |
| ケース記述スタイル | 既存テストを**1〜2件 Read** して実物から抽出 |
| テストデータ生成 | factory / fixture / builder / ヘルパの有無を Grep |
| モック手段 | HTTP スタブ・モックライブラリを依存ファイルから Grep |
| lint / format / 型 | 設定ファイル（`.eslintrc*` / `.rubocop.yml` / `ruff.toml` / `.golangci.yml` / `clippy` / `mypy.ini` 等）とスクリプト定義 |
| pre-commit hook | `.husky/` / `.pre-commit-config.yaml` / `.git/hooks/` / `lefthook.yml` |
| CI | `.github/workflows/*.yml` / `.circleci/config.yml` / `.gitlab-ci.yml` / `Jenkinsfile` |
| ブランチ規約 | `git log --oneline -20` と現在ブランチ名から推定（コミット規約も併せて観察） |
| 独立性の担保 | テストのセットアップ/ティアダウン（`beforeEach`/`setUp`/`t.Cleanup`/`fixture` 等）を Read して実態を抽出 |

### 2-4. 検出結果の提示
```
🔍 プロジェクト走査結果

| 項目 | 検出値 | 確度 |
|---|---|---|
| プロジェクト名 | <name> | 確定 |
| 言語 | <lang> | 確定 |
| テストランナー | <runner> | 確定 / 推定 |
| 単一ケース実行 | <cmd> | 推定（要確認） |
| テスト配置 | <layout>（既存 N 件） | 確定 |
| ケース記述スタイル | <実物から抽出> | 確定 |
| 独立性の担保 | <抽出結果 or 不明> | 推定 / 不明 |
| lint / 型 | <cmd or 未導入> | 確定 |
| pre-commit hook | あり / なし | 確定 |
| CI | <name or なし> | 確定 |

❓ 未確定の項目: <列挙>
```

---

## Step 3: 対話ヒアリング（未確定項目のみ・このスキルの本体）

**未確定・推定の項目だけ** AskUserQuestion で聞く。確定済みを聞き直して手間を増やさない。
1 回の AskUserQuestion に最大 4 問まで。項目が多ければ**優先度順に複数回**に分ける（下記の優先順）。

### 優先度 1（これが無いと動かない・必ず確定させる）
1. **対象パッケージ**（多言語/モノレポ検出時のみ）: 候補ディレクトリを選択肢に。
2. **テストランナー**（推定止まりのとき）: 候補を選択肢に + 「その他」で自由入力。
3. **単一ケース実行コマンド**: 検出/表からの候補を提示し、実物と合っているか確認。`{path}`/`{case}`/`{line}` のどの形式かも確定させる。
4. **単一ファイル実行コマンド**: 同上。

### 優先度 2（品質に直結）
5. **テスト独立性の担保方法**: 選択肢例 —「トランザクションロールバック」「各ケースで DB/状態を初期化」「モック・スタブを毎回リセット」「共有状態なし（純粋関数中心）」「その他（自由入力）」。**複数選択可**（`multiSelect: true`）。
6. **ランダム順序実行コマンド**: 候補提示 or 「未対応」。
7. **言語固有の慣習**: 自由入力で「このリポでテストを書くときに必ず守っていること」を聞く（例: table-driven test にする / モックは手書きに限る / アサーションは1ケース1つ / 生成物もコミットする）。

### 優先度 3（あると良い）
8. lint 自動修正コマンド / 型チェックコマンド（未検出時）。
9. カバレッジコマンド（未検出時）。
10. プロジェクト固有の追加不変条件（`{{EXTRA_INVARIANTS}}`。無ければ空でよい）。

> 質問設計の指針: 選択肢には**検出値を第一候補（推奨）**として置く。ユーザーが「その他」で自由入力した内容はそのまま採用する。**分からないと言われた項目は「未導入」「未対応」と明記して書く**（推測で埋めない）。

---

## Step 4: 承認ゲート

検出値 + ヒアリング結果を統合し、**生成される project-settings.md の全項目**を一覧提示：

```
↑ の内容で `.claude/skills/_shared-tdd/` を生成しますか？
[y] 生成 / [e] 個別編集 / [n] 中断
```

- `[y]` → Step 5 へ
- `[e]` → 「どの項目を変更しますか？」を聞き、自由入力で上書き。再度 `[y]/[e]/[n]` 確認。
- `[n]` → 中断（何も生成しない）

承認なしに Write してはいけない（**停止**）。

## Step 5: ファイル生成

`.claude/skills/_shared-tdd/` を作成し、以下 4 ファイルを Write：

### 5-1. `project-settings.md`
plugin 同梱テンプレ（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/project-settings.md`）を Read し、**すべての `{{...}}` を確定値で置換**して Write。
- **`{{` を1つも残さない**（残っていると `/tdd` の Phase 0 が未 bootstrap と判定して止まる）。
- 「無い」ものは削除ではなく **「未導入」「未対応」「なし」と明記**する（後から `/tdd-project-settings-update` で追記しやすい）。
- `{{LANGUAGE_IDIOMS}}` / `{{ISOLATION_STRATEGY}}` はヒアリング結果を箇条書きで。空にしない（何も無ければ「特になし（既存テストの慣習を踏襲する）」と書く）。
- `{{EXTRA_INVARIANTS}}` が空なら、不変条件の 8 番目の項目行を削除する。

### 5-2. `commit-convention.md` / `workflow-schema.md` / `state-machine.md`
plugin 同梱の **テンプレ**（`${CLAUDE_PLUGIN_ROOT}/skills/_shared-tdd/{filename}`）を Read してそのまま Write する（プロジェクト固有差分は project-settings.md に集約）。`${CLAUDE_PLUGIN_ROOT}` が解決できない環境では `plugins/tdd-universal/skills/_shared-tdd/{filename}` を相対 Read する。

### 5-3. 自己検証（必須）
生成した `project-settings.md` を Read し直し、**`{{` が残っていないこと**と、単一ケース/単一ファイル実行コマンドが実在することを確認する。残っていれば埋めてから完了とする。

## Step 6: ワークフロー状態の git 追跡設定（確認）

`/tdd` は実行中に `.claude/tdd-workflow/` へ状態ファイルを書き出す（`workflow-{id}.json` / `current-cycle.json` / `notion-context-*.json` / `optimization-report-*.md`）。これらは**開発者ごとの進行中の作業状態**であり、コミットするとレビューのノイズや複数人作業時のコンフリクトの原因になる。Notion 連携を使う場合はタスク本文のキャッシュも含まれる。

### 6-1. 現状確認
```bash
git check-ignore -q .claude/tdd-workflow/ && echo ignored || echo not-ignored
```
- **既に無視されている** → 何もせず次へ（サマリで「設定済み」と報告）。
- **無視されていない** → 6-2 へ。
- git 管理下でない（コマンドが失敗する）→ このステップをスキップ。

### 6-2. ユーザーに確認（AskUserQuestion・必須）
「TDD ワークフローの状態ファイルを git 管理から除外しますか？」として次を提示する:

- **`.gitignore` に追加（推奨）** — チーム全員に効く。`.gitignore` の変更自体はコミット対象になる。
- **`.git/info/exclude` に追加** — このクローンのみ。`.gitignore` を変更したくない場合に。他メンバーには効かない。
- **除外しない** — ワークフローの計画・進捗をチームで共有・レビューしたい場合。

### 6-3. 適用（承認された選択のみ）
対象ファイル（`.gitignore` または `.git/info/exclude`）を Read し、**同じ行が既にあれば何もしない**。無ければ末尾に追記して Write する:

```
# TDD ワークフローの進行状態（開発者ごとの一時ファイル）
.claude/tdd-workflow/
```

追記後に `git check-ignore -q .claude/tdd-workflow/` を再実行し、**実際に効いていることを確認**する。効いていなければ原因（別の否定パターン等）を提示する。

> ⚠️ `.claude/skills/_shared-tdd/` は**チームで共有すべき設定**なので絶対に ignore しない。このステップの対象は `.claude/tdd-workflow/` のみ。

## Step 7: サマリ提示

```
✅ Bootstrap 完了 — `.claude/skills/_shared-tdd/`
言語: {lang} / ランナー: {runner} / 対象: {package_root}

- project-settings.md  (検出 + ヒアリングから生成)
- commit-convention.md / workflow-schema.md / state-machine.md (テンプレからコピー)

ヒアリングで確定した項目: {列挙}
未導入として記録: {列挙}

次のステップ:
1. project-settings.md を確認（特にテスト実行コマンド）
2. /tdd "<タスク>" で TDD ワークフロー開始
   ※ 後から直すときは /tdd-project-settings-update "<指示>"
```

> サマリには**ワークフロー状態の git 追跡設定の結果**（`.gitignore` に追加 / `.git/info/exclude` に追加 / 除外しない / 既に設定済み）を 1 行含める。

## エラーハンドリング

- **マニフェストが1つも見つからない**: 「言語を自動判定できませんでした」と伝え、Step 3 の優先度1をすべてヒアリングして生成する（自動検出ゼロでも対話だけで成立させる）。
- **既存テストが0件**: ケース記述スタイル・独立性の担保方法を実物から抽出できないため、両方ヒアリングする。「最初のテストがこのリポの流儀を決める」ことを伝える。
- **専用プラグインが存在するスタックだった場合**（Rails / Python+pytest / Vue+Vitest / Rails+Vue モノレポ）: その旨を提示し、`tdd-rails` / `tdd-python` / `tdd-frontend` / `tdd-monorepo` の方が言語固有の作法まで踏み込めることを案内する。ただし**ユーザーがこのまま汎用版で進めたい場合はそのまま生成する**（強制しない）。
- **既存 `.claude/skills/_shared-tdd/` がある状態で `--force` 未指定** → 承認なしに上書きしてはいけない。
