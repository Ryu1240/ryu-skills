---
name: tdd-project-settings-update
description: tdd-node スキル群の共通設定 .claude/skills/_shared-tdd/project-settings.md を自然言語指示で調整・追記・修正するスキル。「tdd（の設定）に〜を覚えさせて」「project-settings に追記して」「TDD スキルの共通設定を更新・調整して」「テスト実行コマンド／レイヤー構成／不変条件の記載を直して」など、TDD スキル群の挙動を規定する共通設定の変更依頼が来たら、直接ファイルを編集せずこのスキルを使う（diff 提案と承認を挟むため）。初回生成は tdd-bootstrap、恒常的な微調整はこのスキルが担う。
argument-hint: <update-instructions>
allowed-tools:
  - Read
  - Edit
  - Write
  - Grep
  - Glob
  - AskUserQuestion
  - Bash(git diff:*)
  - Bash(git status:*)
examples:
  - input: /tdd-project-settings-update テストは pnpm test:unit で実行するよう修正
    description: 既存記載の修正
  - input: /tdd-project-settings-update レイヤーに usecases を追加した旨を反映
    description: レイヤー構成の変更を反映
  - input: /tdd-project-settings-update 不変条件に「repository のテストは testcontainers を使う」を追加
    description: 不変条件の変更（警告付き追加確認あり）
---

tdd-node の全 TDD スキル（tdd / tdd-red / tdd-green / tdd-refactor / tdd-commit / tdd-coverage-review / tdd-optimize / tdd-evacuator / tdd-workflow-update）が参照する単一情報源 `.claude/skills/_shared-tdd/project-settings.md` を、自然言語の指示から安全に更新する。

初回のプロジェクト検出・生成は `tdd-bootstrap` が担い、このスキルは生成済み設定の恒常的な微調整・追記・修正を担う（`tdd-bootstrap --force` の再生成と違い、手編集を潰さず差分だけを当てる）。

このファイルへの誤った編集は全 TDD フェーズの挙動に一斉に波及する。だから「diff 提案 → 承認 → 適用 → 検証 → メモリ同期」の順を守る。

## 前提チェック

1. 指示（`$ARGUMENTS`）が非空。空なら「何を変更しますか？」と確認して中断。
2. カレントリポジトリに `.claude/skills/_shared-tdd/project-settings.md` が存在する。無ければ「まだ bootstrap されていません。`/tdd-bootstrap` で生成してください」と案内して中断。

## Step 1: 現状読込

`.claude/skills/_shared-tdd/project-settings.md` を全文 Read し、セクション構成（構成とテスト / レイヤー構成 / テスト実行コマンド / CI・hook / 不変条件 / ブランチ・コミット）を把握する。指示内容と矛盾・重複する既存記載がないかをこの時点で洗い出す。

## Step 2: diff 提案

指示を解釈し、編集操作を組み立てて適用前に提示する:

- 追記: 既存セクションに収まるなら既存セクションへ。新概念のみ新セクション。このファイルは全 TDD スキルのコンテキストに毎回ロードされるため、肥大化はコスト。冗長な説明より簡潔な事実+理由の一行を優先する。
- 修正: 対象箇所の before/after を明示。
- 削除: 削除理由と、削除によって挙動が変わる TDD スキル・フェーズを一言添える。
- 書式: 既存の書式に合わせる。
- 矛盾検出: 既存記載と衝突する場合は上書きか併記かを提案に含める。

### 特別扱いが必要なセクション

- テスト実行コマンド: ここが誤ると全フェーズが空振りする。変更時は `package.json` の `scripts` を Read して実在を裏取りしてから提案する。裏取りできなければ「未検証」と明示して承認を求める。
- レイヤー構成: Red のテスト配置判定・Refactor のレイヤー衛生チェックに直結する。変更時は実際の `src/` のディレクトリを Glob で確認してから提案する。
- ⚠️ 不変条件: 「不変条件」への追加・変更・削除は品質ガードレール（テスト独立性、DI による差し替え、境界の検証、レイヤーの依存方向）の変更を意味する。diff 提案時に⚠️付きで明示し、影響（どのスキルのどの判断が変わるか）を説明したうえで、通常の承認とは別に変更意図を再確認する。

## Step 3: 承認ゲート（必須）

AskUserQuestion で `[適用] / [キャンセル] / [部分適用]` を確認。[適用] のときのみ Step 4 へ。[部分適用] は変更単位ごとに採否を再質問。[キャンセル] は何も書かずに終了。

## Step 4: 適用と検証

1. Edit で承認済みの変更のみ適用。承認していない箇所には触れない。
2. `git diff -- .claude/skills/_shared-tdd/project-settings.md` で実際の差分を提示し、提案どおりか確認する。
3. コミットはしない。変更は working tree に残し、コミット判断はユーザーに委ねる（明示的に指示された場合のみコミット）。

## Step 5: 永続メモリとの同期提案（任意・メモリ機能が有効な場合のみ）

このスキルはリポジトリ配置でチーム共有される。実行者が永続メモリ機能を使っている場合に限り、project-settings.md の運用知識と重複・矛盾するメモリがないか確認する。メモリディレクトリが存在しない実行環境ではこの Step をスキップし、Step 6 へ進む（他メンバーの環境ではメモリが無いのが普通）。

システムプロンプトにメモリディレクトリ（MEMORY.md がインデックス）が示されている場合:
- 今回の変更と矛盾または重複する既存メモリを Grep で探す（例: vitest / prisma / コマンド名 / レイヤー名で検索）。
- 矛盾するメモリが見つかったら、同期更新案（メモリ本文と MEMORY.md のインデックス行）を提示し、承認後に更新する。
- 見つからなければ「メモリ同期不要」と報告するだけでよい。新規メモリの作成はユーザーが求めた場合のみ。

## Step 6: 完了サマリ

変更したセクション / 保護した箇所（触れなかった不変条件等）/ コマンドの裏取り結果 / メモリ同期の有無 / 「コミットは未実施（working tree に差分あり）」を簡潔に報告する。
