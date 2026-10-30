#!/usr/bin/env python3
"""Render a pathfinder map.json into a self-contained interactive knowledge map (HTML).

Usage:
    python build_map.py learning/<slug>/map.json            # -> learning/<slug>/map.html
    python build_map.py map.json -o out.html --open
    python build_map.py map.json --check                     # validate only

The page has three views (mind map, dependency graph, route/pipeline), a detail
panel per node, and in-browser progress tracking. No CDN or network needed.
"""
import argparse
import json
import os
import sys
import webbrowser

HERE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE = os.path.join(HERE, "..", "assets", "templates", "knowledge-map.html")
PLACEHOLDER = "/*__MAP_DATA__*/null"
PRIORITIES = {"core", "important", "optional"}
STATUSES = {"todo", "learning", "mastered", "known", "skip"}


def validate(data):
    """Return (errors, warnings). Errors make the map unusable; warnings are worth fixing."""
    errors, warnings = [], []
    if not isinstance(data, dict):
        return ["顶层必须是 JSON 对象"], []
    if not data.get("topic"):
        errors.append("缺少 topic")
    nodes = data.get("nodes")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 必须是非空数组")
        return errors, warnings

    ids = set()
    for i, n in enumerate(nodes):
        if not isinstance(n, dict) or "id" not in n or "label" not in n:
            errors.append("nodes[%d] 缺少 id 或 label" % i)
            continue
        nid = str(n["id"])
        if nid in ids:
            errors.append("重复的节点 id：%s" % nid)
        ids.add(nid)
        if n.get("priority") and n["priority"] not in PRIORITIES:
            warnings.append("%s：priority 应为 %s" % (nid, "/".join(sorted(PRIORITIES))))
        if n.get("status") and n["status"] not in STATUSES:
            warnings.append("%s：status 应为 %s" % (nid, "/".join(sorted(STATUSES))))

    prereqs = {}
    for n in nodes:
        if not isinstance(n, dict) or "id" not in n:
            continue
        nid = str(n["id"])
        parent = n.get("parent")
        if parent is not None and str(parent) not in ids:
            warnings.append("%s：parent '%s' 不存在，将挂到根节点" % (nid, parent))
        pre = [str(p) for p in (n.get("prereqs") or [])]
        for p in pre:
            if p not in ids:
                warnings.append("%s：prereq '%s' 不存在，已忽略" % (nid, p))
        prereqs[nid] = [p for p in pre if p in ids and p != nid]

    # parent cycles would make the mind map recurse forever
    parents = {str(n["id"]): str(n["parent"]) for n in nodes if isinstance(n, dict) and n.get("parent") is not None and "id" in n}
    for start in parents:
        seen, cur = set(), start
        while cur in parents and cur not in seen:
            seen.add(cur)
            cur = parents[cur]
        if cur in seen:
            errors.append("parent 形成循环，涉及节点：%s" % cur)
            break

    cycle = find_cycle(prereqs)
    if cycle:
        warnings.append("prereqs 存在循环依赖：%s（依赖图会出错，请修正）" % " → ".join(cycle))

    focus = data.get("focus")
    if focus is not None and not isinstance(focus, dict):
        warnings.append("focus 应为对象，聚焦视图将不显示")
        data.pop("focus")

    for s in data.get("stages") or []:
        for nid in s.get("nodes") or []:
            if str(nid) not in ids:
                warnings.append("阶段 '%s' 引用了不存在的节点 '%s'" % (s.get("label", "?"), nid))
    return errors, warnings


def find_cycle(graph):
    color, stack = {}, []

    def dfs(u):
        color[u] = 1
        stack.append(u)
        for v in graph.get(u, []):
            if color.get(v) == 1:
                return stack[stack.index(v):] + [v]
            if color.get(v) is None:
                found = dfs(v)
                if found:
                    return found
        stack.pop()
        color[u] = 2
        return None

    for node in graph:
        if color.get(node) is None:
            found = dfs(node)
            if found:
                return found
    return None


def render(data):
    with open(TEMPLATE, encoding="utf-8") as f:
        template = f.read()
    if PLACEHOLDER not in template:
        sys.exit("模板中找不到数据占位符：%s" % PLACEHOLDER)
    # "</" would let a label like "</script>" end the script block early
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    return template.replace(PLACEHOLDER, payload)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("map_json")
    ap.add_argument("-o", "--output", help="output HTML (default: map.html next to the JSON)")
    ap.add_argument("--open", action="store_true", help="open the result in the default browser")
    ap.add_argument("--check", action="store_true", help="validate only, do not write HTML")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    try:
        with open(args.map_json, encoding="utf-8-sig") as f:
            data = json.load(f)
    except (OSError, ValueError) as e:
        sys.exit("无法读取 %s：%s" % (args.map_json, e))

    errors, warnings = validate(data)
    for w in warnings:
        print("⚠ " + w, file=sys.stderr)
    if errors:
        for e in errors:
            print("✗ " + e, file=sys.stderr)
        sys.exit(1)
    if args.check:
        print("✓ map.json 有效：%d 个节点，%d 个警告" % (len(data["nodes"]), len(warnings)))
        return

    out = args.output or os.path.join(os.path.dirname(os.path.abspath(args.map_json)), "map.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(render(data))
    print("✓ 已生成 %s（%d 个节点）" % (out, len(data["nodes"])))
    if args.open:
        webbrowser.open("file:///" + os.path.abspath(out).replace("\\", "/").lstrip("/"))


if __name__ == "__main__":
    main()
