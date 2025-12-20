# Paper_Spider｜arXiv 爬虫

按关键词从 arXiv 抓取论文条目，下载 PDF，并维护 CSV（增量更新）。

## 目录结构
- `arxiv_spider.py`：异步爬虫入口（httpx + requests）
- `config.json`：统一配置
- `requirements.txt`：依赖列表
- `README.md`：使用说明

## 环境要求
- Python 3.10+
- 可访问 `arxiv.org`

## 安装依赖
```bash
python -m venv .venv
. .venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install httpx
```

## 配置
`config.json` 示例：
```json
{
  "BASE_DATA_DIR": "D:\\app\\Data\\Arxiv\\",
  "start_date": "2000-01-01",
  "end_date": "2099-12-31",
  "MAX_RETRIES": 3,
  "RETRY_DELAY": 1,
  "REQUEST_TIMEOUT": 30,
  "CRAWL4AI_CACHE": true,
  "MAX_CONCURRENT_DOWNLOADS": 6
}
```


## 使用
```bash
python arxiv_spider.py --keyword "zero trust"
```

### 抓取策略
- 设定时间范围：使用 `start_date` 和 `end_date`（`YYYY-MM-DD`）。
- 增量抓取：当两者均为 `"-1"` 时，若已存在该关键词 CSV，则从其中最新 `发布日期` 到当前日期抓取；否则从 `2000-01-01` 到当前日期。
- CSV 仅追加新增论文（以 `链接` 唯一去重）。

### 终端与日志
- 终端输出：新增论文数量、成功下载 PDF 数等。
- 日志文件：运行时生成到 `log/`，文件名为时间戳（`YYYYMMDDHHMMSS`）。

### PDF 命名
- 文件名：`YYYY_Qq_<清理后的标题>.pdf`
- 标题清理：替换非法字符、空格压缩为 `_`、长度截断保留扩展名。

## 其他
- 如遇网络异常或超时：调整 `REQUEST_TIMEOUT`、`MAX_RETRIES` 后重试。
- 如需禁止下载 PDF：可在代码中关闭相关逻辑。
