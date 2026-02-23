from elasticsearch import Elasticsearch
from elasticsearch import helpers
from sentence_transformers import SentenceTransformer
import pandas as pd
import json
import re

def get_stock_info():
    base_url = "http://kind.krx.co.kr/corpgeneral/corpList.do"    
    method = "download"
    url = "{0}?method={1}".format(base_url, method)   
    df = pd.read_html(url, header=0, encoding='euc-kr')[0]
    
    df['종목코드'] = df['종목코드'].apply(lambda x: f"{x:06}")     
    if '지역' in df.columns:
        df = df.drop(columns=['지역'])
        
    df['업종'] = df['업종'].fillna('')
    df['주요제품'] = df['주요제품'].fillna('')
    df['업종_리스트'] = df['업종'].apply(lambda x: x.split() if x else [])
    df['주요제품_리스트'] = df['주요제품'].apply(lambda x: [item.strip() for item in re.split(r'및|,', x) if item.strip()] if x else [])
    
    # 🌟 통합검색을 위한 텍스트 합치기
    df['통합텍스트'] = df['회사명'] + " " + df['업종'] + " " + df['주요제품']
    
    return df

if __name__ == "__main__":
    print("⏳ 데이터를 다운로드하고 AI 모델을 불러옵니다. (최초 실행 시 모델 다운로드로 시간이 걸릴 수 있습니다.)")
    df = get_stock_info()
    
    # 🌟 한국어 문장 임베딩 모델 로드
    model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')
    
    print("🧠 텍스트를 벡터로 변환 중입니다...")
    # 통합텍스트를 768차원 벡터로 변환하여 새로운 컬럼에 저장
    df['text_vector'] = df['통합텍스트'].apply(lambda x: model.encode(x).tolist())

    json_str = df.to_json(orient='records')
    json_records = json.loads(json_str)

    es = Elasticsearch("http://localhost:9200", request_timeout=60)
    index_name = 'stock_info'
    
    # 🌟 벡터 검색을 위한 인덱스 매핑 정의
    mapping = {
        "mappings": {
            "properties": {
                "text_vector": {
                    "type": "dense_vector",
                    "dims": 768,
                    "index": True,
                    "similarity": "cosine" # 코사인 유사도 사용
                }
            }
        }
    }
    
    es.options(ignore_status=[400, 404]).indices.delete(index=index_name)
    es.options(ignore_status=[400]).indices.create(index=index_name, body=mapping)
    
    action_list = []
    for row in json_records:
        record = {
            '_op_type': 'index',
            '_index': index_name,
            '_source': row
        }
        action_list.append(record)
        
    print("💾 Elasticsearch에 데이터를 적재합니다...")
    helpers.bulk(es, action_list)
    print("✅ 데이터 전처리 및 벡터 적재 완료!")