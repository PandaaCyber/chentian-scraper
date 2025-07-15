import requests
from bs4 import BeautifulSoup
import time
from ebooklib import epub
import os

def get_article_urls(category_url):
    """获取一个分类页面下所有文章的链接"""
    urls = []
    # 添加请求头，模拟浏览器访问
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    current_page_url = category_url
    while current_page_url:
        print(f"正在分析列表页面：{current_page_url}")
        try:
            # 使用 timeout 参数增加程序的健壮性
            response = requests.get(current_page_url, headers=headers, timeout=30)
            response.raise_for_status()  # 如果请求不成功 (如 404, 500)，则会抛出异常
            soup = BeautifulSoup(response.text, 'html.parser')

            # 寻找当前页面的所有文章链接
            # 网站结构可能会变化，这里的 'article' 和 'a' 标签是根据当前网站结构来的
            article_tags = soup.find_all('article')
            if not article_tags:
                print("警告：在此页面上没有找到 <article> 标签，可能页面结构已改变。")

            for article in article_tags:
                link_tag = article.find('a', href=True)
                if link_tag:
                    urls.append(link_tag['href'])

            # 寻找“下一页”的链接
            next_page_link = soup.find('a', class_='next')
            if next_page_link and next_page_link.get('href'):
                # 确保获取的是完整的 URL
                current_page_url = next_page_link['href']
            else:
                current_page_url = None # 没有下一页了，循环结束

        except requests.exceptions.RequestException as e:
            print(f"抓取页面 {current_page_url} 时发生网络错误: {e}")
            current_page_url = None # 发生错误，停止翻页

        # 遵守“君子协议”，每次请求后暂停2-4秒，降低对服务器的压力
        time.sleep(2) 

    # 去重，以防万一有重复的链接
    unique_urls = list(dict.fromkeys(urls))
    print(f"总共找到 {len(unique_urls)} 篇不重复的文章链接。")
    return unique_urls

def get_article_content(article_url):
    """获取单篇文章的标题和内容"""
    print(f"正在下载文章：{article_url}")
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    try:
        response = requests.get(article_url, headers=headers, timeout=30)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')

        # 提取标题
        title_tag = soup.find('h1', class_='entry-title')
        if not title_tag:
            print(f"警告：在 {article_url} 未找到标题。")
            return None, None
        title = title_tag.get_text(strip=True)

        # 提取内容区域
        content_div = soup.find('div', class_='entry-content')
        if not content_div:
            print(f"警告：在 {article_url} 未找到正文内容。")
            return None, None

        # 移除内容中的非文章部分，如“相关文章”、脚本等
        for element in content_div.find_all(['script', 'style', 'div.sharedaddy', 'div.jp-relatedposts']):
            element.decompose()

        content_html = str(content_div)
        return title, content_html

    except requests.exceptions.RequestException as e:
        print(f"抓取文章 {article_url} 时发生网络错误: {e}")
        return None, None
    except Exception as e:
        print(f"解析文章 {article_url} 时发生未知错误: {e}")
        return None, None

def create_epub(filename, book_title, articles):
    """根据文章数据创建EPUB文件"""
    if not articles:
        print("没有可以创建电子书的文章。")
        return

    book = epub.EpubBook()
    book.set_identifier(f'id_{int(time.time())}')
    book.set_title(book_title)
    book.set_language('zh')
    book.add_author('chentianyuzhou.com')

    chapters = []
    for i, (article_title, article_content_html) in enumerate(articles):
        chapter_filename = f'chap_{i+1}.xhtml'
        chapter = epub.EpubHtml(title=article_title, file_name=chapter_filename, lang='zh')
        # 组装完整的 HTML 内容
        chapter.content = f'<html><head><title>{article_title}</title></head><body><h1>{article_title}</h1>{article_content_html}</body></html>'
        book.add_item(chapter)
        chapters.append(chapter)

    # 定义书的目录结构和阅读顺序
    book.toc = chapters
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = ['nav'] + chapters

    # 检查文件名是否以 .epub 结尾
    if not filename.endswith('.epub'):
        filename += '.epub'

    epub.write_epub(filename, book, {})
    print(f"电子书 '{filename}' 已成功创建！它位于当前文件夹中。")


if __name__ == '__main__':
    # ================== 配置区 ==================
    # 你要爬取的分类起始页URL
    START_URL = 'https://chentianyuzhou.com/category/selected/'
    # 生成的EPUB文件名
    EPUB_FILENAME = '精选长文.epub'
    # 电子书的标题
    EBOOK_TITLE = 'chentianyuzhou.com 精选长文'
    # ==========================================

    print("开始执行爬虫任务...")
    all_article_urls = get_article_urls(START_URL)

    if all_article_urls:
        articles_data = []
        total_articles = len(all_article_urls)
        for i, url in enumerate(all_article_urls):
            print(f"--- 处理进度: {i+1}/{total_articles} ---")
            article_title, article_content = get_article_content(url)
            if article_title and article_content:
                articles_data.append((article_title, article_content))
            # 每次抓取文章后也暂停一下
            time.sleep(2)

        create_epub(EPUB_FILENAME, EBOOK_TITLE, articles_data)
    else:
        print("未能获取到任何文章链接，程序退出。")
