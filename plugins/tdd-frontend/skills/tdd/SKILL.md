---
name: tdd
description: Vue 3 + Vite + Vitest フロントエンド向けの TDD オーケストレーター。計画 → Red/Green/Refactor/Commit のサイクル → 網羅性レビュー → テスト最適化までを同じセッションで進める。「TDD で実装して」「テストファーストで進めて」と頼まれたとき、または進行中の TDD ワークフローを再開するときに使う。Notion のタスク URL からも計画できる。
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
  - Bash(mkdir .claude/tdd-workflow/:*)
  - Bash(mv .claude/tdd-workflow/:*)
  - Grep
  - Glob
examples:
  - input: /tdd https://www.notion.so/task-id
    description: Notion タスクから計画（JSON を書き出して承認を待ち、承認されたら同じセッションで Red へ進む）
  - input: /tdd "商品一覧に在庫フィルタを追加し composable で状態管理" -- component は Vue Testing Library で検証
    description: Plan phase from free-text with additional instructions
  - input: /tdd
    description: 引数なし。進行中ワークフローがあれば再開を提案、無ければ会話文脈から計画
  - input: /tdd tdd-20260613-101500
    description: 既存ワークフローの実行（current_cycle から継続、既定はフェーズ停止）
  - input: /tdd tdd-20260613-101500 --auto
    description: 一気通貫モードで実行（承認ゲートは Claude が代行レビュー、逸脱時のみ停止）
---

storefront に対して、完全な TDD ワークフロー（Plan → Red→Green→Refactor→Commit → Coverage Review → Optimize）を実行する。

## 共通契約（単一情報源）
起動時に Read する。以降のフェーズスキルは同じセッション内でこの内容を使い回す。
- `.claude/skills/_shared-tdd/project-settings.md` — Vue/Vite/Vitest・パス・テストコマンド・不変条件・CI/hook
- `.claude/skills/_shared-tdd/workflow-schema.md` — 状態 JSON の正準スキーマ（キー名固定）
- `.claude/skills/_shared-tdd/state-machine.md` — フェーズ遷移・2モード・承認ゲート・停止条件
- `.claude/skills/_shared-tdd/commit-convention.md` — コミット規約・署名・hook 準拠

---

## Phase 0: Project Settings 確認（自動）

引数解析・以降のすべてのフェーズに先立って実行する。`.claude/skills/_shared-tdd/project-settings.md` を Read し、次のいずれかなら bootstrap を提案して停止する：

1. 不在:
   ```
   ⚠️ `.claude/skills/_shared-tdd/project-settings.md` が見つかりません。
   このプロジェクト用の TDD 設定を生成しますか？
   [y] /tdd-bootstrap を実行 / [n] 中断
   ```
   - `[y]` → `Skill(tdd-bootstrap)` を起動。完了後に Phase 0 から再実行。
   - `[n]` → 中断（Phase 1 以降へは進まない）。

2. サンプル設定のまま: 内容に `storefront` というリポ名が含まれていれば「サンプル既定値」と判定。
   ```
   ⚠️ project-settings.md がサンプル設定（storefront）のままです。
   このプロジェクト用に書き換えますか？
   [y] /tdd-bootstrap を実行 / [s] このまま続行 / [n] 中断
   ```
   - `[y]` → `Skill(tdd-bootstrap)` 起動。完了後 Phase 0 から再実行。
   - `[s]` → 警告を残したまま引数解析へ進む（既定値ベースで動作。テスト計画が空振りする可能性あり）。
   - `[n]` → 中断。

3. カスタマイズ済み（リポ名が `storefront` を含まない、または bootstrap 生成済み）→ そのまま引数解析へ進む。

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
| `notion.so` を含む URL | — | 計画（Phase 1a→2→3） |
| URL でも workflow_id でもない自由テキスト | — | 計画（Phase 1b→2→3） |
| 空（引数なし） | — | 再開検出 → 無ければ Phase 1c |
| `tdd-YYYYMMDD-HHMMSS` 形式 | None | 実行（Phase 4、`current_cycle` 継続） |
| `tdd-...` 形式 | 非 None | 動的更新: `tdd-workflow-update` を Skill 起動 → 承認後に再読込して Phase 4 継続 |
| `--phase=coverage-review` / `=optimize` | — | 該当フェーズのみ |

### 引数なし時の再開検出
`Glob .claude/tdd-workflow/workflow-*.json` で `status` が `"in_progress"` または `"planning_done"`（計画承認後、最初のコミット前に中断したもの）のものを `updated_at` 降順に探し、あれば最新を提示して再開可否を問う（停止）。無ければ Phase 1c。

---

## Phase 1: タスク仕様の取得（計画ルートのみ）

### 1a. Notion URL
1. ToolSearch でキーワード解決: `query: "notion-fetch"` を実行し、利用可能な `*notion-fetch` ツールを得る（サーバー ID はハードコードしない）。
2. 解決したツールで取得。`page_id` は URL から: `?` 以降除去 → 32桁 hex 抽出 → `8-4-4-4-12` 形式に整形。
3. タイトル / 内容 / 技術的制約 を抽出し `.claude/tdd-workflow/notion-context-{page_id}.json` にキャッシュ。

### 1b. 自由テキスト
引数全体をタスク仕様に。タイトルは冒頭から自動生成（最大60字）。

### 1c. 引数なし
会話文脈・開いているファイルから推定し、提示して確認（停止）。`[m]` なら再入力。

### 1-3. workflow_id 生成
`date +%Y%m%d-%H%M%S` → `workflow_id = tdd-{timestamp}`。

---

## Phase 2: 既存コード分析（計画ルートのみ）

- project-settings の構成に従い、Grep/Glob で既存 spec（`*.spec.ts`）・factory（`src/testUtils/factory/`）・MSW handler（`src/testUtils/mocks/handlers/`）・実装（component/composable/store）を探索（最大5件）して Read。
- 既存パターン（spec_kind、API 連携の要否＝MSW handler の要否、Testing Library / user-event / Pinia の使い方）を `patterns` に記録。

---

## Phase 3: タスク分解 → JSON 確定書き込み（計画ルートのみ）

### 3-1. 分解（1サイクル=1テスト）
各サイクルが1つの `it`（または1ケース）になるよう分解。`kind` に「spec種別 + 正常系/異常系/境界」を記す。
- 例: composable 正常系 → 異常系（API エラー） → component レンダリング（props/表示） → ユーザー操作（イベント発火） → 空/エラー状態の表示。

### 3-2. TaskCreate
タイトル `TDD: {task_title}`、各サイクルを1項目で作成。返却 ID を `todo_task_id` に記録。

### 3-2b. ユーザー指示（additional_instructions が None のときのみ）
追加指示の有無を確認（停止）。入力されれば `user_instructions` に保存、空なら空文字。

### 3-3. ワークフロー JSON の確定書き込み
`workflow-schema.md` の正準スキーマで `.claude/tdd-workflow/workflow-{workflow_id}.json` を Write（必須キー全部 + `status:"planning_done"` + `run_mode` + `current_cycle:1` + `completed_cycles:[]`）。
Write する前に、必須キーが揃い `cycle_plan` の長さが `total_cycles` と一致することを確かめる。欠けていれば計画完了としない。

### 3-4. 計画の承認（停止）
```
📋 計画完了 — {workflow_id}（{total_cycles} サイクル, run_mode={run_mode}）
[y] このまま Red へ / [a] 一気通貫（--auto）で進める / [e] 計画を修正 / [n] ここで終了（後で /tdd {workflow_id} で再開）
```
ここで停止してユーザーの返答を待つ。`[y]` / `[a]` なら同じセッションのまま Phase 4 へ進む（計画時の分析や判断の経緯が文脈に残っているほうが Red の精度が上がるため、別セッションへの切り替えは勧めない）。`[a]` は `run_mode="auto"` を保存してから進む。`[e]` は指示を聞いて `cycle_plan` と `total_cycles` を直し、3-3 の検証（必須キー・`cycle_plan` の長さ == `total_cycles`）をやり直して JSON を Write し直す。TODO の項目も追加・削除・改題して同期してから、再度この承認を出す（後続の tdd-red は JSON と TODO から今サイクルの計画を読むため、文脈だけ直しても反映されない）。

> 注: 計画フェーズは JSON を Write するため Plan モードでは動かない（編集ブロック）。自動承認モードで実行すること。

---

## Phase 4: TDD サイクルループ（実行ルート）

`state-machine.md` の遷移表・モード・承認ゲートに従う。

### 4-1. 復元
同じセッションで計画から続けている場合、計画内容は文脈にあるので読み直さなくてよい。`/tdd {workflow_id}` で再開した場合（別セッション・compact 後）は `workflow-{id}.json` を Read して必須キーを検証する。`current_cycle` で次サイクル特定。`run_mode` 取得（引数で上書き指定があれば更新保存）。`todo_task_id` で TaskGet。未完了が無ければ Phase 5 へ。
再開時に `current-cycle.json` が残っていれば、サイクルの途中で中断している。Red からやり直さず、その `phase` の続きから 4-2 に入る（`red` → 承認ゲート①、`green` → Evac(plan)、`refactor` → Evac(review) → 承認ゲート②）。

### 4-2. サイクル実行（state-machine #2〜#8）
引数は `{workflow_id}`：
1. Red: `Skill(tdd-red, "{workflow_id}")` → テスト追加・失敗確認・`current-cycle.json` 作成。→ 承認ゲート①（state-machine 準拠）。
2. Green: `Skill(tdd-green, "{workflow_id}")` → 最小実装・pass。（自動）
3. Evac(plan): `Skill(tdd-evacuator, "{workflow_id} --mode=plan")` → 提示のみ。（自動）
4. Refactor: `Skill(tdd-refactor, "{workflow_id}")` → 品質改善・pass維持。（自動）
5. Evac(review): `Skill(tdd-evacuator, "{workflow_id} --mode=review")` → 評価提示。→ 承認ゲート②。
6. Commit: `Skill(tdd-commit, "{workflow_id}")` → コミット・`completed_cycles` 追記・`current-cycle.json` 削除。

### 4-3. Commit 検証ゲート（必須）
`git log -1 --format="%H"` が空でない / `completed_cycles` 末尾 `commit` が一致・`current_cycle`+1 / `current-cycle.json` 不在、を確認。失敗なら tdd-commit 再実行を指示し中断。

### 4-4. サイクル境界（停止 or 継続）
TaskUpdate で完了サイクルを `[x]`。`run_mode` に従う：
- `phase-stop`: まず `Skill(tdd-evacuator, "{workflow_id} --mode=boundary")` で次サイクル以降の追加テスト提案を取得し、提案リストとともに停止して提示：
  ```
  ✅ Commit {sha} / 進捗 {current_cycle-1}/{total_cycles}

  📋 追加テスト提案（次サイクル以降）:
    1. {spec_file}: {it の概要} — {理由}
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
`Skill(tdd-coverage-review, "{workflow_id}")`。spec種別×カテゴリの網羅性を分析し不足を追加・コミット、`coverage_review` 記録。（自動遷移。早期終了後こそ実行）

## Phase 5b: Optimize
`Skill(tdd-optimize, "{workflow_id}")`（assess→analyze→plan→承認→execute→独立性検証）。

## Phase 6: 完了 + アーカイブ
- 完了サマリ表示。`status` を `"done"`、`updated_at` 更新。
- 任意: `status:"done"` の古い JSON を `.claude/tdd-workflow/archive/` へ移動。
- 次ステップ案内（push すれば CI がテスト実行。PR 作成）。

---

## エラーハンドリング
- Notion 取得失敗: 原因を提示し自由テキスト再起動を案内、中断。
- フェーズスキル失敗: `[r]再実行 / [s]保存して一時停止 / [q]Coverage Review へ`。状態は保存済みで再開可能。
- 状態 JSON 不整合: state-machine の停止条件に該当。修正方法を提示して中断。

全フェーズ完了/中断時に `updated_at` を更新し、ファイルから再開可能な状態を保つ。
