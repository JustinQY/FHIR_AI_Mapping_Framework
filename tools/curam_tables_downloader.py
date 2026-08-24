from .utils import *

_thread_local = threading.local()

# Read from CSV specified column as allowed ids, return as a set for quick lookup
# csv: IDH_Databricks_Capacity Planning_02_Dec_2025(CPIN Curam Prod Table Size)
# col_index: 0-based index of the column to read IDs from (default 2 means 3rd column: Curam Table Name)
def load_allowed_ids_from_csv(
    csv_path: Path,
    col_index: int,
    has_header: bool = True,
) -> set[str]:
    if not csv_path.exists():
        raise FileNotFoundError(f"CSV not found: {csv_path.resolve()}")

    allowed: set[str] = set()
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        first = True
        for row in reader:
            if not row:
                continue
            if first and has_header:
                first = False
                continue
            first = False

            if col_index >= len(row):
                continue

            v = (row[col_index] or "").strip()
            if v:
                allowed.add(v.lower())  # case-insensitive match

    print(f"[CSV] Loaded allowed ids: {len(allowed)} from {csv_path.name} (col={col_index + 1})\n\n")
    return allowed


# Extract entity detail page links from index HTML content
# index_html: the full HTML content of index-entity.html (IBM Curam Analysis Documentation-Database Tables Index)
# base_url: the base URL to resolve relative links
# allowed_ids: (optional) set of allowed IDs for filtering (came from CSV-Curam Table column)

def extract_entity_links(
    index_html: str, 
    base_url: str, 
    allowed_ids: set[str] | None = None
) -> list[str]:
    """
    Select <a ... href="...">...</a> from the first field of each record in index_html.
    The entity id is derived from the href filename stem, so links without an explicit
    id="..." attribute (e.g. infrastructure tables) are matched too.
    Before download the current table detail page, filter it by allowed_ids set:
        - allowed_ids is None: no filtering, return all links
        - allowed_ids is not None: only return links whose entity id (href filename stem) is in allowed_ids
    """

    pattern = re.compile(
        r"""
        \[\s*                             # record starts with [
            ['"]\s*<a\s+[^>]*?            # first element starts with "<a ..."
            href\s*=\s*['"](?P<href>      # capture href
                (?:\./)?entities/[^'"]+\.html
                |/curamanalysisdocumentation/entities/[^'"]+\.html
            )['"]
            [^>]*?>.*?</a>\s*['"]\s*,     # rest of <a ...>...</a>, then comma
        """,
        re.IGNORECASE | re.VERBOSE | re.DOTALL,
    )

    seen = set()
    abs_links: list[str] = []
    kept = 0
    skipped = 0

    for m in pattern.finditer(index_html):
        href = m.group("href")
        # entity id = href filename stem (e.g. .../entities/BatchProcDef.html -> "batchprocdef");
        # works whether or not the <a> tag has an id="..." attribute
        entity_id = Path(urlparse(href).path).stem.strip().lower()  # case-insensitive

        if allowed_ids is not None and entity_id not in allowed_ids:
            skipped += 1
            continue

        abs_url = urljoin(base_url, href)
        if abs_url not in seen:
            seen.add(abs_url)
            abs_links.append(abs_url)
            kept += 1

    if allowed_ids is None:
        print(f"[LINKS] extracted={len(abs_links)} (no filtering)")
    else:
        print(f"[LINKS] extracted={kept}, skipped={skipped} (filtered by <IDH_Databricks_Capacity Planning_02_Dec_2025> Domains, exclude infra, Log and Utilities tables)")

    return abs_links


# Normalize text by replacing non-breaking spaces, collapsing whitespace, and trimming
# s: input string
# return: normalized string
def normalize_text(
    s: str
) -> str:
    s = s or ""
    s = s.replace("\xa0", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


# Get filename from URL
def filename_from_url(url: str) -> str:
    # Example: http://.../entities/AbsencePeriod.html -> AbsencePeriod.html
    p = urlparse(url)
    return Path(p.path).name


def _get_thread_session(user_agent: str, cookie: str | None = None) -> requests.Session:
    """
    Get a thread-local requests.Session to avoid sharing session across threads.
    """
    sess = getattr(_thread_local, "session", None)
    if sess is None:
        sess = requests.Session()
        sess.headers.update({"User-Agent": user_agent})
        if cookie:
            sess.headers.update({"Cookie": cookie})
        _thread_local.session = sess
    return sess


def _fetch_with_retry(
    session: requests.Session,
    url: str,
    timeout_sec: int,
    max_retries: int = 4,
    base_backoff_sec: float = 0.6,
) -> str:
    """
    Fetch url with retry and exponential backoff. Return response.text.
    """
    last_err: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            resp = session.get(url, timeout=timeout_sec)
            resp.raise_for_status()
            return resp.text
        except Exception as e:
            last_err = e
            # exponential backoff with jitter
            sleep_sec = base_backoff_sec * (2 ** (attempt - 1)) + random.random() * 0.2
            time.sleep(sleep_sec)
    raise RuntimeError(f"Fetch failed after {max_retries} retries: {url} | last_error={last_err}")


def _download_one_entity(
    idx: int,
    total: int,
    url: str,
    out_dir: Path,
    timeout_sec: int,
    cookie: str | None,
    user_agent: str,
    delay_sec: float,
) -> tuple[str, str | None]:
    """
    Worker:
    - download remote html
    - build remote signature hash
    - compare to local signature hash if exists
    - write file if new/changed
    Return: (url, error_message_or_None)
    """
    try:
        session = _get_thread_session(user_agent=user_agent, cookie=cookie)

        fn = filename_from_url(url)
        fp = out_dir / fn

        # polite jitter (spread concurrent requests)
        if delay_sec and delay_sec > 0:
            time.sleep(random.random() * delay_sec)

        remote_html = _fetch_with_retry(session, url, timeout_sec=timeout_sec)
        fp.write_text(remote_html, encoding="utf-8")
        print(f"[{idx}/{total}] downloaded and saved {fn}")
        return url, None

    except Exception as e:
        return url, f"{type(e).__name__}: {e}"


def download_all_tables_parallel(
    index_url: str,
    base_url: str,
    out_dir: Path,
    delay_sec: float = 0.15,
    timeout_sec: int = 30,
    cookie: str | None = None,
    allowed_ids: set[str] | None = None,
    max_workers: int = 12,
    user_agent: str = "gary_qiao2_ontario; CuramTableDownloader",
) -> None:
    """
    Parallel version of download_all_tables:
    - fetch index once
    - extract entity detail links (optional whitelist filtering)
    - download+signature-compare+write concurrently
    - write error log
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    # NEW: clear out_dir before download
    clear_out_dir = Path("data/curam_tables_html")
    if clear_out_dir:
        for p in out_dir.glob("*.html"):
            try:
                p.unlink()
            except Exception as e:
                print(f"[WARN] failed to delete {p}: {e}")

    # 1) fetch index
    print(f"Fetching index page: {index_url}\n\n")
    sess = requests.Session()
    sess.headers.update({"User-Agent": user_agent})
    if cookie:
        sess.headers.update({"Cookie": cookie})

    r = sess.get(index_url, timeout=timeout_sec)
    r.raise_for_status()
    index_html = r.text

    entity_urls = extract_entity_links(index_html, base_url, allowed_ids=allowed_ids)
    total = len(entity_urls)
    print(f"Found {total} entity detail pages.\n\n")

    if total == 0:
        debug_path = out_dir.parent / "_index_debug.html"
        debug_path.write_text(index_html, encoding="utf-8")
        print("[ERROR] No matching entity links were found.")
        print(f"Saved debug HTML to: {debug_path.resolve()}")
        print("Open it to confirm it contains the JS table data (not a login/403 page).\n\n")
        return

    # 2) parallel download
    errors: list[tuple[str, str]] = []
    t0 = time.time()

    # NOTE: because output log uses idx, keep submission order with enumerate
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futures = []
        for i, url in enumerate(entity_urls, start=1):
            futures.append(ex.submit(
                _download_one_entity,
                i, total, url, out_dir,
                timeout_sec, cookie, user_agent, delay_sec
            ))

        done = 0
        for fut in as_completed(futures):
            done += 1
            url, err = fut.result()
            if err:
                print(f"[ERROR] {url} -> {err}")
                errors.append((url, err))

            if done % 50 == 0 or done == total:
                elapsed = time.time() - t0
                rate = done / elapsed if elapsed > 0 else 0
                print(f"[PROGRESS] {done}/{total} | err={len(errors)} | {rate:.1f} pages/sec")

    # 3) error log
    if errors:
        with ERROR_LOG.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["url", "error"])
            w.writerows(errors)
        print(f"Wrote error log to: {ERROR_LOG.resolve()}")

    elapsed = time.time() - t0
    print(f"[DONE] total={total} err={len(errors)} time={elapsed:.1f}s")