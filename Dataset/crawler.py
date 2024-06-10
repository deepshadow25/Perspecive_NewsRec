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

# 전처리 함수 정의
def preprocessing(d):
    d = d.lower()
    d = re.sub(r'[a-z0-9\-_.]{3,}@[a-z0-9\-_.]{3,}(?:[.]?[a-z]{2})+', ' ', d)
    d = re.sub(r'‘’ⓒ\'\"“”…=□*◆:/_]', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^\s|\s$', '', d)
    # d = re.sub(r'[\<br\>]','',d)
    d = re.sub(r'[<*>_="/]', '', d)
    return d

# Base URL 설정
"""
페이지수를 볼 수 있는 네이버 뉴스 주소 
(일반 뉴스는 .../main/main.naver?... 주소로 이루어짐)
'https://news.naver.com/main/list.naver?
mode=LSD&
mid=shm&
sid1=100&   -- 카테고리
date={date}& -- 상세카테고리
page={page}' -- 페이지

sid1 (카테고리) : 100(정치), 101(경제), 102(사회), 103(생활문화), 104(세계), 105(IT과학), 106(연예), 107(스포츠), 110(오피니언)

sid2 (상세카테고리) : 
"""




# Base URL 설정

base_url = 'https://news.naver.com/main/list.naver?mode=LSD&mid=shm&date={date}&page={page}'
ua = UserAgent()
headers = {'User-Agent':ua.random}

# 예외 단어 처리 - 재사용하기 위해 컴파일로 미리 저장.
exclude_keywords = re.compile(r'(속보|포토|헤드라인|지지율|여론조사|기념촬영|운세|날씨|주요뉴스|간추린)')

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
       
        # 제목내 예외단어 발견 or 한글이 없을 시 추출 건너뛰기 (넘어가기)
        if exclude_keywords.search(title_text) or len(re.sub("[a-zA-Z\s,.0-9\'’?…s\-$\{\}\[\]\(\)]+", "", preprocessing(title_text)))==0:
            continue
    
        # 기사 링크 태그, 주소, 요약 태그, 기자 태그
        link_tag = title_tag.find('a')
        article_url = link_tag['href']
        source_tag = article.find('span', class_='writing')
        

        # 기사별 메타데이터 딕셔너리 생성
        article_dict = {
            'title': title_text, # 뉴스제목
            'link': article_url, # 뉴스링크
            'media': source_tag.get_text(strip=True) if source_tag else '' # 언론사
        }
        
        # 여러 기사에 대해 메타데이터 작성
        article_data_list.append(article_dict)

    return article_data_list, dom

# 다음 페이지 넘어가기 : 최대 100페이지 전까지 정의
def get_next_page(dom, current_page):
    if current_page < 101:
        next_page_tag = dom.select_one(f'.paging a[href*="page={current_page + 1}"]')
        if next_page_tag:
            return urljoin(base_url, next_page_tag['href'])
    return None

# 일자별 크롤링 함수
def generate_dates(date):
    current_date = date
    while current_date <= date:
        yield current_date
        current_date += timedelta(days=1)

# 댓글 통계 가져오는 함수

        
# 기사 본문, 기자 정보 수집 함수
def fetch_article_data(article_url):
    resp = get(article_url, headers=headers)
    article_dom = BeautifulSoup(resp.text, 'html.parser')


    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    
    # 이미지 태그, 요약 태그 걸러내기 : 클러스터링 성능 강화
    # 동영상은 별도 태그여서 본 과정 안 거침
    img_tag = content_tag.find('img')
    if img_tag:
        img_tag.extract()
        
    em_tag = content_tag.find('em')
    if em_tag:
        em_tag.extract()
    
    sum_tag = content_tag.find('strong')
    if sum_tag:
        sum_tag.extract()
    
    # 기사 본문 전처리
    content = preprocessing(content_tag.get_text(strip=True)) if content_tag else ''
    
    # # 문장 수 제한 (10문장 이상)
    if len(content.split('.')) < 10:
        content = ''
 
    # 기자 정보 추출
    reporter_tag = article_dom.select_one('div.byline span')
    reporter = reporter_tag.get_text(strip=True) if reporter_tag else ''

    article_data = {
        'link': article_url, # 기사링크
        'article': content,  # 기사본문
        'reporter': reporter # 기자
    }

    return article_data


## 기사 본문 추가 전처리 함수
def refine_article(df):
    # 기사 끝부분 불필요한 부분
    # ".....입니다. 제보 ~~ 더보기 등." 에서 제보 부분부터 걸러내는 방식.
    m5_list = ['더팩트']
    # m3_list = ['kbc광주방송']
    m2_list = ['YTN', 'MBC', 'KBS', 'MBN', '채널A', 'kbc광주방송']
    m1_list = ['SBS', 'TV조선', 'JTBC']
    
    new_articles = []

    for media, article in zip(df['media'], df['article']):
        # 특정 문자 기준으로 자르고 남는 부분 처리
        if '※' in article:
            article = ','.join(article.split('※')[:-1])
        elif '#' in article:
            article = ','.join(article.split('#')[:1])
            
        # 괄호로 시작하는 기사본문 중 맨 앞 괄호 내용 제거
        if len(article) > 0:
            if article[0] == '[':
                article = ','.join(article.split(']')[1:])
            elif article[0] == '(':
                article = ','.join(article.split(')')[1:])
            elif article[0] == '【':
                article = ','.join(article.split('】')[1:])    
        
        # media에 따른 article 수정
        if media in m5_list:
            new_articles.append(','.join(article.split('.')[:-5]))
        # elif media == m3_list:
        #     new_articles.append(','.join(article.split('.')[:-3]))
        elif media in m2_list:
            new_articles.append(','.join(article.split('.')[:-2]))
        elif media in m1_list:
            new_articles.append(','.join(article.split('.')[:-1]))
        else:
            new_articles.append(article)
    
    # 수정된 article 값을 데이터프레임에 반영
    df['article'] = new_articles
    
    return df
    

## 기사 메타데이터 합치기
def main(date_str):
    date = datetime.strptime(date_str, '%Y-%m-%d')
    
    csv_filename = f'News_{str(date)[:10]}.csv'

    try:
        all_articles = []

        for single_date in tqdm(generate_dates(date)):
            date_str = single_date.strftime('%Y%m%d')
            page = 1
            url = base_url.format(date=date_str, page=page)
            
            
            while url and page <= 100:
                article_data_list, dom = fetch_articles(url)
                all_articles.extend(article_data_list)
                url = get_next_page(dom, page)
                page += 1
                time.sleep(1)  # 서버에 부담을 주지 않도록 잠시 대기

        # # 메타데이터 데이터프레임 생성 + 메타데이터 백업
        df1 = pd.DataFrame(all_articles)
        df1.drop_duplicates(ignore_index=True)
        metadata_filename = f'metadata_{str(date)[:10]}.csv'
        df1.to_csv(f'./Naver_News/{metadata_filename}', index=False, encoding='utf-8-sig')

        print(f"메타데이터를 파일로 저장했습니다: {metadata_filename}")

        # 기사 본문, 기자 정보 리스트에 저장하기
        # df1 = pd.read_csv(f'./Naver_News/{metadata_filename}', encoding='utf-8-sig')
        article_data_list = []
        for url in tqdm(list(df1['link'])):
            article_data = fetch_article_data(url)
            article_data_list.append(article_data)

        # 본문, 기자 정보 데이터프레임 만들기
        df2 = pd.DataFrame(article_data_list)
        
        # 데이터프레임 합치기
        df = pd.merge(df1, df2)

        # 데이터프레임 열 순서 바꾸기
        df = df[['media', 'reporter', 'title', 'link', 'article']]

        # 중복, 빈 본문 기사 제거
        df.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=True)
        
        # 기사 본문 추가전처리
        
        df = refine_article(df)
        
        # 열 이름 변경
        df.columns = ['media', 'reporter', 'title', 'link', 'article']
        
        df.to_csv(f'./Naver_News/{csv_filename}', index=False, encoding='utf-8-sig')
        
        return df
        
    except (ProtocolError, ConnectionError, UnboundLocalError, ChunkedEncodingError) as e:
        print (f'{e} occured..!!')
        return df

    finally:
        # CSV 파일로 저장
        
        df = pd.read_csv(f'./Naver_News/{csv_filename}', encoding='utf-8-sig')
        df.dropna(subset=['article'], inplace=True, axis=0)
        df.to_csv(f'./Naver_News/{csv_filename}', index=False, encoding='utf-8-sig')

        print(f"CSV 파일로 저장되었습니다: {csv_filename}")
    
    
# parser 작동 구문

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='뉴스 기사 크롤러')
    parser.add_argument('--date', type=str, required=True, help='수집할 기사의 발행일자 (예: 2024-04-20)')
    args = parser.parse_args()

    main(args.date)

