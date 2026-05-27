from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import dataclass
import json
from re import search
import time

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


def build_google_service_account_info_from_json(json_text: str) -> dict[str, str]:
    try:
        payload = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError("gcp_service_account_json 값이 올바른 JSON 형식이 아닙니다.") from exc

    if not isinstance(payload, dict):
        raise ValueError("gcp_service_account_json 값은 JSON 객체여야 합니다.")

    return build_google_service_account_info(payload)


def build_google_service_account_info_from_base64(encoded_text: str) -> dict[str, str]:
    try:
        decoded = base64.b64decode(encoded_text).decode("utf-8")
    except Exception as exc:
        raise ValueError("gcp_service_account_json_base64 값이 올바른 base64 형식이 아닙니다.") from exc

    return build_google_service_account_info_from_json(decoded)


def extract_spreadsheet_id(settings: Mapping[str, object]) -> str:
    spreadsheet_id = str(settings.get("spreadsheet_id", "")).strip()
    if spreadsheet_id:
        return spreadsheet_id

    spreadsheet_url = str(settings.get("spreadsheet_url", "")).strip()
    match = search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", spreadsheet_url)
    if match:
        return match.group(1)

    raise ValueError("Google Sheets 문서 ID 또는 URL 설정이 없습니다.")


def format_google_sheets_api_error(exc: Exception, spreadsheet_id: str, client_email: str) -> str:
    status_code = getattr(getattr(exc, "response", None), "status_code", None)

    if status_code in (403, 404):
        return (
            "Google Sheets 문서에 접근할 수 없습니다. "
            f"문서 ID(`{spreadsheet_id}`)가 맞는지 확인하고, "
            f"`{client_email}` 계정을 해당 시트의 편집자로 공유해 주세요."
        )

    return (
        "Google Sheets API 호출 중 오류가 발생했습니다. "
        "시트 공유 권한과 spreadsheet_id를 다시 확인해 주세요."
    )


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

    def _retry_google_api_call(self, func, api_error_type, retries: int = 3, delay_seconds: float = 0.6):
        last_error = None
        for attempt in range(retries):
            try:
                return func()
            except api_error_type as exc:
                last_error = exc
                if attempt == retries - 1:
                    raise
                time.sleep(delay_seconds * (attempt + 1))
        raise last_error  # pragma: no cover

    def _open_worksheet(self, worksheet_name: str):
        import gspread
        from google.oauth2.service_account import Credentials

        scopes = ["https://www.googleapis.com/auth/spreadsheets"]
        credentials = Credentials.from_service_account_info(self.service_account_info, scopes=scopes)
        client = gspread.authorize(credentials)
        try:
            spreadsheet = self._retry_google_api_call(
                lambda: client.open_by_key(self.spreadsheet_id),
                gspread.APIError,
            )
        except gspread.APIError as exc:
            raise ValueError(
                format_google_sheets_api_error(
                    exc,
                    spreadsheet_id=self.spreadsheet_id,
                    client_email=self.service_account_info["client_email"],
                )
            ) from exc

        try:
            return spreadsheet.worksheet(worksheet_name)
        except gspread.WorksheetNotFound:
            return spreadsheet.add_worksheet(title=worksheet_name, rows=1000, cols=32)

    def load_dataframe(self, worksheet_name: str, columns: list[str]) -> pd.DataFrame:
        worksheet = self._open_worksheet(worksheet_name)
        values = self._retry_google_api_call(worksheet.get_all_values, Exception)

        if not values:
            self._retry_google_api_call(lambda: worksheet.update("A1", [columns]), Exception)
            return pd.DataFrame(columns=columns)

        return sheet_values_to_dataframe(values, columns)

    def save_dataframe(self, worksheet_name: str, frame: pd.DataFrame, columns: list[str]) -> None:
        worksheet = self._open_worksheet(worksheet_name)
        self._retry_google_api_call(worksheet.clear, Exception)
        self._retry_google_api_call(lambda: worksheet.update("A1", build_sheet_rows(frame, columns)), Exception)
