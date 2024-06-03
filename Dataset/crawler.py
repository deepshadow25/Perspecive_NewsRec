## 사용방법
"""
python crawler.py --start_date 2024-04-20 --end_date 2024-04-24
또는
python crawler.py --start_date 2024-04-20 --end_date 2024-04-24 --filter 로 filter 옵션 추가 가능
"""

# Import Library
from requests import get
from requests.compat import urljoin
from bs4 import BeautifulSoup
from crawLib import *
from datetime import datetime, timedelta
from fake_useragent import UserAgent
from urllib3.exceptions import *
from requests.exceptions import *
from tqdm import tqdm
import pandas as pd
import argparse
import re
import json
import time

# Base URL 설정
base_url = 'https://news.naver.com/main/list.naver?mode=LSD&mid=shm&date={date}&page={page}'
ua = UserAgent()
headers = {'User-Agent':ua.random}
           #:'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36'}

# 예외 단어 처리 - 재사용하기 위해 컴파일로 미리 저장.
exclude_keywords = re.compile(r'(속보|포토|헤드라인|지지율|여론조사)')

## 함수 정의

# 기사 가져오는 함수
def fetch_articles(url):
    resp = get(url, headers=headers)
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
        
        if len(re.sub('[a-zA-Z\s]+', '', title_text))==0:
            continue
    
        # 기사 링크 태그, 주소, 요약 태그, 기자 태그
        link_tag = title_tag.find('a')
        article_url = link_tag['href']
        # summary_tag = article.find('span', class_='lede')
        source_tag = article.find('span', class_='writing')
        
        # 기사 콘텐츠 (본문) 수집기
        # content = fetch_article_content(article_url)

        # 기사별 메타데이터 딕셔너리 생성
        article_dict = {
            '제목': title_text,
            '기사링크': article_url,
            # '본문요약': summary_tag.get_text(strip=True) if summary_tag else '',
            '언론사': source_tag.get_text(strip=True) if source_tag else '',
            # 'content': content
        }
        
        # 여러 기사에 대해 메타데이터 작성
        article_data_list.append(article_dict)

    return article_data_list, dom

# 다음 페이지 넘어가기 : 최대 30페이지 전까지 정의
def get_next_page(dom, current_page):
    if current_page < 51:
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
    resp = get(article_url, headers=headers)
    article_dom = BeautifulSoup(resp.text, 'html.parser')
    
    # 기사 제목 추출
    # title_tag = article_dom.select_one('h2#title_area')
    # title = title_tag.get_text(strip=True) if title_tag else ''

    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    content = preprocessing(content_tag.get_text(strip=True)) if content_tag else ''
    
    # 문장 수 제한 (10문장 이상)
    if len(content) < 10:
        pass
 
    # 기사 요약(봇) 추출
    # summary = crawl_summaryBot(article_url)

    # 언론사 정보 추출
    # source_tag = article_dom.select_one('meta[property="og:article:author"]')
    # source = source_tag['content'] if source_tag else ''
    
    # 기자 정보 추출
    reporter_tag = article_dom.select_one('div.byline span')
    reporter = reporter_tag.get_text(strip=True) if reporter_tag else ''

    article_data = {
        # 'title': title,
        '기사링크': article_url,
        # '기사요약' : summary,
        '기사본문': content,
        # 'source': source,
        '기자': reporter
    }

    return article_data
        
## 기사 메타데이터 수집하기
def main(start_date_str, end_date_str, filter_news):
    start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
    end_date = datetime.strptime(end_date_str, '%Y-%m-%d')

    headers = {'User-Agent':ua.random}
    try:
        all_articles = []

        for single_date in tqdm(generate_dates(start_date, end_date)):
            date_str = single_date.strftime('%Y%m%d')
            page = 1
            url = base_url.format(date=date_str, page=page)
            
            
            while url and page <= 50:
                article_data_list, dom = fetch_articles(url)
                all_articles.extend(article_data_list)
                url = get_next_page(dom, page)
                page += 1
                time.sleep(1)  # 서버에 부담을 주지 않도록 잠시 대기

        # # 메타데이터 데이터프레임 생성 + 메타데이터 백업
        df1 = pd.DataFrame(all_articles)
        df1.drop_duplicates(ignore_index=True)
        metadata_filename = f'메타데이터_{str(start_date)[:10]}_{str(end_date)[:10]}.csv'
        df1.to_csv(f'./Naver_News/{metadata_filename}', index=False, encoding='utf-8-sig')

        print(f"메타데이터를 파일로 저장했습니다: {metadata_filename}")


        # 기사 본문, 기자 정보 리스트에 저장하기
        # df1 = pd.read_csv(f'./Naver_News/{metadata_filename}', encoding='utf-8-sig')
        article_data_list = []
        for url in tqdm(list(df1['기사링크'])):
            article_data = fetch_article_data(url)
            article_data_list.append(article_data)

        # 본문, 기자 정보 데이터프레임 만들기
        df2 = pd.DataFrame(article_data_list)

        # 데이터프레임 합치기
        df = pd.merge(df1, df2)

        # 데이터프레임 열 순서 바꾸기
        df = df[['언론사', '기자', '제목', '기사본문', '기사링크']]

        # 중복 제거
        df.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=True)

        # 열 이름 변경
        df.columns = ['언론사', '기자', '제목', '기사본문', '기사링크']
        
        if filter_news:
            df = filter_and_label(df)

        # df['기사요약'] = df.apply(lambda row: row['기사요약'] if row['기사요약'] != '요약없음' else row['본문요약'], axis=1)

        df = df[['언론사', '기자', '제목', '기사본문', '기사링크']]
        df.columns = ['언론사', '기자', '제목', '기사본문', '기사링크']
                
        return df
        
    except (ProtocolError, ConnectionError, UnboundLocalError, ChunkedEncodingError) as e:
        print (f'{e}에러가 발생하였습니다... 이런 제길!!')
        return df

    finally:
        # CSV 파일로 저장

        csv_filename = f'뉴스기사_{str(start_date)[:10]}_{str(end_date)[:10]}.csv'
        df.to_csv(f'./Naver_News/{csv_filename}', index=False, encoding='utf-8-sig')

        print(f"CSV 파일로 저장되었습니다: {csv_filename}")
    


# parser 작동 구문

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='뉴스 기사 크롤러')
    parser.add_argument('--start_date', type=str, required=True, help='시작 날짜 (예: 2024-04-20)')
    parser.add_argument('--end_date', type=str, required=True, help='종료 날짜 (예: 2024-04-24)')
    parser.add_argument('--filter', action='store_true', help='특정 언론사만 남기기')
    args = parser.parse_args()

    main(args.start_date, args.end_date, args.filter)
