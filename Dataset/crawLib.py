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

# 기사 본문, 기자 정보 수집 함수
# 네이버뉴스 기준
def fetch_Naver_article(article_url):
    resp = get(article_url)
    article_dom = BeautifulSoup(resp.text, 'html.parser')
    
    # 기사 제목 추출
    title_tag = article_dom.select_one('h2#title_area')
    title = title_tag.get_text(strip=True) if title_tag else ''

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
        '제목': title,
        '기사링크': article_url,
        '기사전문': content,
        '언론사': source,
        '기': reporter
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
