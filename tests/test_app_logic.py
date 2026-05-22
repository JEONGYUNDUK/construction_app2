import unittest
from datetime import date

import pandas as pd

from app_logic import (
    assign_display_numbers,
    build_period_text,
    choose_store_data_source,
    find_store_by_code,
    find_store_by_name_and_code,
    get_agency_options,
    get_marketing_display_label,
    get_marketing_options,
    get_selection_widget_keys,
    get_store_options,
    merge_targets_with_records,
    make_store_display_options,
    make_target_store_record,
    parse_period_text,
    resolve_period_text_for_update,
    remove_registered_target_duplicates,
)


class AppLogicTests(unittest.TestCase):
    def setUp(self) -> None:
        self.stores = pd.DataFrame(
            [
                {
                    "마케팅팀": "경북",
                    "대리점명": "서울대리점",
                    "매장코드": "D200",
                    "매장명": "강남점",
                    "주소": "서울 강남구",
                },
                {
                    "마케팅팀": "서대구",
                    "대리점명": "부산대리점",
                    "매장코드": "D100",
                    "매장명": "해운대점",
                    "주소": "부산 해운대구",
                },
                {
                    "마케팅팀": "동대구",
                    "대리점명": "가나다대리점",
                    "매장코드": "D150",
                    "매장명": "중앙점",
                    "주소": "대구 중구",
                },
            ]
        )

    def test_build_period_text_formats_two_dates(self) -> None:
        self.assertEqual(
            build_period_text(date(2026, 5, 22), date(2026, 6, 1)),
            "2026-05-22 ~ 2026-06-01",
        )

    def test_find_store_by_code_is_case_insensitive(self) -> None:
        result = find_store_by_code(self.stores, "d200")

        self.assertIsNotNone(result)
        self.assertEqual(result["매장명"], "강남점")

    def test_make_store_display_options_sorts_by_store_name(self) -> None:
        options = make_store_display_options(self.stores)

        self.assertEqual(
            options,
            ["강남점 / D200", "중앙점 / D150", "해운대점 / D100"],
        )

    def test_make_target_store_record_keeps_store_identity_fields(self) -> None:
        record = make_target_store_record(self.stores.iloc[0])

        self.assertIn("대상ID", record)
        self.assertEqual(
            record,
            {
                "대상ID": record["대상ID"],
                "등록일시": record["등록일시"],
                "마케팅팀": "경북",
                "대리점명": "서울대리점",
                "매장명": "강남점",
                "매장코드": "D200",
                "주소": "서울 강남구",
            },
        )

    def test_remove_registered_target_duplicates_keeps_duplicate_targets(self) -> None:
        targets = pd.DataFrame(
            [
                {"대상ID": "T1", "매장코드": "D100", "매장명": "강남점"},
                {"대상ID": "T2", "매장코드": "D100", "매장명": "강남점"},
                {"대상ID": "T3", "매장코드": "D200", "매장명": "해운대점"},
            ]
        )

        deduped = remove_registered_target_duplicates(targets)

        self.assertEqual(deduped["대상ID"].tolist(), ["T1", "T2", "T3"])

    def test_get_marketing_options_returns_sorted_unique_values(self) -> None:
        options = get_marketing_options(self.stores)

        self.assertEqual(options, ["서대구", "동대구", "경북"])

    def test_get_marketing_options_normalizes_team_suffix_and_orders_values(self) -> None:
        stores = pd.DataFrame(
            [
                {"마케팅팀": "경북마케팅팀", "대리점명": "A", "매장코드": "D1", "매장명": "A", "주소": "1"},
                {"마케팅팀": "서대구마케팅팀", "대리점명": "B", "매장코드": "D2", "매장명": "B", "주소": "2"},
                {"마케팅팀": "동대구마케팅팀", "대리점명": "C", "매장코드": "D3", "매장명": "C", "주소": "3"},
            ]
        )

        options = get_marketing_options(stores)

        self.assertEqual(options, ["서대구", "동대구", "경북"])

    def test_get_marketing_display_label_appends_team_suffix(self) -> None:
        self.assertEqual(get_marketing_display_label("서대구"), "서대구마케팅팀")
        self.assertEqual(get_marketing_display_label("동대구"), "동대구마케팅팀")
        self.assertEqual(get_marketing_display_label("경북"), "경북마케팅팀")

    def test_get_marketing_display_label_does_not_double_append_suffix(self) -> None:
        self.assertEqual(get_marketing_display_label("서대구마케팅팀"), "서대구마케팅팀")

    def test_get_agency_options_filters_by_marketing_team(self) -> None:
        options = get_agency_options(self.stores, "동대구")

        self.assertEqual(options, ["가나다대리점"])

    def test_get_agency_options_returns_korean_sorted_values(self) -> None:
        stores = pd.DataFrame(
            [
                {"마케팅팀": "경북", "대리점명": "하나대리점", "매장코드": "D300", "매장명": "A", "주소": "1"},
                {"마케팅팀": "경북", "대리점명": "가나다대리점", "매장코드": "D301", "매장명": "B", "주소": "2"},
            ]
        )
        options = get_agency_options(stores, "경북")

        self.assertEqual(options, ["가나다대리점", "하나대리점"])

    def test_get_store_options_filters_by_marketing_and_agency_and_sorts_by_code(self) -> None:
        stores = pd.DataFrame(
            [
                {"마케팅팀": "경북", "대리점명": "서울대리점", "매장코드": "D300", "매장명": "C점", "주소": "1"},
                {"마케팅팀": "경북", "대리점명": "서울대리점", "매장코드": "D100", "매장명": "A점", "주소": "2"},
            ]
        )
        options = get_store_options(stores, "경북", "서울대리점")

        self.assertEqual(options, ["A점 / D100", "C점 / D300"])

    def test_find_store_by_name_and_code_returns_matching_store(self) -> None:
        result = find_store_by_name_and_code(self.stores, "강남점 / D200")

        self.assertIsNotNone(result)
        self.assertEqual(result["주소"], "서울 강남구")

    def test_merge_targets_with_records_includes_empty_record_fields(self) -> None:
        targets = pd.DataFrame(
            [
                {
                    "대상ID": "T1",
                    "등록일시": "2026-05-22 09:00:00",
                    "마케팅팀": "경북",
                    "대리점명": "서울대리점",
                    "매장명": "강남점",
                    "매장코드": "D200",
                    "주소": "서울 강남구",
                }
            ]
        )
        records = pd.DataFrame(
            columns=[
                "등록일시",
                "마케팅팀",
                "대리점명",
                "매장명",
                "매장코드",
                "주소",
                "공사내용",
                "시공업체",
                "공사기간",
                "공사완료여부",
            ]
        )

        merged = merge_targets_with_records(targets, records)

        self.assertEqual(merged.iloc[0]["매장명"], "강남점")
        self.assertEqual(merged.iloc[0]["공사내용"], "")
        self.assertEqual(merged.iloc[0]["시공업체"], "")
        self.assertEqual(merged.iloc[0]["공사기간"], "")
        self.assertEqual(merged.iloc[0]["공사완료여부"], "")

    def test_merge_targets_with_records_prefers_registered_record_values(self) -> None:
        targets = pd.DataFrame(
            [
                {
                    "대상ID": "T1",
                    "등록일시": "2026-05-22 09:00:00",
                    "마케팅팀": "경북",
                    "대리점명": "서울대리점",
                    "매장명": "강남점",
                    "매장코드": "D200",
                    "주소": "서울 강남구",
                }
            ]
        )
        records = pd.DataFrame(
            [
                {
                    "대상ID": "T1",
                    "등록일시": "2026-05-23 11:00:00",
                    "마케팅팀": "경북",
                    "대리점명": "서울대리점",
                    "매장명": "강남점",
                    "매장코드": "D200",
                    "주소": "서울 강남구",
                    "공사내용": "간판 교체",
                    "시공업체": "티엔에스",
                    "공사기간": "2026-05-23 ~ 2026-05-30",
                    "공사완료여부": "Y",
                }
            ]
        )

        merged = merge_targets_with_records(targets, records)

        self.assertEqual(merged.iloc[0]["공사내용"], "간판 교체")
        self.assertEqual(merged.iloc[0]["시공업체"], "티엔에스")
        self.assertEqual(merged.iloc[0]["공사기간"], "2026-05-23 ~ 2026-05-30")
        self.assertEqual(merged.iloc[0]["공사완료여부"], "Y")

    def test_assign_display_numbers_uses_sub_numbering_for_duplicate_store(self) -> None:
        rows = pd.DataFrame(
            [
                {"대상ID": "T1", "등록일시": "2026-05-22 09:00:00", "매장코드": "D100", "매장명": "A점"},
                {"대상ID": "T2", "등록일시": "2026-05-22 09:01:00", "매장코드": "D200", "매장명": "B점"},
                {"대상ID": "T3", "등록일시": "2026-05-22 09:02:00", "매장코드": "D200", "매장명": "B점"},
                {"대상ID": "T4", "등록일시": "2026-05-22 09:03:00", "매장코드": "D300", "매장명": "C점"},
            ]
        )

        numbered = assign_display_numbers(rows)

        self.assertEqual(numbered["NO"].tolist(), ["1", "2-1", "2-2", "3"])

    def test_assign_display_numbers_groups_duplicate_rows_together(self) -> None:
        rows = pd.DataFrame(
            [
                {"대상ID": "T1", "등록일시": "2026-05-22 09:00:00", "매장코드": "D100", "매장명": "A점"},
                {"대상ID": "T2", "등록일시": "2026-05-22 09:01:00", "매장코드": "D200", "매장명": "B점"},
                {"대상ID": "T3", "등록일시": "2026-05-22 09:02:00", "매장코드": "D300", "매장명": "C점"},
                {"대상ID": "T4", "등록일시": "2026-05-22 09:03:00", "매장코드": "D200", "매장명": "B점"},
            ]
        )

        numbered = assign_display_numbers(rows)

        self.assertEqual(numbered["매장코드"].tolist(), ["D100", "D200", "D200", "D300"])
        self.assertEqual(numbered["NO"].tolist(), ["1", "2-1", "2-2", "3"])

    def test_parse_period_text_returns_two_dates(self) -> None:
        start_date, end_date = parse_period_text("2026-05-23 ~ 2026-05-30")

        self.assertEqual(start_date, date(2026, 5, 23))
        self.assertEqual(end_date, date(2026, 5, 30))

    def test_parse_period_text_returns_none_for_invalid_value(self) -> None:
        self.assertIsNone(parse_period_text(""))

    def test_resolve_period_text_for_update_keeps_blank_when_original_blank_and_default_dates_used(self) -> None:
        self.assertEqual(
            resolve_period_text_for_update(
                current_period_text="",
                selected_period=(date(2026, 5, 22), date(2026, 5, 22)),
                default_today=date(2026, 5, 22),
            ),
            "",
        )

    def test_resolve_period_text_for_update_formats_period_when_dates_are_selected(self) -> None:
        self.assertEqual(
            resolve_period_text_for_update(
                current_period_text="",
                selected_period=(date(2026, 5, 22), date(2026, 5, 30)),
                default_today=date(2026, 5, 22),
            ),
            "2026-05-22 ~ 2026-05-30",
        )

    def test_choose_store_data_source_prefers_csv(self) -> None:
        self.assertEqual(choose_store_data_source(csv_exists=True, excel_exists=True), "csv")

    def test_choose_store_data_source_falls_back_to_excel(self) -> None:
        self.assertEqual(choose_store_data_source(csv_exists=False, excel_exists=True), "excel")

    def test_get_selection_widget_keys_changes_with_reset_token(self) -> None:
        first_keys = get_selection_widget_keys(0)
        second_keys = get_selection_widget_keys(1)

        self.assertNotEqual(first_keys["selected_marketing"], second_keys["selected_marketing"])
        self.assertNotEqual(first_keys["selected_store_label"], second_keys["selected_store_label"])



if __name__ == "__main__":
    unittest.main()
