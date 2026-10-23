"""Read local CSV and XLSX inventory files without contacting network services."""

from __future__ import annotations

import csv
import re
import zipfile
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


class InventoryError(ValueError):
    """Raised when an inventory file cannot be read as a tabular file."""


def load_inventory(path: str | Path) -> tuple[list[str], list[dict[str, str]]]:
    """Load the first worksheet of an .xlsx file or the first table in a CSV."""
    source = Path(path)
    suffix = source.suffix.lower()
    if suffix == ".csv":
        return _load_csv(source)
    if suffix == ".xlsx":
        return _load_xlsx(source)
    raise InventoryError("Choose a .csv or .xlsx file. Legacy .xls files are not supported.")


def _load_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    try:
        with path.open("r", encoding="utf-8-sig", newline="") as stream:
            sample = stream.read(8192)
            stream.seek(0)
            try:
                dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
            except csv.Error:
                dialect = csv.excel
            rows = list(csv.reader(stream, dialect))
    except (OSError, UnicodeError, csv.Error) as exc:
        raise InventoryError(f"Could not read CSV: {exc}") from exc
    return _records_from_rows(rows)


def _load_xlsx(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    ns = {
        "main": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
        "rel": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
        "pkg": "http://schemas.openxmlformats.org/package/2006/relationships",
    }
    try:
        with zipfile.ZipFile(path) as archive:
            names = set(archive.namelist())
            workbook = ET.fromstring(archive.read("xl/workbook.xml"))
            sheet = workbook.find("main:sheets/main:sheet", ns)
            if sheet is None:
                raise InventoryError("The workbook has no worksheets.")
            rel_id = sheet.attrib.get(f"{{{ns['rel']}}}id")
            rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            target = next(
                (r.attrib["Target"] for r in rels.findall("pkg:Relationship", ns)
                 if r.attrib.get("Id") == rel_id),
                None,
            )
            if not target:
                raise InventoryError("Could not locate the first worksheet.")
            sheet_path = _package_path("xl", target)
            if sheet_path not in names:
                raise InventoryError("The first worksheet is missing from the workbook.")
            shared: list[str] = []
            if "xl/sharedStrings.xml" in names:
                strings = ET.fromstring(archive.read("xl/sharedStrings.xml"))
                shared = ["".join(t.text or "" for t in item.findall(".//main:t", ns))
                          for item in strings.findall("main:si", ns)]
            root = ET.fromstring(archive.read(sheet_path))
            rows: list[list[str]] = []
            for row_node in root.findall(".//main:sheetData/main:row", ns):
                cells: dict[int, str] = {}
                for cell in row_node.findall("main:c", ns):
                    ref = cell.attrib.get("r", "")
                    index = _column_index(ref)
                    if index is None:
                        continue
                    value_node = cell.find("main:v", ns)
                    kind = cell.attrib.get("t")
                    if kind == "inlineStr":
                        value = "".join(t.text or "" for t in cell.findall(".//main:t", ns))
                    elif value_node is None:
                        value = ""
                    elif kind == "s":
                        try:
                            value = shared[int(value_node.text or "0")]
                        except (ValueError, IndexError):
                            value = ""
                    else:
                        value = value_node.text or ""
                    cells[index] = value
                if cells:
                    line = [""] * (max(cells) + 1)
                    for index, value in cells.items():
                        line[index] = value
                    rows.append(line)
    except InventoryError:
        raise
    except (OSError, zipfile.BadZipFile, KeyError, ET.ParseError, ValueError) as exc:
        raise InventoryError(f"Could not read XLSX workbook: {exc}") from exc
    return _records_from_rows(rows)


def _package_path(base: str, target: str) -> str:
    if target.startswith("/"):
        return target.lstrip("/")
    parts = base.split("/")
    for item in target.split("/"):
        if item in ("", "."):
            continue
        if item == "..":
            if parts:
                parts.pop()
        else:
            parts.append(item)
    return "/".join(parts)


def _column_index(reference: str) -> int | None:
    match = re.match(r"([A-Z]+)", reference.upper())
    if not match:
        return None
    result = 0
    for char in match.group(1):
        result = result * 26 + ord(char) - ord("A") + 1
    return result - 1


def _records_from_rows(rows: Iterable[list[str]]) -> tuple[list[str], list[dict[str, str]]]:
    materialized = [row for row in rows if any(str(value).strip() for value in row)]
    if not materialized:
        raise InventoryError("The selected file is empty.")
    headers = [str(value).strip() for value in materialized[0]]
    if not any(headers):
        raise InventoryError("The first non-empty row must contain column headers.")
    used: dict[str, int] = {}
    unique_headers: list[str] = []
    for index, header in enumerate(headers):
        name = header or f"Column {index + 1}"
        used[name] = used.get(name, 0) + 1
        unique_headers.append(name if used[name] == 1 else f"{name} ({used[name]})")
    records = []
    for row in materialized[1:]:
        padded = list(row[:len(unique_headers)]) + [""] * max(0, len(unique_headers) - len(row))
        records.append({key: str(value).strip() for key, value in zip(unique_headers, padded)})
    if not records:
        raise InventoryError("The file contains headers but no inventory rows.")
    return unique_headers, records
