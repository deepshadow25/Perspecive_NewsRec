import numpy as np
import faiss
import pandas as pd
from sentence_transformers import SentenceTransformer
import pymysql
from news_service.database import get_news_dataset, get_embedding_dataset


# 피어슨 상관계수 구하기
def pearson_similarity(a, b):
    return np.dot((a-np.mean(a)), (b-np.mean(b)))/((np.linalg.norm(a-np.mean(a)))*(np.linalg.norm(b-np.mean(b))))

# 현재 읽고 있는 기사와 유사한 기사 찾기


def find_similar_news(target_title, model):

    # db에 저장된 임베딩 데이터 불러오기
    query = 'SELECT summary_embedding FROM db_summary_embeddings'
    db_summary_embeddings = get_embedding_dataset(query)

    # 현재 읽고 있는 기사 요약문 임베딩
    target_summary_embedding = model.encode(target_title,
                                            normalize_embeddings=True)

    # 피어슨 상관계수 기반으로 계산
    threshold = 0.55  # 최소 유사도 threshold
    similar_list = []
    for i in range(len(db_summary_embeddings)):
        similarity = pearson_similarity(
            target_summary_embedding, db_summary_embeddings[i])

        if similarity > threshold:
            # threshold 이상이면 유사한 기사 리스트에 추가
            similar_list.append((similarity, i))

    # 유사도 기준 내림차순 정렬
    sorted_similar_list = sorted(
        similar_list, key=lambda x: x[0], reverse=True)

    # 100개만 추려서 반환
    if len(similar_list) > 100:
        return [item[1] for item in sorted_similar_list[:100]]

    # 100개 이하면 모두 반환
    else:
        return [item[1] for item in sorted_similar_list]

