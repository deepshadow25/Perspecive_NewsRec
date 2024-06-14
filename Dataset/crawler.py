# * python 3.9
"""
python crawler.py
"""

# Import Library
from requests import get
from requests.compat import urljoin
from bs4 import BeautifulSoup
from datetime import datetime, timedelta, date
from fake_useragent import UserAgent

from urllib3.exceptions import *
from requests.exceptions import *

from tqdm import tqdm
import pandas as pd
import argparse
import re
import json
import time

import mysql.connector
from mysql.connector import Error, connect
from datetime import datetime


# 전처리 함수 정의
def preprocessing(d):
    d = d.lower()
    d = re.sub(r'[a-z0-9\-_.]{3,}@[a-z0-9\-_.]{3,}(?:[.]?[a-z]{2})+', ' ', d)
    d = re.sub(r'‘’ⓒ\'\"“”…=□*◆:/_]', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^\s|\s$', '', d)
    d = re.sub(r'[<*>_="/]', '', d)
    return d

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

        
# 기사 본문 수집 함수
def fetch_article_data(article_url):
    resp = get(article_url, headers=headers)
    article_dom = BeautifulSoup(resp.text, 'html.parser')

    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    
    # 이미지 태그, 요약 태그 걸러내기 : 클러스터링 성능 강화
    # 동영상은 별도 태그여서 본 과정 안 거침
    if content_tag is None:
        pass
    else:
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
    
    # 문장 수 제한 (10문장 이상)
    if len(content.split('.')) < 10:
        content = ''

    article_data = {
        'link': article_url, # 기사링크
        'article': content,  # 기사본문
        }

    return article_data


# 기사 본문 추가 전처리 함수
def refine_article(df):
    """
    기사 끝부분 불필요한 부분  거르는 함수
    ".....입니다(기사 내용). 제보 ~~ 더보기 등." 에서 제보 부분부터 걸러내는 방식.
    """
    m5_list = ['더팩트']
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
        elif media in m2_list:
            new_articles.append(','.join(article.split('.')[:-2]))
        elif media in m1_list:
            new_articles.append(','.join(article.split('.')[:-1]))
        else:
            new_articles.append(article)
    
    # 수정된 article 값을 데이터프레임에 반영
    df['article'] = new_articles
    
    return df

# MySQL DB(서버) 연결 함수
def create_connection(host_name, user_name, user_password, db_name):
    try:
        connection = connect(
            host=host_name,
            user=user_name,
            password=user_password,
            database=db_name
        )
        print("Connection to MySQL DB successful")
    except Error as e:
        print(f"The error '{e}' occurred")
        return None
    return connection

# MySQL 쿼리문 실행 함수
def execute_query(connection, query):
    cursor = connection.cursor()
    try:
        cursor.execute(query)
        connection.commit()
        print("Query executed successfully")
    except mysql.connector.Error as e:
        print(f"The error '{e}' occurred")


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
                time.sleep(0.7)  # 서버에 부담을 주지 않도록 잠시 대기

        # # 메타데이터 데이터프레임 생성 + 메타데이터 백업
        df1 = pd.DataFrame(all_articles)
        df1.drop_duplicates(ignore_index=True)
                
        article_data_list = []
        for url in tqdm(list(df1['link'])):
            article_data = fetch_article_data(url)
            article_data_list.append(article_data)
            time.sleep(0.7)

        # 본문, 기자 정보 데이터프레임 만들기
        df2 = pd.DataFrame(article_data_list)
        
        # 데이터프레임 합치기
        df = pd.merge(df1, df2)

        # 데이터프레임 열 순서 바꾸기
        df = df[['title', 'link', 'article']]

        # 중복, 빈 본문 기사 제거
        df.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=True)
        
        # 기사 본문 추가전처리, 빈 본문 행 제거
        df = refine_article(df)
        df.dropna(subset=['article'], inplace=True)
        
        # 열 이름 변경
        df.columns = ['title', 'link', 'article']
        
        # SQL 서버 연결. "db" DB에 연결
        # 언론사, 기자, 기사제목, 기사링크, 기사본문을 기본 데이터로 지정 + "news" 테이블에 정보 저장
        connection = create_connection(host_name, user_name, user_password, db_name)
        if connection:
            metadata_table_sql = """
            CREATE TABLE IF NOT EXISTS news (
                title TEXT,
                link VARCHAR(255) UNIQUE,
                article TEXT
            )
            """
            execute_query(connection, metadata_table_sql)
            
            insert_sql = """
            INSERT IGNORE INTO news (title, link, article)
            VALUES (%s, %s, %s, %s, %s)
            """
            data = [tuple(x) for x in df.values]
            cursor = connection.cursor()
            cursor.executemany(insert_sql, data)
            connection.commit()
            print("Data inserted successfully")

            # 중복데이터 별도 처리 단계 (중복 제거되지 않을 경우 추가로 처리)
            cleanup_queries = [
                "CREATE TEMPORARY TABLE news_temp AS SELECT * FROM news WHERE article IS NOT NULL AND TRIM(article) != '';",
                "TRUNCATE TABLE news;",
                "INSERT INTO news SELECT * FROM news_temp;",
                "DROP TABLE news_temp;"
            ]
            for query in cleanup_queries:
                execute_query(connection, query)
                
            
            connection.close()
        
    except (ProtocolError, ConnectionError, UnboundLocalError, ChunkedEncodingError, mysql.connector.Error) as e:
        print (f'{e} occured..!!')
        



if __name__ == "__main__":
    # MySQL 서버 연결에 필요한 ip주소, 사용자 이름, 비밀번호, db이름 설정
    host_name = "DB.Server.Ip.Address" # ip 주소
    user_name = "Username" # 사용자 이름
    user_password = "Password" # 비밀번호
    db_name = "DBName"     # db 이름
    
    main((date.today()).strftime("%Y-%m-%d"))

