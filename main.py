import argparse

from tools.utils import *
from tools.curam_tables_downloader import *
from tools.curam_tables_parser import *


DEFAULT_WHITELIST = Path("white_list_csv/Curam_FHIR_Feasibility_Assessment_Batch1_2.csv")
DEFAULT_ASSESSMENT_DIR = Path("data/Curam_FHIR_Feasibility_Assessment_Batch1_2")
DEFAULT_BATCH_SIZE = 35


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download Curam table definitions and build Word batches for FHIR mapping."
    )
    parser.add_argument(
        "--whitelist",
        type=Path,
        help="CSV containing Curam table names in the first column. Prompts when omitted.",
    )
    parser.add_argument(
        "--assessment-dir",
        type=Path,
        help="Assessment folder where Word batches will be written. Prompts when omitted.",
    )
    parser.add_argument(
        "--whitelist-has-header",
        action="store_true",
        default=None,
        help="Skip the first CSV row when it contains a header. Prompts when omitted.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        help="Number of Curam tables per Word batch. Prompts when omitted.",
    )
    return parser.parse_args()


def prompt_path(label: str, default: Path) -> Path:
    value = input(
        f"{label} (default: {default}, press Enter to use default): "
    ).strip()
    return Path(value.strip('"')) if value else default


def prompt_yes_no(label: str, default: bool = False) -> bool:
    default_hint = "no" if not default else "yes"
    while True:
        value = input(
            f"{label} (yes/no, default: {default_hint}, press Enter to use default): "
        ).strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print("Please enter yes or no.")


def prompt_positive_int(label: str, default: int) -> int:
    while True:
        value = input(
            f"{label} (default: {default}, press Enter to use default): "
        ).strip()
        if not value:
            return default
        try:
            number = int(value)
        except ValueError:
            print("Please enter a whole number greater than zero.")
            continue
        if number > 0:
            return number
        print("Please enter a whole number greater than zero.")


def prompt_for_missing_args(args: argparse.Namespace) -> argparse.Namespace:
    if args.whitelist is None:
        args.whitelist = prompt_path("Insert whitelist CSV path", DEFAULT_WHITELIST)
    if args.assessment_dir is None:
        args.assessment_dir = prompt_path(
            "Insert assessment output directory", DEFAULT_ASSESSMENT_DIR
        )
    if args.whitelist_has_header is None:
        args.whitelist_has_header = prompt_yes_no(
            "Does the whitelist CSV have a header row?"
        )
    if args.batch_size is None:
        args.batch_size = prompt_positive_int(
            "Insert number of tables per Word batch", DEFAULT_BATCH_SIZE
        )
    return args


def print_mapping_next_steps(
    assessment_dir: Path,
    word_batches_dir: Path,
) -> None:
    reference_workbook = assessment_dir / "assessment_result_for_referrence.xlsx"

    print()
    print(f"[READY] Word batches for Copilot mapping: {word_batches_dir.resolve()}")
    print()
    print("[NEXT] Continue the mapping task in VS Code Copilot Chat:")
    if reference_workbook.exists():
        print(f"[OK] Reference workbook found: {reference_workbook.resolve()}")
    else:
        print("[ACTION REQUIRED] Add the reviewed reference workbook here:")
        print(f"  {reference_workbook.resolve()}")
    print()
    print("1. Open Copilot Chat and select the custom agent: curam-fhir-planner")
    print("   Prompt:")
    print("   Inspect the active assessment, verify the reference workbook and all Word batches,")
    print("   initialize mapping_progress.json and tables_json.json, and provide the execution")
    print("   plan. Do not map yet.")
    print()
    print("2. After the planner finishes, select the custom agent: curam-fhir-orchestrator")
    print("   Prompt:")
    print("   Process all remaining Word files from mapping_progress.json. If a file is pending")
    print("   review, review it first. For each remaining Word file, invoke curam-fhir-mapper")
    print("   to map exactly one file, run scripts/validate_mapping_json.py, then invoke")
    print("   curam-fhir-reviewer. Continue this mapper-validator-reviewer loop automatically")
    print("   until every Word file is reviewed and mapping_progress.json has status complete.")
    print("   Stop only on a validator failure, reviewer failure, blocked status, or another")
    print("   hard-stop error, and report the exact failure without advancing to the next file.")
    print()
    print("[IMPORTANT] Start the orchestrator only after the planner confirms the assessment")
    print("is ready_for_mapping or ready_for_next_file. No manual agent switching is required.")
    print()
    print(f"[OUTPUT] Mapping results will be written to: {(assessment_dir / 'tables_json.json').resolve()}")


if __name__ == "__main__":
    args = prompt_for_missing_args(parse_args())
    whitelist_csv_path = args.whitelist
    assessment_dir = args.assessment_dir
    assessment_dir.mkdir(parents=True, exist_ok=True)

    allowed_ids = load_allowed_ids_from_csv(
        whitelist_csv_path,
        col_index=curam_tablename_idx,
        has_header=args.whitelist_has_header,
    )

    download_all_tables_parallel(
        index_url=INDEX_URL,
        base_url=BASE_URL,
        out_dir=OUT_DIR,
        delay_sec=0.15,
        timeout_sec=30,
        cookie=cookie,
        allowed_ids=allowed_ids,
        max_workers=12,
    )

    downloaded_files = sorted(OUT_DIR.glob("*.html"))
    if len(downloaded_files) != len(allowed_ids):
        raise RuntimeError(
            f"Expected {len(allowed_ids)} downloaded tables, found {len(downloaded_files)}. "
            "Check the whitelist names, network access, and download errors before continuing."
        )

    # ------------------------------------
    # Sample Parsing Test (after download)
    # ------------------------------------
    html_files = sorted(OUT_DIR.glob("*.html"))
    if html_files:
        sample_file = html_files[0]
        result = parse_entity_html_file(sample_file)
        print("\n\n=== Sample Parsing Result ===")
        print("table_name:", result["table_name"])
        print("description (first 300 chars):", (result["description"] or "")[:300])
        print("attributes_count:", len(result["attributes"]))
        if result["attributes"]:
            print("first_attribute:", result["attributes"][0])
        print("\n\n")
    else:
        print(f"[WARN] no html files found in {OUT_DIR}")


    # ------------------------------------------------
    # Concurrent Parse all HTML -> JSONL for LLM
    # ------------------------------------------------
    parsed_count, parse_error_count = parse_all_entities_to_jsonl_parallel(
        entities_dir=OUT_DIR,
        out_jsonl=Path("data/curam_tables_llm.jsonl"),
        out_errors_csv=Path("data/parse_errors.csv"),
        out_warnings_csv=Path("data/parse_warnings.csv"),
        limit=None,
        max_workers=16,
        log_every=50,
        keep_order=True,
    )
    if parse_error_count or parsed_count != len(allowed_ids):
        raise RuntimeError(
            f"Expected {len(allowed_ids)} parsed tables, got {parsed_count} successful "
            f"and {parse_error_count} failed. Check the parse reports before continuing."
        )

    # --------------------------------------------------------------
    # Split JSONL to individual JSON files + Bundle to Word batches
    # --------------------------------------------------------------
    jsonl_file = Path("data/curam_tables_llm.jsonl")
    out_dir = Path("data/curam_tables_json")

    json_count = split_jsonl_to_individual_json(
        jsonl_path=jsonl_file,
        out_dir=out_dir,
        filename_field="table_name",
        overwrite=True, 
    )
    if json_count != len(allowed_ids):
        raise RuntimeError(
            f"Expected {len(allowed_ids)} per-table JSON files, created {json_count}."
        )

    out_dir = assessment_dir / "curam_tables_word_batches"

    bundle_tables_to_word(
        tables_dir=Path("data/curam_tables_json"),
        out_dir=out_dir,
        batch_size=args.batch_size,
        remove_llm_context=True
    )

    print_mapping_next_steps(assessment_dir, out_dir)
