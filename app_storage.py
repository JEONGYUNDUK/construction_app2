from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from re import search

import pandas as pd


def build_google_service_account_info(secrets: Mapping[str, object]) -> dict[str, str]:
    required_keys = [
        "type",
        "project_id",
        "private_key_id",
        "private_key",
        "client_email",
        "client_id",
        "token_uri",
    ]
    info: dict[str, str] = {}

    for key in required_keys:
        value = str(secrets.get(key, "")).strip()
        if value == "":
            raise ValueError(f"Google 서비스 계정 설정에 '{key}' 값이 없습니다.")
        info[key] = value

    info["private_key"] = info["private_key"].replace("\\n", "\n")
    return info


def extract_spreadsheet_id(settings: Mapping[str, object]) -> str:
    spreadsheet_id = str(settings.get("spreadsheet_id", "")).strip()
    if spreadsheet_id:
        return spreadsheet_id

    spreadsheet_url = str(settings.get("spreadsheet_url", "")).strip()
    match = search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", spreadsheet_url)
    if match:
        return match.group(1)

    raise ValueError("Google Sheets 문서 ID 또는 URL 설정이 없습니다.")


def sheet_values_to_dataframe(values: list[list[str]], columns: list[str]) -> pd.DataFrame:
    if not values:
        return pd.DataFrame(columns=columns)

    header, *rows = values
    if not rows:
        return pd.DataFrame(columns=columns)

    frame = pd.DataFrame(rows, columns=header).fillna("")
    for column in columns:
        if column not in frame.columns:
            frame[column] = ""
    return frame[columns].astype(str).fillna("")


def build_sheet_rows(frame: pd.DataFrame, columns: list[str]) -> list[list[str]]:
    normalized = frame.copy()
    for column in columns:
        if column not in normalized.columns:
            normalized[column] = ""
    normalized = normalized[columns].fillna("").astype(str)
    rows = normalized.values.tolist()
    return [columns] + rows


@dataclass
class GoogleSheetsRepository:
    spreadsheet_id: str
    service_account_info: dict[str, str]

    def _open_worksheet(self, worksheet_name: str):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(self.service_account_info, scopes=scopes)
        client = gspread.authorize(credentials)
        spreadsheet = client.open_by_key(self.spreadsheet_id)

        try:
            return spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=32)

    def load_dataframe(self, worksheet_name: str, columns: list[str]) -> pd.DataFrame:
        worksheet = self._open_worksheet(worksheet_name)
        values = worksheet.get_all_values()

        if not values:
            worksheet.update("A1", [columns])
            return pd.DataFrame(columns=columns)

        return sheet_values_to_dataframe(values, columns)

    def save_dataframe(self, worksheet_name: str, frame: pd.DataFrame, columns: list[str]) -> None:
        worksheet = self._open_worksheet(worksheet_name)
        worksheet.clear()
        worksheet.update("A1", build_sheet_rows(frame, columns))
