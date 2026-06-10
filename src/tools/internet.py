from langchain_core.tools import tool
from langchain_community.document_loaders import WebBaseLoader, FireCrawlLoader
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from typing import Annotated, List
from bs4 import BeautifulSoup

from ..logger import setup_logger
from ..config import FIRECRAWL_API_KEY, CHROMEDRIVER_PATH
# 设置日志记录器
logger = setup_logger()


def _get_chrome_service() -> Service:
    """获取 ChromeDriver 服务，自动管理驱动版本。"""
    try:
        from webdriver_manager.chrome import ChromeDriverManager
        driver_path = ChromeDriverManager().install()
        logger.info(f"ChromeDriver 自动管理路径: {driver_path}")
        return Service(driver_path)
    except Exception as e:
        logger.warning(f"webdriver-manager 失败 ({e})，回退到 CHROMEDRIVER_PATH")
        return Service(CHROMEDRIVER_PATH)


@tool
def google_search(query: Annotated[str, "要使用的搜索查询"]) -> Annotated[str, "前 5 条 Google 搜索结果。"]:
    """
    根据给定的查询执行 Google 搜索，并返回前 5 条结果。

    此函数使用 Selenium 执行无头 Google 搜索，并使用 BeautifulSoup 解析结果。

    """
    try:
        logger.info(f"正在对查询执行 Google 搜索: {query}")
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")

        with webdriver.Chrome(options=chrome_options, service=_get_chrome_service()) as driver:
            # 设置超时时间，防止慢网络时挂起
            driver.set_page_load_timeout(30)
            url = f"https://www.google.com/search?q={query}"
            logger.debug(f"正在访问 URL: {url}")
            driver.get(url)
            html = driver.page_source

        soup = BeautifulSoup(html, 'html.parser')
        search_results = soup.select('.g')
        search = ""
        for result in search_results[:5]:
            title_element = result.select_one('h3')
            title = title_element.text if title_element else 'No Title'
            snippet_element = result.select_one('.VwiC3b')
            snippet = snippet_element.text if snippet_element else 'No Snippet'
            link_element = result.select_one('a')
            link = link_element['href'] if link_element else 'No Link'
            search += f"{title}\n{snippet}\n{link}\n\n"

        logger.info("Google 搜索成功完成")
        return search
    except Exception as e:
        logger.error(f"Google 搜索期间出错: {str(e)}")
        return f'Error: {e}'
\
def _scrape_webpages(urls: Annotated[List[str], "要抓取的 URL 列表"]) -> Annotated[str, "从 WebBaseLoader 抓取的内容。"]:
    """
    使用 WebBaseLoader 抓取所提供的网页以获取详细信息。

    此函数使用 WebBaseLoader 加载并抓取所提供 URL 的内容。
    """
    try:
        logger.info(f"正在抓取网页: {urls}")
        loader = WebBaseLoader(urls)
        docs = loader.load()
        content = "\n\n".join([f'\n{doc.page_content}\n' for doc in docs])
        logger.info("网页抓取成功完成")
        return content
    except Exception as e:
        logger.error(f"网页抓取期间出错: {str(e)}")
        raise  # 重新抛出异常，交由调用函数捕获

def _firecrawl_scrape_webpages(urls: Annotated[List[str], "要抓取的 URL 列表"]) -> Annotated[str, "从 FireCrawl 抓取的内容。"]:
    """
    使用 FireCrawlLoader 抓取所提供的网页以获取详细信息。

    此函数使用 FireCrawlLoader 加载并抓取所提供 URL 的内容。

    """
    if not FIRECRAWL_API_KEY:
        raise ValueError("FireCrawl API key is not set")

    try:
        logger.info(f"正在使用 FireCrawl 抓取网页: {urls}")
        results = []
        for url in urls:
            loader = FireCrawlLoader(
                api_key=FIRECRAWL_API_KEY,
                url=url,
                mode="scrape"
            )
            res = loader.load()
            # 标准化加载器可能返回的不同类型
            if isinstance(res, list):
                for doc in res:
                    if hasattr(doc, "page_content"):
                        results.append(str(doc.page_content))
                    else:
                        results.append(str(doc))
            else:
                results.append(str(res))
        aggregated = "\n\n".join(results)
        logger.info("FireCrawl 抓取成功完成")
        return aggregated
    except Exception as e:
        logger.error(f"FireCrawl 抓取期间出错: {str(e)}")
        raise  # 重新抛出异常，交由调用函数捕获
@tool
def scrape_webpages(urls: Annotated[List[str], "要抓取的 URL 列表"]) -> Annotated[str, "从 FireCrawl 或 WebBaseLoader 抓取的内容。"]:
    """
    尝试使用 FireCrawl 抓取网页，若不成功则回退到 WebBaseLoader。
    """
    try:
        return _firecrawl_scrape_webpages(urls)
    except Exception as e:
        logger.warning(f"FireCrawl 抓取失败: {str(e)}。回退到 WebBaseLoader。")
        try:
            return _scrape_webpages(urls)
        except Exception as e:
            logger.error(f"两种抓取方法均失败。错误: {str(e)}")
            return f"Error: Unable to scrape webpages using both methods. {str(e)}"

logger.info("网页抓取工具已初始化")