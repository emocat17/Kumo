from datetime import datetime
import pandas as pd
import os
import re
import argparse
import json
import requests
import time
import asyncio
import httpx
import sys, io
import concurrent.futures
import threading
from logger import Logger

# 强制使用 UTF-8 输出，避免 Windows GBK 编码导致打印异常（例如 '✓'）
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    try:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass
#  python .\arxiv_spider.py --keyword "zero trust"
# 读取配置文件
def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"读取配置文件失败: {e}, 使用默认配置")
        return {"BASE_DATA_DIR": "D:\\app\\Data\\Arxiv\\"}

# 基础数据目录
CONFIG = load_config()
BASE_DATA_DIR = CONFIG.get('BASE_DATA_DIR', "D:\\app\\Data\\Arxiv\\")

def _get_int(config, key, default):
    try:
        v = config.get(key, default)
        return int(v)
    except Exception:
        return default

def _get_bool(config, key, default):
    v = config.get(key, default)
    if isinstance(v, bool):
        return v
    if isinstance(v, str):
        return v.strip().lower() in ('true', '1', 'yes', 'y', 't')
    if isinstance(v, int):
        return v != 0
    return default

# 配置参数
MAX_RETRIES = _get_int(CONFIG, 'MAX_RETRIES', 3)
RETRY_DELAY = _get_int(CONFIG, 'RETRY_DELAY', 1)
REQUEST_TIMEOUT = _get_int(CONFIG, 'REQUEST_TIMEOUT', 30)
CRAWL4AI_CACHE = _get_bool(CONFIG, 'CRAWL4AI_CACHE', True)
MAX_CONCURRENT_DOWNLOADS = _get_int(CONFIG, 'MAX_CONCURRENT_DOWNLOADS', 6)

# 线程安全的计数器
class Counter:
    def __init__(self, total):
        self.total = total
        self.current = 0
        self.lock = threading.Lock()
    
    def increment(self):
        with self.lock:
            self.current += 1
            return self.current
    
    def get_current(self):
        with self.lock:
            return self.current

def clean_filename(title):
    illegal_chars_pattern = r'[\\/:*?"<>|\n]'
    safe_title = re.sub(illegal_chars_pattern, ' ', title)
    safe_title = re.sub(r'\s+', '_', safe_title.strip())
    safe_title = re.sub(r'[^\w\s-]', '', safe_title)
    safe_title = safe_title.strip('_')
    # 限制文件名长度，为年份+季度+论文名称预留空间
    return safe_title[:180] if len(safe_title) > 180 else safe_title


def download_pdf_sync(pdf_url, title, year, quarter, keyword, counter):
    """同步版本的PDF下载函数，用于多线程"""
    # 创建关键词目录和PDF子目录
    keyword_dir = os.path.join(BASE_DATA_DIR, keyword)
    pdf_dir = os.path.join(keyword_dir, 'pdf')
    if not os.path.exists(pdf_dir):
        os.makedirs(pdf_dir, exist_ok=True)
    
    # 使用新的命名规则: 年份_季度_论文名称.pdf
    safe_title = clean_filename(title)
    new_filename = f"{year}_Q{quarter}_{safe_title}.pdf"
    # 确保整个文件名不超过系统限制（通常为255个字符）
    if len(new_filename) > 250:  # 为.pdf扩展名预留空间
        new_filename = new_filename[:250] + ".pdf"
    pdf_path = os.path.join(pdf_dir, new_filename)

    if os.path.exists(pdf_path):
        return f'文件已存在'
    
    # 使用requests库下载PDF
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = requests.get(pdf_url, timeout=REQUEST_TIMEOUT)
            if response.status_code == 200:
                # 检查内容是否为PDF
                content = response.content
                if len(content) > 100 and content.startswith(b'%PDF'):
                    with open(pdf_path, 'wb') as f:
                        f.write(content)
                    return f'下载成功'
                else:
                    return f'下载内容不是有效的PDF文件'
            else:
                if attempt < MAX_RETRIES:
                    time.sleep(RETRY_DELAY)
                    continue
                return f'下载失败({response.status_code})'
        except requests.exceptions.Timeout:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            return f'下载超时'
        except Exception as e:
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_DELAY)
                continue
            return f'下载异常({str(e)})'

def download_pdf_wrapper(args):
    """多线程下载包装函数"""
    pdf_url, title, year, quarter, keyword, counter = args
    current = counter.increment()
    logger.log(f"正在下载 ({current}/{counter.total}): {title}")
    
    result = download_pdf_sync(pdf_url, title, year, quarter, keyword, counter)
    if result != '下载成功':
        logger.log(f"结果: {result}")
    return result

async def fetch_papers(query, start_date, end_date, keyword):
    base_url = 'https://export.arxiv.org/api/query?'
    start = 0
    max_results = 1000
    data = []
    pdf_links = []
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT, http2=True) as client:
        while True:
            params = {
                'search_query': query,
                'start': start,
                'max_results': max_results,
                'sortBy': 'submittedDate',
                'sortOrder': 'ascending'
            }
            full_url = base_url + '&'.join([f"{k}={v}" for k, v in params.items()])
            try:
                resp = await client.get(full_url)
                if resp.status_code != 200:
                    logger.log(f"请求失败({resp.status_code})")
                    break
                import html
                import re
                text = resp.text
                if text.startswith('<html>') or '<pre>' in text:
                    match = re.search(r'<pre[^>]*>(.*?)</pre>', text, re.DOTALL)
                    if match:
                        xml_content = html.unescape(match.group(1))
                    else:
                        xml_content = html.unescape(text)
                else:
                    xml_content = text
                import xml.etree.ElementTree as ET
                root = ET.fromstring(xml_content)
                ns = {'atom': 'http://www.w3.org/2005/Atom', 'arxiv': 'http://arxiv.org/schemas/atom'}
                entries = root.findall('atom:entry', ns)
                if not entries:
                    break
                stop = False
                for entry in entries:
                    published_elem = entry.find('atom:published', ns)
                    if published_elem is not None:
                        published_text = published_elem.text.split('T')[0]
                        published_date = datetime.strptime(published_text, '%Y-%m-%d')
                    else:
                        continue
                    if published_date < start_date:
                        continue
                    if published_date > end_date:
                        stop = True
                        break
                    year = published_date.year
                    quarter = (published_date.month - 1) // 3 + 1
                    title_elem = entry.find('atom:title', ns)
                    title = title_elem.text if title_elem is not None else "Unknown Title"
                    authors = []
                    for author in entry.findall('atom:author', ns):
                        name_elem = author.find('atom:name', ns)
                        if name_elem is not None:
                            authors.append(name_elem.text)
                    authors_str = ', '.join(authors)
                    summary_elem = entry.find('atom:summary', ns)
                    summary = summary_elem.text if summary_elem is not None else ""
                    link_elem = entry.find('atom:id', ns)
                    link = link_elem.text if link_elem is not None else ""
                    pdf_link = None
                    for link_tag in entry.findall('atom:link', ns):
                        if link_tag.get('title') == 'pdf':
                            pdf_link = link_tag.get('href')
                            break
                    entry_data = {
                        '发布日期': published_date.strftime('%Y-%m-%d'),
                        '标题': title,
                        '作者': authors_str,
                        '摘要': summary,
                        '链接': link,
                        'PDF链接': pdf_link
                    }
                    data.append(entry_data)
                    if pdf_link:
                        pdf_links.append({
                            'pdf_url': pdf_link,
                            'title': title,
                            'year': year,
                            'quarter': quarter,
                            'keyword': keyword
                        })
                start += len(entries)
                await asyncio.sleep(0.1)
            except Exception as e:
                logger.log(f"请求异常 ({str(e)})")
                break
            if stop:
                break
    
    # 下载所有PDF文件并显示进度
    metrics = {"total_pdfs": 0, "pdf_success": 0}
    if pdf_links:
        total_pdfs = len(pdf_links)
        metrics["total_pdfs"] = total_pdfs
        logger.log(f"找到 {total_pdfs} 篇论文")
        counter = Counter(total_pdfs)
        download_args = [
            (pdf_info['pdf_url'], 
             pdf_info['title'], 
             pdf_info['year'], 
             pdf_info['quarter'], 
             pdf_info['keyword'],
             counter) 
            for pdf_info in pdf_links
        ]
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_CONCURRENT_DOWNLOADS) as executor:
            futures = [executor.submit(download_pdf_wrapper, args) for args in download_args]
            concurrent.futures.wait(futures)
            try:
                metrics["pdf_success"] = sum(1 for f in futures if f.result() == '下载成功')
            except Exception:
                pass
        logger.log("所有PDF下载完成")
    else:
        logger.log("没有找到需要下载的PDF文件")

    data.sort(key=lambda x: x['发布日期'], reverse=True)
    return data, metrics

class ArxivSpider:
    @staticmethod
    async def fetch_arxiv_data(keyword):
        # 创建关键词目录
        keyword_dir = os.path.join(BASE_DATA_DIR, keyword)
        if not os.path.exists(keyword_dir):
            os.makedirs(keyword_dir, exist_ok=True)
        
        # 创建PDF子目录
        pdf_dir = os.path.join(keyword_dir, 'pdf')
        if not os.path.exists(pdf_dir):
            os.makedirs(pdf_dir, exist_ok=True)

        query = f'all:"{keyword}"'
        start_date = datetime(2000, 1, 1)
        end_date = datetime.now()
        csv_filename = os.path.join(keyword_dir, f"{keyword}_papers.csv")
        sd = CONFIG.get('start_date')
        ed = CONFIG.get('end_date')
        if isinstance(sd, str) and isinstance(ed, str) and sd == '-1' and ed == '-1':
            if os.path.exists(csv_filename):
                try:
                    df_existing = pd.read_csv(csv_filename, encoding='utf-8-sig')
                    if '发布日期' in df_existing.columns and not df_existing.empty:
                        try:
                            latest = pd.to_datetime(df_existing['发布日期']).max()
                            if pd.notna(latest):
                                start_date = latest.to_pydatetime()
                        except Exception:
                            start_date = datetime(2000, 1, 1)
                except Exception:
                    start_date = datetime(2000, 1, 1)
            end_date = datetime.now()
        else:
            try:
                if isinstance(sd, str) and sd:
                    start_date = datetime.strptime(sd, '%Y-%m-%d')
            except Exception:
                pass
            try:
                if isinstance(ed, str) and ed:
                    end_date = datetime.strptime(ed, '%Y-%m-%d')
            except Exception:
                pass

        papers_data, metrics = await fetch_papers(query, start_date, end_date, keyword)
        
        # 在关键词目录下创建CSV文件
        df_new = pd.DataFrame(papers_data)
        new_count = 0
        if os.path.exists(csv_filename):
            try:
                df_existing = pd.read_csv(csv_filename, encoding='utf-8-sig')
            except Exception:
                df_existing = pd.DataFrame(columns=df_new.columns)
            if '链接' in df_new.columns and '链接' in df_existing.columns:
                df_append = df_new[~df_new['链接'].isin(df_existing['链接'])]
            else:
                df_append = df_new
            if not df_append.empty:
                new_count = df_append.shape[0]
                df_append.to_csv(csv_filename, mode='a', header=False, index=False, encoding='utf-8-sig')
        else:
            new_count = df_new.shape[0]
            df_new.to_csv(csv_filename, index=False, encoding='utf-8-sig')

        logger.log(f"新增论文数量: {new_count}")
        logger.log(f"爬取成功 {metrics.get('pdf_success', 0)} 篇论文PDF")
        logger.log(f"关键词: {keyword}")
        logger.log(f"起始日期: {start_date.strftime('%Y-%m-%d')}")
        logger.log(f"结束日期: {end_date.strftime('%Y-%m-%d')}")
        logger.log(f"抓取论文条目: {len(papers_data)}")
        logger.log(f"PDF下载总数: {metrics.get('total_pdfs', 0)}")
        logger.log(f"PDF下载成功: {metrics.get('pdf_success', 0)}")
        logger.log(f"CSV路径: {csv_filename}")

        logger.log(f"CSV文件已保存至 {csv_filename}")
        return f"CSV文件已保存至 {csv_filename}"

async def main():
    parser = argparse.ArgumentParser(description='基于crawl4ai的arXiv爬虫程序')
    parser.add_argument('--keyword', type=str, required=True, 
                        help='搜索关键词，例如 "deep learning"')
    args = parser.parse_args()
    
    global logger
    keyword_dir = os.path.join(BASE_DATA_DIR, args.keyword)
    logger = Logger(os.path.join(keyword_dir, 'log'))
    logger.log(f"开始爬取关键词: {args.keyword}")
    arxiv_spider = ArxivSpider()
    await arxiv_spider.fetch_arxiv_data(args.keyword)

if __name__ == '__main__':
    asyncio.run(main())

    #  python .\arxiv_spider.py --keyword "zero trust"


#   "start_date": "2000-01-01",
#   "end_date": "2099-12-31",
