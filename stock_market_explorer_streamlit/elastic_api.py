from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search
from sentence_transformers import SentenceTransformer

ES_HOST = 'http://localhost:9200'

# AI 모델은 전역으로 한 번만 로드하여 검색 속도 향상
embedding_model = SentenceTransformer('snunlp/KR-SBERT-V40K-klueNLI-augSTS')

def get_client():
    return Elasticsearch(ES_HOST, request_timeout=30)

def search_index(index_name, field_name, match_name, max_results=100):
    """
    기존의 키워드 기반 정확도 검색 수행
    """
    client = get_client()
    s = Search(using=client, index=index_name)
    
    # 검색 필드가 여러 개일 경우 (리스트 형태)
    if isinstance(field_name, list):
        s = s.query("multi_match", query=match_name, fields=field_name)
    # 단일 필드일 경우
    else:
        s = s.query("match", **{field_name: match_name})
        
    s = s.extra(size=max_results)
    response = s.execute()
    
    return response

def semantic_search(index_name, query_text, max_results=50):
    """
    의미 기반 통합 검색 (Vector Search) 수행
    """
    client = get_client()
    
    # 1. 사용자의 검색어를 벡터로 변환
    query_vector = embedding_model.encode(query_text).tolist()
    
    # 2. Elasticsearch 8.x의 kNN 검색 실행
    response = client.search(
        index=index_name,
        knn={
            "field": "text_vector",
            "query_vector": query_vector,
            "k": max_results,
            "num_candidates": 100
        },
        _source=["회사명", "종목코드", "시장구분", "업종", "주요제품", "상장일", "업종_리스트", "주요제품_리스트"] 
    )
    return response