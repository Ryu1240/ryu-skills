# 実測による裏取り（Phase 3.5 の任意手順）

> 差分に含まれるテストは「作者が固定したい振る舞い」だが、実際に通るかどうかは別の事実である。
> 依存が軽く数分で終わる見込みなら、scratchpad に複製して実行し、結果を「実測」としてプランに書く。
> 判定（良し悪し）はしない。「N 例中 M 例が落ちる、原因は X」という事実だけを書く。

## 原則

1. **作業ツリーには触れない。** ユーザーの依存ディレクトリ（`node_modules`、`.venv`、`vendor`、`target`）やビルド成果物を汚さない。`git archive` で head を scratchpad に展開する
2. **head 基準で実行する。** ローカルブランチが遅れていることがある。展開元は `refs/pr-tour/<id>/head`
3. **結果は出力そのままを根拠にする。** 落ちたテスト名と assertion のメッセージを転記する。推測で書かない
4. **時間の上限を決める。** 依存インストールを含めて 5 分を超えそうなら省略し、「未実行（理由）」と書く。DB・外部サービス・コンテナが要るテストも、用意が軽くなければ省略する

## 手順

```bash
S=<scratchpad>/verify
mkdir -p "$S" && git archive refs/pr-tour/<id>/head | tar -x -C "$S"
cd "$S"
# 依存を入れ、差分に関係するテストだけを回す（下の表でコマンドを決める）
```

モノレポやワークスペースでは、ワークスペース全体を展開する。パッケージ単体だけを展開すると、ルートの設定（ワークスペース定義、共有のバージョン指定）が見つからず依存解決に失敗する。

### テストコマンドの見つけ方

まずリポジトリの文書（`CLAUDE.md`、`README`、`CONTRIBUTING.md`）と CI の定義を見る。CI が回しているコマンドが、そのリポジトリにとっての正解。無ければマニフェストから推定する。

| 手掛かり | 依存の導入 | 単体テストの例 |
|---|---|---|
| `package.json`（ロックファイルで npm / pnpm / yarn / bun を判別） | `npm ci` / `pnpm install --frozen-lockfile` / `yarn install --frozen-lockfile` | `scripts.test`。ワークスペースなら対象パッケージに絞る |
| `pyproject.toml` / `requirements*.txt` | `uv sync` / `poetry install` / `pip install -r ...`（仮想環境は scratchpad 内に作る） | `pytest <対象パス>` |
| `Gemfile` | `bundle install`（`BUNDLE_PATH` を scratchpad 内に） | `bundle exec rspec <対象 spec>` |
| `go.mod` | 不要（モジュールキャッシュを使う） | `go test ./<対象パッケージ>/...` |
| `Cargo.toml` | 不要 | `cargo test -p <crate>` |
| `Makefile` / `justfile` | ターゲットを読む | `make test` 相当 |

CI が lint・型検査・依存ルール検査も回しているなら、差分がどの検査に掛かるかも「実測」の一部として書ける。

## よくある落とし穴

| 症状 | 原因と回避 |
|---|---|
| バックグラウンド実行で `command not found`（node / python / ruby 等） | 非対話シェルはバージョンマネージャ（mise / asdf / nvm / rbenv / pyenv 等）の PATH を持たない。対話シェルで `which <cmd>` を確かめ、そのディレクトリを `PATH` の先頭に足して実行する |
| 依存解決が lockfile と食い違って失敗 | frozen / locked 系のフラグを付けて、lockfile のとおりに入れる。失敗したらそれ自体を実測として書く |
| インストールが対話の確認で止まる | `CI=1` を付ける |
| Python heredoc が `Non-UTF-8 code starting with ...` | 1 行目に `# -*- coding: utf-8 -*-` を置く |
| テストが DB・外部サービス・資格情報を要求する | 用意が軽くなければ実行しない。「未実行（DB が必要）」と書き、通る前提で語らない |
| ローカルの HTML をブラウザで描画確認できない | `scripts/fig.py --check <html>` で SVG の整形式だけ確認し、見た目は Artifact 公開後に見る |

## 外部サービスの挙動を確かめたいとき

ローカルで再現できる実物が無いものは、確かめられる範囲を限る。

1. テスト用のフェイク・モックを使った単体・結合テスト
2. IaC の合成・plan の出力（権限の Action / Resource、環境変数、トリガーの結線）
3. サービス提供元の公開スキーマ・API リファレンス

それ以上（本番相当の環境での挙動）は「未確認」としてプランに残す。

## 記録の書き方

プランの先頭の「実測メモ」に 1 行、テスト対応表の備考欄に「実測 全成功」「実測 失敗（理由）」「未実行（理由）」を書く。

```
- 実測メモ: scratchpad 複製で `pytest tests/orders` を実行。12/12 成功。lint は未実行（CI でのみ設定）
```
