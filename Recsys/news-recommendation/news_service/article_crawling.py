import requests
from bs4 import BeautifulSoup
import re


def preprocessing(d):  # 한국어 기사 본문 전처리 함수
    d = d.lower()
    d = re.sub(r'[a-z0-9\-_.]{3,}@[a-z0-9\-_.]{3,}(?:[.]?[a-z]{2})+', ' ', d)
    d = re.sub(r'‘’ⓒ\'\"“”…=□*◆:/_]', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^\s|\s$', '', d)
    d = re.sub(r'[<*>_="/■□▷▶]', '', d)
    return d


def fetch_article_data(article_url):  # 기사 본문, 기자 정보 수집 함수
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    resp = requests.get(article_url, headers=headers)
    if resp.status_code != 200:
        return "Failed to retrieve the article"

    article_dom = BeautifulSoup(resp.content, 'html.parser')

    # 특정 선택자를 사용하여 기사 본문 추출
    content_tag = article_dom.select_one(
        'article#dic_area.go_trans._article_content')

    content = preprocessing(content_tag.get_text(
        strip=True)) if content_tag else ''

    # 기자 정보 추출
    reporter_tag = article_dom.select_one('div.byline span') or \
        article_dom.select_one('p.byline') or \
        article_dom.select_one('span.byline')

    reporter = reporter_tag.get_text(strip=True) if reporter_tag else ''

    article_data = {
        "link": article_url,  # 기사 링크
        "article": content,  # 기사 본문
        "reporter": reporter  # 기자
    }

    return article_data
