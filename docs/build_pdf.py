#!/usr/bin/env python3
"""Собрать шесть документов из Markdown: самостоятельные LaTeX и PDF."""

import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import quote, unquote, urlsplit

ROOT = Path(__file__).resolve().parent
REPO = ROOT.parent
DATE = "07.11.2026"
DOCUMENTS = [
    {
        "id": "DOC-05", "version": "0.4",
        "title": "Системные требования. Сессии, интеграция и ранцевые задачи",
        "author": "Анохин Г.А.",
        "sources": ["04_Системные_требования/DOC-05_Системные_требования.md",
                    "04_Системные_требования/Сессии_задач.md",
                    "04_Системные_требования/Интеграция.md",
                    "04_Системные_требования/Ранцевые_задачи.md"],
    },
    {
        "id": "DOC-06", "version": "0.6", "title": "Сводные программные требования",
        "author": "Анохин Г.А.",
        "sources": ["07_Программные_требования/DOC-06_Программные_требования.md"],
    },
    {
        "id": "DOC-06.2", "version": "0.9", "title": "Сессии задач и планировщик",
        "author": "Анохин Г.А.",
        "sources": ["07_Программные_требования/DOC-06.2_Сессии_задач_и_планировщик.md",
                    "07_Программные_требования/Контракты_сессий.md"],
    },
    {
        "id": "DOC-06.3", "version": "0.8", "title": "Ранцевые криптосистемы",
        "author": "Георгиев Д.Д.",
        "change": "Подготовлена первая редакция подсистемных требований; трассировка на SR-KNAP; зафиксированы известные особенности реализации.",
        "sources": ["07_Программные_требования/DOC-06.3_Ранцевые_криптосистемы.md"],
    },
    {
        "id": "DOC-07", "version": "0.5", "title": "Архитектура ПО",
        "author": "Георгиев Д.Д.",
        "change": "Подготовлен проект архитектуры: слои, компоненты и связи, развёртывание, соответствие требованиям.",
        "sources": ["09_Архитектура_и_API/DOC-07_Архитектура.md"],
    },
    {
        "id": "Методика ID", "version": "0.3", "title": "Методика идентификаторов",
        "author": "Анохин Г.А.",
        "sources": ["02_Общие_соглашения/Методика_идентификаторов.md"],
    },
    {
        "id": "Глоссарий", "version": "0.3", "title": "Глоссарий",
        "author": "Анохин Г.А.",
        "sources": ["02_Общие_соглашения/Глоссарий.md"],
    },
    {
        "id": "Карточка домена", "version": "0.3", "title": "Карточка домена: сессии задач",
        "author": "Анохин Г.А.",
        "sources": ["03_Карточки_доменов/Сессии_задач.md"],
    },
]
ROOT_EXPORTS = {
    "DOC-05": "04_Системные_требования/DOC-05_Системные_требования.pdf",
    "DOC-06": "07_Программные_требования/DOC-06_Программные_требования.pdf",
    "DOC-06.2": "07_Программные_требования/DOC-06.2_Сессии_задач_и_планировщик.pdf",
    "DOC-06.3": "07_Программные_требования/DOC-06.3_Ранцевые_криптосистемы.pdf",
    "DOC-07": "09_Архитектура_и_API/DOC-07_Архитектура.pdf",
    "Методика ID": "notes/methodology/Методика_идентификаторов.pdf",
    "Глоссарий": "notes/methodology/Глоссарий.pdf",
    "Карточка домена": "notes/domains/Сессии_задач.pdf",
}


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, **kwargs)


def escape(text):
    replacements = {"\\": r"\textbackslash{}", "&": r"\&", "%": r"\%",
                    "$": r"\$", "#": r"\#", "_": r"\_", "{": r"\{",
                    "}": r"\}", "~": r"\textasciitilde{}", "^": r"\textasciicircum{}"}
    return "".join(replacements.get(char, char) for char in text)


def inline_text(nodes):
    pieces = []
    for node in nodes:
        kind = node.get("t")
        if kind == "Str":
            pieces.append(node["c"])
        elif kind in ("Space", "SoftBreak", "LineBreak"):
            pieces.append(" ")
        elif kind == "Code":
            pieces.append(node["c"][1])
        elif kind in ("Emph", "Strong", "Strikeout"):
            pieces.append(inline_text(node["c"]))
    return "".join(pieces)


def slug(title):
    return re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")


def pdf_path(document):
    if "root_pdf" in document:
        return REPO / document["root_pdf"]
    return (ROOT / document["sources"][0]).with_suffix(".pdf")


def remap_link(target, origin, document, owners, headings):
    parsed = urlsplit(target)
    if parsed.scheme or target.startswith("//"):
        return target
    dest = (origin.parent / unquote(parsed.path)).resolve() if parsed.path else origin
    fragment = unquote(parsed.fragment)
    owner = owners.get(dest)
    if owner:
        anchor = fragment or headings[dest]
        if owner["id"] == document["id"]:
            return "#" + anchor
        relative = Path(os.path.relpath(pdf_path(owner), pdf_path(document).parent)).as_posix()
        return quote(relative) + "#nameddest=" + quote(anchor)
    if dest.suffix == ".tex" and dest.with_suffix(".pdf").exists():
        return quote(Path(os.path.relpath(dest.with_suffix(".pdf"), pdf_path(document).parent)).as_posix())
    try:
        relative = dest.relative_to(REPO).as_posix()
    except ValueError:
        raise ValueError("Ссылка за пределы репозитория: " + target)
    return "https://github.com/Kokorev-VD/mephi-samolety/blob/main/" + quote(relative) + ("#" + quote(fragment) if fragment else "")


def transform(value, origin, document, owners, headings):
    if isinstance(value, list):
        return [transform(v, origin, document, owners, headings) for v in value]
    if not isinstance(value, dict):
        return value
    result = {k: transform(v, origin, document, owners, headings) for k, v in value.items()}
    if result.get("t") == "Link":
        result["c"][2][0] = remap_link(result["c"][2][0], origin, document, owners, headings)
    if result.get("t") == "Code":
        literal = result["c"][1]
        if len(literal) > 18 and not re.search(r"\s", literal):
            wrapped = "".join(escape(char) + (r"\allowbreak{}" if char in "/.-_" else "") for char in literal)
            return {"t": "RawInline", "c": ["latex", r"\texttt{" + wrapped + "}"]}
    if result.get("t") == "Table":
        table = result["c"]
        count = len(table[2])
        rows = list(table[3][1])
        for group in table[4]:
            rows.extend(group[2])
            rows.extend(group[3])

        def words(node):
            if isinstance(node, list):
                return " ".join(words(n) for n in node)
            if not isinstance(node, dict):
                return ""
            if node.get("t") == "Str":
                return node["c"]
            if node.get("t") == "Code":
                return node["c"][1]
            return words(node.get("c", []))

        if count == 2:
            widths = [0.32, 0.68]
        elif count == 3 and rows and "HTTP" in words(rows[0][1][0][-1]):
            widths = [0.10, 0.34, 0.56]
        else:
            sizes = [math.sqrt(max(20, sum(len(words(row[1][i][-1])) for row in rows if len(row[1]) == count) / max(1, len(rows)))) for i in range(count)]
            total = sum(sizes)
            widths = [n / total for n in sizes]
        for spec, width in zip(table[2], widths):
            spec[1] = {"t": "ColWidth", "c": width}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pandoc", default=os.environ.get("PANDOC", "pandoc"))
    parser.add_argument("--tectonic", default=os.environ.get("TECTONIC", "tectonic"))
    parser.add_argument("--tex-only", action="store_true")
    parser.add_argument("--root-copies", action="store_true",
                        help="Также обновить .tex и .pdf в исходных корневых папках")
    args = parser.parse_args()
    pandoc = shutil.which(args.pandoc)
    tectonic = shutil.which(args.tectonic)
    if not pandoc or (not args.tex_only and not tectonic):
        parser.error("Нужны Pandoc и Tectonic в PATH либо пути через --pandoc и --tectonic")
    build = ROOT / ".build"
    build.mkdir(exist_ok=True)
    template = (ROOT / "latex/document.tex").read_text()
    asts, owners, headings = {}, {}, {}
    for document in DOCUMENTS:
        for source in document["sources"]:
            path = (ROOT / source).resolve()
            ast = json.loads(run([pandoc, "-f", "markdown-smart", "-t", "json", str(path)], capture_output=True).stdout)
            asts[path] = ast
            owners[path] = document
            title = next(block for block in ast["blocks"] if block["t"] == "Header" and block["c"][0] == 1)
            headings[path] = slug(inline_text(title["c"][2]))
    jobs = [(document, owners) for document in DOCUMENTS]
    if args.root_copies:
        root_documents = [{**document, "root_pdf": ROOT_EXPORTS[document["id"]]} for document in DOCUMENTS]
        root_owners = {(ROOT / source).resolve(): document
                       for document in root_documents for source in document["sources"]}
        jobs.extend((document, root_owners) for document in root_documents)
    report = []
    for index, (document, group_owners) in enumerate(jobs):
        combined = None
        for position, source in enumerate(document["sources"]):
            path = (ROOT / source).resolve()
            ast = copy.deepcopy(asts[path])
            blocks = []
            for block in ast["blocks"]:
                if block["t"] == "Header":
                    level, attributes, inlines = block["c"]
                    attributes[0] = slug(inline_text(inlines))
                    if level == 1 and position == 0:
                        blocks.append({"t": "RawBlock", "c": ["latex", r"\hypertarget{" + attributes[0] + "}{}"]})
                        continue
                    block["c"][0] = max(1, level - 1) if position == 0 else level
                    if inlines and inlines[0]["t"] == "Str" and re.fullmatch(r"\d+\.", inlines[0]["c"]):
                        block["c"][2] = inlines[2:] if len(inlines) > 1 and inlines[1]["t"] == "Space" else inlines[1:]
                blocks.append(block)
                if block["t"] == "Header":
                    blocks.append({"t": "RawBlock", "c": ["latex", r"\hypertarget{" + block["c"][1][0] + "}{}"]})
            ast["blocks"] = transform(blocks, path, document, group_owners, headings)
            if combined is None:
                combined = ast
            else:
                combined["blocks"].extend(ast["blocks"])
        body = run([pandoc, "-f", "json", "-t", "latex", "--wrap=none", "--no-highlight"], input=json.dumps(combined, ensure_ascii=False), capture_output=True).stdout
        values = {"TITLE": document["title"], "DOCID": document["id"], "VERSION": document["version"],
                  "DATE": DATE, "AUTHOR": document.get("author", "Анохин Г.А."),
                  "CHANGE": document.get("change", "Уточнены правила и контракты; расширено описание сценариев; подготовлена печатная редакция.")}
        tex = template
        for key, value in values.items():
            tex = tex.replace("@@" + key + "@@", escape(value))
        tex = tex.replace("@@BODY@@", body)
        tex = "% Источники: " + ", ".join(document["sources"]) + "\n% Генератор: docs/build_pdf.py\n" + tex
        target = pdf_path(document).with_suffix(".tex")
        target.write_text(tex)
        if not args.tex_only:
            outdir = build / ("pdf-" + str(index))
            outdir.mkdir(exist_ok=True)
            result = subprocess.run([tectonic, "--keep-logs", "--outdir", str(outdir), target.name], cwd=target.parent,
                                    text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            (outdir / "build-output.txt").write_text(result.stdout)
            if result.returncode:
                print(result.stdout)
                raise SystemExit("Не собран " + target.name)
            shutil.copyfile(outdir / target.with_suffix(".pdf").name, pdf_path(document))
        if "root_pdf" in document and document["id"] == "DOC-05":
            alias = REPO / "04_Системные_требования/Системные_требования.tex"
            shutil.copyfile(target, alias)
            if not args.tex_only:
                shutil.copyfile(pdf_path(document), alias.with_suffix(".pdf"))
        report.append({"id": document["id"], "tex": str(target.relative_to(REPO)),
                       "pdf": str(pdf_path(document).relative_to(REPO)), "sources": document["sources"]})
        print(document["id"] + ": " + str(target.relative_to(REPO)), flush=True)
    (build / "documents.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
