import pymysql
import pandas as pd
import numpy as np
import json


with open("db.json", "r") as f:  # DB에서 데이터 가져오기
    db = json.load(f)


def get_embedding_dataset(query):  # 임베딩 데이터 불러오기
    conn = pymysql.connect(
        host=db['host'],
        port=db['port'],
        user=db['user'],
        password=db['password'],
        db=db['db'],
        charset=db['charset']
    )

    try:
        with conn.cursor() as cursor:
            # DB에 저장된 기사 임베딩 가져오기
            cursor.execute(query)

            results = cursor.fetchall()

            db_embeddings = []

            # 임베딩을 TEXT형식으로 저장했기 때문에 numpy 형식으로 바꾸는 과정
            for row in results:
                db_embeddings.append(
                    np.fromstring(row[0][1:-1], dtype=np.float32, sep=' '))

            db_embeddings = np.array(db_embeddings)

    finally:
        conn.close()  # DB connect 종료

    return db_embeddings  # 임베딩 데이터 반환


def get_news_dataset(query):  # 뉴스기사 데이터 불러오기
    conn = pymysql.connect(
        host=db['host'],
        port=db['port'],
        user=db['user'],
        password=db['password'],
        db=db['db'],
        charset=db['charset']
    )

    db_news = pd.read_sql(query, conn)  # db에 저장된 뉴스기사 불러오기
    conn.close()

    return db_news
