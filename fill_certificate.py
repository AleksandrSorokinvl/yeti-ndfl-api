#!/usr/bin/env python3
"""
Заполняет справку КНД 1151158 (об оплате образовательных услуг) реальными
полями AcroForm PDF-бланка, на основе данных из формы на сайте + данных
организации/сотрудника, которые заполняются на стороне школы.

Использование:
    python3 fill_certificate.py input_data.json output.pdf

input_data.json — см. sample_data.json рядом со скриптом.
"""

import io
import json
import sys
from datetime import date
from pathlib import Path
from pypdf import PdfReader, PdfWriter
from pypdf.generic import NameObject, BooleanObject

TEMPLATE_PATH = Path(__file__).parent / "template.pdf"

REQUIRED_FIELDS = [
    "year", "student_name", "student_dob", "student_doc_type", "student_doc_no",
    "student_doc_date", "payer_name", "payer_dob", "payer_passport", "payer_passport_date",
]

# --- Данные организации (Йети Парк) — меняются редко, вынесены в константы ---
ORG_INN = "2543105803"
ORG_KPP = "254301001"
ORG_NAME = 'ООО "Йети парк"'  # шрифт бланка не поддерживает кавычки-ёлочки « »
ORG_FULL_TIME = "1"  # обучение (занятия) очные — всегда "1"
DEFAULT_SIGNER_NAME = "Сорокин Александр Михайлович"

DOC_TYPE_CODES = {
    "birth_cert": "03",  # свидетельство о рождении
    "passport": "21",    # паспорт РФ
}


def split_fio(full_name):
    parts = full_name.strip().split()
    last = parts[0] if len(parts) > 0 else ""
    first = parts[1] if len(parts) > 1 else ""
    middle = " ".join(parts[2:]) if len(parts) > 2 else ""
    return last, first, middle


def split_date(iso_date):
    """'2026-08-21' -> ('21', '08', '2026'); пусто -> ('', '', '')"""
    if not iso_date:
        return "", "", ""
    y, m, d = iso_date.split("-")
    return d, m, y


def split_amount(amount_rub):
    """1234.5 -> ('1234', '50')"""
    if amount_rub in (None, ""):
        return "", ""
    whole = int(amount_rub)
    kopecks = round((float(amount_rub) - whole) * 100)
    return str(whole), f"{kopecks:02d}"


def build_field_values(data):
    payer_last, payer_first, payer_middle = split_fio(data["payer_name"])
    student_last, student_first, student_middle = split_fio(data["student_name"])

    payer_dob_d, payer_dob_m, payer_dob_y = split_date(data["payer_dob"])
    payer_doc_d, payer_doc_m, payer_doc_y = split_date(data["payer_passport_date"])
    student_dob_d, student_dob_m, student_dob_y = split_date(data["student_dob"])
    student_doc_d, student_doc_m, student_doc_y = split_date(data["student_doc_date"])

    signer_last, signer_first, signer_middle = split_fio(data.get("signer_name") or DEFAULT_SIGNER_NAME)
    sign_date = data.get("sign_date") or date.today().isoformat()
    sign_d, sign_m, sign_y = split_date(sign_date)

    amount_whole, amount_kop = split_amount(data.get("amount_rub"))

    org_name_lines = [ORG_NAME[i:i + 40] for i in range(0, len(ORG_NAME), 40)]
    org_name_lines += [""] * (4 - len(org_name_lines))

    values = {
        # Шапка (общая для обеих страниц)
        "Text1": ORG_INN,
        "Text2": ORG_KPP,

        # Стр. 1 — номер справки / корректировка / год
        "Text4": data.get("cert_number", ""),
        "Text5.0": data.get("correction_number", "0"),
        "Text3": str(data["year"]),

        # Стр. 1 — наименование организации + признак очной формы
        "Text6.0": org_name_lines[0],
        "Text6.1": org_name_lines[1],
        "Text6.2": org_name_lines[2],
        "Text6.3": org_name_lines[3],
        "Text14.1": ORG_FULL_TIME,

        # Стр. 1 — плательщик (родитель)
        "Text7.0": payer_last,
        "Text7.1": payer_first,
        "Text7.2": payer_middle,
        "Text8": data.get("payer_inn", ""),
        "Text9.0": payer_dob_d, "Text10.0": payer_dob_m, "Text11.0": payer_dob_y,
        "Text12": "21",  # у взрослого плательщика всегда паспорт РФ
        "Text13": data["payer_passport"],
        "Text9.1.0.0": payer_doc_d, "Text10.1.0.0": payer_doc_m, "Text11.1.0.0": payer_doc_y,

        # Стр. 1 — плательщик и обучаемый НЕ одно лицо (родитель платит за ребёнка)
        "Text14.0": "0",

        # Стр. 1 — сумма расходов (заполняется сотрудником по факту оплат!)
        "Text15.0": amount_whole,
        "Text16.0": amount_kop,

        # Стр. 1 — подписант + дата подписания + кол-во страниц
        "Text17.0": signer_last,
        "Text17.1": signer_first,
        "Text17.2": signer_middle,
        "Text9.1.1": sign_d, "Text10.1.1": sign_m, "Text11.1.1": sign_y,
        "Text5.1": "2",

        # Стр. 2 — данные ребёнка (обучающегося)
        "Text18.0": student_last,
        "Text18.1": student_first,
        "Text18.2": student_middle,
        "Text20": data.get("student_inn", ""),
        "Text21.0": student_dob_d, "Text22.0": student_dob_m, "Text23.0": student_dob_y,
        "Text25": DOC_TYPE_CODES.get(data["student_doc_type"], ""),
        "Text260": data["student_doc_no"],
        "Text21.1": student_doc_d, "Text22.1": student_doc_m, "Text23.1": student_doc_y,
        "Text30": f"{sign_d}.{sign_m}.{sign_y}" if sign_d else "",
    }
    return values


def render_pdf_bytes(data: dict) -> bytes:
    """Заполняет шаблон данными и возвращает готовый PDF как bytes."""
    missing = [f for f in REQUIRED_FIELDS if not data.get(f)]
    if missing:
        raise ValueError(f"Не хватает обязательных полей: {', '.join(missing)}")

    reader = PdfReader(str(TEMPLATE_PATH))
    writer = PdfWriter()
    writer.append(reader)

    values = build_field_values(data)
    for page in writer.pages:
        writer.update_page_form_field_values(page, values, auto_regenerate=True)

    if writer._root_object.get("/AcroForm") is not None:
        writer._root_object["/AcroForm"][NameObject("/NeedAppearances")] = BooleanObject(True)

    buf = io.BytesIO()
    writer.write(buf)
    return buf.getvalue()


def fill(input_json_path, output_pdf_path):
    with open(input_json_path, encoding="utf-8") as f:
        data = json.load(f)
    pdf_bytes = render_pdf_bytes(data)
    with open(output_pdf_path, "wb") as f:
        f.write(pdf_bytes)
    print(f"Готово: {output_pdf_path}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Использование: python3 fill_certificate.py input_data.json output.pdf")
        sys.exit(1)
    fill(sys.argv[1], sys.argv[2])
