from flask import Flask, request
from sentence_transformers import SentenceTransformer
from news_service.similarity import find_similar_news
from news_service.clustering import clustering
from news_service.database import get_news_dataset
from news_service.article_crawling import fetch_article_data
from news_service.summary import summarize_article

app = Flask(__name__)


@app.route('/news_service', methods=['GET', 'POST'])
def news_service():
    # 현재 읽고 있는 뉴스 url 받아서 본문 크롤링
    data = request.get_json()
    url = data.get('url')
    target_data = fetch_article_data(url)  # 현재 읽고 있는 뉴스 크롤링
    target_article = target_data['article']
    target_summary1 = summarize_article(target_article)

    target_summary = " ".join(target_summary1)  # 요약문 하나로 합치기

    model = SentenceTransformer('bongsoo/kpf-sbert-128d-v1')  # 임베딩 모델

    similar_news_index = find_similar_news(
        target_summary, model)  # 유사한 기사 찾기

    various_news_index = clustering(
        target_article, similar_news_index)  # 클러스터링

    various_news = get_news_dataset(
        '''SELECT link FROM news''')
    
    if url in various_news['link']:
        same_news_index=various_news[various_news['link']==url].index
        various_news_index.remove(same_news_index)

    various_news = various_news.loc[various_news_index][:3]  # 클러스터링 결과
    # JSON 형식으로 반환 (추천 기사 + 현재 기사 요약문)
    return {
        "news": {"link1": list(various_news[['link']].iloc[0].values),
                 "link2": list(various_news[['link']].iloc[1].values),
                 "link3": list(various_news[['link']].iloc[2].values)},
        "summary": {
            "sentence1": target_summary1[0],
            "sentence2": target_summary1[1],
            "sentence3": target_summary1[2]}
    }


if __name__ == '__main__':

    # 모델 로드
    app.debug = True
    app.run('0.0.0.0', port=5000)
