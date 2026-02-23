from elasticsearch import Elasticsearch
from elasticsearch import helpers
import pandas as pd
import json
import re

def get_stock_info():
    base_url = "http://kind.krx.co.kr/corpgeneral/corpList.do"    
    method = "download"
    url = "{0}?method={1}".format(base_url, method)   
    df = pd.read_html(url, header=0, encoding='euc-kr')[0]
    
    # 1. 종목코드 포맷팅
    df['종목코드'] = df['종목코드'].apply(lambda x: f"{x:06}")     
    
    # 2. 불필요한 열(지역) 제거
    if '지역' in df.columns:
        df = df.drop(columns=['지역'])
        
    # 3. 데이터 전처리 (결측치 처리 및 문자열 분리)
    df['업종'] = df['업종'].fillna('')
    df['주요제품'] = df['주요제품'].fillna('')
    
    # 공백으로 업종 분리
    df['업종_리스트'] = df['업종'].apply(lambda x: x.split() if x else [])
    
    # '및' 또는 ',' 기준으로 주요제품 분리
    df['주요제품_리스트'] = df['주요제품'].apply(lambda x: [item.strip() for item in re.split(r'및|,', x) if item.strip()] if x else [])
    
    return df

if __name__ == "__main__":
    df = get_stock_info()
    json_str = df.to_json(orient='records')
    json_records = json.loads(json_str)

    # Elasticsearch 연결
    es = Elasticsearch("http://localhost:9200", request_timeout=30)
    index_name = 'stock_info'
    
    es.options(ignore_status=[400, 404]).indices.delete(index=index_name)
    es.options(ignore_status=[400]).indices.create(index=index_name)
    
    action_list = []
    for row in json_records:
        record = {
            '_op_type': 'index',
            '_index': index_name,
            '_source': row
        }
        action_list.append(record)
        
    helpers.bulk(es, action_list)
    print("✅ 데이터 전처리 및 Elasticsearch 적재 완료!")