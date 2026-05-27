import unittest
import json
import base64

import pandas as pd

from app_storage import (
    build_google_service_account_info,
    build_google_service_account_info_from_base64,
    build_google_service_account_info_from_json,
    build_sheet_rows,
    extract_spreadsheet_id,
    format_google_sheets_api_error,
    sheet_values_to_dataframe,
)


class AppStorageTests(unittest.TestCase):
    def test_build_google_service_account_info_restores_private_key_newlines(self) -> None:
        secrets = {
            "type": "service_account",
            "project_id": "demo-project",
            "private_key_id": "key-id",
            "private_key": "-----BEGIN PRIVATE KEY-----\\nabc\\ndef\\n-----END PRIVATE KEY-----\\n",
            "client_email": "svc@example.iam.gserviceaccount.com",
            "client_id": "client-id",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

        info = build_google_service_account_info(secrets)

        self.assertEqual(
            info["private_key"],
            "-----BEGIN PRIVATE KEY-----\nabc\ndef\n-----END PRIVATE KEY-----\n",
        )

    def test_build_google_service_account_info_from_base64_parses_encoded_json(self) -> None:
        json_text = json.dumps(
            {
                "type": "service_account",
                "project_id": "demo-project",
                "private_key_id": "key-id",
                "private_key": "-----BEGIN PRIVATE KEY-----\\nabc\\ndef\\n-----END PRIVATE KEY-----\\n",
                "client_email": "svc@example.iam.gserviceaccount.com",
                "client_id": "client-id",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )
        encoded = base64.b64encode(json_text.encode("utf-8")).decode("ascii")

        info = build_google_service_account_info_from_base64(encoded)

        self.assertEqual(info["project_id"], "demo-project")
        self.assertEqual(
            info["private_key"],
            "-----BEGIN PRIVATE KEY-----\nabc\ndef\n-----END PRIVATE KEY-----\n",
        )

    def test_build_google_service_account_info_from_json_parses_json_string(self) -> None:
        json_text = json.dumps(
            {
                "type": "service_account",
                "project_id": "demo-project",
                "private_key_id": "key-id",
                "private_key": "-----BEGIN PRIVATE KEY-----\\nabc\\ndef\\n-----END PRIVATE KEY-----\\n",
                "client_email": "svc@example.iam.gserviceaccount.com",
                "client_id": "client-id",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        )

        info = build_google_service_account_info_from_json(json_text)

        self.assertEqual(info["project_id"], "demo-project")
        self.assertEqual(
            info["private_key"],
            "-----BEGIN PRIVATE KEY-----\nabc\ndef\n-----END PRIVATE KEY-----\n",
        )

    def test_extract_spreadsheet_id_accepts_full_google_sheets_url(self) -> None:
        spreadsheet_id = extract_spreadsheet_id(
            {"spreadsheet_url": "https://docs.google.com/spreadsheets/d/abc123xyz456/edit#gid=0"}
        )

        self.assertEqual(spreadsheet_id, "abc123xyz456")

    def test_sheet_values_to_dataframe_returns_empty_dataframe_for_header_only_sheet(self) -> None:
        columns = ["대상ID", "매장코드", "매장명"]

        result = sheet_values_to_dataframe([columns], columns)

        self.assertEqual(result.columns.tolist(), columns)
        self.assertTrue(result.empty)

    def test_sheet_values_to_dataframe_reindexes_rows_to_expected_columns(self) -> None:
        columns = ["대상ID", "매장코드", "매장명", "주소"]
        values = [
            ["대상ID", "매장코드", "매장명"],
            ["T1", "D100", "강남점"],
        ]

        result = sheet_values_to_dataframe(values, columns)

        self.assertEqual(result.iloc[0].to_dict(), {"대상ID": "T1", "매장코드": "D100", "매장명": "강남점", "주소": ""})

    def test_build_sheet_rows_includes_header_and_blank_values(self) -> None:
        columns = ["대상ID", "매장코드", "매장명", "주소"]
        frame = pd.DataFrame([{"대상ID": "T1", "매장코드": "D100", "매장명": "강남점"}])

        rows = build_sheet_rows(frame, columns)

        self.assertEqual(rows[0], columns)
        self.assertEqual(rows[1], ["T1", "D100", "강남점", ""])

    def test_format_google_sheets_api_error_mentions_share_and_sheet_id_for_404(self) -> None:
        class FakeResponse:
            status_code = 404

        class FakeAPIError(Exception):
            response = FakeResponse()

        message = format_google_sheets_api_error(
            FakeAPIError(),
            spreadsheet_id="sheet-123",
            client_email="svc@example.iam.gserviceaccount.com",
        )

        self.assertIn("sheet-123", message)
        self.assertIn("svc@example.iam.gserviceaccount.com", message)
        self.assertIn("편집자", message)


if __name__ == "__main__":
    unittest.main()
