---
name: tdd
description: Full TDD workflow orchestrator (Plan → Red→Green→Refactor→Commit cycles → Coverage Review → Optimize) for a Go backend with the standard testing package, with optional Notion integration
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
  - Grep
  - Glob
examples:
  - input: /tdd https://www.notion.so/task-id
    description: Plan phase from Notion task (writes workflow JSON, then stops)
  - input: /tdd "出荷APIに在庫引当を追加し在庫不足なら409を返す" -- repository はフェイクにせず実DBで
    description: Plan phase from free-text with additional instructions
  - input: /tdd
    description: 引数なし。進行中ワークフローがあれば再開を提案、無ければ会話文脈から計画
  - input: /tdd tdd-20260613-101500
    description: 既存ワークフローの実行（current_cycle から継続、既定はフェーズ停止）
  - input: /tdd tdd-20260613-101500 --auto
    description: 一気通貫モードで実行（承認は Opus 代行レビュー、逸脱時のみ停止）
---

shipment-api（Go バックエンド）に対して、完全な TDD ワークフロー（Plan → Red→Green→Refactor→Commit → Coverage Review → Optimize）を実行する。

## 起動時に必ず読む共通契約（単一情報源）
- `.claude/skills/_shared-tdd/project-settings.md` — レイヤー構成・パス・テストコマンド・**不変条件**・CI/hook
- `.claude/skills/_shared-tdd/workflow-schema.md` — 状態 JSON の**正準スキーマ（キー名固定）**
- `.claude/skills/_shared-tdd/state-machine.md` — フェーズ遷移・**2モード**・承認ゲート・停止条件
- `.claude/skills/_shared-tdd/commit-convention.md` — コミット規約・署名・**hook 準拠**

> 不変条件の要点: 1サイクル=1テスト=1コミット / TDDメタ情報を書かない / **テスト独立性（DBはロールバック・`t.Cleanup` で後片付け）** / **外部 I/O はインターフェイスで注入** / **エラーは `%w` でラップし `errors.Is` で判定** / **`ctx` を第一引数で伝搬・レイヤーの依存方向を守る** / 最小実装 / 承認ゲートは Red後と Commit前 / 既定フェーズ停止・一気通貫は `--auto`。

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

2. **サンプル設定のまま**: 内容に `shipment-api` というリポ名が含まれていれば「サンプル既定値」と判定。
   ```
   ⚠️ project-settings.md がサンプル設定（shipment-api）のままです。
   このプロジェクト用に書き換えますか？
   [y] /tdd-bootstrap を実行 / [s] このまま続行 / [n] 中断
   ```
   - `[y]` → `Skill(tdd-bootstrap)` 起動。完了後 Phase 0 から再実行。
   - `[s]` → 警告を残したまま引数解析へ進む（既定値ベースで動作。パスが空振りする可能性あり）。
   - `[n]` → 中断。

3. **カスタマイズ済み**（リポ名が `shipment-api` を含まない、または bootstrap 生成済み）→ そのまま引数解析へ進む。

> `--phase=...` 指定時も Phase 0 は実行する（コミット・コマンドの参照解決に project-settings が必要なため）。

---

## 引数解析

### Step 0: `--` 分割とフラグ抽出
- 引数全体を最初の ` -- ` で `primary` と `additional_instructions` に2分割（無ければ後者 None）。
- `--auto` → `run_mode="auto"`、`--phase-stop` → `run_mode="phase-stop"`（既定）。`--phase=...` を抽出。
- `additional_instructions` 非 None なら計画時に `user_instructions` へ即保存し対話質問(3-2b)を SKIP。

### ケース判定

| primary | additional | ルート |
|---|---|---|
| `notion.so` を含む URL | — | **計画**（Phase 1a→2→3） |
| URL でも workflow_id でもない自由テキスト | — | **計画**（Phase 1b→2→3） |
| 空（引数なし） | — | **再開検出** → 無ければ Phase 1c |
| `tdd-YYYYMMDD-HHMMSS` 形式 | None | **実行**（Phase 4、`current_cycle` 継続） |
| `tdd-...` 形式 | 非 None | **動的更新**: `tdd-workflow-update` を Skill 起動 → 承認後に再読込して Phase 4 継続 |
| `--phase=coverage-review` / `=optimize` | — | 該当フェーズのみ |

### 引数なし時の再開検出
`Glob .claude/tdd-workflow/workflow-*.json` で `status:"in_progress"` を `updated_at` 降順に探し、あれば最新を提示して再開可否を問う（**停止**）。無ければ Phase 1c。

---

## Phase 1: タスク仕様の取得（計画ルートのみ）

### 1a. Notion URL
1. **ToolSearch でキーワード解決**: `query: "notion-fetch"` を実行し、利用可能な `*notion-fetch` ツールを得る（サーバー ID はハードコードしない）。
2. 解決したツールで取得。`page_id` は URL から: `?` 以降除去 → 32桁 hex 抽出 → `8-4-4-4-12` 形式に整形。
3. タイトル / 内容 / 技術的制約 を抽出し `.claude/tdd-workflow/notion-context-{page_id}.json` にキャッシュ。

### 1b. 自由テキスト
引数全体をタスク仕様に。タイトルは冒頭から自動生成（最大60字）。

### 1c. 引数なし
会話文脈・開いているファイルから推定し、提示して確認（**停止**）。`[m]` なら再入力。

### 1-3. workflow_id 生成
`date +%Y%m%d-%H%M%S` → `workflow_id = tdd-{timestamp}`。

---

## Phase 2: 既存コード分析 + レイヤー判定（計画ルートのみ）

- **レイヤー判定**: タスク内容から主戦場を判定する（`patterns.layer`）。
  - HTTP の入出力・ステータスコード・リクエストのデコード/バリデーション → `handler`
  - ビジネスロジック・複数リソースの整合・業務エラー（sentinel error）の判定 → `service`（+ `domain`）
  - クエリ・永続化・集計・トランザクション → `repository`
  - 型・sentinel error・値オブジェクトの定義のみ → `domain`
  - CLI プロジェクト（cobra 等）なら `cli`（`cmd/` の `Execute` をテスト。project-settings の読み替えに従う）
  - 複数レイヤーに跨る場合は**サイクルを分ける**（1サイクル=1レイヤーが原則。handler の HTTP 契約テストと service のロジックテストを混ぜない）。
- project-settings の構成に従い、Grep/Glob で既存テスト（`*_test.go`）・フェイク/ファクトリ（`internal/testutil/`）・実装を探索（最大5件）して Read。
- 既存パターン（test_kind、`package foo` か `package foo_test` か、アサーションライブラリ、DB 利用の有無、外部 API の有無、`httptest` / 手書きフェイクの使い方）を `patterns` に記録。

---

## Phase 3: タスク分解 → JSON 確定書き込み（計画ルートのみ）

### 3-1. 分解（1サイクル=1テスト）
各サイクルが1つのサブテスト（`t.Run` の 1 ケース、または 1 つの `TestXxx`）になるよう分解。`kind` に「テスト種別 + 正常系/異常系/境界」を記す。
- 典型: domain の型・sentinel error → repository のクエリ（実 DB・ロールバック）→ service のロジック（正常 → 業務エラー `errors.Is` → 境界）→ handler（200/201 契約 → 400 デコード/バリデーション → 404/409 異常系 → 401/403 認可）。

### 3-2. TaskCreate
タイトル `TDD: {task_title}`、各サイクルを1項目で作成。返却 ID を `todo_task_id` に記録。

### 3-2b. ユーザー指示（additional_instructions が None のときのみ）
追加指示の有無を確認（**停止**）。入力されれば `user_instructions` に保存、空なら空文字。

### 3-3. ワークフロー JSON の確定書き込み（最重要）
`workflow-schema.md` の正準スキーマで `.claude/tdd-workflow/workflow-{workflow_id}.json` を **Write**（必須キー全部 + `status:"planning_done"` + `run_mode` + `current_cycle:1` + `completed_cycles:[]`）。
**自己検証**: Read し直し、必須キーが揃い `cycle_plan` 長 == `total_cycles` を確認。揃うまで計画完了としない。

### 3-4. 計画完了（停止）
```
📋 計画フェーズ完了 — {workflow_id}（{total_cycles} サイクル, run_mode={run_mode}）
JSON 保存済み。承認したら:  /tdd {workflow_id}   （一気通貫なら --auto）
```
ここで**停止**。Phase 4 には進まない。

> 注: 計画フェーズは JSON を Write するため **Plan モードでは動かない**（編集ブロック）。自動承認モードで実行すること。

---

## Phase 4: TDD サイクルループ（実行ルート）

`state-machine.md` の遷移表・モード・承認ゲートに厳密に従う。

### 4-1. 復元
`workflow-{id}.json` を Read（必須キー検証）。`current_cycle` で次サイクル特定。`run_mode` 取得（引数で上書き指定があれば更新保存）。`todo_task_id` で TaskGet。未完了が無ければ Phase 5 へ。

### 4-2. サイクル実行（state-machine #2〜#8）
引数は `{workflow_id}`：
1. **Red**: `Skill(tdd-red, "{workflow_id}")` → テスト追加・失敗確認・`current-cycle.json` 作成。→ **承認ゲート①**（state-machine 準拠）。
2. **Green**: `Skill(tdd-green, "{workflow_id}")` → 最小実装・pass。（自動）
3. **Evac(plan)**: `Skill(tdd-evacuator, "{workflow_id} --mode=plan")` → 提示のみ。（自動）
4. **Refactor**: `Skill(tdd-refactor, "{workflow_id}")` → 品質改善・pass維持。（自動）
5. **Evac(review)**: `Skill(tdd-evacuator, "{workflow_id} --mode=review")` → 評価提示。→ **承認ゲート②**。
6. **Commit**: `Skill(tdd-commit, "{workflow_id}")` → コミット・`completed_cycles` 追記・`current-cycle.json` 削除。

### 4-3. Commit 検証ゲート（必須）
`git log -1 --format="%H"` が空でない / `completed_cycles` 末尾 `commit` が一致・`current_cycle`+1 / `current-cycle.json` 不在、を確認。失敗なら tdd-commit 再実行を指示し中断。

### 4-4. サイクル境界（停止 or 継続）
TaskUpdate で完了サイクルを `[x]`。`run_mode` に従う：
- `phase-stop`: まず `Skill(tdd-evacuator, "{workflow_id} --mode=boundary")` で**次サイクル以降の追加テスト提案**を取得し、提案リストとともに**停止**して提示：
  ```
  ✅ Commit {sha} / 進捗 {current_cycle-1}/{total_cycles}

  📋 追加テスト提案（次サイクル以降）:
    1. {file}: {サブテストの概要} — {理由}
    2. ...
  [Enter] 次サイクルへ / [+] 上記提案からテストを追加（サイクル挿入） / [a] ここから--auto / [q] 残りスキップして Coverage Review
  ```
  - `[+]`: 採用する提案（番号 or 自由入力）を聞き、`cycle_plan` 末尾に追加・`total_cycles`+1（JSON と TODO 両方更新）。
  - `[a]`: `run_mode="auto"` に更新して保存し、停止せず継続。 / `[q]`: Phase 5 へ。
- `auto`: 停止せず次サイクルの Red へ（サイクル境界の提案はスキップし、スコープは計画どおり維持。停止すべき条件に該当時は強制停止）。

### 4-5. ループ判定
未完了あり→4-2へ。全完了 or `[q]`→Phase 5へ。

---

## Phase 5: Coverage Review
`Skill(tdd-coverage-review, "{workflow_id}")`。レイヤー×カテゴリの網羅性を分析し不足を追加・コミット、`coverage_review` 記録。（自動遷移。早期終了後こそ実行）

## Phase 5b: Optimize
`Skill(tdd-optimize, "{workflow_id}")`（assess→analyze→plan→**承認**→execute→独立性検証）。

## Phase 6: 完了 + アーカイブ
- 完了サマリ表示。`status` を `"done"`、`updated_at` 更新。
- 任意: `status:"done"` の古い JSON を `.claude/tdd-workflow/archive/` へ移動。
- 次ステップ案内（push すれば CI が `go test -race` / `golangci-lint` を実行。PR 作成）。

---

## エラーハンドリング
- **Notion 取得失敗**: 原因を提示し自由テキスト再起動を案内、中断。
- **レイヤー判定不能**: 候補を提示してユーザー選択を待つ（停止）。
- **フェーズスキル失敗**: `[r]再実行 / [s]保存して一時停止 / [q]Coverage Review へ`。状態は保存済みで再開可能。
- **状態 JSON 不整合**: state-machine の停止条件に該当。修正方法を提示して中断。

全フェーズ完了/中断時に `updated_at` を更新し、ファイルから再開可能な状態を保つ。
