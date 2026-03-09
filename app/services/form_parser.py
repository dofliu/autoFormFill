import re

import fitz  # PyMuPDF
from docx import Document as DocxDocument

from app.schemas.form import FormField

TEMPLATE_PATTERN = re.compile(r"\{\{(\w+)\}\}")


def parse_form(file_path: str, file_type: str) -> list[FormField]:
    """Parse a form file and return detected fields."""
    if file_type == "docx":
        return parse_docx(file_path)
    elif file_type == "pdf":
        return parse_pdf(file_path)
    else:
        raise ValueError(f"Unsupported file type: {file_type}")


def parse_docx(file_path: str) -> list[FormField]:
    """Parse a .docx file for template variables and table blanks."""
    doc = DocxDocument(file_path)
    fields: list[FormField] = []
    seen = set()

    # Scan paragraphs for {{variable}} tags
    for i, para in enumerate(doc.paragraphs):
        for match in TEMPLATE_PATTERN.finditer(para.text):
            name = match.group(1)
            if name not in seen:
                seen.add(name)
                fields.append(
                    FormField(
                        field_name=name,
                        field_type="template_var",
                        location=f"paragraph_{i + 1}",
                    )
                )

    # Scan tables for {{variable}} tags
    for t_idx, table in enumerate(doc.tables):
        for r_idx, row in enumerate(table.rows):
            for c_idx, cell in enumerate(row.cells):
                for match in TEMPLATE_PATTERN.finditer(cell.text):
                    name = match.group(1)
                    if name not in seen:
                        seen.add(name)
                        fields.append(
                            FormField(
                                field_name=name,
                                field_type="table_cell",
                                location=f"table_{t_idx + 1}_row_{r_idx + 1}_col_{c_idx + 1}",
                            )
                        )

    return fields


def parse_pdf(file_path: str) -> list[FormField]:
    """Parse a PDF for interactive form widgets."""
    doc = fitz.open(file_path)
    fields: list[FormField] = []
    seen = set()

    for page_num in range(len(doc)):
        page = doc[page_num]
        # Check for interactive form widgets (fillable PDF fields)
        for widget in page.widgets():
            name = widget.field_name or f"field_p{page_num + 1}_{len(fields)}"
            if name not in seen:
                seen.add(name)
                fields.append(
                    FormField(
                        field_name=name,
                        field_label=widget.field_label,
                        field_type="pdf_widget",
                        location=f"page_{page_num + 1}",
                    )
                )

    doc.close()
    return fields
