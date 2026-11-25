#!/usr/bin/env python3
"""Собрать проектные документы из Markdown в самостоятельные LaTeX и PDF."""

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
        "id": "DOC-03", "version": "1.0", "date": "25.11.2026",
        "title": "План управления конфигурацией программного обеспечения", "author": "Самбьюи А.Ж.",
        "change": "Уточнены управление изменениями, состояния, трассировка, выпуск, восстановление и сборка из Markdown. Подготовлено к проверке.",
        "sources": ["03_ПУКПО_План_управления_конфигурацией/DOC-03_ПУКПО.md"],
    },
    {
        "id": "DOC-02", "version": "1.1", "date": "20.11.2026",
        "title": "Техническое задание", "author": "Анохин Г.А.",
        "change": "Определены права преподавателя на группы, подтверждение группы студента через МИФИ, время проведения контрольной и условия повторного прохождения.",
        "sources": ["02_Техническое_задание/DOC-02_Техническое_задание.md"],
    },
    {
        "id": "DOC-05", "version": "1.2", "date": "25.11.2026",
        "title": "Системные требования к учебной платформе",
        "author": "Анохин Г.А.",
        "change_author": "Самбьюи А.Ж.",
        "change": "Уточнены условия проверки SR-CFG-001–008 и SR-SYS-011–015; сохранены ID, роли, сроки и численные показатели.",
        "sources": ["04_Системные_требования/DOC-05_Системные_требования.md",
                    "04_Системные_требования/Сессии_задач.md",
                    "04_Системные_требования/Интеграция.md",
                    "04_Системные_требования/Ранцевые_задачи.md",
                    "04_Системные_требования/Платформенные_и_предметные_требования.md"],
    },
    {
        "id": "DOC-06", "version": "1.3", "date": "25.11.2026", "title": "Сводные программные требования",
        "author": "Анохин Г.А.",
        "change_author": "Самбьюи А.Ж.",
        "change": "Включено приложение Б: проект физической модели PostgreSQL, ER-диаграммы, поля, типы, ограничения и связи таблиц с API.",
        "sources": ["07_Программные_требования/DOC-06_Программные_требования.md",
                    "07_Программные_требования/Программные_требования_платформы.md",
                    "07_Программные_требования/Конфигурации_и_модерация.md",
                    "07_Программные_требования/Модель_данных.md"],
    },
    {
        "id": "DOC-06.6", "version": "1.0", "date": "25.11.2026",
        "title": "Шаблоны наборов задач и модерация", "author": "Самбьюи А.Ж.",
        "change": "Подготовлен кандидат v1.0; сверены модель, API, кейсы и трассировка, уточнены права подготовки банка и черновика. Принятие ожидается.",
        "sources": ["07_Программные_требования/DOC-06.6_Конфигурации_и_модерация.md",
                    "07_Программные_требования/Конфигурации_и_модерация.md"],
    },
    {
        "id": "DOC-06.2", "version": "1.0", "date": "20.11.2026", "title": "Сессии задач и планировщик",
        "author": "Анохин Г.А.",
        "change": "Переработаны требования к жизненному циклу сессии, восстановлению и контрактам операций.",
        "sources": ["07_Программные_требования/DOC-06.2_Сессии_задач_и_планировщик.md",
                    "07_Программные_требования/Контракты_сессий.md"],
    },
    {
        "id": "DOC-06.3", "version": "1.0", "date": "21.11.2026", "title": "Ранцевые криптосистемы",
        "author": "Георгиев Д.Д.", "change_author": "Георгиев Д.Д.",
        "change": "Согласована редакция 0.9, унифицирована терминология; выпуск версии 1.0.",
        "sources": ["07_Программные_требования/DOC-06.3_Ранцевые_криптосистемы.md"],
    },
    {
        "id": "DOC-07", "version": "1.0", "date": "21.11.2026", "title": "Архитектура ПО",
        "author": "Анохин Г.А.", "change_author": "Георгиев Д.Д.",
        "change": "Редакция от 20.11.2026 согласована владельцем документа; версия 1.0 выпущена.",
        "sources": ["09_Архитектура_и_API/DOC-07_Архитектура.md"],
    },
    {
        "id": "DOC-08", "version": "1.2", "date": "25.11.2026",
        "title": "Справочник API учебной платформы", "author": "Анохин Г.А.",
        "change_author": "Самбьюи А.Ж.",
        "change": "Актуализирован статус авторского исправления TC-CFG-008 в DOC-10; контракты операций сохранены.",
        "sources": ["09_Архитектура_и_API/DOC-08_Справочник_API.md",
                    "09_Архитектура_и_API/DOC-08_API_сессий.md"],
    },
    {
        "id": "DOC-10", "version": "1.1", "date": "25.11.2026",
        "title": "План верификации программного обеспечения", "author": "Анохин Г.А.",
        "change_author": "Самбьюи А.Ж.",
        "change": "Уточнены собственные кейсы CFG и инфраструктуры: роли, чтение на границах срока, публикация, повторы и восстановление. Исполнение не проводилось.",
        "sources": ["10_Верификация_и_тестирование/DOC-10_План_верификации.md",
                    "10_Верификация_и_тестирование/DOC-10_Верификация_сессий.md"],
    },
    {
        "id": "DOC-13.5", "version": "0.3", "date": "25.11.2026",
        "title": "Протокол формальной инспекции архитектуры и API", "author": "Анохин Г.А.",
        "change_author": "Самбьюи А.Ж.",
        "change": "Сохранена исходная сверка от 20.11, добавлены материалы повторного разбора двух авторских исправлений; решение участников ожидается.",
        "sources": ["08_Протоколы_формальных_инспекций/DOC-13.5_Протокол_ФИ-АРХ-API.md"],
    },
    {
        "id": "Методика ID", "version": "0.4", "date": "20.11.2026", "title": "Методика идентификаторов",
        "author": "Анохин Г.А.",
        "change": "Уточнены границы доменов для мероприятий и личных сессий с сохранением действующих обозначений.",
        "sources": ["02_Общие_соглашения/Методика_идентификаторов.md"],
    },
    {
        "id": "Глоссарий", "version": "0.4", "date": "20.11.2026", "title": "Глоссарий",
        "author": "Анохин Г.А.",
        "change": "Различены группа студента и управляемые группы преподавателя, повторное прохождение, срок контрольной и срок практики.",
        "sources": ["02_Общие_соглашения/Глоссарий.md"],
    },
    {
        "id": "Карточка домена", "version": "0.4", "date": "20.11.2026", "title": "Карточка домена: сессии задач",
        "author": "Анохин Г.А.",
        "change": "Описаны автоматическое закрытие мероприятия, срок личной сессии и повторное прохождение по настройке преподавателя.",
        "sources": ["03_Карточки_доменов/Сессии_задач.md"],
    },
    {
        "id": "Вклад DOC-09", "version": "0.1", "date": "25.11.2026",
        "title": "Вклад Самбьюи в матрицу трассировки", "author": "Самбьюи А.Ж.",
        "change": "Подготовлены связи 13 собственных SR с реальными SWR/TC; общая матрица остаётся за редактором.",
        "sources": ["05_Трассировка/DOC-09_Вклад_Самбьюи.md"],
    },
    {
        "id": "DOC-13.4", "version": "0.1", "date": "25.11.2026",
        "title": "Пакет подготовки ФИ-SWR", "author": "Самбьюи А.Ж.",
        "change": "Подготовлены комплект, план ролей, вопросы и форма записи итогов; заседание не подтверждено.",
        "sources": ["08_Протоколы_формальных_инспекций/DOC-13.4_Подготовка_ФИ-SWR.md"],
    },
    {
        "id": "DOC-13.6", "version": "0.1", "date": "25.11.2026",
        "title": "Пакет секретаря ФИ-TRACE+VER", "author": "Самбьюи А.Ж.",
        "change": "Подготовлены зависимости, вопросы и форма протокола; полный объект инспекции и заседание ожидаются.",
        "sources": ["08_Протоколы_формальных_инспекций/DOC-13.6_Подготовка_ФИ-TRACE-VER.md"],
    },
]
ROOT_EXPORTS = {
    "DOC-03": "03_ПУКПО_План_управления_конфигурацией/ПУКПО.pdf",
    "DOC-02": "02_Техническое_задание/Техническое_задание.pdf",
    "DOC-05": "04_Системные_требования/DOC-05_Системные_требования.pdf",
    "DOC-06": "07_Программные_требования/DOC-06_Программные_требования.pdf",
    "DOC-06.6": "07_Программные_требования/DOC-06.6_Конфигурации_и_модерация.pdf",
    "DOC-06.2": "07_Программные_требования/DOC-06.2_Сессии_задач_и_планировщик.pdf",
    "DOC-06.3": "07_Программные_требования/DOC-06.3_Ранцевые_криптосистемы.pdf",
    "DOC-07": "09_Архитектура_и_API/DOC-07_Архитектура.pdf",
    "DOC-08": "09_Архитектура_и_API/DOC-08_Справочник_API.pdf",
    "DOC-10": "10_Верификация_и_тестирование/DOC-10_План_верификации.pdf",
    "DOC-13.5": "08_Протоколы_формальных_инспекций/DOC-13.5_Протокол_ФИ-АРХ-API.pdf",
    "Вклад DOC-09": "05_Трассировка/DOC-09_Вклад_Самбьюи.pdf",
    "DOC-13.4": "08_Протоколы_формальных_инспекций/DOC-13.4_Подготовка_ФИ-SWR.pdf",
    "DOC-13.6": "08_Протоколы_формальных_инспекций/DOC-13.6_Подготовка_ФИ-TRACE-VER.pdf",
    "Методика ID": "notes/methodology/Методика_идентификаторов.pdf",
    "Глоссарий": "notes/methodology/Глоссарий.pdf",
    "Карточка домена": "notes/domains/Сессии_задач.pdf",
}


def run(command, **kwargs):
    return subprocess.run(command, check=True, text=True, encoding="utf-8", **kwargs)


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


def html_anchor(node):
    if node.get("t") == "RawInline" and node["c"][0] == "html":
        match = re.fullmatch(r'<a id="([a-z0-9-]+)">', node["c"][1])
        if match:
            return match[1]


def latex_inline(text):
    return {"t": "RawInline", "c": ["latex", text]}


def standalone_anchor(block):
    if block.get("t") == "Para":
        inlines = block["c"]
        if len(inlines) == 2 and inlines[1].get("c") == ["html", "</a>"]:
            return html_anchor(inlines[0])


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
        return relative + "#" + anchor
    if dest.suffix == ".tex" and dest.with_suffix(".pdf").exists():
        return Path(os.path.relpath(dest.with_suffix(".pdf"), pdf_path(document).parent)).as_posix()
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
    if result.get("t") == "Image":
        attrs, label, address = result["c"]
        asset = (origin.parent / unquote(address[0])).resolve()
        if not asset.is_relative_to(REPO) or not asset.exists():
            raise ValueError("Не найдено изображение в репозитории: " + address[0])
        if asset.with_suffix(".pdf").exists():
            asset = asset.with_suffix(".pdf")
        address[0] = Path(os.path.relpath(asset, pdf_path(document).parent)).as_posix()
    if result.get("t") == "Link":
        attrs, label, address = result["c"]
        target = remap_link(address[0], origin, document, owners, headings)
        if urlsplit(target).scheme or target.startswith("//"):
            address[0] = target
        else:
            # File links in PDF use file-system paths and destination names, not URL fragments.
            if target.startswith("#"):
                opening = r"\hyperlink{" + escape(target[1:]) + "}{"
            else:
                opening = r"\href{" + escape(target) + "}{"
            return {"t": "Span", "c": [attrs, [latex_inline(opening), *label, latex_inline("}")]]}
    anchor = html_anchor(result)
    if anchor:
        return latex_inline(r"\hypertarget{" + anchor + "}{}")
    if result.get("t") == "Code":
        literal = result["c"][1]
        if len(literal) > 10 and (any(char in literal for char in "/.-_") or re.search(r"[a-z][A-Z]", literal)):
            wrapped = "".join((r"\allowbreak{}" if i and char.isupper() and literal[i-1].islower() else "")
                              + escape(char) + (r"\allowbreak{}" if char in "/.?=-_" else "")
                              for i, char in enumerate(literal))
            return {"t": "RawInline", "c": ["latex", r"\texttt{" + wrapped + "}"]}
    if result.get("t") == "Table":
        table = result["c"]
        count = len(table[2])
        original_table = value["c"]
        rows = list(original_table[3][1])
        for group in original_table[4]:
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
    parser.add_argument("--pdflatex", help="Собрать PDF через указанный pdfLaTeX вместо Tectonic")
    parser.add_argument("--tex-only", action="store_true")
    parser.add_argument("--root-copies", action="store_true",
                        help="Также обновить .tex и .pdf в исходных корневых папках")
    parser.add_argument("--only", nargs="+", choices=[doc["id"] for doc in DOCUMENTS],
                        help="Собрать только перечисленные документы")
    args = parser.parse_args()
    pandoc = shutil.which(args.pandoc)
    tectonic = shutil.which(args.tectonic)
    pdflatex = shutil.which(args.pdflatex) if args.pdflatex else None
    if args.pdflatex and not pdflatex:
        parser.error("Не найден pdfLaTeX: " + args.pdflatex)
    if not pandoc or (not args.tex_only and not (tectonic or pdflatex)):
        parser.error("Нужны Pandoc и Tectonic либо pdfLaTeX через --pandoc, --tectonic, --pdflatex")
    build = ROOT / ".build"
    build.mkdir(exist_ok=True)
    template = (ROOT / "latex/document.tex").read_text(encoding="utf-8")
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
        if args.only and document["id"] not in args.only:
            continue
        # A shared chapter is internal when it belongs to the current assembled document.
        document_owners = dict(group_owners)
        definition_anchors = set()
        for source in document["sources"]:
            path = (ROOT / source).resolve()
            document_owners[path] = document
            source_blocks = asts[path]["blocks"]
            for block_index, block in enumerate(source_blocks):
                if block.get("t") == "Header" and block_index:
                    alias = standalone_anchor(source_blocks[block_index - 1])
                    if alias:
                        definition_anchors.add(alias)
        combined = None
        for position, source in enumerate(document["sources"]):
            path = (ROOT / source).resolve()
            ast = copy.deepcopy(asts[path])
            blocks = []
            for block_index, block in enumerate(ast["blocks"]):
                if block["t"] != "Header":
                    alias = standalone_anchor(block)
                    next_is_header = (block_index + 1 < len(ast["blocks"])
                                      and ast["blocks"][block_index + 1].get("t") == "Header")
                    # Preserve Markdown compatibility anchors, but let the printed definition
                    # own the destination when both sources occur in one PDF.
                    if alias in definition_anchors and not next_is_header:
                        continue
                    blocks.append(block)
                    continue
                level, attributes, inlines = block["c"]
                attributes[0] = slug(inline_text(inlines))
                destinations = [attributes[0]]
                # A Markdown anchor preceding a heading belongs on the same printed page.
                alias = standalone_anchor(blocks[-1]) if blocks else None
                if alias:
                    blocks.pop()
                    destinations.append(alias)
                if position != 0 or level != 1:
                    block["c"][0] = max(1, level - 1) if position == 0 else level
                    if inlines and inlines[0]["t"] == "Str" and re.fullmatch(r"\d+(?:\.\d+)*\.", inlines[0]["c"]):
                        block["c"][2] = inlines[2:] if len(inlines) > 1 and inlines[1]["t"] == "Space" else inlines[1:]
                    blocks.append(block)
                for name in destinations:
                    blocks.append({"t": "RawBlock", "c": ["latex", r"\hypertarget{" + name + "}{}"]})
            ast["blocks"] = transform(blocks, path, document, document_owners, headings)
            if combined is None:
                combined = ast
            else:
                combined["blocks"].extend(ast["blocks"])
        body = run([pandoc, "-f", "json", "-t", "latex", "--wrap=none", "--no-highlight"], input=json.dumps(combined, ensure_ascii=False), capture_output=True).stdout
        values = {"TITLE": document["title"], "DOCID": document["id"], "VERSION": document["version"],
                  "DATE": document.get("date", DATE), "AUTHOR": document.get("author", "Анохин Г.А."),
                  "CHANGE_AUTHOR": document.get("change_author", document["author"]),
                  "CHANGE": document.get("change", "Уточнены правила и контракты; расширено описание сценариев; подготовлена печатная редакция.")}
        tex = template
        for key, value in values.items():
            tex = tex.replace("@@" + key + "@@", escape(value))
        tex = tex.replace("@@BODY@@", body)
        tex = "% Источники: " + ", ".join(document["sources"]) + "\n% Генератор: docs/build_pdf.py\n" + tex
        target = pdf_path(document).with_suffix(".tex")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(tex, encoding="utf-8")
        if not args.tex_only:
            outdir = build / ("pdf-" + str(index))
            outdir.mkdir(exist_ok=True)
            if pdflatex:
                # ASCII staging names avoid Windows TeX filename-encoding limitations.
                # Printed TeX keeps portable paths; the ASCII staging file resolves images
                # against the printed file's directory while compiling from the build folder.
                staged_tex = re.sub(r"(\\includegraphics(?:\[[^\]]*\])?)\{([^}]+)\}",
                                    lambda match: match[1] + "{" + (target.parent / match[2]).resolve().as_posix() + "}", tex)
                (outdir / "document.tex").write_text(staged_tex, encoding="utf-8")
                for name in ("document.aux", "document.toc", "document.out"):
                    (outdir / name).unlink(missing_ok=True)
                for attempt in range(1, 5):
                    result = subprocess.run([pdflatex, "-interaction=nonstopmode", "-halt-on-error",
                                             "-no-shell-escape", "document.tex"], cwd=outdir,
                                            text=True, encoding="utf-8", errors="replace",
                                            stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                    (outdir / f"pass-{attempt}.txt").write_text(result.stdout, encoding="utf-8")
                    if result.returncode:
                        print(result.stdout)
                        raise SystemExit("Не собран " + target.name)
                    log = (outdir / "document.log").read_text(encoding="utf-8", errors="replace")
                    if attempt >= 2 and not re.search(r"Rerun to get|Rerun .* right|rerun LaTeX", log):
                        break
                else:
                    raise SystemExit("Не стабилизировались ссылки: " + target.name)
                if re.search(r"undefined references|Reference .* undefined|Missing character", log):
                    raise SystemExit("Не разрешены ссылки или символы: " + target.name)
                compiled_pdf = outdir / "document.pdf"
            else:
                result = subprocess.run([tectonic, "--keep-logs", "--outdir", str(outdir), target.name], cwd=target.parent,
                                        text=True, encoding="utf-8", errors="replace",
                                        stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
                (outdir / "build-output.txt").write_text(result.stdout, encoding="utf-8")
                if result.returncode:
                    print(result.stdout)
                    raise SystemExit("Не собран " + target.name)
                compiled_pdf = outdir / target.with_suffix(".pdf").name
            shutil.copyfile(compiled_pdf, pdf_path(document))
        if "root_pdf" in document and document["id"] == "DOC-05":
            alias = REPO / "04_Системные_требования/Системные_требования.tex"
            shutil.copyfile(target, alias)
            if not args.tex_only:
                shutil.copyfile(pdf_path(document), alias.with_suffix(".pdf"))
        report.append({"id": document["id"], "tex": str(target.relative_to(REPO)),
                       "pdf": str(pdf_path(document).relative_to(REPO)), "sources": document["sources"]})
        print(document["id"] + ": " + str(target.relative_to(REPO)), flush=True)
    (build / "documents.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
