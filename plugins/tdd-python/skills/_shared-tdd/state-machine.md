# TDD 状態機械（フェーズ遷移・モード・停止条件）

> オーケストレータ `tdd`（実行ループ）と各フェーズスキルが従う唯一の遷移定義。
> 「次に何をするか」「いつ止まるか」はこの表で決まる。各スキルは自分のセルを実装するだけ。

## フェーズ遷移表

| # | フェーズ | スキル | 事前条件（入口ゲート） | 完了時の事後条件 | 既定モードの挙動 |
|---|---|---|---|---|---|
| 1 | Plan | `tdd`（計画） | — | `workflow-{id}.json` が正準スキーマの必須キーを満たし Read で自己検証済み（`status:planning_done`） | **停止**（`/tdd {id}` 案内、または再開検出に委ねる） |
| 2 | Red | `tdd-red` | 前サイクルの `current-cycle.json` 不在（cycle2+）。計画 JSON 存在 | `current-cycle.json` (`phase:red`) 作成。テストが期待通り失敗 | **承認ゲート①で停止** |
| 3 | Green | `tdd-green` | `current-cycle.json.phase=="red"` | `phase:green`、`implementation_files` 非空、全テスト pass | 自動遷移（停止しない） |
| 4 | Evac(plan) | `tdd-evacuator --mode=plan` | `phase=="green"` | 今サイクルのリファクタ候補・テスト妥当性の提示のみ（read-only） | 自動遷移 |
| 5 | Refactor | `tdd-refactor` | `phase=="green"` | `phase:refactor`、`refactor_details` 非空、全テスト pass | 自動遷移 |
| 6 | Evac(review) | `tdd-evacuator --mode=review` | `phase=="refactor"` | 評価提示。新規テスト追加なしを確認 | 自動遷移（提示）→ 承認ゲート②へ |
| 7 | Commit | `tdd-commit` | `phase=="refactor"`、`refactor_details` 非空 | コミット作成、`completed_cycles` 追記、`current_cycle+1`、`current-cycle.json` 削除＆不在確認 | **承認ゲート②で停止**（commit 前に承認） |
| 8 | ループ判定 | `tdd` + `tdd-evacuator --mode=boundary` | Commit 検証ゲート pass | 次サイクル以降の**追加テスト提案を提示**。未完了サイクルあり→2へ / 全完了→9へ | **停止**（提案を提示し、次サイクルへ進むか `[+]` で追加かを確認） |
| 9 | Coverage Review | `tdd-coverage-review` | 全サイクル完了 or 早期終了 | 不足テスト追加・コミット、`coverage_review` 記録 | 自動遷移 |
| 10 | Optimize | `tdd-optimize-*` | Coverage Review 後 | 最適化（承認後）・レポート | **停止**（完了サマリ） |

> **追加テスト提案のタイミング**: 次サイクル以降のエッジケース提案は **#8（サイクル境界）** で `tdd-evacuator --mode=boundary` が生成し、停止時に提示する（`[+]` で `cycle_plan` に採用）。`#4 Evac(plan)` は今サイクルのリファクタ/妥当性のみを扱う。`auto` では #8 の提案はスキップし、計画どおり進む。

## 2つの実行モード（`run_mode`）

ユーザー方針: **既定はフェーズ停止。一気通貫は opt-in。切替は都度。**

### `phase-stop`（既定）
- 上表「既定モードの挙動」に従い、**停止マーク（承認ゲート①②・Plan完了・ループ判定）で必ずターンを終える**。
- 自動遷移マークのフェーズ（Green/Evac/Refactor）は止めずに連続実行してよい（承認ゲートはメモリ準拠で Red と Commit の2箇所のみ）。
- 各停止点では必ず状態を JSON に確定保存してから終える（再開はファイルからの復元に依存）。

### `auto`（opt-in: 起動時 `--auto`、または途中チェックポイントで選択）
- 停止マークでも止まらず、Opus が**代行レビュー**して連続実行する。
- 代行レビューの判定: 「計画（cycle_plan）・契約（不変条件）・モデル定義と整合 → 継続」。
- **強制停止条件（auto でも必ず止まる）**: 後述の「停止すべき条件」に1つでも該当したとき。
- 途中で `phase-stop` に戻す指定も受け付ける（`run_mode` を書き換え）。

### モード切替
- 起動引数 `--auto` / `--phase-stop`、または各停止点での選択（「ここから一気通貫」）で `workflow-{id}.json.run_mode` を更新。
- `run_mode` は永続化されるので、再開時も維持される。

## 承認ゲート（人間レビュー）

メモリ準拠で**2箇所のみ**。これは `run_mode` と直交する概念：

- **ゲート①: Red 完了後** — 追加したテストコードをユーザーに見せて承認（Green に進む前）。
- **ゲート②: Commit 直前**（Evac review 後）— Refactor 結果をユーザーに見せて承認（Commit する前）。
- `phase-stop` ではこのゲートで自然に停止。`auto` では Opus が代行レビューし整合なら通す（逸脱時は強制停止）。

## 停止すべき条件（`auto` でも強制停止／代行レビューで止める）

1. 計画（cycle_plan）と実装/テストが矛盾する。
2. 設計判断が必要（モデル設計の選択、命名規則の新設、スコープ変更など）。
3. 想定外のテスト失敗（期待した失敗パターン以外、または Green/Refactor 後にテストが通らない）。
4. 機密情報の検出（コミット前）。
5. 状態 JSON の整合性検証に失敗（必須キー欠落・スキーマ不一致）。
6. リトライ上限（Green は最大3回）到達。

いずれも、停止して状態を保存し、ユーザーに状況と選択肢を報告する。
