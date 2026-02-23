import FinanceDataReader as fdr
from pykrx import stock
import yfinance as yf
import datetime
import pandas as pd

def get_stock_price_data(ticker, timeframe='월봉', market='유가'):
    """선택한 주기에 맞춰 주가 데이터를 가져오고 리샘플링합니다."""
    end_date = datetime.datetime.today()
    
    if timeframe == '월봉':
        start_date = end_date - datetime.timedelta(days=365 * 5) # 월봉은 최근 5년치
        df = fdr.DataReader(ticker, start_date, end_date)
        if not df.empty:
            # Pandas 최신 버전 권장에 따라 'ME' (Month End) 사용, 구버전은 'M'
            df = df.resample('ME').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
            
    elif timeframe == '주봉':
        start_date = end_date - datetime.timedelta(days=365 * 2) # 주봉은 최근 2년치
        df = fdr.DataReader(ticker, start_date, end_date)
        if not df.empty:
            df = df.resample('W-FRI').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last', 'Volume':'sum'}).dropna()
            
    elif timeframe == '일봉':
        start_date = end_date - datetime.timedelta(days=365) # 일봉은 최근 1년치
        df = fdr.DataReader(ticker, start_date, end_date)
        
    elif timeframe == '분봉':
        # 분봉은 yfinance를 활용 (최근 7일치, 1분 간격)
        suffix = ".KS" if "유가" in market else ".KQ"
        yf_ticker = f"{ticker}{suffix}"
        df = yf.download(yf_ticker, period="7d", interval="1m")
        # yfinance 최신 버전의 MultiIndex 컬럼 평탄화
        if not df.empty and isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
    return df

def get_market_index(market_name):
    """코스닥, 코넥스, 유가 지수 조회"""
    end_date = datetime.datetime.today()
    start_date = end_date - datetime.timedelta(days=365)
    
    if market_name == "코스닥":
        symbol = "KQ11"
    elif market_name == "유가":
        symbol = "KS11"
    else: 
        # 코넥스 지수(KNX)는 무료 API 지원이 제한적이므로 우선 코스닥으로 매핑하거나 빈 데이터프레임 반환
        symbol = "KQ11" 
        
    return fdr.DataReader(symbol, start_date, end_date)

def get_today_market_ranking():
    # 최근 5일 중 데이터가 존재하는 가장 최근 영업일 찾기
    df = pd.DataFrame()
    for i in range(5):
        target_date = (datetime.datetime.today() - datetime.timedelta(days=i)).strftime("%Y%m%d")
        temp_df = stock.get_market_ohlcv(target_date, market="KOSPI")
        if not temp_df.empty:
            df = temp_df
            break

    df = df.reset_index()
    df['종목명'] = df['티커'].apply(lambda x: stock.get_market_ticker_name(x))
    
    top_volume = df.sort_values(by='거래량', ascending=False).head(10)[['종목명', '종가', '거래량']]
    top_gainers = df.sort_values(by='등락률', ascending=False).head(10)[['종목명', '종가', '등락률']]
    top_losers = df.sort_values(by='등락률', ascending=True).head(10)[['종목명', '종가', '등락률']]
    
    return top_volume, top_gainers, top_losers

def get_stock_volume_rank(ticker):
    df = pd.DataFrame()
    for i in range(5):
        target_date = (datetime.datetime.today() - datetime.timedelta(days=i)).strftime("%Y%m%d")
        temp_df = stock.get_market_ohlcv(target_date, market="ALL")
        if not temp_df.empty:
            df = temp_df
            break

    if df.empty: return None, 0
    df = df.sort_values(by='거래량', ascending=False).reset_index()
    if ticker in df['티커'].values:
        rank = df[df['티커'] == ticker].index[0] + 1
        return rank, len(df)
    return None, len(df)