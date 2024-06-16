import pandas as pd
from news_service.split_into_paragraphs import split_into_paragraphs
from bertopic import BERTopic
import faiss
import numpy as np
from sklearn.feature_extraction.text import CountVectorizer
from news_service.database import get_embedding_dataset, get_news_dataset
from sentence_transformers import SentenceTransformer


# 클러스터
def clustering(target_article, similar_news):
    db_paragraph_data = get_news_dataset(
        '''SELECT * FROM db_paragraph_data''')  # DB에서 데이터 가져오기
    db_paragraph_embeddings = get_embedding_dataset(
        '''SELECT paragraph_embedding FROM db_paragraph_embeddings''')  # DB에서 단락임베딩 데이터 가져오기
    db_paragraph_embeddings = db_paragraph_embeddings[db_paragraph_data['index'].isin(
        similar_news)]  # 유사한 기사 데이터만 가져오기
    db_paragraph_data = db_paragraph_data[db_paragraph_data['index'].isin(
        similar_news)]  # 유사한 기사 데이터만 가져오기

    # 단락 별로 문장 자르기 (3줄)#
    # paragraphs=similar_news['article'].apply(split_into_paragraphs)

    # paragraph_data=[]
    # for i, data in enumerate(paragraphs.values):
    #    for j in range(len(data)):
    #        paragraph_data.append([paragraphs.index[i]]+[data[j]])

    # paragraph_data=pd.DataFrame(
    #    data=paragraph_data,
    #    columns=['index','paragraph'])

    # 현재 읽고 있는 기사의 단락 데이터
    target_paragraphs = split_into_paragraphs(target_article)
    target_paragraph_data = []
    for data in target_paragraphs:
        target_paragraph_data.append([-1]+[data])

    target_paragraph_data = pd.DataFrame(
        data=target_paragraph_data,
        columns=['index', 'paragraph'])

    model = SentenceTransformer('bongsoo/kpf-sbert-128d-v1')

    target_embeddings = model.encode(
        target_paragraph_data['paragraph'].tolist())  # 현재 읽고 있는 기사 단락 임베딩

    # 현재 읽고 있는 기사 데이터와 유사한 기사 데이터를 합쳐서 훈련 데이터로 들어감
    train_paragraph_embeddings = np.vstack(
        (target_embeddings, db_paragraph_embeddings))
    train_paragraph_data = pd.concat(
        [target_paragraph_data, db_paragraph_data], axis=0)

    # BERTopic을 이용한 클러스터링
    model = BERTopic(embedding_model='bongsoo/kpf-sbert-128d-v1',
                     min_topic_size=5)

    topics, probs = model.fit_transform(
        documents=train_paragraph_data['paragraph'], embeddings=train_paragraph_embeddings)  # 클러스터링 만들기
    train_paragraph_data['topic'] = topics  # 토픽 저장

    # 현재 읽고 있는 기사의 토픽 모델링
    target_paragraph_data = pd.merge(target_paragraph_data, train_paragraph_data[[
                                     'paragraph', 'topic']], on='paragraph', how='inner')
    # 토픽이 -1, 0은 제외
    target_paragraph_data = target_paragraph_data[target_paragraph_data['topic'] > 0]

    if len(target_paragraph_data) == 0:  # 만약 현재 읽고 있는 기사의 토픽이 없으면
        print('토픽이 없네요 ㅠㅠ')
        return similar_news[:3]  # 아무 기사3개 랜덤으로

    # 유사한 기사들의 토픽 모델링 결과 저장
    db_paragraph_data = pd.merge(db_paragraph_data, train_paragraph_data[[
        'paragraph', 'topic']], on='paragraph', how='inner')
    # 토픽 -1, 0 제외
    db_paragraph_data = db_paragraph_data[db_paragraph_data['topic'] > 0]

    # 토픽 간 거리 구하기
    topic_embeddings = model.topic_embeddings_
    topic_embeddings = topic_embeddings[1:]

    target_topic = target_paragraph_data['topic'].value_counts().idxmax()
    target_topic_embedding = topic_embeddings[target_topic]

    # 현재 토픽 개수 0~n
    num_topics = len(model.get_topic_freq()) - 1

    # faiss를 이용해서 토픽 간 코사인 유사도 계산
    index = faiss.IndexFlatIP(128)
    faiss.normalize_L2(topic_embeddings)
    index.add(topic_embeddings)
    distances, indices = index.search(np.expand_dims(
        target_topic_embedding, axis=0), num_topics)

    # 가장 유사도가 낮은 토픽 순으로 단락 정렬
    indices = indices[0][::-1]
    indices = np.delete(indices, np.where(indices == 0)[0][0])
    db_paragraph_data['topic'] = pd.Categorical(
        db_paragraph_data['topic'], categories=indices, ordered=True)
    db_paragraph_data = db_paragraph_data.sort_values('topic')

    # 토픽이 3개 이상이면
    if num_topics - 2 > 3:
        index_counts = db_paragraph_data.groupby(
            'topic')['index'].value_counts().rename('count').reset_index()
        most_common_index_per_topic = index_counts.loc[index_counts.groupby('topic')[
            'count'].idxmax()]
        most_common_index_per_topic=most_common_index_per_topic.drop_duplicates(subset='index') # 중복 제거

        return most_common_index_per_topic['index'].iloc[:3].tolist()

    else:
        db_paragraph_data=db_paragraph_data.drop_duplicates(subset='index') #중복 제거
        return db_paragraph_data['index'].iloc[:3].tolist()

        # 토픽이 3개 이하라면
        # 아무 뉴스 3개 추천

        # article_index = db_paragraph_data.drop_duplicates(subset='index')
        # db_paragraph_data = db_paragraph_data[db_paragraph_data['topic']
        #                                      != target_topic]

        # 클러스터링 된 토픽이 3개 이상이면
        # if num_topics - 2 > 3:
        #    article_index = db_paragraph_data[db_paragraph_data['topic'].isin(
        #        indices)]['index'].unique()

        # else:
        #    article_index = db_paragraph_data['index'].unique()  # 모든 기사 넘겨주기

        # return similar_news[similar_news.index.isin(article_index)]
