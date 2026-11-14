# -*- coding: utf-8 -*-
"""pr-tour の図解用 SVG ヘルパー。

Artifact の各 Step に入れる「仕組みが見える 1 枚」を、手書き SVG として生成する。
線と文字は currentColor、塗りは CSS 変数（--card / --accent-soft / --warn-soft / --ctx-soft / --test-soft）
なので、ライト・ダーク両テーマで読める。外部ライブラリ不要。

使い方（Python 3.9+）:

    import sys; sys.path.insert(0, "<このファイルのあるディレクトリ>")
    from fig import Fig
    f = Fig("f3", 860, 400, "この図が示す主張を 1 文で（aria-label になる）")
    f.box(20, 90, 120, 48, ["Client", "POST /orders"], "ctx")
    f.arrow([(140, 114), (180, 114)], "request")
    f.box(180, 90, 130, 48, ["create(params)", "orders.go:56"], "accent")
    html = f.render("Step 3: 図の下に出る 1 行の説明")
    open("fig3.html", "w", encoding="utf-8").write(html)   # plan-step.py --figure に渡す

fid は同じページ内で一意にすること（矢印マーカーの id に使う）。
座標は viewBox の単位。幅 860 が Artifact のカード幅に収まる目安。
日本語 11px は 1 文字 ≒ 11px、ASCII は ≒ 6px として、文字列が viewBox からはみ出さないよう
長い注記は 2 行に分ける。ラベルは短く、説明文は figcaption かチャットに置く。

部品:
  box(x, y, w, h, lines, kind)      kind = plain | accent | warn | ctx | test。lines は 1〜5 行
  region(x, y, w, h, label)         点線の領域（「このPRが足した範囲」など境界の明示）
  arrow(points, label, kind)        折れ線矢印。points は [(x,y), ...]。lx/ly/anchor でラベル位置を調整
  lifeline(x, y1, y2, label, w)     シーケンス図の縦線とヘッダー
  msg(x1, x2, y, label, kind)       シーケンス図の水平メッセージ。dashed=True で戻り
  bracket(x, y1, y2, label)         縦の括弧（トランザクション範囲など）
  text(x, y, s, fs, anchor, kind)   自由配置のテキスト。kind で色（warn / accent / test）
  render(caption) -> str            <figure><svg …>…</svg><figcaption>…</figcaption></figure>

公開前の検査:
  python3 fig.py --check <page.html>   ページ内の全 <svg> が整形式かを確かめる
"""
import html

FS = 12


def esc(s):
    return html.escape(str(s), quote=True)


class Fig:
    def __init__(self, fid, W, H, claim):
        self.fid, self.W, self.H, self.claim = fid, W, H, claim
        self.parts = []

    def box(self, x, y, w, h, lines, kind="plain", fs=FS, dashed=False):
        style = {
            "plain": "fill:var(--card);stroke:currentColor",
            "accent": "fill:var(--accent-soft);stroke:var(--accent)",
            "warn": "fill:var(--warn-soft);stroke:var(--warn)",
            "ctx": "fill:var(--ctx-soft);stroke:currentColor",
            "test": "fill:var(--test-soft);stroke:var(--test)",
        }[kind]
        da = ' stroke-dasharray="4 3"' if dashed else ""
        self.parts.append(
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" style="{style}" stroke-width="1.2"{da}/>'
        )
        n = len(lines)
        for i, ln in enumerate(lines):
            ty = y + h / 2 + (i - (n - 1) / 2) * (fs + 3) + fs * 0.35
            f = fs if i == 0 else max(fs - 1, 10)
            self.parts.append(
                f'<text x="{x + w / 2}" y="{ty:.1f}" font-size="{f}" text-anchor="middle" fill="currentColor">{esc(ln)}</text>'
            )

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
        color = {"plain": "currentColor", "accent": "var(--accent)", "warn": "var(--warn)", "test": "var(--test)"}[kind]
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

    def lifeline(self, x, y1, y2, label, w=170):
        self.box(x - w / 2, y1, w, 34, [label], kind="ctx", fs=12)
        self.parts.append(
            f'<line x1="{x}" y1="{y1 + 34}" x2="{x}" y2="{y2}" stroke="currentColor" stroke-opacity=".5" stroke-dasharray="3 4"/>'
        )

    def msg(self, x1, x2, y, label, kind="plain", dashed=False, fs=11, lx=None, anchor="middle"):
        color = {"plain": "currentColor", "accent": "var(--accent)", "warn": "var(--warn)"}[kind]
        da = ' stroke-dasharray="5 4"' if dashed else ""
        self.parts.append(
            f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" stroke="{color}" stroke-width="1.3"{da} marker-end="url(#{self.fid}-ar)"/>'
        )
        if lx is None:
            lx = (x1 + x2) / 2
        self.parts.append(
            f'<text x="{lx}" y="{y - 5}" font-size="{fs}" text-anchor="{anchor}" fill="{color}">{esc(label)}</text>'
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


def check_well_formed(html_text):
    """ページ内の全 <svg> が整形式かを返す。ローカル HTML はブラウザで描画確認できないことがあるため、
    公開前の機械検査として使う。戻り値は (svg 数, 壊れている index のリスト)。"""
    import re
    import xml.etree.ElementTree as ET

    bad = []
    svgs = re.findall(r"<svg .*?</svg>", html_text, re.S)
    for i, s in enumerate(svgs):
        try:
            ET.fromstring(s)
        except ET.ParseError:
            bad.append(i)
    return len(svgs), bad


if __name__ == "__main__":
    import sys

    if len(sys.argv) == 3 and sys.argv[1] == "--check":
        n, bad = check_well_formed(open(sys.argv[2], encoding="utf-8").read())
        print(f"svgs={n} malformed={bad}")
        sys.exit(1 if bad else 0)
    print(__doc__)
