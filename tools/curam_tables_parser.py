from .utils import *

# Robust parser for Curam entity HTML pages (IBM Curam Analysis Documentation).
# html_path: Path to the entity HTML file
# return: dict with parsed data
# Extract:
#     - table_name
#     - description (Table Description section)
#     - attributes (Attributes table rows)
def parse_entity_html_file(html_path: Path) -> dict:
    html = html_path.read_text(encoding="utf-8", errors="ignore")
    soup = BeautifulSoup(html, "html.parser")

    # -----------------------------
    # 1) Table name
    # -----------------------------
    table_name = None
    header_candidates = soup.find_all(string=re.compile(r"\bDatabase\s+Table\s*:", re.IGNORECASE))
    if header_candidates:
        parent_text = header_candidates[0].parent.get_text(" ", strip=True) if header_candidates[0].parent else header_candidates[0]
        m = re.search(r"Database\s+Table\s*:\s*(.+)$", parent_text, re.IGNORECASE)
        if m:
            table_name = m.group(1).strip()
    if not table_name:
        table_name = html_path.stem

    # -----------------------------
    # helper: find the nearest "next table" after a section title
    # -----------------------------
    def find_section_by_title_exact(title: str):
        # match exact visible text
        return soup.find(lambda tag: tag.name in ("td", "th", "div", "span")
                         and tag.get_text(strip=True) == title)

    def find_next_table_after(node):
        """From a section-title node, find the nearest following table."""
        if not node:
            return None
        # Try: next tables in document order
        return node.find_next("table")

    # -----------------------------
    # 2) Table Description
    # -----------------------------
    description = ""
    desc_title_node = find_section_by_title_exact("Table Description")

    # "Table Description" is a section bar，and content is in the next table
    desc_table = find_next_table_after(desc_title_node)

    if desc_table:
        # Usually the first row is the section header, and the rest contains description text
        # Grab all text in the table, but exclude the title itself.
        text = desc_table.get_text(" ", strip=True)
        # Remove duplicated title if present
        text = re.sub(r"^Table Description\s*", "", text).strip()
        description = re.sub(r"\s+", " ", text).strip()

    # If still empty, try fallback: find the first bold label line under description area
    if not description and desc_title_node:
        container = desc_title_node.find_parent("table") or desc_title_node.find_parent("div")
        if container:
            description = container.get_text("\n", strip=True)

    # -----------------------------
    # 3) Attributes table (Curam specific DOM)
    # -----------------------------
    attributes: list[dict] = []

    # The real attributes data is under: div#wrapAtts table.nested-table
    wrap_atts = soup.find("div", id="wrapAtts")
    nested = wrap_atts.find("table", class_="nested-table") if wrap_atts else None

    if nested:
        # Header row uses <td class="heading"> (NOT <th>)
        header_tr = nested.find("thead").find("tr") if nested.find("thead") else None
        header_cells = header_tr.find_all("td") if header_tr else []
        headers = [re.sub(r"\s+", " ", c.get_text(" ", strip=True)).strip() for c in header_cells]
        col_idx = {h: i for i, h in enumerate(headers)}

        def norm_cell_text(td) -> str:
            # Turn &nbsp into empty string, collapse whitespace
            txt = td.get_text(" ", strip=True)
            txt = txt.replace("\xa0", " ")  # nbsp
            txt = re.sub(r"\s+", " ", txt).strip()
            return "" if txt in {"&nbsp;"} else txt

        body = nested.find("tbody")
        if body:
            for tr in body.find_all("tr", class_=re.compile(r"listValue(Odd|Even)")):
                tds = tr.find_all("td")
                if not tds:
                    continue

                def get_col(name: str) -> str:
                    i = col_idx.get(name, -1)
                    if i < 0 or i >= len(tds):
                        return ""
                    return norm_cell_text(tds[i])

                # Attribute name column: first col typically has <a id="...">name</a>
                attr_name = get_col("Attribute")
                if not attr_name:
                    continue

                attributes.append({
                    "name": attr_name,
                    "stereotype": get_col("Stereotype"),
                    "nullable": get_col("Nullable"),
                    "description": get_col("Description"),
                    "domain_definition": get_col("Domain Definition"),
                    "codetable": get_col("Codetable"),
                    "ddl_type": get_col("DDL Type"),
                })

    return {
        "table_name": table_name,
        "description": description,
        "attributes": attributes,
        "source_file": str(html_path),
    }


# Convert parsed table record to LLM context string
# record: parsed table record dict
# return: formatted string suitable for LLM prompt context
def table_to_llm_context(record: dict) -> str:
    table_name = record.get("table_name", "").strip()
    desc = (record.get("description") or "").strip()
    attrs = []

    for a in record.get("attributes", []):
        aname = (a.get("name") or "").strip()
        astereotype = (a.get("stereotype") or "").strip()
        anullable = (a.get("nullable") or "").strip()
        adesc = (a.get("description") or "").strip()
        adomain_def = (a.get("domain_definition") or "").strip()
        acodetable = (a.get("codetable") or "").strip()
        addl_type = (a.get("ddl_type") or "").strip()

        if not aname:
            continue
        attrs.append((aname, adesc, astereotype, anullable, adomain_def, acodetable, addl_type))

    lines = []
    lines.append(f"Table: {table_name}\n")
    if desc:
        lines.append(f"Description: {desc}\n")
    else:
        lines.append("Description: (empty)\n")

    lines.append("Attributes: \n")
    if not attrs:
        lines.append("(none)\n")
    else:
        for name, adesc, astereotype, anullable, adomain_def, acodetable, addl_type in attrs:
            lines.append(f"name: {name} \nstereotype: {astereotype} \nnullable: {anullable} \ndescription: {adesc} \ndomain_definition: {adomain_def} \ncodetable: {acodetable} \nddl_type: {addl_type}")

    return "\n".join(lines)


# Convert parsed table record to LLM context minimum essential structure
def build_llm_ready_record(record: dict) -> dict:
    table_name = (record.get("table_name") or "").strip()
    desc = (record.get("description") or "").strip()
    desc = re.sub(r"\s+", " ", desc).strip()

    attrs_min = []
    for a in record.get("attributes", []):
        aname = (a.get("name") or "").strip()
        astereotype = (a.get("stereotype") or "").strip()
        anullable = (a.get("nullable") or "").strip()
        adesc = (a.get("description") or "").strip()
        adomain_def = (a.get("domain_definition") or "").strip()
        acodetable = (a.get("codetable") or "").strip()
        addl_type = (a.get("ddl_type") or "").strip()

        if not aname:
            continue
        attrs_min.append({
            "name": aname,
            "description": adesc,
            "stereotype": astereotype,
            "nullable": anullable,
            "domain_definition": adomain_def,
            "codetable": acodetable,
            "ddl_type": addl_type
        })

    return {
        "table_name": table_name,
        "table_description": desc,
        "attributes": attrs_min
    }


# Validate LLM-ready record
# llm_record: LLM-ready record dict
# return: list of warning messages, empty if all valid
def validate_llm_record(llm_record: dict) -> list[str]:
    warnings = []
    tn = (llm_record.get("table_name") or "").strip()

    if not tn:
        warnings.append("missing table_name")

    # description nullable, but if both description and attributes are empty, likely a parse failure
    desc = (llm_record.get("table_description") or "").strip()
    attrs = llm_record.get("attributes") or []
    if not desc and not attrs:
        warnings.append("empty description AND empty attributes")

    # attributes list validation
    if not isinstance(attrs, list):
        warnings.append("attributes not a list")
    else:
        for idx, a in enumerate(attrs[:5]):  # check first 5 only
            if not isinstance(a, dict):
                warnings.append(f"attribute[{idx}] not a dict")
                break
            if not (a.get("name") or "").strip():
                warnings.append(f"attribute[{idx}] missing name")
                break

    # llm_context format check
    ctx = (llm_record.get("llm_context") or "").strip()
    if not ctx.startswith("Table:"):
        warnings.append("llm_context does not start with 'Table:'")

    return warnings


# Thread worker function: parse one HTML file to llm_record
# fp: Path to the HTML file
# return: (file_path_str, llm_record, error, warnings)
def _parse_one_file_to_llm_record(fp: Path) -> tuple[str, dict | None, str | None, list[str] | None]:
    try:
        parsed = parse_entity_html_file(fp)
        llm_record = build_llm_ready_record(parsed)
        llm_record["llm_context"] = table_to_llm_context(parsed)

        warnings = validate_llm_record(llm_record)
        return str(fp), llm_record, None, warnings

    except Exception as e:
        return str(fp), None, str(e), None


def parse_all_entities_to_jsonl_parallel(
    entities_dir: Path,
    out_jsonl: Path = Path("data/curam_tables_llm.jsonl"),
    out_errors_csv: Path = Path("data/parse_errors.csv"),
    out_warnings_csv: Path = Path("data/parse_warnings.csv"),
    limit: int | None = None,
    max_workers: int | None = None,
    log_every: int = 10,
    keep_order: bool = True
) -> tuple[int, int]:
    """
    Batch parse all entity HTML files in a directory to JSONL using multithreading
    - entities_dir: directory containing entity HTML files
    - out_jsonl: output JSONL file path
    - out_errors_csv: output CSV file path for parse errors
    - out_warnings_csv: output CSV file path for validation warnings
    - limit: (optional) limit on number of files to parse
    - max_workers: (optional) number of threads to use
    - log_every: log progress every N files
    - keep_order: whether to keep the original file order in output JSONL

    - return: (success_count, error_count)
    """
    out_jsonl.parent.mkdir(parents=True, exist_ok=True)
    out_errors_csv.parent.mkdir(parents=True, exist_ok=True)
    out_warnings_csv.parent.mkdir(parents=True, exist_ok=True)

    html_files = sorted(entities_dir.glob("*.html"))

    if limit is not None:
        html_files = html_files[:limit]


    total = len(html_files)
    if total == 0:
        print(f"[WARN] No html files found under: {entities_dir.resolve()}")
        return 0, 0

    # default number of threads: typically 8-32 works well for IO + parsing mixed tasks
    if max_workers is None:
        cpu = os.cpu_count() or 8
        max_workers = min(32, max(8, cpu * 2))

    print(f"[START] Parallel parsing {total} files | workers={max_workers} | keep_order={keep_order}")
    print(f"[OUT]   JSONL -> {out_jsonl.resolve()}")
    print(f"[OUT]   ERR   -> {out_errors_csv.resolve()}")
    print(f"[OUT]   WARN  -> {out_warnings_csv.resolve()}")

    t0 = time.time()

    # results stashed by index
    # key: index -> llm_record
    index_by_path = {str(fp): i for i, fp in enumerate(html_files)}
    results: dict[int, dict] = {}
    errors: list[tuple[str, str]] = []
    warnings_rows: list[tuple[str, str]] = []

    done = 0
    ok = 0

    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = [ex.submit(_parse_one_file_to_llm_record, fp) for fp in html_files]

        for fut in as_completed(futures):
            path_str, llm_record, err, warns = fut.result()
            done += 1

            if err is not None:
                errors.append((path_str, err))
            else:
                ok += 1
                if keep_order:
                    results[index_by_path[path_str]] = llm_record  # type: ignore[assignment]
                else:
                    results[done - 1] = llm_record  # type: ignore[assignment]

                if warns:
                    warnings_rows.append((path_str, "; ".join(warns)))

            if (done % log_every == 0) or (done == total):
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] {done}/{total} | ok={ok} | err={len(errors)} | {rate:.1f} files/sec")

    # write JSONL: single-threaded, reproducible order
    with out_jsonl.open("w", encoding="utf-8") as jf:
        if keep_order:
            for i in range(total):
                rec = results.get(i)
                if rec is None:
                    continue
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")
        else:
            for _, rec in sorted(results.items(), key=lambda x: x[0]):
                jf.write(json.dumps(rec, ensure_ascii=False) + "\n")

    # write errors / warnings
    if errors:
        with out_errors_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "error"])
            w.writerows(errors)

    if warnings_rows:
        with out_warnings_csv.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["file", "warnings"])
            w.writerows(warnings_rows)

    elapsed = time.time() - t0
    print(f"[DONE] ok={ok} err={len(errors)} warn={len(warnings_rows)} time={elapsed:.1f}s")

    return ok, len(errors)


def preview_one_llm_context(entities_dir: Path, pick_name: str | None = None):
    """
    Randomly or specifically pick a table, print out the llm_context, for you to visually confirm if the format is suitable for the prompt.
    
    :param entities_dir: path to the directory containing entity HTML files
    :type entities_dir: Path
    :param pick_name: (optional) specific HTML file name to pick; if None, pick a random one
    :type pick_name: str | None
    """
    if pick_name:
        fp = entities_dir / pick_name
        if not fp.exists():
            raise FileNotFoundError(f"Not found: {fp}")
    else:
        candidates = list(entities_dir.glob("*.html"))
        if not candidates:
            raise FileNotFoundError(f"No html files under: {entities_dir}")
        fp = random.choice(candidates)

    parsed = parse_entity_html_file(fp)
    ctx = table_to_llm_context(parsed)
    print("\n==================== LLM CONTEXT PREVIEW ====================")
    print(ctx)
    print("=============================================================\n")


def split_jsonl_to_individual_json(
    jsonl_path: Path,
    out_dir: Path,
    filename_field: str = "table_name",
    overwrite: bool = True,
    clean_out_dir: bool = True,
) -> int:
    """Split a JSONL file into one JSON file per table."""
    if not jsonl_path.exists():
        raise FileNotFoundError(f"JSONL not found: {jsonl_path.resolve()}")

    out_dir.mkdir(parents=True, exist_ok=True)

    if clean_out_dir:
        for path in out_dir.glob("*.json"):
            try:
                path.unlink()
            except Exception as error:
                print(f"[WARN] failed to delete {path}: {error}")

    written = 0
    with jsonl_path.open("r", encoding="utf-8") as source:
        for line_number, line in enumerate(source, start=1):
            line = line.strip()
            if not line:
                continue

            try:
                record = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON on line {line_number}: {error}") from error

            name = (record.get(filename_field) or "").strip()
            if not name:
                raise ValueError(f"Missing '{filename_field}' on line {line_number}")

            safe_name = re.sub(r"[^\w\-\.]", "_", name)
            output_path = out_dir / f"{safe_name}.json"

            if output_path.exists() and not overwrite:
                continue

            with output_path.open("w", encoding="utf-8") as destination:
                json.dump(record, destination, ensure_ascii=False, indent=2)

            written += 1

    print(f"[OK] Split {written} tables into JSON files -> {out_dir.resolve()}")
    return written


def iter_json_files(tables_dir: Path) -> list[Path]:
    return sorted([p for p in tables_dir.glob("*.json") if p.is_file()])


def strip_llm_context(obj: dict) -> dict:
    """
    Return a copy of obj with 'llm_context' removed (if exists).
    """
    # shallow copy is enough here
    cleaned = dict(obj)
    cleaned.pop("llm_context", None)
    return cleaned


def json_to_pretty_text(obj: dict) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2)


def bundle_tables_to_word(
    tables_dir: Path,
    out_dir: Path,
    batch_size: int = 20,
    *,
    remove_llm_context: bool = True,
    save_clean_json_dir: Path | None = None,
    clean_out_dir: bool = True,
) -> None:
    """
    Read per-table JSON files under tables_dir, optionally remove 'llm_context',
    then bundle them into multiple Word documents (batch_size tables per doc).

    Args:
        tables_dir: directory containing per-table *.json files
        out_dir: output directory for .docx batches
        batch_size: number of tables per Word file (e.g., 15-20)
        remove_llm_context: whether to remove 'llm_context' field
        save_clean_json_dir: if provided, also write cleaned JSON copies here
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    if save_clean_json_dir is not None:
        save_clean_json_dir.mkdir(parents=True, exist_ok=True)

    # Clear stale .docx from previous runs so out_dir reflects only this run's batches.
    if clean_out_dir:
        for p in out_dir.glob("*.docx"):
            try:
                p.unlink()
            except Exception as e:
                print(f"[WARN] failed to delete {p}: {e}")

    files = iter_json_files(tables_dir)
    if not files:
        raise FileNotFoundError(f"No JSON files found in: {tables_dir.resolve()}")

    total = len(files)

    def chunked(items: list[Path], n: int) -> Iterable[list[Path]]:
        for i in range(0, len(items), n):
            yield items[i : i + n]

    for batch_idx, batch in enumerate(chunked(files, batch_size), start=1):
        start_no = (batch_idx - 1) * batch_size + 1
        end_no = start_no + len(batch) - 1

        doc = Document()
        doc.add_heading(f"Curam Tables Batch {start_no:03d}-{end_no:03d}", level=1)
        doc.add_paragraph(f"Source dir: {str(tables_dir)}")
        doc.add_paragraph(f"Tables in batch: {len(batch)} / Total: {total}")
        doc.add_paragraph("")

        for i, fp in enumerate(batch, start=1):
            raw = json.loads(fp.read_text(encoding="utf-8"))
            cleaned = strip_llm_context(raw) if remove_llm_context else raw

            # (Optional) save cleaned JSON copies
            if save_clean_json_dir is not None:
                out_json_path = save_clean_json_dir / fp.name
                out_json_path.write_text(
                    json.dumps(cleaned, ensure_ascii=False, indent=2),
                    encoding="utf-8",
                )

            table_name = cleaned.get("table_name") or fp.stem

            # Clear separators help Copilot avoid mixing tables
            doc.add_paragraph("============================================================")
            doc.add_heading(f"{i}. {table_name}", level=2)
            doc.add_paragraph(f"Source file: {fp.name}")
            doc.add_paragraph("------------------------------------------------------------")

            # Put JSON as plain text
            doc.add_paragraph(json_to_pretty_text(cleaned))

            doc.add_paragraph("")  # spacing

        out_path = out_dir / f"curam_tables_{start_no:03d}_{end_no:03d}.docx"
        doc.save(out_path)
        print(f"[OK] Wrote {out_path.name} ({len(batch)} tables)")


def _mappings_to_text(mappings: list[dict]) -> str:
    """
    Convert mapping list into a readable multi-line string for Excel cells.
    """
    if not mappings:
        return ""
    lines = []
    for m in mappings:
        curam = (m.get("curam_attribute") or "").strip()
        fhir = (m.get("fhir_path") or "").strip()
        notes = (m.get("notes") or "").strip()

        target = (m.get("extension_target") or "").strip()
        usage = (m.get("suggested_extension_usage") or "").strip()
        example = (m.get("example_fhir_path") or "").strip()

        # Native mapping style
        if fhir or notes:
            lines.append(f"{curam} -> {fhir or '(null)'} | {notes}".strip())
        # Extension mapping style
        elif target or usage or example:
            lines.append(
                f"{curam} | target={target} | usage={usage} | path={example}"
            )
        else:
            lines.append(json.dumps(m, ensure_ascii=False))

    return "\n".join(lines)


def _candidates_to_text(candidates: list[dict]) -> str:
    """
    Convert candidate_resources_considered into a readable multi-line string.
    """
    if not candidates:
        return ""
    lines = []
    for c in candidates:
        resource = (c.get("resource") or "").strip()
        decision = (c.get("decision") or "").strip()
        reason = (c.get("reason") or "").strip()
        lines.append(f"{resource} [{decision}] | {reason}".strip())
    return "\n".join(lines)


def _reference_learning_to_text(ref: dict | None) -> str:
    """
    Convert reference_learning_applied object into a readable multi-line string.
    """
    if not ref:
        return ""
    used = ref.get("used_reference")
    matched = ref.get("matched_reference_tables") or []
    pattern = (ref.get("learned_pattern") or "").strip()
    diff = (ref.get("differences_from_reference") or "").strip()
    return "\n".join([
        f"used_reference={used}",
        f"matched_reference_tables={', '.join(matched) if matched else '(none)'}",
        f"learned_pattern={pattern}",
        f"differences_from_reference={diff}",
    ])


def _quality_checks_to_text(checks: dict | None) -> str:
    """
    Convert quality_checks object into a readable multi-line string.
    """
    if not checks:
        return ""
    return "\n".join(f"{k}={v}" for k, v in checks.items())


# Column order for the mapping assessment Excel export.
_EXCEL_COLUMNS = [
    "source_file",
    "source_table_index",
    "table_name",
    "data_domain",
    "data_domain_confidence",
    "data_domain_rationale",
    "match_type",
    "fhir_target_resource",
    "fhir_target_path",
    "embedded_fhir_structure_used",
    "candidate_resources_considered",
    "native_mappings",
    "extension_required_mappings",
    "reference_learning_applied",
    "quality_checks",
    "overall_notes",
]


def json_to_excel(
    json_path: Path,
    xlsx_path: Path,
    sheet_name: str = "results",
) -> None:
    data = json.loads(json_path.read_text(encoding="utf-8"))

    rows = []
    for item in data:
        rows.append({
            "source_file": item.get("source_file", ""),
            "source_table_index": item.get("source_table_index", ""),
            "table_name": item.get("table_name", ""),
            "data_domain": item.get("data_domain", ""),
            "data_domain_confidence": item.get("data_domain_confidence", ""),
            "data_domain_rationale": item.get("data_domain_rationale", ""),
            "match_type": item.get("match_type", ""),
            "fhir_target_resource": item.get("fhir_target_resource", ""),
            "fhir_target_path": item.get("fhir_target_path", ""),
            "embedded_fhir_structure_used": item.get("embedded_fhir_structure_used", "") or "",
            "candidate_resources_considered": _candidates_to_text(item.get("candidate_resources_considered") or []),
            "native_mappings": _mappings_to_text(item.get("native_mappings") or []),
            "extension_required_mappings": _mappings_to_text(item.get("extension_required_mappings") or []),
            "reference_learning_applied": _reference_learning_to_text(item.get("reference_learning_applied")),
            "quality_checks": _quality_checks_to_text(item.get("quality_checks")),
            "overall_notes": item.get("overall_notes", ""),
        })

    xlsx_path.parent.mkdir(parents=True, exist_ok=True)
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = sheet_name
    worksheet.append(_EXCEL_COLUMNS)
    for row in rows:
        worksheet.append([row.get(column, "") for column in _EXCEL_COLUMNS])

    header_font = Font(bold=True)
    wrap = Alignment(wrap_text=True, vertical="top")
    col_widths = {
        "source_file": 26,
        "source_table_index": 12,
        "table_name": 24,
        "data_domain": 16,
        "data_domain_confidence": 14,
        "data_domain_rationale": 50,
        "match_type": 14,
        "fhir_target_resource": 22,
        "fhir_target_path": 24,
        "embedded_fhir_structure_used": 32,
        "candidate_resources_considered": 50,
        "native_mappings": 50,
        "extension_required_mappings": 50,
        "reference_learning_applied": 45,
        "quality_checks": 32,
        "overall_notes": 50,
    }
    for index, column_name in enumerate(_EXCEL_COLUMNS, start=1):
        letter = get_column_letter(index)
        worksheet.column_dimensions[letter].width = col_widths.get(column_name, 24)
        header_cell = worksheet.cell(row=1, column=index)
        header_cell.font = header_font
        header_cell.alignment = wrap
    for row in worksheet.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = wrap
    worksheet.freeze_panes = "A2"
    workbook.save(xlsx_path)