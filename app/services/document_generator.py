import os
import re
import uuid

from docxtpl import DocxTemplate

from app.config import settings


def fill_docx_template(template_path: str, context: dict) -> str:
    """Fill a .docx template with {{variable}} tags using docxtpl.

    Returns the output file path.
    """
    output_name = f"filled_{uuid.uuid4().hex[:8]}.docx"
    output_path = os.path.join(settings.output_dir, output_name)

    tpl = DocxTemplate(template_path)
    tpl.render(context)
    tpl.save(output_path)

    return output_path


def fill_docx_regex(file_path: str, fill_data: dict) -> str:
    """Fill a .docx by regex-replacing {{variable}} patterns.

    Fallback for documents that aren't strict Jinja2 templates.
    Returns the output file path.
    """
    from docx import Document

    output_name = f"filled_{uuid.uuid4().hex[:8]}.docx"
    output_path = os.path.join(settings.output_dir, output_name)

    doc = Document(file_path)
    pattern = re.compile(r"\{\{(\w+)\}\}")

    # Replace in paragraphs
    for para in doc.paragraphs:
        if pattern.search(para.text):
            _replace_in_paragraph(para, fill_data, pattern)

    # Replace in tables
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                for para in cell.paragraphs:
                    if pattern.search(para.text):
                        _replace_in_paragraph(para, fill_data, pattern)

    doc.save(output_path)
    return output_path


def _replace_in_paragraph(para, fill_data: dict, pattern: re.Pattern) -> None:
    """Replace {{variable}} patterns in a paragraph, handling split runs."""
    # Merge all runs' text, do replacement, then set on first run and clear rest
    full_text = "".join(run.text for run in para.runs)
    if not pattern.search(full_text):
        return

    new_text = pattern.sub(
        lambda m: fill_data.get(m.group(1), m.group(0)), full_text
    )

    if para.runs:
        para.runs[0].text = new_text
        for run in para.runs[1:]:
            run.text = ""


def generate_filled_document(
    template_path: str, file_type: str, fill_data: dict
) -> str:
    """Generate a filled document. Returns the output file path."""
    if file_type == "docx":
        try:
            return fill_docx_template(template_path, fill_data)
        except Exception:
            # Fallback to regex-based replacement
            return fill_docx_regex(template_path, fill_data)
    else:
        raise ValueError(f"Document generation not supported for: {file_type}")
