# Linear 連携

> PR 本文やブランチ名の `TEC-123` で issue に紐づく。ただしスタックの上の段の PR は、マージしても issue が Done にならないことがある。マージ後に全 issue を確かめる。

## 紐づけ

Linear の GitHub 連携は、次のどれかに issue ID があると PR を issue に紐づける。

- ブランチ名（Linear の「Copy git branch name」の `<user>/tec-123-<slug>`）
- PR タイトル
- PR 本文（`TEC-123`、または `Fixes TEC-123` / `Closes TEC-123` などの magic word 付き）

1 PR に複数 issue を含むときは、ブランチ名に入るのは 1 つだけなので、残りは本文に書く。位置ブロックの `Linear:` 行（`create.md`）に並べる。

紐づくと、PR を開いた時点で issue が In Progress / In Review に、マージで Done に進む（ワークスペースの設定による）。

## base が main でない PR は Done にならないことがある

実際に起きたこと: スタックをマージした後、base が main でない PR（base が下の PR のブランチ）に紐づいた issue が自動で Done にならず、手で Done にした。

考えられる理由（未確認）: Linear のワークフロー自動化は、マージ先のブランチで状態を変えるかを決める設定（チームの Git 連携設定の、ブランチごとのルール）がある。PR が作られた時点や紐づいた時点の base が main 以外だと、「既定ブランチへのマージ」と見なされない可能性がある。

対処:

1. マージの前に、スタックに含まれる全 issue ID を控えておく（`stack-status.sh` の `linear` 列。本文・タイトル・ブランチ名から拾っている。スクリプトは open な PR しか辿らないので、マージ後には出ない）
2. 各 issue の状態を確かめる（Linear の MCP があれば `get_issue`、無ければユーザーに確かめてもらう）
3. Done になっていない issue を一覧にしてユーザーに示す
4. OK をもらってから Done にする（Linear の MCP があれば `save_issue` で状態を変える。無ければ一覧を渡して手で変えてもらう）

予防として、チームの Git 連携設定でスタックの base になるブランチ（`*` や `<user>/*`）へのマージでも Done に進むルールを足せるかを、ワークスペースの管理者に確かめてもらうとよい（設定の可否は未確認）。

## このスキルが Linear に対してしないこと

- issue の作成・本文の変更・担当者の変更
- ユーザーの OK を得ない状態変更

依頼元が Linear の操作を別に受け持っている場合（オーケストレーション側のセッションなど）は、Done にすべき issue の一覧を出力して止まり、操作は依頼元に任せる。
