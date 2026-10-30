#!/usr/bin/env python3
"""Extract structured text from learning materials into Markdown.

Supports .pptx (with speaker notes) and .docx using only the standard library,
.pdf via pypdf / PyMuPDF / pdfplumber / pdftotext (whichever is available),
and .md / .txt / .html. Pass a file or a directory.

Usage:
    python extract_material.py slides.pptx -o source.md
    python extract_material.py course_folder/ -o source.md
    python extract_material.py paper.pdf --max-chars 200000
"""
import argparse
import html
import os
import re
import shutil
import subprocess
import sys
import zipfile
import xml.etree.ElementTree as ET

NS = {
    "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    "p": "http://schemas.openxmlformats.org/presentationml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
    "rel": "http://schemas.openxmlformats.org/package/2006/relationships",
}
SUPPORTED = (".pptx", ".docx", ".pdf", ".md", ".markdown", ".txt", ".html", ".htm")
SPARSE_CHARS = 15  # pages with less text than this are flagged as probably image-based


def sparse_flag(text, pictures=0):
    n = len(re.sub(r"\s", "", text))
    sparse = n < SPARSE_CHARS or (pictures and n < 3 * SPARSE_CHARS)
    return "  ⚠ 文本很少，可能是图片/公式/扫描页，建议查看原页面" if sparse else ""


# ---------- pptx ----------

def _shape_paragraphs(elem):
    """Yield (level, text) for each paragraph under elem."""
    for para in elem.iter("{%s}p" % NS["a"]):
        runs = [t.text or "" for t in para.iter("{%s}t" % NS["a"])]
        text = "".join(runs).strip()
        if not text:
            continue
        ppr = para.find("a:pPr", NS)
        level = int(ppr.get("lvl", "0")) if ppr is not None else 0
        yield level, text


def _slide_order(z):
    """Return slide part paths in presentation order."""
    pres = ET.fromstring(z.read("ppt/presentation.xml"))
    rels = ET.fromstring(z.read("ppt/_rels/presentation.xml.rels"))
    rid_to_target = {r.get("Id"): r.get("Target") for r in rels.findall("rel:Relationship", NS)}
    order = []
    sld_list = pres.find("p:sldIdLst", NS)
    if sld_list is not None:
        for sld in sld_list.findall("p:sldId", NS):
            target = rid_to_target.get(sld.get("{%s}id" % NS["r"]))
            if not target:
                continue
            if target.startswith("/"):
                order.append(target.lstrip("/"))
            else:
                order.append(os.path.normpath(os.path.join("ppt", target)).replace("\\", "/"))
    if not order:  # fall back to numeric file order
        names = [n for n in z.namelist() if re.match(r"ppt/slides/slide\d+\.xml$", n)]
        order = sorted(names, key=lambda n: int(re.findall(r"\d+", n)[-1]))
    return order


def _notes_for(z, slide_path):
    rels_path = slide_path.replace("slides/", "slides/_rels/") + ".rels"
    if rels_path not in z.namelist():
        return ""
    rels = ET.fromstring(z.read(rels_path))
    for r in rels.findall("rel:Relationship", NS):
        if r.get("Type", "").endswith("/notesSlide"):
            target = os.path.normpath(os.path.join(os.path.dirname(slide_path), r.get("Target"))).replace("\\", "/")
            if target in z.namelist():
                root = ET.fromstring(z.read(target))
                texts = []
                for sp in root.iter("{%s}sp" % NS["p"]):
                    ph = sp.find(".//p:nvPr/p:ph", NS)
                    if ph is not None and ph.get("type") == "body":
                        texts.extend(t for _, t in _shape_paragraphs(sp))
                return "\n".join(texts)
    return ""


def extract_pptx(path):
    out = []
    with zipfile.ZipFile(path) as z:
        for i, slide_path in enumerate(_slide_order(z), 1):
            root = ET.fromstring(z.read(slide_path))
            title, body = "", []
            for sp in root.iter("{%s}sp" % NS["p"]):
                ph = sp.find(".//p:nvPr/p:ph", NS)
                is_title = ph is not None and ph.get("type") in ("title", "ctrTitle")
                paras = list(_shape_paragraphs(sp))
                if is_title and not title:
                    title = " ".join(t for _, t in paras)
                else:
                    body.extend(paras)
            # tables
            for tbl in root.iter("{%s}tbl" % NS["a"]):
                for tr in tbl.iter("{%s}tr" % NS["a"]):
                    cells = ["".join(t.text or "" for t in tc.iter("{%s}t" % NS["a"])).strip() for tc in tr.iter("{%s}tc" % NS["a"])]
                    body.append((0, "| " + " | ".join(cells) + " |"))
            n_pics = sum(1 for _ in root.iter("{%s}pic" % NS["p"]))
            text = "\n".join(("  " * lvl) + "- " + t if not t.startswith("|") else t for lvl, t in body)
            out.append("## [幻灯片 %d] %s%s" % (i, title or "(无标题)", sparse_flag(title + text, n_pics)))
            if text:
                out.append(text)
            if n_pics:
                out.append("_（本页含 %d 张图片）_" % n_pics)
            notes = _notes_for(z, slide_path)
            if notes:
                out.append("> **备注：** " + notes.replace("\n", "\n> "))
            out.append("")
    return "\n".join(out)


# ---------- docx ----------

def extract_docx(path):
    out = []
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    body = root.find("w:body", NS)
    for block in body:
        tag = block.tag.split("}")[1]
        if tag == "p":
            text = "".join(t.text or "" for t in block.iter("{%s}t" % NS["w"])).strip()
            if not text:
                continue
            style = block.find("w:pPr/w:pStyle", NS)
            sval = style.get("{%s}val" % NS["w"]) if style is not None else ""
            m = re.search(r"(?:Heading|标题)\s*(\d)", sval, re.I) or re.match(r"^(\d)$", sval)
            if m:
                out.append("#" * min(int(m.group(1)) + 1, 6) + " " + text)
            elif block.find("w:pPr/w:numPr", NS) is not None:
                out.append("- " + text)
            else:
                out.append(text)
        elif tag == "tbl":
            for tr in block.iter("{%s}tr" % NS["w"]):
                cells = ["".join(t.text or "" for t in tc.iter("{%s}t" % NS["w"])).strip() for tc in tr.iter("{%s}tc" % NS["w"])]
                out.append("| " + " | ".join(cells) + " |")
            out.append("")
    return "\n\n".join(out)


# ---------- pdf ----------

def _pdf_pages(path):
    """Return a list of page texts using whichever backend is installed."""
    try:
        import fitz  # PyMuPDF
        with fitz.open(path) as doc:
            return [page.get_text() for page in doc]
    except ImportError:
        pass
    try:
        from pypdf import PdfReader
        return [p.extract_text() or "" for p in PdfReader(path).pages]
    except ImportError:
        pass
    try:
        import pdfplumber
        with pdfplumber.open(path) as pdf:
            return [p.extract_text() or "" for p in pdf.pages]
    except ImportError:
        pass
    if shutil.which("pdftotext"):
        res = subprocess.run(["pdftotext", "-layout", path, "-"], capture_output=True)
        if res.returncode != 0:
            raise RuntimeError("pdftotext 失败：" + res.stderr.decode("utf-8", "replace").strip())
        pages = res.stdout.decode("utf-8", "replace").split("\f")
        return pages[:-1] if pages and not pages[-1].strip() else pages  # trailing form feed
    raise RuntimeError(
        "没有可用的 PDF 解析库。请安装其一：\n"
        "    pip install pypdf\n"
        "    pip install pymupdf   (更快，对中文和复杂排版更好)"
    )


def extract_pdf(path):
    out = []
    for i, text in enumerate(_pdf_pages(path), 1):
        text = re.sub(r"[ \t]+\n", "\n", text).strip()
        out.append("## [第 %d 页]%s" % (i, sparse_flag(text)))
        if text:
            out.append(text)
        out.append("")
    return "\n".join(out)


# ---------- plain ----------

def extract_text(path):
    with open(path, "rb") as f:
        raw = f.read()
    for enc in ("utf-8-sig", "gb18030", "latin-1"):
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    if path.lower().endswith((".html", ".htm")):
        text = re.sub(r"(?is)<(script|style).*?</\1>", "", text)
        text = re.sub(r"(?i)<br\s*/?>|</p>|</h\d>|</li>", "\n", text)
        text = html.unescape(re.sub(r"<[^>]+>", "", text))
        text = re.sub(r"\n\s*\n+", "\n\n", text)
    return text.strip()


EXTRACTORS = {".pptx": extract_pptx, ".docx": extract_docx, ".pdf": extract_pdf}


def extract(path):
    ext = os.path.splitext(path)[1].lower()
    return EXTRACTORS.get(ext, extract_text)(path)


def collect(target):
    if os.path.isdir(target):
        files = []
        for root, _, names in os.walk(target):
            files.extend(os.path.join(root, n) for n in names if n.lower().endswith(SUPPORTED) and not n.startswith("~$"))
        return sorted(files)
    return [target]


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target", help="file or directory")
    ap.add_argument("-o", "--output", help="write Markdown here (default: stdout)")
    ap.add_argument("--max-chars", type=int, default=0, help="truncate output to this many characters (0 = no limit)")
    args = ap.parse_args()
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    if not os.path.exists(args.target):
        sys.exit("找不到：%s" % args.target)

    parts, failed = [], []
    for f in collect(args.target):
        try:
            parts.append("# 📄 %s\n\n%s" % (os.path.basename(f), extract(f)))
        except Exception as e:  # keep going on other files
            failed.append((f, e))
    result = "\n\n".join(parts)
    if args.max_chars and len(result) > args.max_chars:
        result = result[: args.max_chars] + "\n\n…（已截断，共 %d 字符）" % len(result)

    if args.output:
        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "w", encoding="utf-8") as fh:
            fh.write(result)
        print("已写入 %s（%d 个文件，%d 字符）" % (args.output, len(parts), len(result)))
    else:
        print(result)
    for f, e in failed:
        print("✗ %s: %s" % (f, e), file=sys.stderr)
    if failed and not parts:
        sys.exit(1)


if __name__ == "__main__":
    main()
