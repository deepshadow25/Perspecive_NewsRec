# Defining Functions for News Crawling

# 한국어 기사 본문 전처리 함수
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
exclude_keywords = re.compile(r'(속보|포토|헤드라인|지지율|여론조사|기념촬영|운세|날씨)')

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
        if exclude_keywords.search(title_text) or len(re.sub('[a-zA-Z\s,.0-9\'()’?…s-$[]\{\}\\]+', '', preprocessing(title_text)))==0:
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

        
# 기사 본문, 기자 정보 수집 함수
def fetch_article_data(article_url):
    resp = get(article_url, headers=headers)
    article_dom = BeautifulSoup(resp.text, 'html.parser')


    # 기사 본문 추출
    content_tag = article_dom.select_one('article')
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
    df_select['정치성향분류'] = [1 if x in ['한겨레', '경향신문', '프레시안', '오마이뉴스'] else 0 for x in df_select['언론사']]
    
    return df_select
