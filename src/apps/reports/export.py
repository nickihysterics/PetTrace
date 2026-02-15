from __future__ import annotations

import csv
import json
from io import StringIO

from django.http import HttpResponse


def _stringify(value):
    if value is None:
        return ""
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return json.dumps(value, ensure_ascii=False, default=str)


def _write_dict_rows(writer, payload: dict):
    writer.writerow(["field", "value"])
    for key, value in payload.items():
        if isinstance(value, (list, dict)):
            continue
        writer.writerow([key, _stringify(value)])


def _write_dict_table(writer, rows: list[dict]):
    headers = sorted({key for row in rows for key in row.keys()})
    if not headers:
        writer.writerow(["value"])
        writer.writerow([""])
        return

    writer.writerow(headers)
    for row in rows:
        writer.writerow([_stringify(row.get(header)) for header in headers])


def payload_to_csv_text(payload: dict) -> str:
    buffer = StringIO()
    writer = csv.writer(buffer)

    _write_dict_rows(writer, payload)

    for key, value in payload.items():
        if not isinstance(value, (list, dict)):
            continue

        writer.writerow([])
        writer.writerow([key])

        if isinstance(value, list):
            if not value:
                writer.writerow(["empty"])
                continue
            if all(isinstance(item, dict) for item in value):
                _write_dict_table(writer, value)
                continue
            writer.writerow(["value"])
            for item in value:
                writer.writerow([_stringify(item)])
            continue

        writer.writerow(["field", "value"])
        for nested_key, nested_value in value.items():
            writer.writerow([nested_key, _stringify(nested_value)])

    return buffer.getvalue()


def csv_export_response(*, payload: dict, filename: str) -> HttpResponse:
    csv_text = payload_to_csv_text(payload)
    response = HttpResponse(csv_text, content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response
