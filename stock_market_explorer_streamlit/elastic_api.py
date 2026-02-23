from datetime import datetime
from elasticsearch import Elasticsearch
from elasticsearch_dsl import Search

ES_HOST = 'http://localhost:9200'

def get_client():
    """Elasticsearch 클라이언트 생성"""
    return Elasticsearch(ES_HOST, request_timeout=30)


def search_index(index_name, field_name, match_name, max_results=100):
    """
    인덱스에서 필드 기반 검색 수행

    Args:
        index_name: 검색할 인덱스명
        field_name: 검색할 필드명
        match_name: 검색어
        max_results: 최대 결과 수 (기본 100)

    Returns:
        검색 결과 Response 객체
    """
    client = get_client()
    s = Search(index=index_name).using(client)
    s = s.query("multi_match", fields=field_name, query=match_name)
    s = s[:max_results]
    response = s.execute()
    return response


def search_index_with_date_range(index_name, field_name, match_name, start_date, end_date, max_results=100):
    """
    날짜 범위와 함께 인덱스 검색 수행

    Args:
        index_name: 검색할 인덱스명
        field_name: 검색할 필드명
        match_name: 검색어
        start_date: 시작 날짜
        end_date: 종료 날짜
        max_results: 최대 결과 수 (기본 100)

    Returns:
        검색 결과 Response 객체
    """
    client = get_client()
    s = Search(index=index_name).using(client)
    s = s.query("multi_match", fields=field_name, query=match_name)
    s = s.filter('range', 상장일={'gte': start_date, 'lte': end_date})
    s = s[:max_results]
    response = s.execute()
    return response


def get_all_indices():
    """사용 가능한 모든 인덱스 목록 조회"""
    client = get_client()
    return list(client.indices.get_alias(index="*").keys())

