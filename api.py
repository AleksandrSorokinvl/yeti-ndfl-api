"""
Маленький HTTP-эндпоint поверх fill_certificate.py — принимает JSON с данными
клиента, отдаёт заполненный PDF. Дёргается из сценария Make.com/n8n после
получения вебхука от формы на сайте.

Локальный запуск:
    pip install -r requirements.txt
    API_KEY=secret uvicorn api:app --reload

Деплой: см. README.md (Render.com, бесплатный тариф).
"""

import os

from fastapi import FastAPI, Header, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from fill_certificate import render_pdf_bytes

app = FastAPI(title="Yeti Park — заполнение справки КНД 1151158")

API_KEY = os.environ.get("API_KEY", "")


class CertificateRequest(BaseModel):
    year: int
    student_name: str
    student_dob: str
    student_doc_type: str  # "birth_cert" | "passport"
    student_doc_no: str
    student_doc_date: str
    student_inn: str = ""
    payer_name: str
    payer_dob: str
    payer_inn: str = ""
    payer_passport: str
    payer_passport_date: str
    phone: str = ""
    email: str = ""
    contract: str = ""

    # Заполняется сотрудником школы (не приходит с формы клиента)
    cert_number: str = ""
    correction_number: str = "0"
    amount_rub: float | None = None
    signer_name: str = ""
    sign_date: str = Field(default="")


@app.post("/fill-certificate")
def fill_certificate(payload: CertificateRequest, x_api_key: str = Header(default="")):
    if not API_KEY or x_api_key != API_KEY:
        raise HTTPException(status_code=401, detail="Неверный или отсутствующий X-Api-Key")

    try:
        pdf_bytes = render_pdf_bytes(payload.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    filename = f"spravka_{payload.student_name.split()[0]}_{payload.year}.pdf".encode("ascii", "ignore").decode() or "spravka.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.get("/health")
def health():
    return {"status": "ok"}
