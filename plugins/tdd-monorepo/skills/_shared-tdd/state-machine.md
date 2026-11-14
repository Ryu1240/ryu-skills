# TDD 状態機械（フェーズ遷移・モード・停止条件）— retail-hub

> オーケストレータ `tdd`（実行ループ）と各フェーズスキルが従う唯一の遷移定義。各スキルは自分のセルを実装するだけ。
> モノレポのため各サイクルは `ecosystem`（backend / frontend）を持ち、フェーズスキルはそれに応じて分岐する。

## フェーズ遷移表

| # | フェーズ | スキル | 事前条件（入口ゲート） | 完了時の事後条件 | 既定モードの挙動 |
|---|---|---|---|---|---|
| 1 | Plan | `tdd`（計画） | — | `workflow-{id}.json` が正準スキーマの必須キー（`ecosystem` 含む）を満たす（`status:planning_done`） | 停止 |
| 2 | Red | `tdd-red` | 前サイクルの `current-cycle.json` 不在（cycle2+）。計画 JSON 存在 | `current-cycle.json` (`phase:red`, `ecosystem`) 作成。テストが期待通り失敗 | 承認ゲート①で停止 |
| 3 | Green | `tdd-green` | `phase=="red"` | `phase:green`、`implementation_files` 非空、対象 spec が pass | 自動遷移 |
| 4 | Evac(plan) | `tdd-evacuator --mode=plan` | `phase=="green"` | 今サイクルのリファクタ候補・テスト妥当性の提示のみ（read-only） | 自動遷移 |
| 5 | Refactor | `tdd-refactor` | `phase=="green"` | `phase:refactor`、`refactor_details` 非空、pass 維持 | 自動遷移 |
| 6 | Evac(review) | `tdd-evacuator --mode=review` | `phase=="refactor"` | 評価提示。新規テスト追加なしを確認 | 自動遷移→承認ゲート②へ |
| 7 | Commit | `tdd-commit` | `phase=="refactor"`、`refactor_details` 非空 | コミット、`completed_cycles` 追記、`current_cycle+1`、`current-cycle.json` 削除＆不在確認 | 承認ゲート②で停止 |
| 8 | ループ判定 | `tdd` + `tdd-evacuator --mode=boundary` | Commit 検証ゲート pass | 次サイクル以降の追加テスト提案を提示。未完了→2へ / 全完了→9へ | 停止（提案を提示し、次サイクルへ進むか `[+]` で追加かを確認） |
| 9 | Coverage Review | `tdd-coverage-review` | 全サイクル完了 or 早期終了 | 不足 spec 追加・コミット、`coverage_review` 記録 | 自動遷移 |
| 10 | Optimize | `tdd-optimize` | Coverage Review 後 | 最適化（承認後）・レポート | 停止（完了サマリ） |

> 追加テスト提案のタイミング: 次サイクル以降のエッジケース提案は #8（サイクル境界）で `tdd-evacuator --mode=boundary` が生成し、停止時に提示する（`[+]` で `cycle_plan` に採用）。`#4 Evac(plan)` は今サイクルのリファクタ/妥当性のみを扱う。`auto` では #8 の提案はスキップし、計画どおり進む。

## 2つの実行モード（`run_mode`）

ユーザー方針: 既定はフェーズ停止。一気通貫は opt-in。切替は都度。

- `phase-stop`（既定）: 停止マーク（承認ゲート①②・Plan完了・ループ判定）ではターンを終えてユーザーの返答を待ち、返答を受けたら同じセッションで次へ進む。自動遷移マーク（Green/Evac/Refactor）は止めず連続実行。各停止点では状態を JSON に保存してからターンを終える。
- `auto`（opt-in: 起動時 `--auto` or 途中チェックポイントで選択）: 停止マークでも止まらず、Claude 自身が承認ゲートの代わりにレビューして連続実行。整合なら継続、下記「停止すべき条件」に該当したら強制停止。
- 切替は `workflow-{id}.json.run_mode` を更新（永続化されるので再開時も維持）。

## セッションと状態ファイル

1つのワークフローは計画から最適化まで同じセッションで進めるのが基本。計画時の分析（ecosystem 判定の根拠を含む）・承認時のやり取り・前サイクルで見えた設計判断は会話の文脈に残り、次のフェーズの判断材料になる。

状態 JSON（`workflow-{id}.json` / `current-cycle.json`）は、中断・別セッションでの再開・compact で文脈が要約されたときに復帰するための記録として書き続ける。各フェーズの入口ゲートが JSON を確認するのは、単独起動や再開時の不整合を止めるため（小さいファイルなので同一セッションでも省かない）。各フェーズの backend/frontend 分岐もこの JSON の `ecosystem` に従うので、再開後も分岐は変わらない。

`tdd-evacuator` だけは `context: fork` + `agent: Explore` で別の文脈のサブエージェントとして動かす（`background: false` で結果を待ってから次へ進む）。共通契約や状態 JSON は毎回自分で Read する（`ecosystem` も JSON から読み直す）。実装を書いた側の思い込みを持ち込まずにレビューさせるのが狙いで、文脈を引き継がないのは意図どおり。

## 承認ゲート（人間レビュー）

2箇所のみ（`run_mode` と直交）：
- ゲート①: Red 完了後 — 追加したテストコードを承認（Green 前）。
- ゲート②: Commit 直前（Evac review 後）— Refactor 結果を承認（Commit 前）。
- `phase-stop` は自然に停止。`auto` は Claude が代行レビュー（逸脱時は強制停止）。

## 停止すべき条件（`auto` でも強制停止）

1. 計画（cycle_plan）と実装/テストが矛盾する。
2. 設計判断が必要（モデル/コンポーネント設計・API 契約変更・multi-tenant/状態管理方針・スコープ変更など）。
3. 想定外のテスト失敗（期待した失敗以外、または Green/Refactor 後に pass しない）。
4. 機密情報の検出（コミット前）。
5. 状態 JSON の整合性検証に失敗。
6. リトライ上限（Green は最大3回）到達。
7. pre-commit hook（husky/lint-staged）でコミットがブロックされた（lint エラー等）→ 修正して再試行、解決不能なら停止して報告。
8. ecosystem 判定不能（backend/frontend どちらか判別できない）→ ユーザーに確認。

## Linter（コミット時に hook が自動実行）

backend=Rubocop / frontend=ESLint。Refactor フェーズで明示実行も可（`cd api && bundle exec rubocop -a` / `cd web && yarn lint --fix`）。
