# stock_market_explorer
주식 종목 탐색기

## Troubleshooting
#### 1. Streamlit의 화면 재실행(Rerun)으로 인한 데이터 초기화 문제
**Problem**: 검색 결과 목록에서 특정 기업의 버튼을 클릭하면 상세 정보를 띄워야 하는데, 버튼 클릭 시 스트림릿 스크립트가 처음부터 재실행되면서 검색 결과 화면 자체가 날아가는 현상 발생.
**Solution**: Streamlit의 상태 관리 기능인 `st.session_state`를 도입. 사용자의 검색 결과(search_results), 선택한 기업(selected_company), 현재 페이지 번호(page_number)를 세션에 저장하여, 버튼 상호작용이 일어나도 화면의 상태가 유지되도록 UX를 개선.

#### 2. 대량의 검색 결과로 인한 UI 레이아웃 붕괴
**Problem**: '반도체'와 같은 광범위한 키워드 검색 시 수십 개의 기업 버튼이 한 번에 렌더링되어 대시보드의 가독성이 크게 떨어지고 세로 스크롤이 지나치게 길어짐.
**Solution**: 한 화면에 최대 12개(4열 3행)의 버튼만 보여주는 커스텀 페이지네이션(Pagination) 로직을 구현. `st.session_state.page_number` 변수를 기준으로 데이터를 슬라이싱(`[start_idx : end_idx]`)하고, 하단에 [이전/다음] 버튼을 배치하여 깔끔한 대시보드 UI를 완성.

#### 3. 주말 및 공휴일 금융 API 호출 시 KeyError 발생
**Problem**: pykrx 및 yfinance 라이브러리로 시장 거래량이나 주가를 가져올 때, 당일 날짜(`datetime.today()`)를 기준으로 API를 호출하면 주말이나 장 시작 전에는 데이터가 비어 있어 치명적인 에러가 발생.
**Solution**: 단순 당일 조회가 아니라, 반복문을 사용해 최근 5일간을 역순으로 탐색(range(5))하여 데이터가 존재하는 가장 최근 영업일의 지표를 안전하게 가져오는 방어 로직을 유틸리티(stock_utils.py)에 추가함.

#### 4. 단순 키워드 매칭의 한계와 테마 검색의 필요성
**Problem**: 기존 Elasticsearch의 match 쿼리만으로는 "전기차 배터리", "여름철 무더위" 같은 문맥적 테마 검색이 불가능하여 투자 탐색 도구로서의 활용도가 떨어졌었음.
**Solution**: 한국어에 특화된 Sentence Transformer 임베딩 모델(KR-SBERT)을 도입하여 기업의 메타데이터(회사명+업종+주요제품)를 768차원의 밀집 벡터(Dense Vector) 로 변환. 이를 Elasticsearch 8.x의 kNN (최근접 이웃) 검색과 결합하여, 의미 기반의 통합검색(Semantic Search) 파이프라인을 구축함.