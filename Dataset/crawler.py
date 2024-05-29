## 사용방법
"""
python crawler.py --start_date 2024-04-20 --end_date 2024-04-24
또는
python crawler.py --start_date 2024-04-20 --end_date 2024-04-24 --filter 로 filter 옵션 추가 가능
"""

# Import Library
from requests import get
from requests.compat import urljoin
from crawLib import *
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
from tqdm import tqdm
import pandas as pd
import argparse
import re
import time

# 전처리 함수 정의
def preprocessing(d):
    d = d.lower()
    d = re.sub(r'[a-z0-9\-_.]{3,}@[a-z0-9\-_.]{3,}(?:[.]?[a-z]{2})+', ' ', d)
    d = re.sub(r'‘’ⓒ\'\"“”…=□*◆:/_]', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^\s|\s$', '', d)
    d = re.sub(r'[\<br\>]','',d)
    d = re.sub(r'[<*>_="/]', '', d)
    return d

# Base URL 설정

base_url = 'https://news.naver.com/main/list.naver?mode=LSD&mid=shm&sid1=100&date={date}&page={page}'

# 예외 단어 처리 - 재사용하기 위해 컴파일로 미리 저장.
exclude_keywords = re.compile(r'(속보|포토)')

## 함수 정의

# 기사 가져오는 함수
def fetch_articles(url):
    resp = get(url)
    dom = BeautifulSoup(resp.text, 'html.parser')
    articles = dom.select('.content ul.type06_headline li')
    article_data_list = []

    # DOM select로 얻어낸 html 반복문 실행하여 데이터 추출
    for article in articles:
        title_tag = article.find('dt', class_=None)
        title_text = title_tag.get_text(strip=True)
       
        # 제목내 예외단어 발견시 추출 건너뛰기 (넘어가기)
        if exclude_keywords.search(title_text):
            continue
    
        # 기사 링크 태그, 주소, 요약 태그, 기자 태그
        link_tag = title_tag.find('a')
        article_url = link_tag['href']
        summary_tag = article.find('span', class_='lede')
        source_tag = article.find('span', class_='writing')
        
        # 기사 콘텐츠 (본문) 수집기
        # content = fetch_article_content(article_url)

        # 기사별 메타데이터 딕셔너리 생성
        article_dict = {
            'title': title_text,
            'link': article_url,
            'summary': summary_tag.get_text(strip=True) if summary_tag else '',
            'source': source_tag.get_text(strip=True) if source_tag else '',
            # 'content': content
        }
        
        # 여러 기사에 대해 메타데이터 작성
        article_data_list.append(article_dict)

    return article_data_list, dom

# 다음 페이지 넘어가기 : 최대 10페이지 전까지 정의
def get_next_page(dom, current_page):
    if current_page < 10:
        next_page_tag = dom.select_one(f'.paging a[href*="page={current_page + 1}"]')
        if next_page_tag:
            return urljoin(base_url, next_page_tag['href'])
    return None

# 일자별 크롤링 함수
def generate_dates(start_date, end_date):
    current_date = start_date
    while current_date <= end_date:
        yield current_date
        current_date += timedelta(days=1)
        
# 기사 본문, 기자 정보 수집 함수
def fetch_article_data(article_url):
    resp = get(article_url)
    article_dom = BeautifulSoup(resp.text, 'html.parser')
    
    # 기사 제목 추출
    # title_tag = article_dom.select_one('h2#title_area')
    # title = title_tag.get_text(strip=True) if title_tag else ''

    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    content = preprocessing(content_tag.get_text(strip=True)) if content_tag else ''

    # 언론사 정보 추출
    # source_tag = article_dom.select_one('meta[property="og:article:author"]')
    # source = source_tag['content'] if source_tag else ''
    
    # 기자 정보 추출
    reporter_tag = article_dom.select_one('div.byline span')
    reporter = reporter_tag.get_text(strip=True) if reporter_tag else ''

    article_data = {
        # 'title': title,
        'link': article_url,
        'content': content,
        # 'source': source,
        'reporter': reporter
    }

    return article_data

        
## 기사 메타데이터 수집하기
def main(start_date_str, end_date_str, filter_news):
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    all_articles = []

    for single_date in tqdm(generate_dates(start_date, end_date)):
        date_str = single_date.strftime('%Y%m%d')
        page = 1
        url = base_url.format(date=date_str, page=page)
        
        while url and page <= 10:
            article_data_list, dom = fetch_articles(url)
            all_articles.extend(article_data_list)
            url = get_next_page(dom, page)
            page += 1
            time.sleep(2)  # 서버에 부담을 주지 않도록 잠시 대기

    # 메타데이터 데이터프레임 생성 & 메타데이터 백업
    df1 = pd.DataFrame(all_articles)
    df1.drop_duplicates(ignore_index=True)
    metadata_filename = f'메타데이터_{str(start_date)[:10]}_{str(end_date)[:10]}.csv'
    if df1.empty == 0:
        df1.to_csv(f'./{metadata_filename}', index=False, encoding='utf-8-sig')
    print(f"메타데이터 파일을 저장했습니다: {metadata_filename}")

    # 기사 본문, 기자 정보 리스트에 저장하기
    article_data_list = []
    for url in tqdm(list(df1['link'])):
        article_data = fetch_article_data(url)
        article_data_list.append(article_data)

    # 본문, 기자 정보 데이터프레임 만들기
    df2 = pd.DataFrame(article_data_list)

    # 데이터프레임 합치기
    df = pd.merge(df1, df2)

    # 데이터프레임 열 순서 바꾸기
    df = df[['source', 'reporter', 'title', 'summary', 'content', 'link']]

    # 중복 제거
    df.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=True)

    # 열 이름 변경
    df.columns = ['언론사', '기자', '제목', '기사요약', '기사전문', '기사링크']
    
    if filter_news:
        df = filter_and_label(df)

    # CSV 파일로 저장
    csv_filename = f'뉴스기사_{str(start_date)[:10]}_{str(end_date)[:10]}.csv'
    df.to_csv(f'./{csv_filename}', index=False, encoding='utf-8-sig')

    print(f"CSV 파일로 저장되었습니다: {csv_filename}")





# parser 작동 구문

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='뉴스 기사 크롤러')
    parser.add_argument('--start_date', type=str, required=True, help='시작 날짜 (예: 2024-04-20)')
    parser.add_argument('--end_date', type=str, required=True, help='종료 날짜 (예: 2024-04-24)')
    parser.add_argument('--filter', action='store_true', help='특정 언론사만 남기기')
    args = parser.parse_args()

    main(args.start_date, args.end_date, args.filter)
