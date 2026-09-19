---
name: tdd-green
description: Green phase - Minimal Rust implementation in ledger-core (trait injection / typed errors / layer discipline) to make the failing cargo test pass
argument-hint: <workflow_id>
model: opus
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash(cargo:*)
  - Bash(rustup:*)
  - Bash(make:*)
  - Bash(just:*)
  - Grep
  - Glob
examples:
  - input: /tdd-green tdd-20260613-101500
    description: Execute Green phase for the current cycle
---

TDD の Green フェーズ。今サイクルの失敗テストを通す**最小限の実装**を行う。

## 共通契約（必ず Read）
- `.claude/skills/_shared-tdd/project-settings.md`（**不変条件**・レイヤー構成）/ `workflow-schema.md` / `state-machine.md`

> 原則: ✅テストを通す最小実装 ❌先回り実装 ❌リファクタ（次フェーズ）❌新規テスト追加。

## 入口ゲート
`current-cycle.json` を Read。`phase=="red"`、`test_details.error_type` 非空。違反なら `/tdd-red {id}` 案内し中断。

## 1. 失敗の特定
`current-cycle.json` の `error_type` / `error_message` / `test_file_path` から、不足実装を特定（未定義の型 / トレイトメソッド / enum variant / route ハンドラ / service メソッド / repository クエリ / `From` 実装 / `IntoResponse` のマッピング / Router への配線）。`compile_error_undefined` なら**まず定義してコンパイルを通し**、次にアサーションを満たす。

## 2. 実装（レイヤー別・最小）

### 必須パターン
- **レイヤーの依存方向を守る**（routes → services → repositories、domain は末端）。service に `axum::` / `http::` の型を渡さない。repository 以外に `sqlx::query` を書かない。
- **外部 I/O はトレイトで受け取る**: DB・HTTP クライアント・時刻・乱数 を実装内で直接掴まない（ジェネリクスか `Arc<dyn Trait>`）。トレイトにメソッドを足したら**本実装とフェイクの両方**に実装する。
- **エラーは型で表現し `?` で伝搬**: 業務エラーは `domain` の `thiserror` enum に variant を足し、`IntoResponse for LedgerError`（routes 層の 1 箇所）で HTTP ステータスに変換する。**非テストコードで `unwrap()` / `expect()` / `panic!` を書かない**。`Result` を `let _ =` で捨てない。
- **`unsafe` を書かない**。所有権の問題を `clone()` で逃げない（必要なら設計を見直す。解決不能なら停止条件#8）。
- **DB スキーマ変更が要るならマイグレーションを生成**（`sqlx migrate add`）して適用し、`sqlx::query!` を使うなら **`cargo sqlx prepare` でオフラインデータを再生成**（生成物はコミット対象）。

### 最小実装の線引き
テストが要求していない分岐・引数・設定・抽象化は**作らない**。ジェネリクス化・トレイト抽出・キャッシュ・`impl From` の網羅は Refactor フェーズ以降で。`todo!()` を残したまま Green を終えない。

## 3. テスト pass 確認
```bash
cargo test -p {crate} {module_path}::          # 例: cargo test -p ledger-core services::inventory::
cargo test -p {crate} --test {file}            # tests/{file}.rs の場合
```
モジュール内の全件 pass を確認（対象テストだけでなく同モジュールの既存テストも）。最大3回までリトライ。超えたら state-machine 停止条件#6 として報告。

典型的失敗と対処:
- **トレイト未実装**（`the trait bound ... is not satisfied`）→ 本実装とフェイクの両方にメソッドを追加。
- **`Send` / `Sync` 境界**（`Rc` / `RefCell` を async に持ち込んだ、`dyn Trait` に `+ Send + Sync` が無い）→ `Arc` / `Mutex` か型境界を直す。
- **lifetime / 借用エラー** → `clone()` で逃げない。所有権の受け渡し（値で渡す / `&` で借りる / `Arc`）を設計し直す。解決不能なら停止条件#8。
- **`?` のエラー型不一致**（`the trait From<X> is not implemented`）→ `#[from]` / `impl From` を追加、または `map_err` で variant に変換。
- **sqlx のオフラインデータ再生成忘れ**（`SQLX_OFFLINE` で `query!` が失敗）→ `cargo sqlx prepare`。
- **非網羅 `match`**（`non-exhaustive patterns`）→ 追加した variant の腕を書く（`_ =>` で潰さない）。
- **依存クレートが要る**（`cargo add`）→ 停止条件#2（設計判断）として提示し承認を得る。

**テストを都合よく書き換えて通してはいけない**（Red で承認済み）。テスト側の誤りと判断した場合は停止して報告。

## 4. 状態更新
`current-cycle.json` を Edit: `phase:"green"`, `test_details`(passed/total/failed:0), `implementation_files`(非空。マイグレーション・`.sqlx/` の生成物も含める), `retry_count`。
**自己検証**: `phase=="green"` かつ `implementation_files` 非空を Read で確認。

## 5. サマリ（簡潔）
実装した domain/service/repository/route / トレイト・variant の追加 / マイグレーションの有無 / 全 pass（リトライ回数）/ 次は Refactor。→ 自動遷移。

## 注意
- **依存クレートの追加は設計判断**: 新規クレートが必要になったら停止条件#2 として提示し承認を得る。
- `cargo clippy --all-targets -- -D warnings` を一度通しておくと Commit 時の hook で弾かれない（警告を `#[allow]` で黙らせない）。
- ワークスペースでは `-p {crate}` を必ず付ける（全体ビルドはコンパイル時間が跳ねる）。
