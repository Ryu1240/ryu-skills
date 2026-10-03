# ツアー図（アーティファクト）

アーティファクトは **1ツアーにつき1枚**。Phase 1 で公開し、ステップごとに同じファイルパスへ再publishして同じURLを更新する。ステップごとに新しいアーティファクトを作らない — 読み手が「全体のどこにいるか」を見失い、リンクだけが増える。

**作り直すときも同じファイルパスに上書きする。** アーティファクトを削除する手段は無い（Artifact ツールに delete 相当の操作が無い）ので、試すたびに別名で publish すると消せないものがギャラリーに溜まる。ユーザーが消したい場合は `/artifacts` かギャラリーから操作してもらう。

このページの中身は **図**であって、装飾したリストではない。箱と点を縦に並べただけのものは行程表であり、処理の流れを説明していない。読み手が知りたいのは「誰が誰を、どの順で呼ぶか」「どこで条件が分かれるか」で、それを表すのに適した図式がすでに存在する。使う。

## 図の選び方

| 表したいもの | 図式 |
|---|---|
| 実行の順序、登場人物のやり取り、往復 | `sequenceDiagram` |
| 条件による経路の分かれ、ガード | `flowchart` |
| 状態の遷移（ステータス、ライフサイクル） | `stateDiagram-v2` |
| テーブル・データ構造の関係 | `erDiagram` |
| 層と依存の向き | `flowchart` ＋ `subgraph` で層を切る |

**ツアー全体には1枚。** リクエストを1本追う歩き方なら `sequenceDiagram`（呼び出しの順序と、誰が状態を持つかが一目で出る）。公開面から内へ降りる歩き方では呼び出しの列が無いので、**層と断線を描く `flowchart`** にし、エラーが下から上へ翻訳されて戻る矢印を必ず入れる。

**各ステップには、そのステップ固有の図を2枚並べる。** どちらか一方に置き換えない — 呼び出しの順番と、戻り値で道が分かれる様子は、1枚に押し込むとどちらも読めなくなる。

- **(a) 呼び出し順の `sequenceDiagram`** — `autonumber` を付け、本文のトレースの ①②… と番号を揃える。メッセージのラベルに `:行番号`（呼ぶ側の行 → 呼ばれる側の定義行）を入れる
- **(b) 戻り値・条件による分岐の `flowchart`** — (a) の中の分岐（`alt` の枠）を開いたもの。ノードに file:line を入れる

図が何も足さないステップ（差分なしで通過するだけ等）では、2枚とも省いて全体図だけで済ませて構わない — 無内容な図を置くほうが害になる。

## mermaid で描く

アーティファクトは mermaid をネイティブに描画する。**ライブラリは読み込まない。**

```html
<pre class="mermaid">
sequenceDiagram
    autonumber
    actor U as ユーザー
    participant C as OrderSummaryCard
    ...
</pre>
```

- **描画面は固定の明るい面に置く**（`background:#fbfbfa` + `border` + `border-radius`）。mermaid の既定テーマは暗い地の上だと線も文字も読めなくなるため、ページがダークテーマでも図だけは明るい紙の上に置く
- コンテナに `overflow-x:auto`。シーケンス図は参加者が増えると横に伸びる
- ラベルに `(` `)` `/` `:` `<` を含めるときは `["..."]` で引用する。引用しないとパースが壊れて図が丸ごと消える
- **ラベルに HTML の文字参照（`&quot;` `&gt;` `&lt;` `&amp;`）を書かない。** `<pre class="mermaid">` の中身はブラウザが先に `"` `>` へ戻してから mermaid に渡すので、`["..."]` の途中に `"` が現れてラベルの終わりと読み違え、図が丸ごと描画されない（実測）。記号は言葉にする — 「空文字」「40 超」「以上」
- **`<br/>` で改行しない。** `<pre>` の中で要素として解釈されて危うい。改行が要るときは ` / ` などの区切りで代用する
- 矢印の種類を使い分ける: `->>` 同期呼び出し / `-->>` 戻り値 / `-x` 中断・握り潰し

## 現在地と差分の示し方

| 示すもの | 方法 |
|---|---|
| 現在のステップ | サイドバーの駅ボタンの `aria-current="true"` と、その駅のパネル（固有の図2枚）の表示 |
| 全体図の中の現在位置 | `sequenceDiagram` の該当メッセージ範囲を `rect rgba(13,122,111,.12)` … `end` で囲む |
| このPRで新規・変更 | `flowchart` は `classDef` で塗り分け、`sequenceDiagram` は `Note` で明示 |
| レビューの指摘がある駅 | サイドバーの駅名末尾に `⚠`。未訪問のうちから「この先に指摘がある」と分かる。凡例に意味を1行添える |
| 未実装（線が途切れている） | ノードを破線にするか、`Note` で「このPRには無い」と書く。**無い経路を実線で描かない** |
| 先回り参照（終点で足した値を起点が使う） | 戻り矢印のラベルか `Note` に書く。図の外に注記を逃がさない |

## 構成

**左サイドバー + 右ステージ**の2カラム。訪れた駅の内容はページに残し、サイドバーから自由に行き来できるようにする。ステップごとに中身を捨てると、読み手は「前の駅で何を見たか」を確かめられない。

- **サイドバー（左・固定）** — 対象の識別（PR番号・タイトル）、進捗、**全駅の一覧**、凡例。未訪問の駅は淡く出して押せない状態にする（まだ中身が無いので）
- **ステージ（右）** — 全体図（常設）＋ 選択中の駅のパネル（その駅の図 + 詳細）

駅のパネルは1つだけ表示し、残りは **`data-off` 属性で画面外に置いて** 保持する。**`hidden`（`display:none`）は使わない** — `display:none` の中の mermaid は文字幅を測れないまま描画され、後でサイドバーから開くと図が崩れている（実測）。画面外に置けばレイアウトは計算されるので、どの駅を開いても正しく描画済みになる:

- CSS: `.stage { position:relative; }` と `.panel[data-off] { position:absolute; left:-10000px; top:0; width:100%; visibility:hidden; }`（下の CSS に入れてある）
- JS: 切り替えは `p.toggleAttribute('data-off', p.id !== id)`

狭い画面ではサイドバーを上部の横スクロール帯に落とす。

**全体図にステップのハイライトは入れない。** 現在地はサイドバーが示すので、図の中で `rect` を動かす必要がなくなる。これで全体図はツアー中まったく書き換えずに済む。

## 手順

1. HTMLはスクラッチパッドに置く（`<scratchpad>/pr-tour-<PR番号>.html`）。書く前に `artifact-design` をロードする（Artifact ツールの要件）。図の描き方に迷ったら `artifact-diagramming` も。どちらも無い環境では、この文書の骨組みとCSSだけで書いてよい
2. Phase 1 で publish。アイコンは **初回だけ** 渡す。引数名と値の形は Claude Code のバージョンで違うので、手元の Artifact ツールのスキーマに合わせる — `icon` があればそれに一般名詞1語（`map` 等。絵文字は不可）、`icon` が無く `favicon` だけならそれに絵文字1〜2個。スキーマに無い引数を渡すと検証で弾かれ、publish 自体が失敗する。`title` は `<扱う対象> ツアー`。以後タイトルは変えない — 別セッションから探す手がかりになる。
3. 各ステップの更新は **次の4箇所だけ**。ファイル全体を書き直さない。**過去の駅のパネルは消さない**:
   - a. サイドバーの進捗表示
   - b. その駅のボタンから `disabled` を外し、`aria-current="true"` を移す（前の駅は `"false"` に）
   - c. `<section class="panel" id="s<N>">` を**末尾に追加**（その駅の図 + 3ペイン + 指摘 + 注記）
   - d. 直前まで表示していたパネルに `data-off` を付け、新しいパネルだけ `data-off` なしにする（`hidden` は使わない — 上の「構成」）
4. 同じ `file_path` で Artifact を再度呼ぶ。アイコン（`icon` / `favicon`）は渡さない（アイコンが変わるとタブで見失う）。「一気に」で進める場合は最終状態で1回だけ publish。
5. チャットには「図を更新しました」程度の1行だけ。図の内容を文章で再説明しない。

## Artifact ツールが無い環境

Artifact（claude.ai のアーティファクト）はどの環境にもあるとは限らない（claude.ai にログインしていない、API キーやクラウドプロバイダ経由で動いている等）。無いときもツアー本体は変えず、図の置き場所だけ差し替える:

- 同じHTMLを**ローカルファイル**に書く（スクラッチパッドがあればそこ、無ければユーザーに置き場所を聞く）。Phase 1 の計画の **図解** 行を「全体マップを `<path>` に書き出しました（ブラウザで開き、ステップごとに再読み込み）」に変える
- ローカルのブラウザは mermaid をネイティブに描画しないので、**このときだけ** 末尾に読み込みを1つ足す:
  `<script type="module">import m from "https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.esm.min.mjs"; m.initialize({ startOnLoad: true });</script>`
  （アーティファクトに publish する場合は足さない — 二重に描画される）
- 更新手順（4箇所だけ書き換え・過去の駅を残す）はそのまま。同じパスに上書きする
- チャットに mermaid やASCIIの図を代わりに描かない。図の置き場所が2つになるとズレる、という理由は変わらない

## 骨組み

`<…>` は埋める場所。配色・書体は変えない — ツアーごとに見た目が変わると、同じ道具だと認識できなくなる。

```html
<div class="app">
  <aside class="rail">
    <div class="eyebrow">PR #<番号> · <リポジトリ></div>
    <div class="rail-title"><短いツアー名></div>
    <div class="progress">ツアー計画</div><!-- → Step N / M → 完了 -->

    <nav class="stops">
      <button class="stop" data-target="plan" aria-current="true">計画</button>
      <button class="stop" data-target="s1" aria-current="false" disabled>
        <span class="n">1</span> <見出し>
      </button>
      <!-- 未訪問の駅は disabled のまま並べる -->
    </nav>

    <div class="legend">…</div>
  </aside>

  <main class="stage">
    <figure>
      <h2>全体 — <何の図か></h2>
      <div class="canvas"><pre class="mermaid">…</pre></div>
      <figcaption><主張を1〜2文></figcaption>
    </figure>

    <section class="panel" id="plan">…計画の3ペイン…</section>

    <section class="panel" id="s1" data-off>
      <figure>
        <h2>Step 1 — <呼び出し順></h2>
        <div class="canvas"><pre class="mermaid">sequenceDiagram
  autonumber
  …</pre></div>
        <figcaption><番号が本文の ①②… と対応することと、分岐の枠の読み方></figcaption>
      </figure>
      <figure>
        <h2>Step 1 — <戻り値による分岐></h2>
        <div class="canvas"><pre class="mermaid">flowchart TB
  …</pre></div>
        <figcaption>…</figcaption>
      </figure>
      <h2><見出し></h2>
      <p class="loc"><file:line></p>
      <div class="panes">
        <div class="pane"><h3>すでにあったもの</h3>…</div>
        <div class="pane" data-kind="diff"><h3>このPRでの差分</h3>…</div>
        <div class="pane"><h3>リポジトリの約束事</h3>…</div>
      </div>
      <div class="findings"><h3>レビューでの指摘</h3>…</div><!-- 無ければ要素ごと省く -->
      <p class="note">…</p>
    </section>
  </main>
</div>

<script>
  const stops = [...document.querySelectorAll('.stop')];
  const panels = [...document.querySelectorAll('.panel')];
  const show = (id) => {
    panels.forEach((p) => { p.toggleAttribute('data-off', p.id !== id); });
    stops.forEach((b) => b.setAttribute('aria-current', String(b.dataset.target === id)));
    document.querySelector('.stage').scrollTo?.({ top: 0 });
  };
  stops.forEach((b) => b.addEventListener('click', () => { if (!b.disabled) show(b.dataset.target); }));
  document.addEventListener('keydown', (e) => {
    if (e.key !== 'ArrowDown' && e.key !== 'ArrowUp') return;
    const open = stops.filter((b) => !b.disabled);
    const i = open.findIndex((b) => b.getAttribute('aria-current') === 'true');
    const next = open[i + (e.key === 'ArrowDown' ? 1 : -1)];
    if (next) { next.focus(); show(next.dataset.target); e.preventDefault(); }
  });
</script>
```

レイアウトと描画面のCSS:

```css
.app { display:grid; grid-template-columns:232px 1fr; gap:34px; max-width:1140px; margin:0 auto; align-items:start; }
.rail { position:sticky; top:24px; display:flex; flex-direction:column; gap:14px; }
.stops { display:flex; flex-direction:column; gap:2px; }
.stop { text-align:left; font:inherit; font-size:13px; color:var(--muted); background:none;
        border:0; border-left:2px solid var(--rule); padding:7px 12px; cursor:pointer; border-radius:0 6px 6px 0; }
.stop:hover:not([disabled]) { background:var(--line-soft); color:var(--ink); }
.stop[aria-current="true"] { color:var(--line); font-weight:700; border-left-color:var(--line); background:var(--line-soft); }
.stop[disabled] { opacity:.45; cursor:default; }
.stop .n { font-family:var(--mono); font-size:11px; }
.stop:focus-visible { outline:2px solid var(--line); outline-offset:1px; }
@media (max-width:820px) {
  .app { grid-template-columns:1fr; }
  .rail { position:static; }
  .stops { flex-direction:row; overflow-x:auto; }
  .stop { border-left:0; border-bottom:2px solid var(--rule); white-space:nowrap; border-radius:6px 6px 0 0; }
  .stop[aria-current="true"] { border-bottom-color:var(--line); }
}

/* 非表示の駅は display:none にしない — mermaid が文字幅を測れず崩れる */
.stage { position:relative; }
.panel[data-off] { position:absolute; left:-10000px; top:0; width:100%; visibility:hidden; }

.canvas { background:#fbfbfa; border:1px solid var(--rule); border-radius:10px; padding:18px 14px; overflow-x:auto; }
.canvas .mermaid { display:flex; justify-content:center; min-width:min-content; }
figure h2 { font-size:13px; font-family:var(--mono); letter-spacing:.06em; color:var(--muted); font-weight:500; }
figcaption { font-size:12.5px; color:var(--muted); margin-top:10px; }

/* .plan と .findings は初回ファイルから入れておく — 後から足すと更新が4箇所で済まなくなる */
.plan { margin:0 0 20px; padding-bottom:16px; border-bottom:1px solid var(--rule); font-size:13px; color:var(--muted); }
.plan summary { cursor:pointer; }
.findings { margin-top:20px; padding:14px 16px; border:1px dashed var(--rule); border-radius:8px; font-size:13px; }
.findings h3 { font-family:var(--mono); font-size:11px; letter-spacing:.1em; text-transform:uppercase; color:var(--muted); margin:0 0 8px; }
```

守るのは **1枚・全体図は常設で書き換えない・駅ごとに固有の図2枚（呼び出し順＋分岐）・過去の駅を残す（`hidden` ではなく画面外へ）・図式は目的で選ぶ** の5点。
