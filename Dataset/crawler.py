## 사용방법
"""
python crawler.py --date 2024-04-20
"""

# Import Library
from crawLib import *
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


# Base URL 설정

base_url = 'https://news.naver.com/main/list.naver?mode=LSD&mid=shm&date={date}&page={page}'
ua = UserAgent()
headers = {'User-Agent':ua.random}


        
## 기사 수집 함수
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
