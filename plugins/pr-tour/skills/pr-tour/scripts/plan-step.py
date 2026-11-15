# -*- coding: utf-8 -*-
"""pr-tour のステップ進行を 1 コマンドで反映する。

Markdown（正）と HTML（俯瞰）の 2 ファイルを毎ステップ手で直すと、どちらかを忘れて
文脈要約後に位置を失う。このスクリプトは両方を同時に更新する。

使い方:
  # ステップ k の解説を終えたとき（現在位置を k にする）
  python3 plan-step.py <plan.md> <plan.html> --step k \
      [--figure fig.html [fig2.html]] [--topics "論点1" ...] [--findings "#2 CONFIRMED file:line 要点" ...] \
      [--total-steps M] [--status 完了]

  # 現在位置を変えずに、ステップ m へ指摘・論点・図を追記するとき（後から届いた指摘など）
  python3 plan-step.py <plan.md> <plan.html> --annotate m [--findings ...] [--topics ...] [--figure fig.html]

  # プランを書いた直後に、全ステップの「見る場所」を HTML に反映するとき（Phase 4-8）
  python3 plan-step.py <plan.md> <plan.html> --sync

  # このテンプレートより前に作った HTML に、見る場所・拡大表示・パスのコピーの仕組みを差し込むとき（再開時など）
  python3 plan-step.py <plan.md> <plan.html> --upgrade

やること:
  --step k
    1. plan.md の「- 現在のステップ:」を k に、「- [ ] Step k:」を「- [x] Step k:」にする
    2. plan.html の各ステップの done を plan.md の [x] と同期する（Markdown が正）。
       飛ばしたステップは done にならず、巻き戻しても先の done は消えない。#step-k を current にする
    3. 進捗率は [x] の数 / 全ステップ数。footer の「更新: … ／ 現在: …」を書き換える
    4. Step k の「見る場所」を HTML に反映して「確定」の印を付け、チャットにそのまま貼る
       「### 見る場所」の Markdown を標準出力に出す
  --annotate m
    plan.md の現在位置と [x]、HTML の done / current と進捗率には触れず、#step-m だけを更新する
    （見る場所も同期する。「確定」の印は変えない）
  --sync
    全ステップの「見る場所」を HTML に反映する。plan.md・ステップの状態・図には触れない
  見る場所の書式（plan.md。1 範囲 1 行の子箇条書き。パスはリポジトリ相対のフルパス）:
    - 見る場所:
      - 📖 `src/routes/orders.ts:12-20` — ルートとハンドラの結線
      - ✏️ `src/handlers/cancel-order.ts:88-95` — 入力検証の追加
    タグは 📖 既存 / ✏️ 変更 / 🆕 新規 / 🧪 テスト。旧書式（1 行に「 / 」区切り、理由は（）書き）も読む。
    読めない行は warning を出し、そのステップの HTML の見る場所は変えない
  共通（#step-N の <details class="explain"> の中身）
    --figure があれば図の部分だけを差し替える（1 ステップ 2 枚まで。並べて渡す）。--findings / --topics は既存の箇条書きに追記する
    （同じ文言は重ねない）。指定しなかった部分（既存の図・指摘・論点）はそのまま残す
  --status 完了 なら plan.md の状態を完了にし、HTML の current を外して footer を完了表記にする
  --upgrade
    assets/plan-view.html の id="pr-tour-*" の <style> / <script> をすべて plan.html に差し込む（既にあれば
    差し替える）。plan.md・ステップの状態・図には触れない。何度実行しても結果は同じ

HTML 側の前提: assets/plan-view.html の構造（article.step#step-N と details.explain）。
更新後に fig.py --check で SVG の整形式を確認してから Artifact を再公開する。
"""
import argparse
import datetime as dt
import html
import re
import sys
from pathlib import Path

FINDINGS_RE = re.compile(r'<ul class="findings">(.*?)</ul>\n?', re.S)
TOPICS_RE = re.compile(r'<p class="topics">チャットで議論した論点: (.*?)</p>\n?', re.S)
TEMPLATE = Path(__file__).resolve().parent.parent / "assets" / "plan-view.html"
BLOCK_RE = re.compile(r'<(style|script) id="(pr-tour-[\w-]+)">.*?</\1>\n?', re.S)
MAX_FIGURES = 2

# 見る場所のタグ: 絵文字 → (表示, class, 語)
TAGS = {"📖": ("📖", "ctx", "既存"), "✏": ("✏️", "mod", "変更"), "🆕": ("🆕", "new", "新規"), "🧪": ("🧪", "test", "テスト")}
LOC_RE = re.compile(r"^(📖|✏\ufe0f?|🆕|🧪)\s*`([^`]+)`\s*(?:(?:—|–|：|:|-)\s*(.+?)|（(.+?)）|\((.+?)\))?\s*$")
OLD_SPLIT = re.compile(r"\s*(?:/|、)\s*(?=(?:📖|✏|🆕|🧪))")


def merge_items(existing, new, tag):
    """既存の <li>/<span> の列に、まだ無い文言だけを足す。"""
    items = re.findall(rf"<{tag}>(.*?)</{tag}>", existing, re.S)
    for x in new:
        e = html.escape(x)
        if e not in items:
            items.append(e)
    return items


def update_explain(t, step, figure, findings, topics):
    pat = re.compile(rf'(<article class="[^"]*" id="step-{step}">(?:(?!</article>).)*?<details class="explain"[^>]*><summary>)[^<]*(</summary>)(.*?)(</details>)', re.S)
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
        rest = "\n".join(open(f, encoding="utf-8").read().strip() for f in figure)

    body = "\n" + (rest + "\n" if rest else "")
    f_items = merge_items(old_findings, findings, "li")
    if f_items:
        body += '<ul class="findings">' + "".join(f"<li>{x}</li>" for x in f_items) + "</ul>\n"
    t_items = merge_items(old_topics, topics, "span")
    if t_items:
        body += '<p class="topics">チャットで議論した論点: ' + "".join(f"<span>{x}</span>" for x in t_items) + "</p>\n"
    return t[: m.start()] + m.group(1) + "図解" + m.group(2) + body + m.group(4) + t[m.end():]


def template_blocks():
    tpl = TEMPLATE.read_text(encoding="utf-8")
    blocks = [(m.group(1), m.group(2), m.group(0)) for m in BLOCK_RE.finditer(tpl)]
    if not blocks:
        sys.exit(f"error: テンプレートに id=\"pr-tour-*\" のブロックが見つからない: {TEMPLATE}")
    return blocks


def missing_blocks(t):
    return [bid for kind, bid, _ in template_blocks() if f'<{kind} id="{bid}">' not in t]


def upgrade(t):
    """テンプレートの id="pr-tour-*" ブロックを t に差し込む（あれば差し替える）。"""
    for kind, bid, block in template_blocks():
        pat = re.compile(rf'<{kind} id="{bid}">.*?</{kind}>\n?', re.S)
        if pat.search(t):
            t = pat.sub(lambda _: block, t, count=1)
        elif kind == "style":
            # 本文より前にある最後の <style> の直後に置く
            body = t.find('<div class="wrap">')
            j = t.rfind("</style>", 0, body if body >= 0 else len(t))
            j = j + len("</style>\n") if j >= 0 else 0
            t = t[:j] + block + t[j:]
        else:
            # 末尾のテンプレート説明コメントの前、無ければ末尾に置く
            j = t.rfind("\n<!--")
            j = j + 1 if j > t.rfind("</footer>") >= 0 else len(t)
            t = t[:j] + block + t[j:]
    return t


def inline(s):
    """エスケープしたうえで `…` を <code> にする。"""
    return re.sub(r"`([^`]+)`", r"<code>\1</code>", html.escape(s))


def parse_locations(md, k):
    """plan.md の Step k の「見る場所」を [(タグ, パス, 説明)] で返す。欄が無ければ None。
    2 つ目の戻り値は読めなかった行。"""
    head = re.search(rf"^- \[[ x]\] Step {k}:.*$", md, re.M)
    if not head:
        return None, []
    nxt = re.compile(r"^(?:- \[[ x]\] Step \d+:|#)", re.M).search(md, head.end())
    block = md[head.end(): nxt.start() if nxt else len(md)]
    m = re.search(r"^([ \t]*)- 見る場所:[ \t]*(.*)$", block, re.M)
    if not m:
        return None, []
    indent, rest = len(m.group(1)), m.group(2).strip()
    if rest:
        raw = [x.strip() for x in OLD_SPLIT.split(rest) if x.strip()]
    else:
        raw = []
        for line in block[m.end():].splitlines():
            if not line.strip():
                continue
            lm = re.match(r"^([ \t]*)- (.*)$", line)
            if not lm or len(lm.group(1)) <= indent:
                break
            raw.append(lm.group(2).strip())
    locs, bad = [], []
    for r in raw:
        x = LOC_RE.match(r)
        if not x:
            bad.append(r)
            continue
        key = "✏" if x.group(1).startswith("✏") else x.group(1)
        why = next((g for g in x.group(3, 4, 5) if g), "")
        locs.append((key, x.group(2), why.strip()))
    return locs, bad


def div_end(t, start):
    """t[start] から始まる <div> の、対応する </div> の直後の位置を返す。"""
    depth = 0
    for m in re.compile(r"<div\b|</div>").finditer(t, start):
        depth += 1 if m.group(0) == "<div" else -1
        if depth == 0:
            return m.end()
    return len(t)


def sync_files(t, k, locs, confirm=False):
    """#step-k の <div class="files"> を locs から作り直す。無ければ title の直後に置く。"""
    am = re.search(rf'<article class="[^"]*" id="step-{k}">', t)
    if not am:
        print(f"warning: HTML に #step-{k} が無い。見る場所は反映されなかった", file=sys.stderr)
        return t
    aend = t.find("</article>", am.end())
    aend = aend if aend >= 0 else len(t)
    rows = []
    for key, path, why in locs:
        emoji, cls, word = TAGS[key]
        w = f'<span class="why">{inline(why)}</span>' if why else ""
        rows.append(f'<div class="loc"><span class="tag {cls}">{emoji} {word}</span><code>{html.escape(path)}</code>{w}</div>')
    fm = re.compile(r'<div class="files"([^>]*)>').search(t, am.end(), aend)
    keep = confirm or bool(fm and "data-confirmed" in fm.group(1))
    block = f'<div class="files"{" data-confirmed" if keep else ""}>\n' + "\n".join(rows) + "\n</div>"
    if fm:
        return t[: fm.start()] + block + t[div_end(t, fm.start()):]
    tm = re.compile(r'<div class="title"').search(t, am.end(), aend)
    pos = div_end(t, tm.start()) if tm else am.end()
    return t[:pos] + "\n" + block + t[pos:]


def sync_step(t, md, k, confirm=False):
    locs, bad = parse_locations(md, k)
    for b in bad:
        print(f"warning: Step {k} の見る場所を読めない行: {b}", file=sys.stderr)
    if locs is None:
        print(f"warning: Step {k} に「見る場所:」欄が無い。HTML の見る場所は変えていない", file=sys.stderr)
        return t, None
    if bad or not locs:
        if not bad:
            print(f"warning: Step {k} の見る場所が空。HTML の見る場所は変えていない", file=sys.stderr)
        return t, None
    return sync_files(t, k, locs, confirm), locs


def chat_block(locs):
    lines = ["### 見る場所"]
    for key, path, why in locs:
        lines.append(f"- {TAGS[key][0]} `{path}`" + (f" — {why}" if why else ""))
    return "\n".join(lines)


def set_class(t, k, cls):
    return re.sub(rf'<article class="step[^"]*" id="step-{k}">', f'<article class="{cls}" id="step-{k}">', t, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("md")
    ap.add_argument("html")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--step", type=int, help="解説を終えたステップ。現在位置をここにする")
    g.add_argument("--annotate", type=int, help="現在位置を変えずに追記するステップ")
    g.add_argument("--sync", action="store_true", help="全ステップの見る場所を plan.md から HTML に反映する")
    g.add_argument("--upgrade", action="store_true", help="見る場所・拡大表示・パスのコピーの仕組みをテンプレートから差し込む")
    ap.add_argument("--figure", nargs="+", help=f"fig.py の出力 HTML ファイル。{MAX_FIGURES} 枚まで")
    ap.add_argument("--topics", nargs="*", default=[])
    ap.add_argument("--findings", nargs="*", default=[], help="code-review の指摘。1 件 1 引数")
    ap.add_argument("--total-steps", type=int)
    ap.add_argument("--status", choices=["進行中", "完了"], default="進行中")
    a = ap.parse_args()
    if a.step is None and a.status == "完了":
        ap.error("--status 完了 は --step と一緒に使う")
    if a.figure and len(a.figure) > MAX_FIGURES:
        ap.error(f"図は 1 ステップ {MAX_FIGURES} 枚まで（渡されたのは {len(a.figure)} 枚）")

    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    t = open(a.html, encoding="utf-8").read()

    if a.upgrade:
        t = upgrade(t)
        open(a.html, "w", encoding="utf-8").write(t)
        print("ok upgrade（見る場所・拡大表示・パスのコピーのブロックを反映。ステップの状態は変更なし）")
        return
    miss = missing_blocks(t)
    if miss:
        print(f"warning: 古い HTML（{', '.join(miss)} が無い）。--upgrade で差し込める", file=sys.stderr)

    if a.sync:
        md = open(a.md, encoding="utf-8").read()
        steps = [int(n) for n in re.findall(r"^- \[[ x]\] Step (\d+):", md, flags=re.M)]
        n = 0
        for k in steps:
            t, locs = sync_step(t, md, k)
            n += locs is not None
        open(a.html, "w", encoding="utf-8").write(t)
        print(f"ok sync（見る場所を {n}/{len(steps)} ステップに反映）")
        return

    if a.annotate is not None:
        t, _ = sync_step(t, open(a.md, encoding="utf-8").read(), a.annotate)
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

    t, locs = sync_step(t, md, a.step, confirm=True)
    if a.figure or a.topics or a.findings:
        t = update_explain(t, a.step, a.figure, a.findings, a.topics)

    state = f"状態: 完了（全 {total} ステップ）" if a.status == "完了" else f"現在: Step {a.step} を解説中"
    t, n3 = re.subn(r"更新: [0-9\- :]+ ／ [^<]*", f"更新: {now} ／ {state}", t, count=1)
    if not n3:
        print("warning: footer の「更新: … ／ …」が見つからない", file=sys.stderr)
    open(a.html, "w", encoding="utf-8").write(t)
    print(f"ok step={a.step} done={len(done)}/{total} pct={pct} status={a.status}")
    if locs:
        print("\n--- チャットの「見る場所」（このまま貼る） ---")
        print(chat_block(locs))


if __name__ == "__main__":
    main()
