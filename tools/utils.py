import os
import re
import csv
import json
import time
import random
import hashlib
import requests
import threading

from pathlib import Path
from docx import Document
from bs4 import BeautifulSoup
from datetime import datetime
from typing import Iterable, Any
from urllib.parse import urljoin, urlparse
from openpyxl.styles import Font, Alignment
from openpyxl import Workbook, load_workbook
from openpyxl.utils import get_column_letter
from concurrent.futures import ThreadPoolExecutor, as_completed


RESULT_XLSX = Path("data/fhir_mapping_results.xlsx")
RESULT_XLSX.parent.mkdir(parents=True, exist_ok=True)

# base url for IBM Curam Analysis Documentation
BASE_URL = "http://opcgg100000811.service.gocloud.gov.on.ca:9446/curamanalysisdocumentation/"

# Database Tables Index URL Suffix
INDEX_URL = urljoin(BASE_URL, "index-entity.html")

# Output directory for downloaded entity HTML files (each file contains one table's details)
OUT_DIR = Path("data/curam_tables_html/entities")
OUT_DIR.mkdir(parents=True, exist_ok=True)

# Error log for download failures
ERROR_LOG = Path("data/download_errors.csv")
ERROR_LOG.parent.mkdir(parents=True, exist_ok=True)

cookie = None

curam_tablename_idx = 0