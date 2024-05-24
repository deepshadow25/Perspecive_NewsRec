# 사용조건 및 방법
"""
반드시 각자 네이버 개발자센터에서 API 발급받아서 사용해야 함.
발급받은 ID는 client_id, 비밀번호는 client_secret에 입력하여 사용.

python crawl_search.py --filter
--filter는 사용할 경우에만 입력
터미널에 "검색어를 입력하세요" 라는 메시지가 뜨면 검색어 입력 ex) 정부
"""

# Import Libraries
from requests import get
from bs4 import BeautifulSoup
from tqdm import tqdm
from time import sleep
import argparse
import urllib.request
import pandas as pd
import json
import re

# 전처리 함수 정의
def preprocessing(d):
    d = d.lower()
    d = re.sub(r'[a-z0-9\-_.]{3,}@[a-z0-9\-_.]{3,}(?:[.]?[a-z]{2})+', ' ', d)
    d = re.sub(r'‘’ⓒ\'\"“”…=□*◆:/_]', ' ', d)
    d = re.sub(r'\s+', ' ', d)
    d = re.sub(r'^\s|\s$', '', d)
    d = re.sub(r'[\<br\>].', '', d)
    d = re.sub(r'[<*>_="/■□▷▶]', '', d)
    return d

# 예외 단어 처리 - 재사용하기 위해 컴파일로 미리 저장.
exclude_keywords = re.compile(r'(속보|포토)')

# 메타데이터, 검색어 지정
client_id = "YOUR_CLIENT_ID" # 개발자센터에서 발급받은 Client ID 값
client_secret = "YOUR_CLIENT_PWD" # 개발자센터에서 발급받은 Client Secret 값
user_agent = 'YOUR_WEB_USER_AGENT'

query = input("검색어를 입력하세요 : ")
encText = urllib.parse.quote(query)
# 페이지 (수집할 기사의 양) 수 지정. 최대 1000페이지 (1~1000) 지원
page = list(range(1, 1001))


# 기사 수집 함수 정의
def crawl(url):
    
    # 데이터를 저장할 빈 리스트 생성
    data_list = []

    # 수집한 기사 수 초기화
    article_count = 0
    
    # url 반복
    for i in tqdm(page):
        url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&start={i}"
        request = urllib.request.Request(url)
        # header 정보 추가
        request.add_header("X-Naver-Client-Id", client_id)
        request.add_header("X-Naver-Client-Secret", client_secret)
        request.add_header('User-Agent', user_agent)
        response = urllib.request.urlopen(request)
        rescode = response.getcode()

        if rescode == 200:
            response_body = response.read()
            data = json.loads(response_body.decode('utf-8'))
            items = data.get('items', [])

            for item in items:
                if exclude_keywords.search(item.get('title','')) or item.get('link','')[:25]!='https://n.news.naver.com/':
                    continue 
                data_list.append({
                    '제목': preprocessing(item.get('title', '')),
                    '원본링크': item.get('originallink', ''),
                    '기사링크': item.get('link', ''),
                    '기사요약': preprocessing(item.get('description', '')),
                    '발행일자': item.get('pubDate', '')
                })

            article_count += 1

            # 2초 대기
            sleep(2)
        else:
            print("Error Code:" + rescode)

    # 데이터프레임 생성, 전처리
    df = pd.DataFrame(data_list)
    df.drop_duplicates('기사링크', inplace=True, ignore_index=True)
    df.drop_duplicates(['기사링크', '원본링크'], keep='first', inplace=True, ignore_index=True)
    # df = df[str(df['기사링크'])[-8:] == 'sid=100']
    # for naver_link in tqdm(list(df['기사링크'])):
    #     if naver_link[:25] != 'https://n.news.naver.com' or naver_link[-8:] != 'sid=100':
    #         df.drop(axis=0)
    
    return df



# 기사 본문, 기자 정보 수집 함수
def fetch_article(article_url):
    resp = get(article_url)
    article_dom = BeautifulSoup(resp.text, 'html.parser')
    
    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    content = preprocessing(content_tag.get_text(strip=True)) if content_tag else ''

    # 언론사 정보 추출
    source_tag = article_dom.select_one('meta[property="og:article:author"]')
    source = source_tag['content'] if source_tag else ''
    
    # 기자 정보 추출
    reporter_tag = article_dom.select_one('div.byline span')
    reporter = reporter_tag.get_text(strip=True) if reporter_tag else ''

    article_data = {
        # 'title': title,
        '기사링크': article_url,
        '기사전문': content,
        '언론사': source,
        '기자': reporter
    }

    return article_data

# 특정 언론사 필터링 및 정치성향 라벨링 함수
def filter_and_label(df):
    """
    진보, 보수 성향 언론 4개씩 선정.
    진보 언론 : 한겨레, 경향신문, 프레시안, 오마이뉴스
    보수 언론 : 조선일보, 중앙일보, 동아일보, 문화일보
    """
    df_select = df[(df['언론사']=='조선일보') | (df['언론사']=='중앙일보') | (df['언론사']=='동아일보') | 
                   (df['언론사']=='한겨레') | (df['언론사']=='경향신문') | (df['언론사']=='프레시안') | 
                   (df['언론사']=='오마이뉴스') | (df['언론사']=='문화일보')]

    # 정치 성향 라벨링
    df_select['정치성향분류'] = [1 if x in ['한겨레', '경향신문', '프레시안', '오마이뉴스'] else 0 for x in df_select['source']]
    
    return df_select    

def main(url, query, filter_news):
    df1 = crawl(url)
    
    article_data_list = []
    for link in tqdm(list(df1['기사링크'])):
        article_data = fetch_article(link)
        article_data_list.append(article_data)

    df2 = pd.DataFrame(article_data_list)
    df = pd.merge(df1, df2)
    df = df[['언론사', '기자', '발행일자', '제목', '기사요약','기사전문', '기사링크', '원본링크']]
    
    if filter_news:
        df = filter_and_label(df)
    
    # CSV 파일로 저장
    csv_filename = f'네이버뉴스_{query}.csv'
    df.to_csv(f'./Naver_Politics_News/{csv_filename}', index=False, encoding='utf-8-sig')
    print(f"CSV 파일로 저장되었습니다: {csv_filename}")

    

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='API, 검색어 기반 크롤러')
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&start=1"
    parser.add_argument('--filter', action='store_true', help='특정 언론사 기사만 남기기')
    
    args = parser.parse_args()
    
    main(url, query, args.filter)
    
