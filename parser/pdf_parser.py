# parser/pdf_parser.py — Extract exam info & student emails from Govt PDFs

import re
import os
import logging
import pdfplumber

logger = logging.getLogger(__name__)

# ── Regex patterns ──────────────────────────────────────────────────────────
EMAIL_RE      = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
PHONE_RE      = re.compile(r"(?:\+91[\s\-]?)?[6-9]\d{9}")
DATE_RE       = re.compile(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[\s,]+\d{4})\b", re.I)
VACANCY_RE    = re.compile(r"(?:total\s+)?(?:vacancies?|posts?|seats?)[:\s]+(\d[\d,]+)", re.I)
EXAM_NAME_RE  = re.compile(r"(RRB\s+\w+|SSC\s+\w+|IBPS\s+\w+|SBI\s+\w+|Bank\s+of\s+Baroda\s+\w+)", re.I)
LAST_DATE_RE  = re.compile(r"last\s+date[:\s\w]*?(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})", re.I)
REG_FEE_RE    = re.compile(r"(?:application|registration)\s+fee[:\s]*(?:Rs\.?|INR|₹)\s*(\d[\d,]*)", re.I)
AGE_LIMIT_RE  = re.compile(r"age\s+limit[:\s]+(\d{2})\s*(?:to|-)\s*(\d{2})", re.I)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    full_text = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    full_text.append(text)
    except Exception as e:
        logger.error(f"Failed to read PDF {pdf_path}: {e}")
    return "\n".join(full_text)


def extract_tables_from_pdf(pdf_path: str) -> list[list]:
    """Extract tabular data (e.g. candidate lists) from PDF."""
    all_tables = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                tables = page.extract_tables()
                if tables:
                    all_tables.extend(tables)
    except Exception as e:
        logger.error(f"Table extraction failed for {pdf_path}: {e}")
    return all_tables


def parse_exam_details(text: str) -> dict:
    """
    Parse key exam details from PDF text.
    Returns structured dict with exam metadata.
    """
    details = {
        "exam_names":    [],
        "vacancies":     None,
        "last_date":     None,
        "important_dates": [],
        "age_limit":     None,
        "registration_fee": None,
        "emails_found":  [],
        "phones_found":  [],
        "raw_excerpt":   text[:500].replace("\n", " "),
    }

    # Exam name
    exam_matches = EXAM_NAME_RE.findall(text)
    details["exam_names"] = list(set(exam_matches))

    # Vacancy count
    vac = VACANCY_RE.search(text)
    if vac:
        details["vacancies"] = vac.group(1).replace(",", "")

    # Last date to apply
    ld = LAST_DATE_RE.search(text)
    if ld:
        details["last_date"] = ld.group(1)

    # All dates mentioned
    details["important_dates"] = DATE_RE.findall(text)[:10]

    # Age limit
    age = AGE_LIMIT_RE.search(text)
    if age:
        details["age_limit"] = f"{age.group(1)}-{age.group(2)} years"

    # Registration fee
    fee = REG_FEE_RE.search(text)
    if fee:
        details["registration_fee"] = f"₹{fee.group(1)}"

    # Extract emails (candidates/contacts in PDF)
    details["emails_found"] = list(set(EMAIL_RE.findall(text)))

    # Extract phone numbers
    details["phones_found"] = list(set(PHONE_RE.findall(text)))[:20]

    return details


def parse_student_table(tables: list[list]) -> list[dict]:
    """
    Parse tabular student/candidate data from PDF tables.
    Looks for rows containing name, email, roll number, etc.
    Returns list of student dicts.
    """
    students = []
    for table in tables:
        if not table or len(table) < 2:
            continue

        # Try to detect header row
        header = [str(cell).lower().strip() if cell else "" for cell in table[0]]
        col_map = {}

        for i, h in enumerate(header):
            if any(k in h for k in ["name", "naam", "candidate"]):
                col_map["name"] = i
            elif any(k in h for k in ["email", "mail", "e-mail"]):
                col_map["email"] = i
            elif any(k in h for k in ["roll", "reg", "registration", "id"]):
                col_map["roll_no"] = i
            elif any(k in h for k in ["mobile", "phone", "contact"]):
                col_map["phone"] = i
            elif any(k in h for k in ["exam", "post", "category"]):
                col_map["exam"] = i

        if not col_map:
            continue

        for row in table[1:]:
            if not row:
                continue
            student = {}
            for field, idx in col_map.items():
                if idx < len(row) and row[idx]:
                    student[field] = str(row[idx]).strip()
            if student:
                # Validate email if present
                if "email" in student and not EMAIL_RE.match(student["email"]):
                    del student["email"]
                if student:
                    students.append(student)

    return students


def process_pdf(pdf_path: str) -> dict:
    """
    Full pipeline: extract text + tables, parse exam details + students.
    Returns combined result dict.
    """
    logger.info(f"Processing PDF: {pdf_path}")
    text   = extract_text_from_pdf(pdf_path)
    tables = extract_tables_from_pdf(pdf_path)

    exam_details = parse_exam_details(text)
    students     = parse_student_table(tables)

    return {
        "pdf_path":     pdf_path,
        "exam_details": exam_details,
        "students":     students,
        "page_count":   _get_page_count(pdf_path),
    }


def _get_page_count(pdf_path: str) -> int:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            return len(pdf.pages)
    except Exception:
        return 0


if __name__ == "__main__":
    import sys
    import json
    logging.basicConfig(level=logging.INFO)
    if len(sys.argv) > 1:
        result = process_pdf(sys.argv[1])
        print(json.dumps(result, indent=2, default=str))
    else:
        print("Usage: python pdf_parser.py <path_to_pdf>")
