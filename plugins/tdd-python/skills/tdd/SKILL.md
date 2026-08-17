---
name: tdd
description: taskcli 向け Full TDD workflow orchestrator (Plan → Red→Green→Refactor→Commit cycles → Coverage Review → Optimize) for Python/pytest/pydantic projects with optional Notion integration
argument-hint: <task_url_or_text_or_workflow_id>[ -- <additional_instructions>] [--phase=red|green|refactor|commit|coverage-review|optimize] [--auto|--phase-stop]
model: opus
allowed-tools:
  - Skill
  - ToolSearch
  - TaskCreate
  - TaskUpdate
  - TaskGet
  - TaskList
  - Read
  - Write
  - Edit
  - Bash(date:*)
  - Bash(git:*)
  - Bash(docker:*)
  - Grep
  - Glob
examples:
  - input: /tdd https://www.notion.so/task-id
    description: Plan phase from Notion task (writes workflow JSON, then stops)
  - input: /tdd "Task に priority フィールドを追加" -- field_validator は schemas/_common.py の既存定数を再利用
    description: Plan phase from free-text with additional instructions saved to user_instructions
  - input: /tdd
    description: 引数なし。進行中ワークフローがあれば再開を提案、無ければ会話文脈から計画
  - input: /tdd tdd-20260613-101500
    description: 既存ワークフローの実行（current_cycle から継続、既定はフェーズ停止）
  - input: /tdd tdd-20260613-101500 --auto
    description: 一気通貫モードで実行（承認は Opus 代行レビュー、逸脱時のみ停止）
  - input: /tdd tdd-20260613-101500 -- サイクル5を削除、サイクル4の関数名を変更
    description: 進行中ワークフローを tdd-workflow-update サブスキルで動的更新してから継続
---

`taskcli` リポジトリの `taskcli` パッケージに対して、完全な TDD ワークフロー
（Plan → Red→Green→Refactor→Commit サイクル → Coverage Review → Optimize）を実行する。

## 起動時に必ず読む共通契約（単一情報源）

以下を Read して全フェーズの前提とする。本スキルおよびサブスキルはこれらに従う：

- `.claude/skills/_shared-tdd/project-settings.md` — 対象・パス・実行コマンド・**不変条件**・現行構成
- `.claude/skills/_shared-tdd/workflow-schema.md` — 状態 JSON の**正準スキーマ（キー名固定）**
- `.claude/skills/_shared-tdd/state-machine.md` — フェーズ遷移・**2モード**・承認ゲート・停止条件
- `.claude/skills/_shared-tdd/commit-convention.md` — コミット規約・署名

> 不変条件の要点（詳細は project-settings）: 1サイクル=1テスト=1コミット / TDDメタ情報をコードに書かない /
> テストは docker compose 経由 / StrictModel 継承 / Green は最小実装 / 承認ゲートは Red後と Commit前のみ /
> 既定はフェーズ停止・一気通貫は `--auto`。

---

## Phase 0: Project Settings 確認（自動）

引数解析・以降のすべてのフェーズに先立って実行する。`.claude/skills/_shared-tdd/project-settings.md` を Read し、次のいずれかなら **bootstrap を提案して停止**する：

1. **不在**:
   ```
   ⚠️ `.claude/skills/_shared-tdd/project-settings.md` が見つかりません。
   このプロジェクト用の TDD 設定を生成しますか？
   [y] /tdd-bootstrap を実行 / [n] 中断
   ```
   - `[y]` → `Skill(tdd-bootstrap)` を起動。完了後に Phase 0 から再実行。
   - `[n]` → 中断（Phase 1 以降へは進まない）。

2. **サンプル設定のまま**: 内容に `taskcli` というパッケージ名が含まれていれば「サンプル既定値」と判定。
   ```
   ⚠️ project-settings.md がサンプル設定（taskcli）のままです。
   このプロジェクト用に書き換えますか？
   [y] /tdd-bootstrap を実行 / [s] このまま続行 / [n] 中断
   ```
   - `[y]` → `Skill(tdd-bootstrap)` 起動。完了後 Phase 0 から再実行。
   - `[s]` → 警告を残したまま引数解析へ進む（既定値ベースで動作。テスト計画が空振りする可能性あり）。
   - `[n]` → 中断。

3. **カスタマイズ済み**（パッケージ名が `taskcli` を含まない、または bootstrap 生成済み）→ そのまま引数解析へ進む。

> `--phase=...` 指定時も Phase 0 は実行する（コミット・コマンドの参照解決に project-settings が必要なため）。

---

## 引数解析

### Step 0: `--` 分割とフラグ抽出

- 引数全体を最初の ` -- `（前後スペース付き）で `primary` と `additional_instructions` に2分割（` -- ` 無しなら後者は None）。
- `--auto` / `--phase-stop` / `--phase=...` フラグを抽出して `primary` から除く。
  - `--auto` → `run_mode = "auto"`、`--phase-stop` → `run_mode = "phase-stop"`（既定）。
- `additional_instructions` が非 None なら、計画時は `user_instructions` に即保存し対話質問（3-2b）を SKIP。

### ケース判定

| primary | additional | ルート |
|---|---|---|
| `notion.so` を含む URL | — | **計画**（Phase 1a → 2 → 3） |
| URL でも workflow_id でもない自由テキスト | — | **計画**（Phase 1b → 2 → 3） |
| 空（引数なし） | — | **再開検出**（下記）→ 無ければ Phase 1c |
| `tdd-YYYYMMDD-HHMMSS` 形式 | None | **実行**（Phase 4 から、`current_cycle` で継続） |
| `tdd-...` 形式 | 非 None | **動的更新**: `tdd-workflow-update` を Skill 起動 → 承認されたら再読込して Phase 4 継続。承認されなければ中断 |
| `--phase=coverage-review` / `=optimize` | — | 該当フェーズのみ実行 |

### 引数なし時の再開検出

`Glob .claude/tdd-workflow/workflow-*.json` で `status:"in_progress"` のものを `updated_at` 降順に探す：

- 1件以上あれば最新を提示して再開可否を問う（**停止**）：
  ```
  進行中ワークフローを検出: {workflow_id}
    タスク: {task_title}
    進捗: サイクル {current_cycle-1}/{total_cycles} 完了、現在 {current_phase}
  [Enter] このワークフローを再開（Phase 4 へ） / [n] 無視して会話文脈から新規計画（Phase 1c）
  ```
- 無ければ Phase 1c（会話文脈から計画）。

---

## Phase 1: タスク仕様の取得（計画ルートのみ）

### 1a. Notion URL
1. **ToolSearch でキーワード解決**: `query: "notion-fetch"` を実行し、利用可能な `*notion-fetch` ツールを得る。
   （サーバー ID はハードコードしない。環境により `mcp__<id>__notion-fetch` の `<id>` が変わるため。）
2. 解決した notion-fetch ツールで取得。`page_id` は URL から: `?` 以降除去 → 32桁 hex 抽出 → `8-4-4-4-12` 形式に整形。
3. タスクタイトル / 内容 / 技術的制約 を抽出。取得結果を `.claude/tdd-workflow/notion-context-{page_id}.json` にキャッシュ（再実行時に優先利用）。

### 1b. 自由テキスト
引数全体をタスク仕様とする。タイトルは冒頭から自動生成（最大60字）、本文は全体、制約は明記分を抽出。

### 1c. 引数なし
会話文脈・開いているファイルから推定し、タイトル/内容を提示して確認（**停止**）。`[m]` なら再入力。

### 1-3. workflow_id 生成
`date +%Y%m%d-%H%M%S` → `workflow_id = tdd-{timestamp}`。

---

## Phase 2: 既存コード分析（計画ルートのみ）

- タスクから `target_module` を判定（`schemas` / `commands` / `storage` / `cli`）。判定不能なら停止して確認。
- project-settings の「テスト構成」表で対象テストファイルを決定。Grep/Glob で既存モデル・テスト・fixture を探索（最大5件）し Read。
- 既存パターン（`StrictModel`、命名規則定数の場所 `schemas/_common.py`、テスト構造、`load_json`）を `patterns` に記録。

---

## Phase 3: タスク分解 → JSON 確定書き込み（計画ルートのみ）

### 3-1. 分解（1サイクル=1テスト）
各サイクルが1テスト関数（or 1 parametrize エントリ）になるよう分解。各サイクルに `kind`（`schema_roundtrip` / `logic` / `validation`）を付ける。
推奨順序: basic roundtrip → json_string → missing required → extra forbidden → type mismatch → invariant（命名/値域/model_validator）→ collection。
ロジック系（CLI コマンド/storage/IO）は「1関数の1挙動 = 1サイクル」で分解（正常系→異常系→境界）。

### 3-2. TaskCreate
タイトル `TDD: {task_title}`、各サイクルを1項目で作成。返却 ID を `todo_task_id` に記録。

### 3-2b. ユーザー指示（additional_instructions が None のときのみ）
追加指示の有無を確認（**停止**）。入力されれば `user_instructions` に保存。空なら空文字。
（additional_instructions が渡されている場合はこのステップを SKIP し、その内容を保存済みとする。）

### 3-3. ワークフロー JSON の確定書き込み（最重要）
`workflow-schema.md` の**正準スキーマ**に従い `.claude/tdd-workflow/workflow-{workflow_id}.json` を **Write**する。
必須キーをすべて埋める（`schema_version:1`, `status:"planning_done"`, `run_mode`, `cycle_plan`, `total_cycles`,
`current_cycle:1`, `todo_task_id`, `completed_cycles:[]`, `created_at`, `updated_at` 等）。

**自己検証（必須）**: 書いた JSON を Read し直し、必須キーが全て揃い `cycle_plan` 長 == `total_cycles` であることを確認。
欠落があれば書き直す。**揃うまで計画完了としない**。

### 3-4. 計画完了（停止）
```
📋 計画フェーズ完了 — {workflow_id}（{total_cycles} サイクル, run_mode={run_mode}）
JSON: .claude/tdd-workflow/workflow-{workflow_id}.json に保存済み

承認したら次で実行: /tdd {workflow_id}        （既定: フェーズ停止）
一気通貫で回す場合:   /tdd {workflow_id} --auto
```
ここで**停止**。Phase 4 には進まない（計画ルートは必ずここで終わる）。

---

## Phase 4: TDD サイクルループ（実行ルート）

`state-machine.md` の遷移表に従う。**モード（`run_mode`）と承認ゲートは state-machine の定義に厳密に従うこと。**

### 4-1. 復元
`workflow-{id}.json` を Read（必須キー検証）。`current_cycle` で次サイクルを特定。`run_mode` を取得（引数で上書き指定があれば更新して保存）。
`todo_task_id` で TODO を TaskGet。未完了サイクルが無ければ Phase 5 へ。

### 4-2. サイクル実行（state-machine 表 #2〜#8）
各サイクルで以下を呼ぶ。引数は `{workflow_id}`：

1. **Red**: `Skill(tdd-red, "{workflow_id}")` → テスト追加・失敗確認・`current-cycle.json` 作成。
   → **承認ゲート①**: state-machine に従う。`phase-stop` は停止してテストコードを提示・承認待ち。`auto` は代行レビュー（整合なら継続、逸脱で停止）。
2. **Green**: `Skill(tdd-green, "{workflow_id}")` → 最小実装・pass。（自動遷移）
3. **Evac(plan)**: `Skill(tdd-evacuator, "{workflow_id} --mode=plan")` → 提示のみ。（自動遷移）
4. **Refactor**: `Skill(tdd-refactor, "{workflow_id}")` → 品質改善・pass維持。（自動遷移）
5. **Evac(review)**: `Skill(tdd-evacuator, "{workflow_id} --mode=review")` → 評価提示。
   → **承認ゲート②**: state-machine に従う。`phase-stop` は停止して Refactor 結果を承認待ち。`auto` は代行レビュー。
6. **Commit**: `Skill(tdd-commit, "{workflow_id}")` → コミット・`completed_cycles` 追記・`current-cycle.json` 削除。

### 4-3. Commit 検証ゲート（必須）
tdd-commit 後に Bash/Read で検証（すべて pass で先へ。失敗なら tdd-commit 再実行を指示して中断）：
- `git log -1 --format="%H"` が空でない。
- `workflow-{id}.json`: `completed_cycles` 末尾の `commit` が上記 SHA と一致、`current_cycle` が +1 済み。
- `current-cycle.json` が**存在しない**。

### 4-4. サイクル境界（停止 or 継続）
TaskUpdate で完了サイクルを `[x]`。次の挙動は `run_mode` に従う：
- `phase-stop`: まず `Skill(tdd-evacuator, "{workflow_id} --mode=boundary")` で**次サイクル以降の追加テスト提案**を取得し、提案リストとともに**停止**して提示：
  ```
  ✅ Commit {commit_sha} / 進捗 {current_cycle-1}/{total_cycles}

  📋 追加テスト提案（次サイクル以降）:
    1. {test_file}: {テスト関数の概要} — {理由}
    2. ...
  [Enter] 次サイクルへ / [+] 上記提案からテストを追加（サイクル挿入） / [a] ここから一気通貫(--auto) / [q] 残りスキップして Coverage Review
  ```
  - `[+]`: 採用する提案（番号 or 自由入力）を聞き、`cycle_plan` 末尾に追加・`total_cycles`+1（JSON と TODO 両方更新）。
  - `[a]`: `run_mode="auto"` に更新して保存し、停止せず継続。
  - `[q]`: Phase 5 へ。
- `auto`: 停止せず次サイクルの Red へ（サイクル境界の提案はスキップし、スコープは計画どおり維持）。ただし state-machine の「停止すべき条件」に該当したら強制停止。

### 4-5. ループ判定
未完了サイクルあり → 4-2 へ。全完了 or `[q]` → Phase 5 へ。

---

## Phase 5: Coverage Review
`Skill(tdd-coverage-review, "{workflow_id}")`。モデル×カテゴリ網羅性を分析し不足テストを追加・コミット、`coverage_review` を記録。（自動遷移）
**早期終了（[q]）後こそ価値が高いので必ず実行する。**

## Phase 5b: Optimize
`Skill(tdd-optimize, "{workflow_id}")`（assess→analyze→plan→**承認**→execute→独立性検証）。テスト最適化は承認後に適用。
> 担保重複（セマンティック重複）の整理が必要なら、別途 `tdd-coverage-overlap` を手動で実行（CI 常用しない単発作業）。

## Phase 6: 完了 + アーカイブ
- `workflow-{id}.json` を Read し完了サマリを表示（タスク / 完了サイクル数 / コミット / テスト・実装ファイル / coverage_review）。
- `status` を `"done"`、`updated_at` 更新。
- 任意: `status:"done"` の古いワークフロー JSON を `.claude/tdd-workflow/archive/` に移動（蓄積防止）。
- 次ステップ案内（全件 pytest → PR 作成。CI ではテストが走らない点を明記）。

---

## エラーハンドリング

- **Notion 取得失敗**: 原因（MCP 未起動 / page_id 無効 / 権限）を提示し、自由テキスト再起動を案内して中断。
- **target_module 判定不能**: 候補を提示してユーザー選択を待つ（停止）。
- **フェーズスキル失敗**: `[r] 再実行 / [s] 保存して一時停止 / [q] Coverage Review へ` を提示。状態は保存済みなので再開可能。
- **状態 JSON 不整合**（必須キー欠落・スキーマ不一致）: state-machine の停止条件に該当。修正方法を提示して中断。

すべてのフェーズ完了/中断時に `updated_at` を更新し、ファイルから再開可能な状態を保つ（フェーズ停止運用の前提）。
