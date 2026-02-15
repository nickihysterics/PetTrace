from __future__ import annotations

from io import BytesIO

from django.core.files.base import ContentFile
from django.template import Context, Template
from django.utils import timezone
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import DocumentTemplate, GeneratedDocument


def render_document_template_body(template: DocumentTemplate, payload: dict) -> str:
    context = Context(payload or {})
    return Template(template.body_template).render(context)


def render_pdf_bytes(*, title: str, body: str) -> bytes:
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    y = height - 40
    pdf.setFont("Helvetica-Bold", 14)
    pdf.drawString(40, y, title[:100] or "Document")
    y -= 30

    pdf.setFont("Helvetica", 10)
    for raw_line in (body or "").splitlines():
        line = raw_line.strip()
        if not line:
            y -= 14
            continue
        if y <= 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 10)
            y = height - 40
        pdf.drawString(40, y, line[:140])
        y -= 14

    pdf.showPage()
    pdf.save()
    return buffer.getvalue()


def generate_document_from_template(
    *,
    template: DocumentTemplate,
    payload: dict,
    filename_prefix: str = "document",
    generated_by=None,
    visit=None,
    owner=None,
    pet=None,
    lab_order=None,
) -> GeneratedDocument:
    body = render_document_template_body(template, payload)
    pdf_bytes = render_pdf_bytes(title=template.name, body=body)
    filename = f"{filename_prefix}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.pdf"

    generated = GeneratedDocument(
        template=template,
        visit=visit,
        owner=owner,
        pet=pet,
        lab_order=lab_order,
        payload=payload or {},
        generated_by=generated_by,
    )
    generated.file.save(filename, ContentFile(pdf_bytes), save=False)
    generated.save()
    return generated
