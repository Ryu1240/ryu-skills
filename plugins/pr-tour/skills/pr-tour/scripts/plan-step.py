# -*- coding: utf-8 -*-
"""pr-tour のステップ進行を 1 コマンドで反映する。

Markdown（正）と HTML（俯瞰）の 2 ファイルを毎ステップ手で直すと、どちらかを忘れて
文脈要約後に位置を失う。このスクリプトは両方を同時に更新する。

使い方:
  python3 plan-step.py <plan.md> <plan.html> --step N \
      [--figure fig.html] [--topics "論点1" "論点2" ...] [--findings "#2 CONFIRMED file:line 要点" ...] \
      [--total-steps M] [--status 完了]

やること:
  1. plan.md の「- 現在のステップ: k」を N に、「- [ ] Step N:」を「- [x] Step N:」に
  2. plan.html の article#step-(N-1) 以下を done、#step-N を current に、進捗率を N/M に、
     footer の「更新: … ／ 現在: …」を書き換える
  3. --figure があれば、#step-N の <details class="explain"> の中身をそのファイルの内容
     （fig.py の render() 出力）で置き換える。--findings があれば、その下に code-review の指摘を 🔍 の箇条書きで
     載せる。--topics があれば、さらにその下に「チャットで議論した論点」のタグを付ける
  4. --status 完了 なら plan.md の状態を完了にし、HTML の current を外して footer を完了表記にする

HTML 側の前提: assets/plan-view.html の構造（article.step#step-N と details.explain）。
更新後に fig.py --check で SVG の整形式を確認してから Artifact を再公開する。
"""
import argparse
import datetime as dt
import html
import re
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("html")
    ap.add_argument("--step", type=int, required=True)
    ap.add_argument("--figure", help="fig.py render() の出力 HTML ファイル")
    ap.add_argument("--topics", nargs="*", default=[])
    ap.add_argument("--findings", nargs="*", default=[], help="code-review の指摘。1 件 1 引数")
    ap.add_argument("--total-steps", type=int)
    ap.add_argument("--status", choices=["進行中", "完了"], default="進行中")
    a = ap.parse_args()

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")

    md = open(a.md, encoding="utf-8").read()
    md, n1 = re.subn(r"^- 現在のステップ: \d+$", f"- 現在のステップ: {a.step}", md, count=1, flags=re.M)
    md, _ = re.subn(rf"^- \[ \] Step {a.step}:", f"- [x] Step {a.step}:", md, count=1, flags=re.M)
    if a.status == "完了":
        md = re.sub(r"^- 状態: .*$", f"- 状態: 完了（{now}）", md, count=1, flags=re.M)
    elif re.search(r"^- 状態: 未開始$", md, flags=re.M):
        md = re.sub(r"^- 状態: 未開始$", "- 状態: 進行中", md, count=1, flags=re.M)
    open(a.md, "w", encoding="utf-8").write(md)
    if not n1:
        print("warning: 「- 現在のステップ:」行が見つからない", file=sys.stderr)

    total = a.total_steps or len(re.findall(r"^- \[[ x]\] Step \d+:", md, flags=re.M)) or a.step
    pct = int(round(100 * a.step / total))

    t = open(a.html, encoding="utf-8").read()
    for k in range(1, a.step):
        t = re.sub(rf'<article class="step[^"]*" id="step-{k}">', f'<article class="step done" id="step-{k}">', t, count=1)
    cls = "step done" if a.status == "完了" else "step current"
    t = re.sub(rf'<article class="step[^"]*" id="step-{a.step}">', f'<article class="{cls}" id="step-{a.step}">', t, count=1)
    # ステップを追加・巻き戻ししたときに、先のステップへ done/current が残らないようにする
    for k in range(a.step + 1, total + 1):
        t = re.sub(rf'<article class="step[^"]*" id="step-{k}">', f'<article class="step" id="step-{k}">', t, count=1)
    t = re.sub(r"(\.progress > div \{[^}]*width: )\d+%", rf"\g<1>{pct}%", t, count=1)

    if a.figure or a.topics or a.findings:
        body = ""
        if a.figure:
            body += open(a.figure, encoding="utf-8").read().strip() + "\n"
        if a.findings:
            body += '<ul class="findings">' + "".join(f"<li>{html.escape(x)}</li>" for x in a.findings) + "</ul>\n"
        if a.topics:
            body += '<p class="topics">チャットで議論した論点: ' + "".join(f"<span>{html.escape(x)}</span>" for x in a.topics) + "</p>\n"
        pat = re.compile(rf'(<article class="[^"]*" id="step-{a.step}">.*?<details class="explain"><summary>)[^<]*(</summary>)(.*?)(</details>)', re.S)
        m = pat.search(t)
        if m:
            t = t[: m.start()] + m.group(1) + "図解" + m.group(2) + "\n" + body + m.group(4) + t[m.end():]
        else:
            print("warning: step の <details class=\"explain\"> が見つからない。図は挿入されなかった", file=sys.stderr)

    state = f"状態: 完了（全 {total} ステップ）" if a.status == "完了" else f"現在: Step {a.step} を解説中"
    t, n3 = re.subn(r"更新: [0-9\- :]+ ／ [^<]*", f"更新: {now} ／ {state}", t, count=1)
    if not n3:
        print("warning: footer の「更新: … ／ …」が見つからない", file=sys.stderr)
    open(a.html, "w", encoding="utf-8").write(t)
    print(f"ok step={a.step}/{total} pct={pct} status={a.status}")


if __name__ == "__main__":
    main()
