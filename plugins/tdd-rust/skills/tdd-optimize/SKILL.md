---
name: tdd-optimize
description: TDD 完了後の Rust テストを、独立性を保ったまま最適化する（rstest によるパラメータ化・ビルダー抽出・#[sqlx::test] の fixtures 活用など）。編集は承認後のみ。/tdd から呼ばれるほか、テストファイルを指定して単独でも使える。
argument-hint: <workflow_id_or_test_file_path> [test_file_path]
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cargo:*)
  - Bash(make:*)
  - Bash(just:*)
  - Grep
  - Glob
examples:
  - input: /tdd-optimize tdd-20260613-101500
    description: Optimize all tests for the workflow
  - input: /tdd-optimize src/services/inventory.rs
    description: Standalone mode - optimize the #[cfg(test)] module of a single file
  - input: /tdd-optimize tests/orders_api.rs
    description: Standalone mode - optimize a single integration test file
---

TDD 完了後の ledger-core 向けテスト最適化。テストの独立性を保ったまま、重複セットアップ・冗長アサーション・類似ケースを集約し、実行速度と可読性を上げる。

> このスキルは承認後にファイルを編集する（`agent: Explore` を付けない — Explore は Write/Edit を持たず、承認後の適用が空振りする）。

## 共通契約
このセッションでまだ読んでいない（または compact 後で内容が手元にない）ときだけ Read する。`/tdd` から続けて呼ばれた場合は読み込み済み。
- `.claude/skills/_shared-tdd/project-settings.md`（テストコマンド・不変条件）/ `state-machine.md`

## モード判定
- `$0` が `tdd-` → ワークフローモード（`completed_cycles` から `test_files` 収集。`$1` でファイル限定）。
- `$0` が `.rs` で終わる（`tests/foo.rs`、または `#[cfg(test)]` を含む `src/**/*.rs`）→ スタンドアロン（`test_files=[$0]`、`workflow_id="standalone-{date}"`）。
- ワークフローモードの入口ゲート: `current-cycle.json` が不在（サイクル進行中でない）かつ `coverage_review` が記録済みであること。違反なら中断。

## SP1: Assessment（必要性判断）
各テストファイルを Read し計測（Grep）:
- `#[test]` / `#[tokio::test]` / `#[sqlx::test]` 数、`oneshot(` 呼び出し数、テスト本体で繰り返される struct リテラル構築・`Router` 組み立て・`MockServer::start()` + `Mock::given` 定義、個別フィールドの `assert_eq!` の連続、同じフェイク構造体の重複定義（複数モジュールに `struct FakeRepo`）。

推奨基準: ケース数が多い（≥15）かつ最適化機会が2つ以上、または明らかな重複セットアップ。小規模はスキップ（サマリして終了）。

## SP2: Analysis（集約候補）
- セットアップの巻き上げ: 各ケースで重複する準備（`Router` 構築・フェイク生成・`MockServer` の標準スタブ）を `fn test_app(...)` / ビルダー関数（`#[cfg(test)] pub mod testutil` または `tests/common/mod.rs`）へ。ケース間で共有される可変状態を作らない（`static` の `OnceLock` / `LazyLock` / `lazy_static` に可変値を置かない。ヘルパは呼び出しごとに新規生成）。
- パラメータ化: 入力と期待値だけが違う類似ケース（検証の各違反パターン等）を `rstest` の `#[rstest] #[case(...)]`（導入時）に。未導入ならタプル配列ループ + ケース名付きアサーションに集約（ただし失敗時にどのケースか分かるメッセージを必須にする）。
- `#[sqlx::test]` の fixtures 活用: 同じ初期データを各テストで INSERT しているなら `#[sqlx::test(fixtures("orders"))]` に。
- アサーションの集約: 3つ以上の個別フィールド検証を、`#[derive(PartialEq, Debug)]` した構造体の `assert_eq!` 一括比較へ（`pretty_assertions` 導入時は差分が読みやすい）。失敗時の可読性が落ちすぎない範囲で。
- 重複 HTTP 呼び出しの統合: 同一リクエスト・同一セットアップに対する複数ケースを1ケースで複数観点検証に統合（正常系と異常系をまたぐ統合は不可）。
- フェイクの共通化: 複数モジュールに重複する `struct FakeRepo` を `testutil` に 1 つにまとめる（挙動を設定できる形に）。

各候補の独立性を確認（`#[sqlx::test]` 維持、`MockServer` はテストごと、環境変数を触らない、`static` 可変状態なし）。順序依存が生まれるものは集約不可。

## SP3: Planning（承認・必須）
最適化ステップ（対象・変更・削減見込み）とリスク（失敗時の原因特定が難しくなる、パラメータ化の可読性低下、コンパイル時間への影響）を提示。
ユーザー承認まで SP4 を開始しない・ファイル変更しない: `[Enter/y] 全実行 / [e] 番号指定 / [n] キャンセル`。

## SP4: Execution（適用＋独立性検証）
1. ベースライン: `cargo test -p {crate}`（対象クレート全件。名前フィルタはコンパイル量を減らさない。全 pass 必須。失敗なら中断）。実行時間・ケース数を記録。
2. 各ステップを Edit で適用。
3. 再実行（全 pass）＋ 独立性検証:
   - 単一ケース実行: `cargo test -p {crate} --lib {test_name} -- --exact`（`tests/` 配下は `--test {file} {case} -- --exact`。`test_name` は `completed_cycles` から取る）で代表ケースが単独で pass すること。
   - 直列と並列の双方: `-- --test-threads=1` と既定並列の両方で pass すること（片方だけ落ちる＝共有状態がある）。
   - プロセス分離: `cargo nextest run -p {crate}`（導入時）。
   - 反復: 同じ `cargo test -p {crate}` を 3 回連続で実行して flaky を検出（シェルの `for` ループは allowed-tools 外なので 1 回ずつ呼ぶ。ランダム順序は stable では未対応のため、これで代替）。
   - 共有状態の Grep: `static mut` / `OnceLock` / `LazyLock` / `once_cell::sync::Lazy` / `lazy_static!` / `static … Mutex` / `std::env::set_var` がテストコードに無いことを確認（あれば集約対象から外す）。
   - 失敗＝独立性破壊 → そのステップを Edit でロールバックし次のステップへ。
4. `cargo clippy --all-targets -- -D warnings` / `cargo fmt --all` を通す（hook 対策）。

## SP5: Verification（メトリクス・レポート）
Before/After（ケース数・`oneshot` 呼び出し数・実行時間）を比較。
`.claude/tdd-workflow/optimization-report-{workflow_id}-{date}.md` に Write（メトリクス表・実行ステップ・独立性検証結果）。最終サマリを簡潔表示。

## 原則
- 独立性を最優先する（単一ケース実行・直列/並列双方・nextest・反復で pass。共有可変状態を作らない。破壊したらロールバック）。
- 統合は順序に依存しないものに限る（正常系/異常系混在は統合しない）。
- 承認必須（SP3 で承認を得てから SP4）。
