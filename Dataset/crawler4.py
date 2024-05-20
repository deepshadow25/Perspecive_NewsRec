"""
git clone https://github.com/nlpcl-lab/NaverNewsCrawler
python ./NaverNewsCrawler/main.py --start-date [] --end-date []
--target [Politics] --sub-target [(Only in Economics)]
"""

# from NaverNewsCrawler.korea_news_crawler import exceptions, articleparser, writer
from korea_news_crawler.articlecrawler2 import ArticleCrawler, Writer

import requests
from bs4 import BeautifulSoup
import csv
from datetime import datetime, timedelta
import time
import argparse

def download(url, headers={}, retries=3, timeout=10):
    try:
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        if retries > 0:
            print(f"Error: {e}. Retrying in 5 seconds...")
            time.sleep(5)
            return download(url, headers, retries - 1, timeout)
        else:
            print(f"Failed to retrieve {url} after multiple attempts.")
            return None

def crawl_naver_news(section, start_date, end_date, max_articles=20000):
    articles = []
    current_date = start_date
    base_url = "https://news.naver.com/main/list.naver?mode=LSD&mid=sec&sid1={section}&listType=paper&date={date}&page={page}"

    while len(articles) < max_articles and current_date <= end_date:
        page = 1
        while True:
            url = base_url.format(section=section, date=current_date.strftime("%Y%m%d"), page=page)
            print(f"Fetching: {url}")
            response = download(url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'})

            if response is None:
                break

            soup = BeautifulSoup(response.text, 'html.parser')
            
            # 기사가 없는 날인지 확인
            if soup.select_one('div.result_none'):
                print(f"No articles on {current_date.strftime('%Y-%m-%d')}")
                break

            article_list = soup.select('div.list_body.newsflash_body ul.type06 li dl dt a')
            
            # if not article_list and page == 1:  # 첫 페이지에 기사가 없으면 다음 날짜로
            #     break

            for link in article_list:
                article_url = link['href']
                article_response = download(article_url, headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'})
                if article_response is None:
                    continue

                article_soup = BeautifulSoup(article_response.text, 'html.parser')
                title = link.get_text(strip=True)
                
                body_elem = article_soup.select_one('#articleBodyContents')
                body = body_elem.get_text(strip=True) if body_elem else "N/A"
                
                press_elem = article_soup.select_one('.press_logo img')
                press = press_elem['title'] if press_elem else "N/A"
                
                date_elem = article_soup.select_one('.t11')
                date = date_elem.get_text(strip=True) if date_elem else "N/A"

                articles.append({'title': title, 'body': body, 'url': article_url, 'date': date, 'press': press})
                if len(articles) >= max_articles:
                    break
            

            #다음 페이지가 있는지 확인
            paging_div = soup.select_one('div.paging')
            next_page_link = paging_div.select_one('a.next') if paging_div else None
            last_page_number = 1
            if paging_div:
                last_page_links = paging_div.select('a')
                page += 1
                if last_page_links:
                    last_page_number = int(last_page_links[-1].get_text())

            if next_page_link:
                page += 1
            # elif page < last_page_number:
            #     page += 1
            else:
                break
            
            time.sleep(1)  # 서버에 부하를 줄이기 위해 요청 간격을 둡니다.
            
            # if not next_page_links and page > 1:  # 더 이상 페이지가 없으면 종료
            #     break

        # 다음 날짜로 이동
        current_date += timedelta(days=1)
        if len(articles) >= max_articles:
            break

    return articles

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Naver News Crawler')
    parser.add_argument('--section', type=str, required=True, help='Section code (e.g., 100 for politics)')
    parser.add_argument('--start-date', type=str, required=True, help='Start date in YYYYMMDD format')
    parser.add_argument('--end-date', type=str, required=True, help='End date in YYYYMMDD format')
    parser.add_argument('--max-articles', type=int, default=20000, help='Maximum number of articles to crawl')
    args = parser.parse_args()

    section = args.section
    start_date = datetime.strptime(args.start_date, '%Y%m%d')
    end_date = datetime.strptime(args.end_date, '%Y%m%d')
    max_articles = args.max_articles

    articles = crawl_naver_news(section, start_date, end_date, max_articles)

    filename = f'naver_news_{section}_{args.start_date}_{args.end_date}.csv'
    with open(filename, 'w', newline='', encoding='utf-8-sig') as file:
        writer = csv.DictWriter(file, fieldnames=['title', 'body', 'url', 'date', 'press'])
        writer.writeheader()
        writer.writerows(articles)

    print(f"Collected {len(articles)} articles.")


# if __name__ == "__main__":
#     Crawler = ArticleCrawler()
#     Crawler.set_category("정치")  # 정치, 경제, 생활문화, IT과학, 사회, 세계 카테고리 사용 가능
#     Crawler.set_date_range(2024, 1, 2024, 2)  # 2017년 12월부터 2018년 1월까지 크롤링 시작
#     Crawler.start()
#     Writer.get_writer_csv()
