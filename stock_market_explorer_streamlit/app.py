import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from elastic_api import search_index, semantic_search
from stock_utils import get_stock_price_data, get_market_index, get_today_market_ranking, get_stock_volume_rank

st.set_page_config(page_title="주식 탐색 스캐너", page_icon="📈", layout="wide")

if 'search_results' not in st.session_state:
    st.session_state.search_results = []
if 'selected_company' not in st.session_state:
    st.session_state.selected_company = None
if 'page_number' not in st.session_state:
    st.session_state.page_number = 0 

st.title("주식 탐색 스캐너")

# 상단 검색 영역
# 🌟 상단 검색 모드 선택
st.markdown("### 종목 및 테마 검색")
search_mode = st.radio("검색 모드 선택", ["키워드 검색 (정확도 우선)", "의미 기반 통합검색 (문맥 우선)"], horizontal=True)

if search_mode == "키워드 검색 (정확도 우선)":
    search_field = st.radio("검색 기준", ["회사명", "종목코드", "업종", "주요제품"], horizontal=True)
    st.info("💡 키워드 기반으로 입력해보세요!")
    placeholder_text = "예: 삼성전자"
else:
    search_field = None
    st.info("💡 '전기차 배터리 관련주', '여름철 냉방', '인공지능 소프트웨어' 처럼 자연스럽게 입력해보세요!")
    placeholder_text = "관심 있는 테마나 문장을 자유롭게 입력하세요"

col_search1, col_search2 = st.columns([5, 1])
with col_search1:
    search_query = st.text_input("검색어를 입력하세요", placeholder=placeholder_text, label_visibility="collapsed")
with col_search2:
    search_btn = st.button("검색 실행", use_container_width=True)

if search_btn and search_query:
    with st.spinner("데이터를 조회 중입니다..."):
        st.session_state.selected_company = None 
        st.session_state.page_number = 0 
        
        # 🌟 모드에 따른 검색 로직 분기
        if search_mode == "📌 키워드 검색 (정확도 우선)":
            result = search_index("stock_info", search_field, search_query, 100)
            st.session_state.search_results = result.to_dict()["hits"]["hits"]
        else:
            result = semantic_search("stock_info", search_query, 50)
            st.session_state.search_results = result["hits"]["hits"] # kNN 응답 구조에 맞게 파싱
            
    if not st.session_state.search_results:
        st.warning("⚠️ 일치하는 검색 결과가 없습니다.")

st.markdown("---")

# 메인 레이아웃 분할
col_left, col_right = st.columns([6, 4], gap="large")

# ==========================================
# 좌측 영역: 검색 결과 및 기업 상세 정보 (차트 개선)
# ==========================================
with col_left:
    if st.session_state.search_results:
        st.markdown("### 검색 결과")
        result_list = [hit["_source"] for hit in st.session_state.search_results]
        df_results = pd.DataFrame(result_list)
        display_cols = ['회사명', '종목코드', '시장구분', '업종', '주요제품', '상장일']
        display_cols = [col for col in display_cols if col in df_results.columns]
        st.dataframe(df_results[display_cols], hide_index=True, use_container_width=True, height=200)

        items_per_page = 12 
        total_results = len(st.session_state.search_results)
        total_pages = (total_results - 1) // items_per_page + 1

        start_idx = st.session_state.page_number * items_per_page
        end_idx = start_idx + items_per_page
        current_page_results = st.session_state.search_results[start_idx:end_idx]

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("주가를 확인할 기업을 선택해주세요.")

        btn_cols = st.columns(4)
        for i, hit in enumerate(current_page_results):
            source = hit["_source"]
            corp_name = source.get("회사명", "알 수 없음")
            ticker = source.get("종목코드", "000000")
            if btn_cols[i % 4].button(f"{corp_name}\n({ticker})", key=f"btn_{ticker}_{i}", use_container_width=True):
                st.session_state.selected_company = source
        
        page_col1, page_col2, page_col3 = st.columns([1, 2, 1])
        with page_col1:
            if st.button("← 이전", disabled=(st.session_state.page_number == 0), use_container_width=True):
                st.session_state.page_number -= 1
                st.rerun()
        with page_col2:
            st.markdown(f"<div style='text-align: center; padding-top: 5px;'><b>페이지 {st.session_state.page_number + 1} / {total_pages}</b></div>", unsafe_allow_html=True)
        with page_col3:
            if st.button("다음 →", disabled=(st.session_state.page_number == total_pages - 1), use_container_width=True):
                st.session_state.page_number += 1
                st.rerun()

    if st.session_state.selected_company:
        company_data = st.session_state.selected_company
        corp_name = company_data.get("회사명", "알 수 없음")
        ticker = company_data.get("종목코드", "000000")
        market = company_data.get("시장구분", "유가")
        
        st.divider()
        st.success(f"**{corp_name}** 상세 정보")

        # 차트 주기 선택 라디오 버튼 (디폴트: 월봉 -> index=0)
        timeframe = st.radio("차트 주기", ["월봉", "주봉", "일봉", "분봉"], index=0, horizontal=True)
        
        try:
            price_df = get_stock_price_data(ticker, timeframe=timeframe, market=market)
            
            if not price_df.empty:
                # 이동평균선 계산
                price_df['MA5'] = price_df['Close'].rolling(window=5).mean()
                price_df['MA20'] = price_df['Close'].rolling(window=20).mean()
                price_df['MA60'] = price_df['Close'].rolling(window=60).mean()
                
                # 거래량 상승/하락 색상 (전일 대비 혹은 시가/종가 대비)
                colors = ['red' if row['Close'] >= row['Open'] else 'blue' for _, row in price_df.iterrows()]

                # 서브플롯 생성 (위: 캔들스틱+이평선, 아래: 거래량)
                fig_stock = make_subplots(rows=2, cols=1, shared_xaxes=True, 
                                          vertical_spacing=0.03, row_heights=[0.7, 0.3])
                
                hover_text = [
                    f"날짜: {idx.strftime('%Y-%m-%d %H:%M') if timeframe == '분봉' else idx.strftime('%Y년 %m월 %d일')}<br>시가: {row['Open']:,.0f}원<br>고가: {row['High']:,.0f}원<br>저가: {row['Low']:,.0f}원<br>종가: {row['Close']:,.0f}원<br>거래량: {row['Volume']:,.0f}주"
                    for idx, row in price_df.iterrows()
                ]

                # 1. 캔들스틱 추가
                fig_stock.add_trace(go.Candlestick(
                    x=price_df.index, open=price_df['Open'], high=price_df['High'],
                    low=price_df['Low'], close=price_df['Close'],
                    name="주가", increasing_line_color='red', decreasing_line_color='blue',
                    text=hover_text, hoverinfo='text'
                ), row=1, col=1)
                
                # 2. 이동평균선 추가
                fig_stock.add_trace(go.Scatter(x=price_df.index, y=price_df['MA5'], name='5선', line=dict(color='orange', width=1.5)), row=1, col=1)
                fig_stock.add_trace(go.Scatter(x=price_df.index, y=price_df['MA20'], name='20선', line=dict(color='purple', width=1.5)), row=1, col=1)
                fig_stock.add_trace(go.Scatter(x=price_df.index, y=price_df['MA60'], name='60선', line=dict(color='green', width=1.5)), row=1, col=1)

                # 3. 거래량 바 차트 추가
                fig_stock.add_trace(go.Bar(x=price_df.index, y=price_df['Volume'], name='거래량', marker_color=colors), row=2, col=1)

                fig_stock.update_layout(height=500, margin=dict(l=20, r=20, t=20, b=20), xaxis_rangeslider_visible=False, showlegend=True)
                
                date_format = "%Y-%m-%d %H:%M" if timeframe == '분봉' else "%Y-%m-%d"
                fig_stock.update_xaxes(tickformat=date_format)
                
                st.plotly_chart(fig_stock, use_container_width=True)
            else:
                st.warning("선택한 주기에 해당하는 주가 데이터가 없습니다.")

        except Exception as e:
            st.error(f"데이터를 불러오지 못했습니다. (사유: {e})")

# ==========================================
# 우측 영역: 시장 랭킹 및 시장 지수 차트
# ==========================================
with col_right:
    st.markdown("### 오늘의 시장 랭킹")
    st.info("※ 코스피 기준, 최근 영업일 데이터입니다.")

    @st.cache_data(ttl=600)
    def load_ranking_data():
        return get_today_market_ranking()

    try:
        top_vol, top_gain, top_lose = load_ranking_data()
        
        ranking_type = st.radio("랭킹 탭 선택", ["상승률 상위", "하락률 상위", "거래량 상위"], horizontal=True, label_visibility="collapsed")
        
        if ranking_type == "상승률 상위":
            st.dataframe(top_gain, hide_index=True, use_container_width=True, height=250)
        elif ranking_type == "하락률 상위":
            st.dataframe(top_lose, hide_index=True, use_container_width=True, height=250)
        elif ranking_type == "거래량 상위":
            st.dataframe(top_vol, hide_index=True, use_container_width=True, height=250)
            
    except Exception as e:
        st.error(f"랭킹 데이터를 불러올 수 없습니다. (에러: {e})")

# ==========================================
    # 기업이 선택되었을 때만 시장 지수 흐름 표시
    # ==========================================
    if st.session_state.selected_company:
        st.divider()

        st.markdown("### 시장 지수 흐름")
        
        # 1. 선택된 기업의 시장구분 가져오기
        company_market = st.session_state.selected_company.get("시장구분", "코스닥")
        
        # 2. 라디오 버튼의 기본 인덱스 매핑 (코스닥=0, 코넥스=1, 유가=2)
        default_market_idx = 0 # 기본값 코스닥
        if "코넥스" in company_market:
            default_market_idx = 1
        elif "유가" in company_market or "KOSPI" in company_market.upper() or "코스피" in company_market:
            default_market_idx = 2
            
        # 3. 계산된 인덱스를 바탕으로 라디오 버튼 렌더링
        target_market = st.radio("시장 선택", ["코스닥", "코넥스", "유가"], index=default_market_idx, horizontal=True, label_visibility="collapsed")
        
        try:
            index_df = get_market_index(target_market)
            
            if not index_df.empty:
                hover_text_idx = [
                    f"날짜: {idx.strftime('%Y년 %m월 %d일')}<br>지수: {row['Close']:,.2f} 포인트"
                    for idx, row in index_df.iterrows()
                ]
                
                fig_index = go.Figure(data=[go.Scatter(
                    x=index_df.index, y=index_df['Close'], mode='lines', 
                    line=dict(color='purple', width=2), name="지수",
                    text=hover_text_idx, hoverinfo='text'
                )])
                fig_index.update_layout(height=300, margin=dict(l=20, r=20, t=20, b=20))
                fig_index.update_xaxes(tickformat="%Y-%m-%d")
                
                st.plotly_chart(fig_index, use_container_width=True)
                
                if len(index_df) > 1:
                    prev_date_idx = index_df.index[-2].strftime('%Y년 %m월 %d일')
                    prev_close_idx = index_df['Close'].iloc[-2]
            else:
                st.warning(f"{target_market} 시장 데이터를 불러올 수 없습니다.")
                
        except Exception as e:
            st.error(f"지수 데이터를 불러오지 못했습니다. (사유: {e})")