# TDD スキル共通設定（Project Settings）

> 全 TDD スキル（tdd / tdd-red / tdd-green / tdd-refactor / tdd-commit / tdd-evacuator /
> tdd-coverage-review / tdd-optimize / tdd-coverage-overlap / tdd-workflow-update）の単一情報源。
> 各スキルはこのファイルを `Read .claude/skills/_shared-tdd/project-settings.md` で参照する。

## 対象と環境

| 項目 | 値 |
|---|---|
| 対象パッケージ | `taskcli`（リポジトリは単一パッケージ） |
| ソースルート | `taskcli/taskcli/` |
| テストルート | `taskcli/tests/` |
| Fixture ディレクトリ | `taskcli/tests/fixtures/`（サブディレクトリあり: `fixtures/commands/` 等） |
| Python | 3.10 |
| 依存管理 | Poetry（`taskcli/pyproject.toml`） |
| テストランナー | pytest ^8.2 |
| テスト実行（全件） | `cd taskcli && docker compose run --rm app pytest -v` |
| テスト実行（ファイル） | `cd taskcli && docker compose run --rm app pytest -v {rel_path}` |
| テスト実行（関数/絞り込み） | `... pytest -v {rel_path} -k {keyword}` または `{rel_path}::{test_name}` |
| 未導入ツール | ruff / mypy / black / pytest-cov / mutmut / cosmic-ray / pytest-random-order（いずれも未導入。依存する工程は conditional スキップ） |
| Migration / OpenAPI codegen | 無し（DB レイヤー無し） |
| CI | CircleCI はデプロイのみ。push しても taskcli のテストは自動実行されない。**PR 前に手動で全件 pytest 必須**。 |

> ⚠️ テストは必ず docker compose 経由で実行する。ホスト直の `uv run pytest` / `poetry run pytest` は使わない。

## 現行ソース構成（重要・実態）

`schemas` は**モデル群ごとに分割したパッケージ**。

```
taskcli/taskcli/
  schemas/
    __init__.py     # 公開 re-export と __all__（モデルはここから import 可能）
    _common.py      # StrictModel(extra="forbid")、命名規則正規表現（TASK_ID_PATTERN /
                    #   TAG_PATTERN ...）、共通バリデータ、TaskStatus 等の共通型
    task.py / config.py / output.py   # モデル群ごとの pydantic モデル
  commands/         # サブコマンド実装（add / list / done / remove / edit）
  storage.py        # JSON ファイル永続化（load_tasks / save_tasks）
  cli.py            # 引数パーサ + ディスパッチ
  __main__.py
```

**StrictModel / 命名規則定数 / 共通バリデータ / TaskStatus は `schemas/_common.py`**。
新規モデルはモデル群ファイル（`schemas/task.py` 等）に追加し、`schemas/__init__.py` の import と `__all__` に公開する。

## 現行テスト構成（重要・実態）

テストは対象モジュール/モデル群ごとに分割。

| target_module | 主なテストファイル |
|---|---|
| `schemas`（モデル群別） | `tests/test_task_schemas.py` / `test_config_schemas.py` / `test_output_schemas.py` |
| `commands` | `tests/test_commands_*.py`（add / list / done / remove / edit ...） |
| `storage` | `tests/test_storage.py` |
| `cli` | `tests/test_cli.py` |

**テストファイル選択ルール**: `target_module` と対象のモデル群/機能から上表で対応ファイルを引く。
schema 系で対象モデル群が決まっている場合は `test_{group}_schemas.py` に追記が原則。該当ファイルが無い新機能のみ新規作成。

## Fixture ヘルパ（重要・実態）

- ヘルパ関数は `tests/_helpers.py` の **`load_json`**。
  ```python
  from ._helpers import load_json
  raw = load_json("task.json")            # fixtures/ 直下
  row = load_json("commands/add_input.json")  # サブディレクトリも可
  ```
- 複数テストで使い回す正常系は `tests/conftest.py` に **function-scoped 共有 fixture** として定義済みのものを優先利用（例: `task_canonical`）。各テストは `.copy()` で独立 dict を得て改変する。
- fixture 命名はモデル/対象の snake_case（`Task` → `task.json`）。

## 不変条件（全スキル共通・破ってはいけない線）

1. **1サイクル = 1テスト = 1コミット**。1サイクルに複数テストをまとめない。複数サイクルを1コミットにまとめない。
2. **TDD メタ情報をコード/docstring に残さない**（Red/Green/PR番号/サイクル番号/計画書§参照などを書かない）。
3. **テストは docker compose 経由**で実行する。
4. **新規 pydantic モデルは `StrictModel`（`schemas/_common.py`）を継承**（`extra="forbid"` 自動適用）。直接 `BaseModel` 継承禁止。
5. **Green は最小実装のみ**（YAGNI）。後続サイクルが駆動する validator を先回り実装しない。共通化・抽出は Refactor で。
6. **承認ゲートは Red 完了後と Commit 直前の2箇所**。Green / Refactor の間は自動遷移してよい。
7. **ターン粒度**: 既定は各フェーズで停止して制御をユーザーに返す。一気通貫は `--auto` の明示 opt-in でのみ。→ `state-machine.md` 参照。

## 命名・ブランチ

- ブランチ: `feature/<TICKET-KEY>/<package>/<feature>`（例: `feature/<TICKET-KEY>/taskcli/task-schemas`）。違反は warning のみ、ブロックしない。
- コミット規約・署名は `commit-convention.md` 参照。
- Notion 統合はオプション。詳細は `tdd/SKILL.md` の Phase 1a 参照。
