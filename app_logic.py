from __future__ import annotations

import base64
from io import BytesIO
from datetime import date, datetime, timedelta
from uuid import uuid4

import pandas as pd

DELETE_PASSWORD = "2580"


def normalize_marketing_team(marketing_team: str) -> str:
    value = str(marketing_team).strip()
    suffix = "마케팅팀"

    if value.endswith(suffix):
        return value[: -len(suffix)]

    return value


def choose_store_data_source(csv_exists: bool, excel_exists: bool) -> str | None:
    if csv_exists:
        return "csv"
    if excel_exists:
        return "excel"
    return None


def build_period_text(start_date: date, end_date: date) -> str:
    return f"{start_date:%Y-%m-%d} ~ {end_date:%Y-%m-%d}"


def resolve_period_text_for_update(
    current_period_text: str,
    selected_period: tuple[date, date],
    default_today: date,
) -> str:
    if current_period_text.strip() == "" and selected_period == (default_today, default_today):
        return ""

    return build_period_text(selected_period[0], selected_period[1])


def parse_period_text(period_text: str) -> tuple[date, date] | None:
    if " ~ " not in period_text:
        return None

    start_text, end_text = period_text.split(" ~ ", 1)

    try:
        start_date = datetime.strptime(start_text, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_text, "%Y-%m-%d").date()
    except ValueError:
        return None

    return start_date, end_date


def find_store_by_code(stores: pd.DataFrame, code: str) -> pd.Series | None:
    normalized = code.strip().upper()

    if not normalized:
        return None

    result = stores[stores["매장코드"].str.upper() == normalized]

    if result.empty:
        return None

    return result.iloc[0]


def find_store_by_name_and_code(stores: pd.DataFrame, label: str) -> pd.Series | None:
    if " / " not in label:
        return None

    store_name, store_code = [value.strip() for value in label.rsplit(" / ", 1)]
    result = stores[
        (stores["매장명"] == store_name) & (stores["매장코드"].astype(str).str.upper() == store_code.upper())
    ]

    if result.empty:
        return None

    return result.iloc[0]


def get_marketing_options(stores: pd.DataFrame) -> list[str]:
    preferred_order = ["서대구", "동대구", "경북"]
    values = [normalize_marketing_team(value) for value in stores["마케팅팀"].dropna().astype(str).unique().tolist()]
    ordered = [name for name in preferred_order if name in values]
    remaining = sorted(name for name in values if name not in preferred_order)
    return ordered + remaining


def get_marketing_display_label(marketing_team: str) -> str:
    return f"{normalize_marketing_team(marketing_team)}마케팅팀"


def get_agency_options(stores: pd.DataFrame, marketing_team: str) -> list[str]:
    normalized = normalize_marketing_team(marketing_team)
    filtered = stores[stores["마케팅팀"].astype(str).map(normalize_marketing_team) == normalized]
    return sorted(filtered["대리점명"].dropna().astype(str).unique().tolist())


def get_store_options(stores: pd.DataFrame, marketing_team: str, agency_name: str) -> list[str]:
    normalized = normalize_marketing_team(marketing_team)
    filtered = stores[
        (stores["마케팅팀"].astype(str).map(normalize_marketing_team) == normalized)
        & (stores["대리점명"] == agency_name)
    ].copy()
    filtered = filtered.sort_values(by=["매장코드", "매장명"], ascending=[True, True])
    filtered["매장표시명"] = filtered["매장명"] + " / " + filtered["매장코드"]
    return filtered["매장표시명"].tolist()


def get_selection_widget_keys(reset_token: int) -> dict[str, str]:
    suffix = f"_{reset_token}"
    return {
        "selected_marketing": f"selected_marketing{suffix}",
        "selected_agency": f"selected_agency{suffix}",
        "selected_store_label": f"selected_store_label{suffix}",
        "direct_store_code": f"direct_store_code{suffix}",
    }


def make_store_display_options(stores: pd.DataFrame) -> list[str]:
    store_df = stores.copy()
    store_df["매장표시명"] = store_df["매장명"] + " / " + store_df["매장코드"]
    return sorted(store_df["매장표시명"].tolist())


def make_target_store_record(store: pd.Series) -> dict[str, str]:
    return {
        "대상ID": uuid4().hex,
        "등록일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "마케팅팀": str(store["마케팅팀"]),
        "대리점명": str(store["대리점명"]),
        "매장명": str(store["매장명"]),
        "매장코드": str(store["매장코드"]),
        "주소": str(store["주소"]),
    }


def remove_registered_target_duplicates(targets: pd.DataFrame) -> pd.DataFrame:
    if "대상ID" not in targets.columns:
        return targets

    return targets.drop_duplicates(subset=["대상ID"], keep="first").reset_index(drop=True)


def merge_targets_with_records(targets: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    merged = targets.copy()
    merged["공사내용"] = ""
    merged["시공업체"] = ""
    merged["공사기간"] = ""
    merged["공사완료여부"] = ""
    merged["완료처리일"] = ""

    if records.empty:
        return merged

    use_target_id = (
        "대상ID" in merged.columns
        and "대상ID" in records.columns
        and records["대상ID"].astype(str).str.strip().ne("").any()
    )
    lookup_key = "대상ID" if use_target_id else "매장코드"
    record_lookup = records.drop_duplicates(subset=[lookup_key], keep="last").set_index(lookup_key)

    for idx, row in merged.iterrows():
        lookup_value = row[lookup_key]

        if lookup_value in record_lookup.index:
            merged.at[idx, "공사내용"] = str(record_lookup.at[lookup_value, "공사내용"])
            merged.at[idx, "시공업체"] = str(record_lookup.at[lookup_value, "시공업체"])
            merged.at[idx, "공사기간"] = str(record_lookup.at[lookup_value, "공사기간"])
            merged.at[idx, "공사완료여부"] = str(record_lookup.at[lookup_value, "공사완료여부"])
            if "완료처리일" in record_lookup.columns:
                merged.at[idx, "완료처리일"] = str(record_lookup.at[lookup_value, "완료처리일"])

    return merged


def build_construction_status_rows(targets: pd.DataFrame, records: pd.DataFrame) -> pd.DataFrame:
    return assign_display_numbers(merge_targets_with_records(targets, records))


def assign_display_numbers(rows: pd.DataFrame) -> pd.DataFrame:
    result = rows.copy().reset_index(drop=True)

    if result.empty:
        result["NO"] = pd.Series(dtype="str")
        return result

    result["_original_order"] = range(len(result))
    base_keys = list(dict.fromkeys((str(row["매장코드"]), str(row["매장명"])) for _, row in result.iterrows()))
    base_lookup = {key: index + 1 for index, key in enumerate(base_keys)}
    result["_base_no"] = [
        base_lookup[(str(row["매장코드"]), str(row["매장명"]))]
        for _, row in result.iterrows()
    ]
    result["_dup_seq"] = result.groupby(["매장코드", "매장명"]).cumcount() + 1
    result = result.sort_values(by=["_base_no", "_dup_seq", "_original_order"]).reset_index(drop=True)
    counts = {key: 0 for key in base_keys}
    totals = {
        key: sum(1 for _, row in result.iterrows() if (str(row["매장코드"]), str(row["매장명"])) == key)
        for key in base_keys
    }
    numbers: list[str] = []

    for _, row in result.iterrows():
        key = (str(row["매장코드"]), str(row["매장명"]))
        counts[key] += 1
        base_number = str(base_lookup[key])

        if totals[key] == 1:
            numbers.append(base_number)
        else:
            numbers.append(f"{base_number}-{counts[key]}")

    result["NO"] = numbers
    return result.drop(columns=["_original_order", "_base_no", "_dup_seq"])


def generate_construction_status_pdf(rows: pd.DataFrame) -> bytes:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

    pdfmetrics.registerFont(UnicodeCIDFont("HYSMyeongJo-Medium"))
    font_name = "HYSMyeongJo-Medium"
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=10 * mm,
        bottomMargin=10 * mm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "ConstructionPdfTitle",
        parent=styles["Title"],
        fontName=font_name,
        fontSize=15,
        leading=18,
        textColor=colors.HexColor("#0f172a"),
        alignment=1,
    )
    cell_style = ParagraphStyle(
        "ConstructionPdfCell",
        parent=styles["BodyText"],
        fontName=font_name,
        fontSize=8.5,
        leading=11,
        textColor=colors.black,
    )

    columns = ["NO", "매장명", "매장코드", "주소", "공사내용", "시공업체", "공사기간", "공사완료여부"]
    table_rows: list[list[Paragraph]] = [
        [Paragraph(str(column), cell_style) for column in columns]
    ]

    for _, row in rows.iterrows():
        table_rows.append(
            [
                Paragraph(str(row.get(column, "")).strip() or "-", cell_style)
                for column in columns
            ]
        )

    table = Table(
        table_rows,
        repeatRows=1,
        colWidths=[15 * mm, 24 * mm, 24 * mm, 64 * mm, 42 * mm, 25 * mm, 42 * mm, 22 * mm],
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#dbeafe")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1e3a8a")),
                ("FONTNAME", (0, 0), (-1, -1), font_name),
                ("FONTSIZE", (0, 0), (-1, -1), 8.5),
                ("LEADING", (0, 0), (-1, -1), 11),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("ALIGN", (0, 0), (0, -1), "CENTER"),
                ("ALIGN", (2, 1), (2, -1), "CENTER"),
                ("ALIGN", (5, 1), (5, -1), "CENTER"),
                ("ALIGN", (7, 1), (7, -1), "CENTER"),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
            ]
        )
    )

    story = [
        Paragraph("유통망 공사현황_대구마케팅담당", title_style),
        Spacer(1, 5 * mm),
        table,
    ]
    document.build(story)
    return buffer.getvalue()


def build_pdf_download_name() -> str:
    return "유통망 공사현황_대구마케팅담당.pdf"


def build_pdf_preview_html(pdf_bytes: bytes) -> str:
    pdf_base64 = base64.b64encode(pdf_bytes).decode("utf-8")
    return f"""
    <iframe
        id="construction-pdf-preview"
        width="100%"
        height="900"
        style="border: none; border-radius: 12px;"
    ></iframe>
    <script>
    (function() {{
        const base64 = "{pdf_base64}";
        const binary = atob(base64);
        const bytes = new Uint8Array(binary.length);
        for (let i = 0; i < binary.length; i += 1) {{
            bytes[i] = binary.charCodeAt(i);
        }}
        const blob = new Blob([bytes], {{ type: "application/pdf" }});
        const url = URL.createObjectURL(blob);
        document.getElementById("construction-pdf-preview").src = url;
    }})();
    </script>
    """


def validate_delete_password(password: str) -> bool:
    return password.strip() == DELETE_PASSWORD


def cleanup_expired_completed_rows(
    targets: pd.DataFrame,
    records: pd.DataFrame,
    today: date | None = None,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    if today is None:
        today = date.today()

    if records.empty or "공사완료여부" not in records.columns:
        return targets.reset_index(drop=True), records.reset_index(drop=True)

    use_target_id = "대상ID" in records.columns and records["대상ID"].astype(str).str.strip().ne("").any()
    key_name = "대상ID" if use_target_id else "매장코드"
    expired_keys: list[str] = []

    for _, row in records.iterrows():
        if str(row.get("공사완료여부", "")).strip() != "Y":
            continue

        completed_on = str(row.get("완료처리일", "")).strip()

        if not completed_on:
            continue

        try:
            completed_date = datetime.strptime(completed_on, "%Y-%m-%d").date()
        except ValueError:
            continue

        if today >= completed_date + timedelta(days=8):
            expired_keys.append(str(row[key_name]))

    if not expired_keys:
        return targets.reset_index(drop=True), records.reset_index(drop=True)

    target_key_name = "대상ID" if use_target_id and "대상ID" in targets.columns else "매장코드"
    filtered_targets = targets[~targets[target_key_name].astype(str).isin(expired_keys)].reset_index(drop=True)
    filtered_records = records[~records[key_name].astype(str).isin(expired_keys)].reset_index(drop=True)

    return filtered_targets, filtered_records
