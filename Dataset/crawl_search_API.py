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
from time import sleep, localtime, strftime
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
    d = re.sub(r'[<*>_="/]', '', d)
    return d

# 예외 단어 처리 - 재사용하기 위해 컴파일로 미리 저장.
exclude_keywords = re.compile(r'(속보|포토|헤드라인|지지율|여론조사|기념촬영|운세|날씨|주요뉴스|간추린)')

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
                    'title': preprocessing(item.get('title', '')), # 기사제목
                    'link': item.get('link', ''),                  # 네이버뉴스 링크
                })

            article_count += 1

            # 2초 대기
            sleep(2)
        else:
            print("Error Code:" + rescode)

    # 데이터프레임 생성, 전처리
    df = pd.DataFrame(data_list)
    df.drop_duplicates('link', inplace=True, ignore_index=True)
   
    return df


# 기사 본문 수집 함수
def fetch_article(article_url):
    resp = get(article_url)
    article_dom = BeautifulSoup(resp.text, 'html.parser')
    
    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
    

    if content_tag is None:
        pass
    else:
        img_tag = content_tag.find('img')
        if img_tag:
            img_tag.extract()
        else:
            pass
            
        em_tag = content_tag.find('em')
        if em_tag:
            em_tag.extract()
        
        sum_tag = content_tag.find('strong')
        if sum_tag:
            sum_tag.extract()
    content = preprocessing(content_tag.get_text(strip=True)) if content_tag else ''
    
    # # 문장 수 제한 (10문장 이상)
    if len(content.split('.')) < 10:
        content = ''
        
    # 언론사 정보 추출
    source_tag = article_dom.select_one('meta[property="og:article:author"]')
    source = source_tag['content'] if source_tag else ''
    
    article_data = {
        'link': article_url,
        'article': content,
        'media': source,
    }

    return article_data

## 기사 본문 추가 전처리 함수
def refine_article(df):
    # 기사 끝부분 불필요한 부분
    # ".....입니다. 제보 ~~ 더보기 등." 에서 제보 부분부터 걸러내는 방식.
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


def main(url, query):
    try:
        df1 = crawl(url)
        
        article_data_list = []
        for link in tqdm(list(df1['link'])):
            article_data = fetch_article(link)
            article_data_list.append(article_data)
            sleep(1)

        df2 = pd.DataFrame(article_data_list)
        df = pd.merge(df1, df2)
        df = df[['media', 'title', 'link','article']]

        
        # 중복, 빈 본문 기사 제거
        df.drop_duplicates(subset=None, keep='first', inplace=True, ignore_index=True)
        
        # 기사 본문 추가전처리
        df = refine_article(df)
        df.dropna(subset=['article'], inplace=True)
        
        # 언론사 열 제거 (전처리에만 쓰임)
        df = df.loc[:, ['title', 'link', 'article']]
        
        # 열 이름 변경
        df.columns = ['title', 'link', 'article']
        
    except (ProtocolError, ConnectionError, UnboundLocalError, ChunkedEncodingError) as e:
        print (f'{e} occured..!!')
    
    finally:
        # CSV 파일로 저장
        nowtime = strftime(r'%Y%m%d', localtime())
        csv_filename = f'{query}_{str(nowtime)}.csv'
        df.to_csv(f'./{csv_filename}', index=False, encoding='utf-8-sig')
        print(f"CSV 파일로 저장되었습니다: {csv_filename}")

    

if __name__=="__main__":
    parser = argparse.ArgumentParser(description='API, 검색어 기반 크롤러')
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&start=1"
    args = parser.parse_args()
    
    main(url, query)
    
