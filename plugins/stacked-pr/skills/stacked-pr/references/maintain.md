# スタックを保つ

> 変更は必ず下から上へ順に伝える。main の取り込みも一番下から。上の PR だけを先に進めると、その段と下の段の間が食い違う。

## 実際に詰まった事例

スタックの一番上の PR だけに `origin/main` をマージして push した。

- 一番上のブランチには main の新しいコミットが入ったが、その base（1 つ下の PR の head ブランチ）には入っていない
- GitHub は PR の差分を「base ブランチ」と比べるので、一番上の PR は 1 つ下のブランチとの間で衝突し、`mergeable: CONFLICTING` / `mergeStateStatus: DIRTY` になった
- 衝突している PR にはテスト用のマージコミットが作れないので、`pull_request` イベントの CI が走らなくなった

直し方は、一番下を main に揃え、上へ順に伝え直すこと。一番上に入れた main のマージコミットは、1 つ下まで main が入った後なら差分に残らない（rebase で揃え直すならコミットごと消える）。

## 下の PR を更新したとき

レビュー対応などで下の PR にコミットを足したら、その上を 1 段ずつ揃える。

```bash
git fetch origin
# 2 段目を 1 段目の新しい先端へ
git switch alice/tec-123-refund-endpoint
git rebase origin/alice/tec-121-refund-model
git push --force-with-lease
# 3 段目を 2 段目の新しい先端へ
git switch alice/tec-124-refund-admin-ui
git rebase origin/alice/tec-123-refund-endpoint
git push --force-with-lease
```

- 必ず push 済みの下のブランチ（`origin/...`）に対して rebase する。手元だけ進んだ下のブランチに合わせると、GitHub 上の base と食い違う
- 下の PR を rebase し直した（履歴を書き換えた）ときは、上のブランチに下の古いコミットが残る。`git rebase --onto origin/<下> <下の古い先端> <上>` で古いコミットを落とす。古い先端は `git reflog` か、上のブランチでの `git merge-base` で分かる
- force push はユーザーの OK をもらってから。複数段まとめて OK をもらってよいが、対象のブランチを並べて示す
- 他の人が上のブランチにコミットしているなら、rebase ではなく merge で伝える（相手の手元の履歴を壊さない）

merge で伝える場合:

```bash
git switch alice/tec-123-refund-endpoint && git merge origin/alice/tec-121-refund-model && git push
git switch alice/tec-124-refund-admin-ui && git merge origin/alice/tec-123-refund-endpoint && git push
```

## main を取り込むとき

1. 一番下を main に揃える: `git rebase origin/main`（または `git merge origin/main`）して push
2. 2 段目以降を、上の「下の PR を更新したとき」と同じ手順で順に揃える
3. 途中の段で衝突したら、その段で解消してから次の段へ進む。上の段で同じ衝突がもう一度出ることがある（`git rerere` を有効にしておくと 2 回目以降は自動で解消される）

上の PR だけに main を入れたい理由（上の PR の CI が main の修正を必要とする、など）があっても、上だけに入れない。下から入れる。

## gh stack を使うとき

`gh stack` 拡張が入っていれば、同じことを 1 コマンドで行える。

| やりたいこと | コマンド |
|---|---|
| main から一番上までカスケード rebase | `gh stack rebase` |
| 今いる段より上だけ | `gh stack rebase --upstack` |
| main の取り込みを飛ばしてスタック内だけ | `gh stack rebase --no-trunk` |
| 衝突を解消して続ける / やめる | `gh stack rebase --continue` / `--abort` |
| 全段を push（`--force-with-lease`） | `gh stack push` |
| fetch → trunk 早送り → rebase → push → PR 同期 | `gh stack sync`（マージ済みのブランチを消すなら `--prune`） |
| GitHub が base を付け替えた後に揃える | `gh stack rebase --accept-base-change` |

## 揃えた後の確認

```bash
bash "$SKILL/scripts/stack-status.sh" <どれかの PR>
```

- 全段が `MERGEABLE` か（`UNKNOWN` は GitHub が計算中。少し待ってもう一度）
- 全段で CI が走り始めたか（push 直後にチェックが 1 件も無い段は、衝突か base の誤りを疑う）
- 各段の `gh pr diff <n> --name-only` が、その段の受け持ちのファイルだけになっているか（下の変更が混ざっていれば base か rebase が誤っている）
