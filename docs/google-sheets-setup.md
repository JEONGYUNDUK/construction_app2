# Google Sheets Setup

## 1. Google Cloud 프로젝트 생성

1. Google Cloud Console에서 새 프로젝트를 만듭니다.
2. `Google Sheets API`와 필요 시 `Google Drive API`를 활성화합니다.
3. `IAM 및 관리자` -> `서비스 계정`에서 새 서비스 계정을 만듭니다.
4. 서비스 계정 키를 `JSON` 형식으로 발급받습니다.

## 2. Google Sheets 문서 생성

1. Google Sheets에서 새 문서를 하나 만듭니다.
2. 문서 안에 `targets`, `records` 시트를 만듭니다.
3. 문서 공유에 서비스 계정 이메일을 편집자로 추가합니다.

## 3. Streamlit Secrets 설정

1. 로컬 개발 시 `.streamlit/secrets.toml` 파일을 만듭니다.
2. 배포 환경에서는 Streamlit App 설정의 `Secrets`에 동일한 내용을 붙여넣습니다.
3. 형식은 `.streamlit/secrets.toml.example`를 그대로 참고합니다.

## 4. spreadsheet_id 찾기

Google Sheets 주소가 아래와 같다면:

`https://docs.google.com/spreadsheets/d/1AbCdEfGhIjKlMnOpQrStUvWxYz/edit#gid=0`

`spreadsheet_id` 값은 `1AbCdEfGhIjKlMnOpQrStUvWxYz` 입니다.

## 5. 첫 실행 동작

- 앱은 먼저 Google Sheets의 `targets`, `records` 시트를 읽습니다.
- 시트가 비어 있으면 헤더를 자동 생성합니다.
- 같은 폴더에 기존 `construction_targets.csv`, `construction_records.csv`가 있고 시트가 비어 있으면 1회성 초기 데이터로 업로드합니다.
- 이후 저장은 Google Sheets만 사용합니다.
