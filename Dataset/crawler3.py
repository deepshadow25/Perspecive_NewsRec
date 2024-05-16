import os
import sys
import json
import time
import pandas as pd
import urllib.request
from bs4 import BeautifulSoup
from requests import get, request
from requests.exceptions import HTTPError
from requests.compat import urljoin, urlparse

### 기사 제목, 링크, 언론사, 기자 정보 크롤링

# 네이버 API 기본 제공 코드
# for i in page:
#     url = "https://openapi.naver.com/v1/search/news.json?query=" + encText + f"page={i}"
#     request = urllib.request.Request(url)
#     request.add_header("X-Naver-Client-Id",client_id)
#     request.add_header("X-Naver-Client-Secret",client_secret)
#     response = urllib.request.urlopen(request)
#     rescode = response.getcode()
#     if(rescode==200):
#         response_body = response.read()
#         print(response_body.decode('utf-8'))
#     else:
#         print("Error Code:" + rescode)

# 메타데이터, 검색어 지정
client_id = "YOUR_API_ID" # 개발자센터에서 발급받은 Client ID 값
client_secret = "YOUR_API_PW" # 개발자센터에서 발급받은 Client Secret 값
user_agent = 'BROWSER_USER_AGENT'

query = input("검색어를 입력하세요 : ")
encText = urllib.parse.quote(query)

page = range(1, 30000)


# 데이터를 저장할 빈 리스트 생성
data_list = []

# 수집한 기사 수 초기화
article_count = 0

for i in page:
    url = f"https://openapi.naver.com/v1/search/news.json?query={encText}&start={i}"
    request = urllib.request.Request(url)
    request.add_header("X-Naver-Client-Id", client_id)
    request.add_header("X-Naver-Client-Secret", client_secret)
    response = urllib.request.urlopen(request)
    rescode = response.getcode()

    if rescode == 200:
        response_body = response.read()
        data = json.loads(response_body.decode('utf-8'))
        items = data.get('items', [])

        for item in items:
            data_list.append({
                'title': item.get('title', ''),
                'originallink': item.get('originallink', ''),
                'link': item.get('link', ''),
                'description': item.get('description', ''),
                'pubDate': item.get('pubDate', '')
            })
            
        article_count += 1
            
        # 500개씩 기사를 수집할 때마다 진행 상황 출력
        if article_count % 500 == 0:
            print(f"수집된 기사 수: {article_count}")

        # 5초 대기
        time.sleep(5)
    else:
        print("Error Code:" + rescode)

# 데이터프레임 생성
df = pd.DataFrame(data_list)

# CSV 파일로 저장
df.to_csv('naver_news.csv', index=False, encoding='utf-8-sig')

### 얻은 기사 링크로부터 기사 본문 추출
def download(url, params={}, data={}, headers={}, method='GET', retries=3):
    # if not canFetch(url, url):
    #     print('수집하면 안됨')    
    
    resp = request(method, url, params=params, data=data, headers=headers)
    
    try:
        resp.raise_for_status()
    except HTTPError as e:
         # 비교연산을 <= 이렇게 하면 두 번해서 한번만 하도록 하는게 좋다
        if 499 < resp.status_code and retries > 0: 
            print('재시도 중')
            sleep(9)
            return download(url, params, data, headers, method, retries-1)
        else:
            print(e.response.status_code)
            print(e.request.headers)
            print(e.response.headers)
            return None
        
    return resp


### ------gathering newses---

URLs = df['link']

NEWS_TEXT = []


optin = ['news.naver.com', 'n.news.naver.com']
optout = ['v.daum.net', '']

for i in sect:
    URLs.append({'link':f'https://news.naver.com/section/{i}', 'depth':0})
    
    while URLs and sectdic[i] < 100000:
        url = URLs.pop(-1)
        
        if url['depth'] > depth:
            Skipped.append(url['link'])
            continue
        
        resp = download(url['link'], headers={'user-agent':'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'})
        
        if resp is None:
            continue
        
        if re.search(r'text\/html', resp.headers['content-type']):
            dom = BeautifulSoup(resp.text, 'html.parser')
            
            linksA = dom.select('ul.Nlnb_menu_list li > a')
            linksB = dom.select('div[class$="_text"] > a[href]:has(> strong)')        
            linksC = dom.select('#dic_area a[href], #dic_area img[data-src]')
            article = dom.select_one('#dic_area')


            if article:
                with open(NEWS_TEXT+'/'+f'{i}-'+re.search(r'(\d{10})$', url['link']).group(1)+'.txt', 'w', encoding='utf8') as fp:
                    fp.write(article.get_text())
                    sectdic[i] += 1
            
            for link in linksA+linksB+linksC:
                if link.has_attr('href'):
                    newURL = link.attrs['href']
                if link.has_attr('src'):
                    newURL = link.attrs['src']
                if link.has_attr('data-src'):
                    newURL = link.attrs['data-src']
        
                if not re.match(r'#|Javascript|mailto|data', newURL):
                    normalizedURL = urljoin(url['link'], newURL)
                    
                    if urlparse(normalizedURL).netloc not in optin:
                        continue
                    
                    if normalizedURL not in Visited and \
                        normalizedURL not in Skipped and \
                        normalizedURL not in [url['link'] for url in URLs]:
                        URLs.append({'link':normalizedURL, 'depth':url['depth']+1})
                        
    if sectdic[i] > 100000:
        # URLs 를 초기화시키지 않으면 이전 섹션에서 탐색해둔 기사를 다음 섹션의 번호를 달아서 가져와버린다.
        # Visited, Skipped는 초기화시키면 안됨.
        URLs = []
        i += 1
                    
    # print(len(URLs), len(Visited)) # url이 몇 개인지, 몇 개 사이트를 방문했는지를 매 iteration마다 출력
