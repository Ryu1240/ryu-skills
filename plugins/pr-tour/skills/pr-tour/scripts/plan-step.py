# -*- coding: utf-8 -*-
"""pr-tour のステップ進行を 1 コマンドで反映する。

Markdown（正）と HTML（俯瞰）の 2 ファイルを毎ステップ手で直すと、どちらかを忘れて
文脈要約後に位置を失う。このスクリプトは両方を同時に更新する。

使い方:
  # ステップ k の解説を終えたとき（現在位置を k にする）
  python3 plan-step.py <plan.md> <plan.html> --step k \
      [--figure fig.html] [--topics "論点1" ...] [--findings "#2 CONFIRMED file:line 要点" ...] \
      [--total-steps M] [--status 完了]

  # 現在位置を変えずに、ステップ m へ指摘・論点・図を追記するとき（後から届いた指摘など）
  python3 plan-step.py <plan.md> <plan.html> --annotate m [--findings ...] [--topics ...] [--figure fig.html]

やること:
  --step k
    1. plan.md の「- 現在のステップ:」を k に、「- [ ] Step k:」を「- [x] Step k:」にする
    2. plan.html の各ステップの done を plan.md の [x] と同期する（Markdown が正）。
       飛ばしたステップは done にならず、巻き戻しても先の done は消えない。#step-k を current にする
    3. 進捗率は [x] の数 / 全ステップ数。footer の「更新: … ／ 現在: …」を書き換える
  --annotate m
    plan.md の現在位置と [x]、HTML の done / current と進捗率には触れず、#step-m だけを更新する
  共通（#step-N の <details class="explain"> の中身）
    --figure があれば図の部分だけを差し替える。--findings / --topics は既存の箇条書きに追記する
    （同じ文言は重ねない）。指定しなかった部分（既存の図・指摘・論点）はそのまま残す
  --status 完了 なら plan.md の状態を完了にし、HTML の current を外して footer を完了表記にする

HTML 側の前提: assets/plan-view.html の構造（article.step#step-N と details.explain）。
更新後に fig.py --check で SVG の整形式を確認してから Artifact を再公開する。
"""
import argparse
import datetime as dt
import html
import re
import sys

FINDINGS_RE = re.compile(r'<ul class="findings">(.*?)</ul>\n?', re.S)
TOPICS_RE = re.compile(r'<p class="topics">チャットで議論した論点: (.*?)</p>\n?', re.S)


def merge_items(existing, new, tag):
    """既存の <li>/<span> の列に、まだ無い文言だけを足す。"""
    items = re.findall(rf"<{tag}>(.*?)</{tag}>", existing, re.S)
    for x in new:
        e = html.escape(x)
        if e not in items:
            items.append(e)
    return items


def update_explain(t, step, figure, findings, topics):
    pat = re.compile(rf'(<article class="[^"]*" id="step-{step}">.*?<details class="explain"><summary>)[^<]*(</summary>)(.*?)(</details>)', re.S)
    m = pat.search(t)
    if not m:
        print('warning: step の <details class="explain"> が見つからない。図・指摘は挿入されなかった', file=sys.stderr)
        return t
    inner = m.group(3)
    fm = FINDINGS_RE.search(inner)
    tm = TOPICS_RE.search(inner)
    old_findings = fm.group(1) if fm else ""
    old_topics = tm.group(1) if tm else ""
    rest = TOPICS_RE.sub("", FINDINGS_RE.sub("", inner)).strip()
    if figure:
        rest = open(figure, encoding="utf-8").read().strip()

    body = "\n" + (rest + "\n" if rest else "")
    f_items = merge_items(old_findings, findings, "li")
    if f_items:
        body += '<ul class="findings">' + "".join(f"<li>{x}</li>" for x in f_items) + "</ul>\n"
    t_items = merge_items(old_topics, topics, "span")
    if t_items:
        body += '<p class="topics">チャットで議論した論点: ' + "".join(f"<span>{x}</span>" for x in t_items) + "</p>\n"
    return t[: m.start()] + m.group(1) + "図解" + m.group(2) + body + m.group(4) + t[m.end():]


def set_class(t, k, cls):
    return re.sub(rf'<article class="step[^"]*" id="step-{k}">', f'<article class="{cls}" id="step-{k}">', t, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("html")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--step", type=int, help="解説を終えたステップ。現在位置をここにする")
    g.add_argument("--annotate", type=int, help="現在位置を変えずに追記するステップ")
    ap.add_argument("--figure", help="fig.py render() の出力 HTML ファイル")
    ap.add_argument("--topics", nargs="*", default=[])
    ap.add_argument("--findings", nargs="*", default=[], help="code-review の指摘。1 件 1 引数")
    ap.add_argument("--total-steps", type=int)
    ap.add_argument("--status", choices=["進行中", "完了"], default="進行中")
    a = ap.parse_args()
    if a.annotate is not None and a.status == "完了":
        ap.error("--status 完了 は --step と一緒に使う")

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    t = open(a.html, encoding="utf-8").read()

    if a.annotate is not None:
        t = update_explain(t, a.annotate, a.figure, a.findings, a.topics)
        open(a.html, "w", encoding="utf-8").write(t)
        print(f"ok annotate step={a.annotate}（現在位置・完了状態は変更なし）")
        return

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

    steps = [int(n) for n in re.findall(r"^- \[[ x]\] Step (\d+):", md, flags=re.M)]
    done = {int(n) for n in re.findall(r"^- \[x\] Step (\d+):", md, flags=re.M)}
    total = a.total_steps or len(steps) or a.step
    pct = int(round(100 * len(done) / total)) if total else 0

    # done は Markdown の [x] と同期する。飛ばしたステップは done にせず、巻き戻しても先の done を残す
    for k in sorted(set(steps) | set(range(1, total + 1))):
        t = set_class(t, k, "step done" if k in done else "step")
    if a.status != "完了":
        t = set_class(t, a.step, "step current")
    t = re.sub(r"(\.progress > div \{[^}]*width: )\d+%", rf"\g<1>{pct}%", t, count=1)

    if a.figure or a.topics or a.findings:
        t = update_explain(t, a.step, a.figure, a.findings, a.topics)

    state = f"状態: 完了（全 {total} ステップ）" if a.status == "完了" else f"現在: Step {a.step} を解説中"
    t, n3 = re.subn(r"更新: [0-9\- :]+ ／ [^<]*", f"更新: {now} ／ {state}", t, count=1)
    if not n3:
        print("warning: footer の「更新: … ／ …」が見つからない", file=sys.stderr)
    open(a.html, "w", encoding="utf-8").write(t)
    print(f"ok step={a.step} done={len(done)}/{total} pct={pct} status={a.status}")


if __name__ == "__main__":
    main()
