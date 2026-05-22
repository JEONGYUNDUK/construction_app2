from html import escape
from pathlib import Path
from datetime import date, datetime
from uuid import uuid4

import pandas as pd
import streamlit as st

try:
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
        make_target_store_record,
        parse_period_text,
        resolve_period_text_for_update,
        remove_registered_target_duplicates,
    )
except Exception:
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
            (stores["매장명"] == store_name)
            & (stores["매장코드"].astype(str).str.upper() == store_code.upper())
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


st.set_page_config(
    page_title="유통망 공사정보 공유",
    page_icon="🏗️",
    layout="wide",
    initial_sidebar_state="expanded",
)

EXCEL_FILE = Path("매장리스트.xlsx")
CSV_FILE = Path("매장리스트.csv")
TARGET_FILE = Path("construction_targets.csv")
DATA_FILE = Path("construction_records.csv")

REQUIRED_COLUMNS = ["마케팅팀", "대리점명", "매장코드", "매장명", "주소"]
TARGET_COLUMNS = ["대상ID", "등록일시", "마케팅팀", "대리점명", "매장명", "매장코드", "주소"]
RECORD_COLUMNS = [
    "대상ID",
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
    "완료처리일",
]
CONTRACTOR_OPTIONS = ["", "티엔에스", "디자인피아", "동아광고", "DID", "가구"]

st.markdown(
    """
    <style>
    .main .block-container {
        padding-top: 1.4rem;
        padding-bottom: 2rem;
        max-width: 1180px;
    }

    .hero-card {
        padding: 24px 26px;
        border-radius: 22px;
        background: linear-gradient(135deg, #1e3a8a 0%, #0f172a 60%, #1e293b 100%);
        color: white;
        box-shadow: 0 16px 35px rgba(15, 23, 42, 0.2);
        margin-bottom: 20px;
        border: 1px solid rgba(255, 255, 255, 0.08);
    }

    .hero-title {
        font-size: 30px;
        font-weight: 800;
        margin-bottom: 6px;
        letter-spacing: -0.6px;
        background: linear-gradient(to right, #ffffff, #93c5fd);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }

    .section-card {
        padding: 18px 20px;
        border-radius: 18px;
        border: 1px solid #e2e8f0;
        background: #ffffff;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
        margin-bottom: 18px;
    }

    .info-card {
        padding: 20px;
        border-radius: 18px;
        border: 1px solid #e2e8f0;
        background-color: #ffffff;
        box-shadow: 0 10px 24px rgba(15, 23, 42, 0.04);
        margin-bottom: 14px;
    }

    .metric-label {
        color: #64748b;
        font-size: 13px;
        font-weight: 700;
        margin-bottom: 4px;
    }

    .metric-value {
        color: #0f172a;
        font-size: 17px;
        font-weight: 800;
        word-break: keep-all;
    }

    .stButton > button {
        border-radius: 12px;
        height: 42px;
        font-weight: 800;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 0 16px;
        background: #eff6ff;
        color: #2563eb;
        border: 1px solid #bfdbfe;
        transition: all 0.2s ease;
    }

    .stButton > button:hover {
        background: #dbeafe;
        border-color: #93c5fd;
        color: #1e40af;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37, 99, 235, 0.08);
    }

    button[kind="primary"] {
        background: #fde2e2 !important;
        color: #b42318 !important;
        border: 1px solid #f6b4b4 !important;
        box-shadow: 0 8px 20px rgba(180, 35, 24, 0.12) !important;
    }

    button[kind="primary"]:hover {
        background: #fbd1d1 !important;
        color: #912018 !important;
        border-color: #ef9a9a !important;
    }

    /* -------------------------------------------------------------------------
       100% 순수 CSS 미디어 쿼리 반응형 엔진 (단일 소스)
       ------------------------------------------------------------------------- */
    @media (max-width: 991px) {
        .main .block-container {
            padding-left: 0.8rem;
            padding-right: 0.8rem;
        }

        .hero-card {
            padding: 20px;
            border-radius: 18px;
        }

        .hero-title {
            font-size: 24px;
        }

        .metric-value {
            font-size: 15px;
        }

        /* 1-A. 모바일 뷰포트에서 데스크톱 전용 헤더 컨테이너 완벽 삭제 */
        div[key="desktop_header"],
        div[data-testid="stVerticalBlockBorderWrapper"]:has([key="desktop_header"]) {
            display: none !important;
        }

        /* 1-B. 모바일에서 모든 st.columns(stHorizontalBlock)을 카드 및 세로 플렉스 구조화 */
        div[data-testid="stHorizontalBlock"] {
            display: flex !important;
            flex-direction: row !important;
            flex-wrap: wrap !important;
            background: #ffffff !important;
            border: 1px solid #e2e8f0 !important;
            border-radius: 20px !important;
            padding: 20px !important;
            margin-bottom: 24px !important;
            box-shadow: 0 8px 24px rgba(15, 23, 42, 0.04) !important;
            gap: 12px 0 !important;
        }

        /* 1-C. 1~8번째 데이터 컬럼들을 100% 가로폭으로 세로 배치 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:not(:nth-child(9)):not(:nth-child(10)) {
            width: 100% !important;
            min-width: 100% !important;
            flex-basis: 100% !important;
            margin: 0 !important;
            padding: 0 !important;
        }

        /* 1-D. 9번째(업데이트), 10번째(삭제) 버튼 컬럼들을 하단에 50%씩 반반 가로 배치 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(9),
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(10) {
            width: 48% !important;
            min-width: 48% !important;
            flex-basis: 48% !important;
            display: inline-block !important;
            margin: 0 !important;
            padding: 0 !important;
        }
        
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(9) {
            margin-right: 4% !important;
        }

        /* 1-E. 모바일 뷰포트에서 개별 컬럼 바로 위에 가상 안내 레이블 주입 */
        /* 1번째 컬럼: NO */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(1):before {
            content: "NO / 공사 순번";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 2px;
        }

        /* 2번째 컬럼: 매장명 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2):before {
            content: "매장명";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 2px;
        }
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(2) {
            font-size: 17px !important;
            font-weight: 800 !important;
            color: #0f172a !important;
        }

        /* 3번째 컬럼: 매장코드 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(3):before {
            content: "매장코드";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 2px;
        }

        /* 4번째 컬럼: 주소 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(4):before {
            content: "주소";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #64748b;
            margin-bottom: 2px;
        }

        /* 5번째 컬럼: 공사내용 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(5):before {
            content: "공사내용";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 4px;
            margin-top: 6px;
        }

        /* 6번째 컬럼: 시공업체 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(6):before {
            content: "시공업체";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 4px;
            margin-top: 6px;
        }

        /* 7번째 컬럼: 공사기간 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(7):before {
            content: "공사기간";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 4px;
            margin-top: 6px;
        }

        /* 8번째 컬럼: 공사완료여부 */
        div[data-testid="stHorizontalBlock"] > div[data-testid="column"]:nth-child(8):before {
            content: "공사완료여부";
            display: block;
            font-size: 12px;
            font-weight: 700;
            color: #334155;
            margin-bottom: 4px;
            margin-top: 6px;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def load_store_data() -> pd.DataFrame:
    source = choose_store_data_source(CSV_FILE.exists(), EXCEL_FILE.exists())

    if source is None:
        st.error("매장리스트.csv 또는 매장리스트.xlsx 파일이 없습니다. app.py와 같은 폴더에 넣어 주세요.")
        st.stop()

    if source == "csv":
        df = pd.read_csv(
            CSV_FILE,
            dtype={
                "매장코드": str,
                "대리점코드": str,
            },
        )
    else:
        try:
            df = pd.read_excel(
                EXCEL_FILE,
                dtype={
                    "매장코드": str,
                    "대리점코드": str,
                },
            )
        except ImportError:
            st.error(
                "엑셀 파일을 읽기 위한 openpyxl 패키지를 불러오지 못했습니다. "
                "배포 환경에서는 매장리스트.csv를 함께 사용해 주세요."
            )
            st.stop()

    missing_columns = [col for col in REQUIRED_COLUMNS if col not in df.columns]

    if missing_columns:
        st.error(f"엑셀에 필수 컬럼이 없습니다: {', '.join(missing_columns)}")
        st.stop()

    df = df.copy()

    for col in REQUIRED_COLUMNS:
        df[col] = df[col].fillna("").astype(str).str.strip()

    df = df[df["매장코드"] != ""]
    df = df.drop_duplicates(subset=["매장코드"], keep="first")

    return df


def load_target_stores() -> pd.DataFrame:
    if not TARGET_FILE.exists():
        return pd.DataFrame(columns=TARGET_COLUMNS)

    df = pd.read_csv(TARGET_FILE, dtype=str).fillna("")

    for col in TARGET_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    if (df["대상ID"] == "").any():
        df = df.copy()
        for idx in df.index:
            if df.at[idx, "대상ID"] == "":
                df.at[idx, "대상ID"] = f"legacy-target-{idx + 1}"

    return remove_registered_target_duplicates(df[TARGET_COLUMNS])


def save_target_stores(df: pd.DataFrame) -> None:
    cleaned = remove_registered_target_duplicates(df[TARGET_COLUMNS])
    cleaned.to_csv(TARGET_FILE, index=False, encoding="utf-8-sig")


def load_records() -> pd.DataFrame:
    if not DATA_FILE.exists():
        return pd.DataFrame(columns=RECORD_COLUMNS)

    df = pd.read_csv(DATA_FILE, dtype=str).fillna("")

    for col in RECORD_COLUMNS:
        if col not in df.columns:
            df[col] = ""

    return df[RECORD_COLUMNS]


def save_records(df: pd.DataFrame) -> None:
    df[RECORD_COLUMNS].to_csv(DATA_FILE, index=False, encoding="utf-8-sig")


def validate_period_dates(start_date: date, end_date: date) -> tuple[bool, str]:
    if start_date > end_date:
        return False, "공사 시작일은 종료일보다 늦을 수 없습니다."

    return True, ""


def make_store_card(store: pd.Series) -> None:
    safe_store = {key: escape(str(value)) for key, value in store.items()}

    # ------------------ 데스크톱용 매장 정보 카드 ------------------
    st.markdown('<div class="desktop-only">', unsafe_allow_html=True)
    st.markdown('<div class="info-card">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1.4, 1.1, 2.2])

    with col1:
        st.markdown('<div class="metric-label">매장명</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{safe_store["매장명"]}</div>', unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="metric-label">매장코드</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{safe_store["매장코드"]}</div>', unsafe_allow_html=True)

    with col3:
        st.markdown('<div class="metric-label">주소</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="metric-value">{safe_store["주소"]}</div>', unsafe_allow_html=True)

    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

    # ------------------ 모바일용 매장 정보 카드 ------------------
    st.markdown('<div class="mobile-only">', unsafe_allow_html=True)
    st.markdown(f"""
    <div class="mobile-card">
        <div class="mobile-card-header">
            <div class="mobile-card-title">{safe_store["매장명"]}</div>
            <div class="mobile-card-no">{safe_store["매장코드"]}</div>
        </div>
        <div class="mobile-card-meta"><b>주소:</b> {safe_store["주소"]}</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


stores = load_store_data()
target_stores = load_target_stores()
records = load_records()
reset_token = st.session_state.get("selection_reset_token", 0)
selection_keys = get_selection_widget_keys(reset_token)

st.markdown(
    """
    <div class="hero-card">
        <div class="hero-title">유통망 공사정보 공유</div>
    </div>
    """,
    unsafe_allow_html=True,
)

summary_col1, summary_col2 = st.columns(2)
with summary_col2:
    st.caption(f"2단계 등록 공사정보: {len(records):,}건")


st.subheader("1. 대상 매장 등록")
st.markdown('<div class="section-card">', unsafe_allow_html=True)

select_method = st.radio(
    "",
    ["목록에서 선택", "매장코드 직접입력"],
    horizontal=True,
    label_visibility="collapsed",
    key="select_method",
)

selected_store = None

if select_method == "매장코드 직접입력":
    code = st.text_input(
        "매장코드",
        placeholder="예: D331250000",
        help="공사정보를 등록할 대상 매장의 매장코드를 입력해 주세요.",
        key=selection_keys["direct_store_code"],
    ).strip()

    if code:
        selected_store = find_store_by_code(stores, code)

        if selected_store is None:
            st.warning("입력한 매장코드와 일치하는 매장이 없습니다.")
else:
    # ------------------ 데스크톱 뷰 ------------------
    with st.container(key="desktop_select_container"):
        select_col1, select_col2, select_col3 = st.columns(3)

        with select_col1:
            marketing_options = get_marketing_options(stores)
            selected_marketing = st.selectbox(
                "마케팅팀",
                marketing_options,
                index=None,
                placeholder="마케팅팀을 선택하세요",
                format_func=get_marketing_display_label,
                key=selection_keys["selected_marketing"],
            )

        selected_agency = None
        selected_store_label = None

        with select_col2:
            agency_options = get_agency_options(stores, selected_marketing) if selected_marketing else []
            selected_agency = st.selectbox(
                "대리점명",
                agency_options,
                index=None,
                placeholder="대리점을 선택하세요",
                disabled=not selected_marketing,
                key=selection_keys["selected_agency"],
            )

        with select_col3:
            store_options = get_store_options(stores, selected_marketing, selected_agency) if selected_agency else []
            selected_store_label = st.selectbox(
                "매장명",
                store_options,
                index=None,
                placeholder="매장을 선택하세요",
                disabled=not selected_agency,
                key=selection_keys["selected_store_label"],
            )

    # ------------------ 모바일 뷰 ------------------
    with st.container(key="mobile_select_container"):
        marketing_options_m = get_marketing_options(stores)
        selected_marketing_m = st.selectbox(
            "마케팅팀",
            marketing_options_m,
            index=None,
            placeholder="마케팅팀을 선택하세요",
            format_func=get_marketing_display_label,
            key=selection_keys["selected_marketing"] + "_m",
        )

        selected_agency_m = None
        selected_store_label_m = None

        agency_options_m = get_agency_options(stores, selected_marketing_m) if selected_marketing_m else []
        selected_agency_m = st.selectbox(
            "대리점명",
            agency_options_m,
            index=None,
            placeholder="대리점을 선택하세요",
            disabled=not selected_marketing_m,
            key=selection_keys["selected_agency"] + "_m",
        )

        store_options_m = get_store_options(stores, selected_marketing_m, selected_agency_m) if selected_agency_m else []
        selected_store_label_m = st.selectbox(
            "매장명",
            store_options_m,
            index=None,
            placeholder="매장을 선택하세요",
            disabled=not selected_agency_m,
            key=selection_keys["selected_store_label"] + "_m",
        )

    # 두 뷰 중 하나에서 매장이 선택되면 바인딩
    final_store_label = selected_store_label or selected_store_label_m
    if final_store_label:
        selected_store = find_store_by_name_and_code(stores, final_store_label)

if selected_store is not None:
    make_store_card(selected_store)

    if st.button("대상매장등록", width="stretch"):
        new_target = pd.DataFrame([make_target_store_record(selected_store)])
        updated_targets = pd.concat([target_stores, new_target], ignore_index=True)
        save_target_stores(updated_targets)
        st.session_state["selection_reset_token"] = reset_token + 1
        st.success("대상 매장이 등록되었습니다.")
        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)


st.subheader("2. 공사정보 등록 및 업데이트")
st.markdown('<div class="section-card">', unsafe_allow_html=True)

if target_stores.empty:
    st.info("1단계에서 대상 매장을 먼저 등록해 주세요.")
else:
    records = load_records()
    merged_rows = assign_display_numbers(merge_targets_with_records(target_stores, records))

    if merged_rows.empty:
        st.info("등록된 대상 매장이 없습니다.")
    else:
        # =========================================================================
        # 2-A. 데스크톱 뷰 (PC / Wide) - desktop_container
        # =========================================================================
        with st.container(key="desktop_container"):
            header_cols = st.columns([0.48, 1.0, 0.9, 1.45, 2.0, 1.0, 1.45, 0.95, 0.85, 0.85])
            header_labels = [
                "NO",
                "매장명",
                "매장코드",
                "주소",
                "공사내용",
                "시공업체",
                "공사기간",
                "공사완료여부",
                "업데이트",
                "삭제",
            ]

            for column, label in zip(header_cols, header_labels):
                column.markdown(f"**{label}**")

            for _, row in merged_rows.iterrows():
                target_id = str(row["대상ID"])
                store_code = str(row["매장코드"])
                default_period = parse_period_text(str(row["공사기간"])) or (date.today(), date.today())
                default_contractor = str(row["시공업체"]).strip()
                contractor_index = (
                    CONTRACTOR_OPTIONS.index(default_contractor)
                    if default_contractor in CONTRACTOR_OPTIONS
                    else 0
                )
                status_options = ["", "N", "Y"]
                default_status = str(row["공사완료여부"]).strip()
                status_index = status_options.index(default_status) if default_status in status_options else 0

                row_cols = st.columns([0.48, 1.0, 0.9, 1.45, 2.0, 1.0, 1.45, 0.95, 0.85, 0.85])
                row_cols[0].write(str(row["NO"]))
                row_cols[1].write(str(row["매장명"]))
                row_cols[2].write(store_code)
                row_cols[3].write(str(row["주소"]))

                with row_cols[4]:
                    st.text_input(
                        f"공사내용_{target_id}",
                        value=str(row["공사내용"]),
                        label_visibility="collapsed",
                        key=f"detail_{target_id}",
                        placeholder="공사내용 입력",
                    )

                with row_cols[5]:
                    st.selectbox(
                        f"시공업체_{target_id}",
                        CONTRACTOR_OPTIONS,
                        index=contractor_index,
                        format_func=lambda value: "선택" if value == "" else value,
                        label_visibility="collapsed",
                        key=f"contractor_{target_id}",
                    )

                with row_cols[6]:
                    st.date_input(
                        f"공사기간_{target_id}",
                        value=default_period,
                        format="YYYY-MM-DD",
                        label_visibility="collapsed",
                        key=f"period_{target_id}",
                    )

                with row_cols[7]:
                    st.selectbox(
                        f"공사완료여부_{target_id}",
                        status_options,
                        index=status_index,
                        format_func=lambda value: "선택" if value == "" else value,
                        label_visibility="collapsed",
                        key=f"status_{target_id}",
                    )

                with row_cols[8]:
                    st.button("업데이트", key=f"update_{target_id}", width="stretch")

                with row_cols[9]:
                    st.button("삭제", key=f"delete_{target_id}", width="stretch")

        # =========================================================================
        # 2-B. 모바일 뷰 (모바일 카드) - mobile_container
        # =========================================================================
        with st.container(key="mobile_container"):
            for _, row in merged_rows.iterrows():
                target_id = str(row["대상ID"])
                store_code = str(row["매장코드"])
                default_period = parse_period_text(str(row["공사기간"])) or (date.today(), date.today())
                default_contractor = str(row["시공업체"]).strip()
                contractor_index = (
                    CONTRACTOR_OPTIONS.index(default_contractor)
                    if default_contractor in CONTRACTOR_OPTIONS
                    else 0
                )
                status_options = ["", "N", "Y"]
                default_status = str(row["공사완료여부"]).strip()
                status_index = status_options.index(default_status) if default_status in status_options else 0

                # 개별 매장 정보를 감싸는 모바일 카드
                st.markdown(f"""
                <div class="mobile-card">
                    <div class="mobile-card-header">
                        <span class="mobile-card-no">NO {row["NO"]}</span>
                        <span class="mobile-card-title">{row["매장명"]}</span>
                    </div>
                    <div class="mobile-card-meta"><b>매장코드:</b> {store_code}</div>
                    <div class="mobile-card-meta"><b>주소:</b> {row["주소"]}</div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('<div class="mobile-field-label">공사내용</div>', unsafe_allow_html=True)
                st.text_input(
                    f"공사내용_모바일_{target_id}",
                    value=str(row["공사내용"]),
                    label_visibility="collapsed",
                    key=f"detail_m_{target_id}",
                    placeholder="공사내용 입력",
                )

                st.markdown('<div class="mobile-field-label">시공업체</div>', unsafe_allow_html=True)
                st.selectbox(
                    f"시공업체_모바일_{target_id}",
                    CONTRACTOR_OPTIONS,
                    index=contractor_index,
                    format_func=lambda value: "선택" if value == "" else value,
                    label_visibility="collapsed",
                    key=f"contractor_m_{target_id}",
                )

                st.markdown('<div class="mobile-field-label">공사기간</div>', unsafe_allow_html=True)
                st.date_input(
                    f"공사기간_모바일_{target_id}",
                    value=default_period,
                    format="YYYY-MM-DD",
                    label_visibility="collapsed",
                    key=f"period_m_{target_id}",
                )

                st.markdown('<div class="mobile-field-label">공사완료여부</div>', unsafe_allow_html=True)
                st.selectbox(
                    f"공사완료여부_모바일_{target_id}",
                    status_options,
                    index=status_index,
                    format_func=lambda value: "선택" if value == "" else value,
                    label_visibility="collapsed",
                    key=f"status_m_{target_id}",
                )

                # 업데이트/삭제 가로 배치
                btn_col1, btn_col2 = st.columns(2)
                with btn_col1:
                    st.button("업데이트", key=f"update_m_{target_id}", width="stretch")
                with btn_col2:
                    st.button("삭제", key=f"delete_m_{target_id}", width="stretch")
                
                # 카드 간 구분선
                st.markdown('<div style="margin-bottom: 24px; border-bottom: 2px dashed #e2e8f0;"></div>', unsafe_allow_html=True)

        # =========================================================================
        # 2-C. 업데이트 및 삭제 핸들러 (통합 처리)
        # =========================================================================
        for _, row in merged_rows.iterrows():
            target_id = str(row["대상ID"])
            store_code = str(row["매장코드"])
            
            # 이벤트 트리거 확인
            update_clicked = st.session_state.get(f"update_{target_id}", False)
            update_clicked_m = st.session_state.get(f"update_m_{target_id}", False)
            delete_clicked = st.session_state.get(f"delete_{target_id}", False)
            delete_clicked_m = st.session_state.get(f"delete_m_{target_id}", False)

            if update_clicked or update_clicked_m:
                # 활성화된 위젯 종류에 따라 상태 추출
                if update_clicked_m:
                    detail_val = st.session_state.get(f"detail_m_{target_id}", "").strip()
                    contractor_val = st.session_state.get(f"contractor_m_{target_id}", "")
                    period_val = st.session_state.get(f"period_m_{target_id}", (date.today(), date.today()))
                    status_val = st.session_state.get(f"status_m_{target_id}", "")
                else:
                    detail_val = st.session_state.get(f"detail_{target_id}", "").strip()
                    contractor_val = st.session_state.get(f"contractor_{target_id}", "")
                    period_val = st.session_state.get(f"period_{target_id}", (date.today(), date.today()))
                    status_val = st.session_state.get(f"status_{target_id}", "")

                if len(period_val) != 2:
                    st.error(f"{row['매장명']}의 공사 시작일과 종료일을 모두 선택해 주세요.")
                else:
                    start_date, end_date = period_val
                    is_valid, message = validate_period_dates(start_date, end_date)

                    if not is_valid:
                        st.error(message)
                    else:
                        period_text = resolve_period_text_for_update(
                            current_period_text=str(row["공사기간"]),
                            selected_period=(start_date, end_date),
                            default_today=date.today(),
                        )
                        updated_record = {
                            "대상ID": target_id,
                            "등록일시": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            "마케팅팀": row["마케팅팀"],
                            "대리점명": row["대리점명"],
                            "매장명": row["매장명"],
                            "매장코드": store_code,
                            "주소": row["주소"],
                            "공사내용": detail_val,
                            "시공업체": contractor_val,
                            "공사기간": period_text,
                            "공사완료여부": status_val,
                            "완료처리일": "",
                        }

                        latest_records = load_records()
                        records_without_store = latest_records[latest_records["대상ID"] != target_id]
                        saved_records = pd.concat(
                            [records_without_store, pd.DataFrame([updated_record])],
                            ignore_index=True,
                        )
                        save_records(saved_records)
                        st.success(f"{row['매장명']} 공사정보가 업데이트되었습니다.")
                        st.rerun()

            if delete_clicked or delete_clicked_m:
                st.session_state["pending_delete_target_id"] = target_id
                st.rerun()

            if st.session_state.get("pending_delete_target_id") == target_id:
                confirm_col1, confirm_col2, confirm_col3 = st.columns([2.2, 1.0, 1.0])

                with confirm_col1:
                    st.warning("해당 데이터를 삭제하시겠습니까?")

                with confirm_col2:
                    confirm_choice = st.selectbox(
                        "삭제 확인",
                        ["NO", "YES"],
                        key=f"delete_confirm_choice_{target_id}",
                        label_visibility="collapsed",
                    )

                with confirm_col3:
                    confirm_delete = st.button("확인", key=f"confirm_delete_{target_id}", width="stretch", type="primary")

                if confirm_delete:
                    if confirm_choice == "YES":
                        latest_targets = load_target_stores()
                        latest_records = load_records()
                        saved_targets = latest_targets[latest_targets["대상ID"] != target_id].reset_index(drop=True)
                        saved_records = latest_records[latest_records["대상ID"] != target_id].reset_index(drop=True)
                        save_target_stores(saved_targets)
                        save_records(saved_records)
                        st.session_state.pop("pending_delete_target_id", None)
                        st.success(f"{row['매장명']} 데이터가 삭제되었습니다.")
                        st.rerun()
                    else:
                        st.session_state.pop("pending_delete_target_id", None)
                        st.info("삭제가 취소되었습니다.")
                        st.rerun()

st.markdown("</div>", unsafe_allow_html=True)
