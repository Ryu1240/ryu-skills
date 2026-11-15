# -*- coding: utf-8 -*-
"""pr-tour の図解ヘルパー。

Artifact の各 Step に入れる「仕組みが見える 1 枚」を生成する。図の形の選び方は references/figures.md。
- 線と箱の図（シーケンス・フローチャート・状態遷移・ER・依存関係・層構造・データフロー・タイムライン）は
  Fig クラスで手書き SVG にする
- 表（前後比較・決定表・制約一覧・翻訳表）とディレクトリのツリーは table() / tree() で HTML にする
どちらも線と文字は currentColor、塗りは CSS 変数（--card / --accent-soft / --warn-soft / --ctx-soft /
--test-soft / --new-soft / --mod-soft）なので、ライト・ダーク両テーマで読める。外部ライブラリ不要。

使い方（Python 3.9+）:

    import sys; sys.path.insert(0, "<このファイルのあるディレクトリ>")
    from fig import Fig, table, tree
    f = Fig("f3", 860, 400, "この図が示す主張を 1 文で（aria-label になる）")
    f.box(20, 90, 120, 48, ["Client", "POST /orders"], "ctx")
    f.arrow([(140, 114), (180, 114)], "request")
    f.box(180, 90, 130, 48, ["create(params)", "orders.go:56"], "accent")
    html = f.render("Step 3: 図の下に出る 1 行の説明")
    open("fig3.html", "w", encoding="utf-8").write(html)   # plan-step.py --figure に渡す

    t = table(["入力", "変更前", "変更後"],
              [["`nil`", "500", ("422", "mod")], ["`[]`", "200 空", "200 空"]],
              "Step 4: tags の値ごとのレスポンス")

fid は同じページ内で一意にすること（矢印マーカーの id に使う）。
座標は viewBox の単位。幅 860 が Artifact のカード幅に収まる目安（クリックで拡大できるので、
詰め込まずに幅を取ってよいが、等倍で読めることを優先する）。
日本語 11px は 1 文字 ≒ 11px、ASCII は ≒ 6px として、文字列が viewBox からはみ出さないよう
長い注記は 2 行に分ける。ラベルは短く、説明文は figcaption かチャットに置く。

Fig の部品（kind = plain | accent | warn | ctx | test）:
  box(x, y, w, h, lines, kind)            箱。lines は 1〜5 行。rx で角丸、dashed で破線
  region(x, y, w, h, label)               点線の領域（「このPRが足した範囲」「層」など境界の明示）
  arrow(points, label, kind)              折れ線矢印。points は [(x,y), ...]。lx/ly/anchor でラベル位置を調整
  link(points, label, kind, a, b)         矢印なしの線。a / b は両端の多重度（ER の "1" "N" "0..1"）
  lifeline(x, y1, y2, label, w)           シーケンス図の縦線とヘッダー
  msg(x1, x2, y, label, kind)             シーケンス図の水平メッセージ。dashed=True で戻り
  diamond(cx, cy, w, h, lines, kind)      フローチャートの分岐（菱形）
  state(x, y, w, h, label, kind)          状態遷移図の状態（両端が丸い箱）
  start(cx, cy) / end(cx, cy)             状態遷移図の開始点・終了点
  loop(x, y, label, kind)                 (x, y) を上端とする自己遷移
  entity(x, y, w, name, cols, kind)       ER 図のエンティティ。cols は (カラム, 印, kind) の列。高さを返す
  axis(x1, x2, y, ticks, label)           タイムラインの軸。ticks は [(x, "0s"), ...]
  mark(x, y, label, kind)                 軸上の出来事（点とラベル）
  bracket(x, y1, y2, label)               縦の括弧（トランザクション範囲など）
  text(x, y, s, fs, anchor, kind)         自由配置のテキスト。kind で色（warn / accent / test）
  render(caption) -> str                  <figure><svg …>…</svg><figcaption>…</figcaption></figure>

HTML の図:
  table(header, rows, caption, claim)     表。セルは文字列か (文字列, kind)。kind = new | mod | del | ctx | test | warn | accent。
                                          先頭列は行見出し（row_header=False で外す）。`…` は <code> になる
  tree(entries, caption, claim)           ツリー。entries は (深さ, 名前, タグ, 注記)。タグ = new | mod | del | ctx | test | None

1 ステップに置く図は 2 枚まで。2 枚のときは plan-step.py --figure a.html b.html と並べて渡す。

公開前の検査:
  python3 fig.py --check <page.html>   ページ内の全 <svg> と <figure> が整形式かを確かめる
"""
import html
import re

FS = 12

BOX_STYLE = {
    "plain": "fill:var(--card);stroke:currentColor",
    "accent": "fill:var(--accent-soft);stroke:var(--accent)",
    "warn": "fill:var(--warn-soft);stroke:var(--warn)",
    "ctx": "fill:var(--ctx-soft);stroke:currentColor",
    "test": "fill:var(--test-soft);stroke:var(--test)",
}
LINE_COLOR = {
    "plain": "currentColor",
    "accent": "var(--accent)",
    "warn": "var(--warn)",
    "test": "var(--test)",
    "ctx": "currentColor",
}
ROW_FILL = {"accent": "var(--accent-soft)", "warn": "var(--warn-soft)", "test": "var(--test-soft)", "ctx": "var(--ctx-soft)"}


def esc(s):
    return html.escape(str(s), quote=True)


class Fig:
    def __init__(self, fid, W, H, claim):
        self.fid, self.W, self.H, self.claim = fid, W, H, claim
        self.parts = []

    def _lines(self, cx, cy, lines, fs):
        n = len(lines)
        for i, ln in enumerate(lines):
            ty = cy + (i - (n - 1) / 2) * (fs + 3) + fs * 0.35
            f = fs if i == 0 else max(fs - 1, 10)
            self.parts.append(
                f'<text x="{cx}" y="{ty:.1f}" font-size="{f}" text-anchor="middle" fill="currentColor">{esc(ln)}</text>'
            )

    def box(self, x, y, w, h, lines, kind="plain", fs=FS, dashed=False, rx=6):
        da = ' stroke-dasharray="4 3"' if dashed else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" style="{BOX_STYLE[kind]}" stroke-width="1.2"{da}/>'
        )
        self._lines(x + w / 2, y + h / 2, lines, fs)

    def region(self, x, y, w, h, label):
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="none" stroke="currentColor" stroke-opacity=".45" stroke-dasharray="6 4"/>'
        )
        self.parts.append(
            f'<text x="{x + 8}" y="{y + 14}" font-size="11" fill="currentColor" fill-opacity=".7">{esc(label)}</text>'
        )

    def text(self, x, y, s, fs=11, anchor="start", op=1.0, rot=None, kind=None):
        tr = f' transform="rotate(-90 {x} {y})"' if rot else ""
        fill = {"warn": "var(--warn)", "accent": "var(--accent)", "test": "var(--test)"}.get(kind, "currentColor")
        self.parts.append(
            f'<text x="{x}" y="{y}" font-size="{fs}" text-anchor="{anchor}" fill="{fill}" fill-opacity="{op}"{tr}>{esc(s)}</text>'
        )

    def arrow(self, pts, label=None, kind="plain", dashed=False, lx=None, ly=None, anchor="middle", fs=11):
        color = LINE_COLOR[kind]
        da = ' stroke-dasharray="5 4"' if dashed else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.parts.append(
            f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="1.3"{da} marker-end="url(#{self.fid}-ar)"/>'
        )
        if label:
            if lx is None:
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                lx, ly = (x1 + x2) / 2, min(y1, y2) - 6 if y1 == y2 else (y1 + y2) / 2
            self.parts.append(
                f'<text x="{lx}" y="{ly}" font-size="{fs}" text-anchor="{anchor}" fill="{color}">{esc(label)}</text>'
            )

    def link(self, pts, label=None, kind="plain", dashed=False, a=None, b=None, lx=None, ly=None, fs=11):
        color = LINE_COLOR[kind]
        da = ' stroke-dasharray="5 4"' if dashed else ""
        p = " ".join(f"{x},{y}" for x, y in pts)
        self.parts.append(f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="1.3"{da}/>')
        # 多重度は端点から線に沿って少し内側、線の上側に置く
        for end, nxt, s in ((pts[0], pts[1], a), (pts[-1], pts[-2], b)):
            if s is None:
                continue
            (ex, ey), (nx, ny) = end, nxt
            dx, dy = (nx > ex) - (nx < ex), (ny > ey) - (ny < ey)
            tx, ty = ex + dx * 12 + (4 if dy else 0), ey + dy * 16 - (5 if not dy else 0)
            anchor = "start" if dx >= 0 else "end"
            self.parts.append(
                f'<text x="{tx}" y="{ty}" font-size="{fs}" text-anchor="{anchor}" fill="{color}">{esc(s)}</text>'
            )
        if label:
            if lx is None:
                (x1, y1), (x2, y2) = pts[0], pts[-1]
                lx, ly = (x1 + x2) / 2, (y1 + y2) / 2 - 6
            self.parts.append(
                f'<text x="{lx}" y="{ly}" font-size="{fs}" text-anchor="middle" fill="{color}">{esc(label)}</text>'
            )

    def lifeline(self, x, y1, y2, label, w=170):
        self.box(x - w / 2, y1, w, 34, [label], kind="ctx", fs=12)
        self.parts.append(
            f'<line x1="{x}" y1="{y1 + 34}" x2="{x}" y2="{y2}" stroke="currentColor" stroke-opacity=".5" stroke-dasharray="3 4"/>'
        )

    def msg(self, x1, x2, y, label, kind="plain", dashed=False, fs=11, lx=None, anchor="middle"):
        color = LINE_COLOR[kind]
        da = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="1.3"{da} marker-end="url(#{self.fid}-ar)"/>'
        )
        if lx is None:
            lx = (x1 + x2) / 2
        self.parts.append(
            f'<text x="{lx}" y="{y - 5}" font-size="{fs}" text-anchor="{anchor}" fill="{color}">{esc(label)}</text>'
        )

    def diamond(self, cx, cy, w, h, lines, kind="plain", fs=11):
        pts = f"{cx},{cy - h / 2} {cx + w / 2},{cy} {cx},{cy + h / 2} {cx - w / 2},{cy}"
        self.parts.append(f'<polygon points="{pts}" style="{BOX_STYLE[kind]}" stroke-width="1.2"/>')
        self._lines(cx, cy, lines, fs)

    def state(self, x, y, w, h, label, kind="plain", fs=FS, dashed=False):
        lines = label if isinstance(label, (list, tuple)) else [label]
        self.box(x, y, w, h, lines, kind, fs=fs, dashed=dashed, rx=h / 2)

    def start(self, cx, cy):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="7" fill="currentColor"/>')

    def end(self, cx, cy):
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="10" fill="none" stroke="currentColor" stroke-width="1.3"/>')
        self.parts.append(f'<circle cx="{cx}" cy="{cy}" r="6" fill="currentColor"/>')

    def loop(self, x, y, label=None, kind="plain", dashed=False, fs=11):
        color = LINE_COLOR[kind]
        da = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<path d="M{x - 14},{y} C{x - 30},{y - 38} {x + 30},{y - 38} {x + 14},{y}" fill="none" stroke="{color}" stroke-width="1.3"{da} marker-end="url(#{self.fid}-ar)"/>'
        )
        if label:
            self.parts.append(
                f'<text x="{x}" y="{y - 34}" font-size="{fs}" text-anchor="middle" fill="{color}">{esc(label)}</text>'
            )

    def entity(self, x, y, w, name, cols, kind="plain", row=18, fs=11):
        """cols は (カラム名, 印, kind) / (カラム名, 印) / カラム名 の列。印は "PK" "FK" "UQ" など。
        kind（accent / warn / test / ctx）を付けた行は塗りで強調する（この PR で足したカラムなど）。"""
        head = 26
        h = head + row * len(cols) + 6
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" style="{BOX_STYLE[kind]}" stroke-width="1.2"/>'
        )
        self.parts.append(
            f'<text x="{x + w / 2}" y="{y + 17}" font-size="{FS}" font-weight="600" text-anchor="middle" fill="currentColor">{esc(name)}</text>'
        )
        self.parts.append(
            f'<line x1="{x}" y1="{y + head}" x2="{x + w}" y2="{y + head}" stroke="currentColor" stroke-opacity=".4"/>'
        )
        for i, c in enumerate(cols):
            c = (c,) if isinstance(c, str) else tuple(c)
            label, mark, ck = (c + ("", None))[:3]
            ry = y + head + 3 + row * i
            if ck:
                self.parts.append(
                    f'<rect x="{x + 2}" y="{ry}" width="{w - 4}" height="{row}" rx="3" fill="{ROW_FILL[ck]}"/>'
                )
            ty = ry + row / 2 + fs * 0.35
            if mark:
                self.parts.append(
                    f'<text x="{x + 8}" y="{ty:.1f}" font-size="10" fill="currentColor" fill-opacity=".65">{esc(mark)}</text>'
                )
            self.parts.append(
                f'<text x="{x + 34}" y="{ty:.1f}" font-size="{fs}" fill="currentColor">{esc(label)}</text>'
            )
        return h

    def axis(self, x1, x2, y, ticks=(), label=None, fs=11):
        self.parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="currentColor" stroke-width="1.3" marker-end="url(#{self.fid}-ar)"/>'
        )
        for tx, tl in ticks:
            self.parts.append(f'<line x1="{tx}" y1="{y - 4}" x2="{tx}" y2="{y + 4}" stroke="currentColor"/>')
            self.parts.append(
                f'<text x="{tx}" y="{y + 18}" font-size="{fs}" text-anchor="middle" fill="currentColor" fill-opacity=".75">{esc(tl)}</text>'
            )
        if label:
            self.parts.append(
                f'<text x="{x2}" y="{y + 18}" font-size="{fs}" text-anchor="end" fill="currentColor" fill-opacity=".75">{esc(label)}</text>'
            )

    def mark(self, x, y, label, kind="plain", dy=-10, fs=11):
        color = LINE_COLOR[kind]
        self.parts.append(f'<circle cx="{x}" cy="{y}" r="4.5" fill="{color}"/>')
        self.parts.append(
            f'<text x="{x}" y="{y + dy}" font-size="{fs}" text-anchor="middle" fill="{color}">{esc(label)}</text>'
        )

    def bracket(self, x, y1, y2, label, kind="plain"):
        color = {"plain": "currentColor", "accent": "var(--accent)"}[kind]
        self.parts.append(
            f'<path d="M{x},{y1} h8 M{x + 8},{y1} v{y2 - y1} M{x},{y2} h8" fill="none" stroke="{color}" stroke-width="1.3"/>'
        )
        cy = (y1 + y2) / 2
        self.parts.append(
            f'<text x="{x + 22}" y="{cy}" font-size="11" text-anchor="middle" fill="{color}" transform="rotate(90 {x + 22} {cy})">{esc(label)}</text>'
        )

    def render(self, caption):
        defs = (
            f'<defs><marker id="{self.fid}-ar" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">'
            f'<path d="M0,0 L10,5 L0,10 z" fill="context-stroke"/></marker></defs>'
        )
        body = "\n".join(self.parts)
        return (
            f'<figure><svg viewBox="0 0 {self.W} {self.H}" role="img" aria-label="{esc(self.claim)}" '
            f'font-family="IBM Plex Sans JP, Hiragino Sans, system-ui, sans-serif">{defs}\n{body}\n</svg>'
            f'<figcaption>{esc(caption)}</figcaption></figure>'
        )


CELL_KINDS = {"new", "mod", "del", "ctx", "test", "warn", "accent"}
TREE_TAGS = {"new": "🆕", "mod": "✏️", "del": "🗑️", "ctx": "📖", "test": "🧪"}


def _inline(s):
    """エスケープしたうえで `…` を <code> にする。"""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", esc(s))


def _cell(tag, c, extra=""):
    text, kind = (c[0], c[1]) if isinstance(c, (tuple, list)) else (c, None)
    if kind and kind not in CELL_KINDS:
        raise ValueError(f"unknown cell kind: {kind}")
    cls = f' class="{kind}"' if kind else ""
    return f"<{tag}{extra}{cls}>{_inline(text)}</{tag}>"


def table(header, rows, caption, claim=None, row_header=True):
    """前後比較・決定表・制約一覧などの表を <figure> で返す。変わったセルに kind を付けて強調する。"""
    head = "".join(_cell("th", h, ' scope="col"') for h in header)
    body = []
    for r in rows:
        cells = [_cell("th", r[0], ' scope="row"')] if row_header else [_cell("td", r[0])]
        cells += [_cell("td", c) for c in r[1:]]
        body.append("<tr>" + "".join(cells) + "</tr>")
    label = esc(claim or caption)
    return (
        f'<figure class="fig-html"><div class="fig-scroll"><table class="fig-table" aria-label="{label}">'
        f"<thead><tr>{head}</tr></thead><tbody>{''.join(body)}</tbody></table></div>"
        f"<figcaption>{esc(caption)}</figcaption></figure>"
    )


def tree(entries, caption, claim=None):
    """ディレクトリ・モジュールのツリーを <figure> で返す。entries は (深さ, 名前, タグ, 注記)。"""
    items = []
    for e in entries:
        depth, name, tag, note = (tuple(e) + (None, None))[:4]
        if tag and tag not in TREE_TAGS:
            raise ValueError(f"unknown tree tag: {tag}")
        t = f' <span class="tag {tag}">{TREE_TAGS[tag]}</span>' if tag else ""
        n = f' <span class="note">{_inline(note)}</span>' if note else ""
        items.append(f'<li style="padding-left:{depth * 18}px"><code>{esc(name)}</code>{t}{n}</li>')
    label = esc(claim or caption)
    return (
        f'<figure class="fig-html"><ul class="fig-tree" aria-label="{label}">{"".join(items)}</ul>'
        f"<figcaption>{esc(caption)}</figcaption></figure>"
    )


def check_well_formed(html_text):
    """ページ内の全 <svg> と <figure> が整形式かを返す。ローカル HTML はブラウザで描画確認できないことがあるため、
    公開前の機械検査として使う。戻り値は (svg 数, figure 数, 壊れている箇所のリスト)。"""
    import xml.etree.ElementTree as ET

    bad = []
    for kind, pat in (("svg", r"<svg .*?</svg>"), ("figure", r"<figure[ >].*?</figure>")):
        found = re.findall(pat, html_text, re.S)
        for i, s in enumerate(found):
            try:
                ET.fromstring(s)
            except ET.ParseError:
                bad.append(f"{kind}[{i}]")
        if kind == "svg":
            n_svg = len(found)
        else:
            n_fig = len(found)
    return n_svg, n_fig, bad


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        n, m, bad = check_well_formed(open(sys.argv[2], encoding="utf-8").read())
        print(f"svgs={n} figures={m} malformed={bad}")
        sys.exit(1 if bad else 0)
    print(__doc__)
