# 莱西—莱阳一体化政策文件库

本项目用于从政府网站公开的 HTML 页面与 PDF 附件中发现、下载、提取、去重并编目“莱西—莱阳一体化”相关政策文件。项目不依赖或假设任何统一政策 API；每个来源都在 `config/sources.yaml` 中显式配置，并保留原始网址、抓取时间和内容哈希，便于审计与复现。

## 数据边界

- 仅抓取公开网页及其公开附件。
- 遵守网站 `robots.txt`、使用条款与合理访问频率；默认每次请求至少间隔 1 秒。
- 不绕过登录、验证码、反爬限制或访问控制。
- `config/sources.yaml` 中的入口地址应在运行前人工核验；政府网站改版后需同步更新选择器或入口。
- 仓库默认只提交目录、配置和元数据表头，不提交批量下载的原始文件。

## 快速开始

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

python scripts/discover.py --config config/sources.yaml --output data/discovered.csv
python scripts/download.py --input data/discovered.csv --metadata data/metadata.csv
python scripts/extract.py --metadata data/metadata.csv --output-dir data/extracted
python scripts/deduplicate.py --metadata data/metadata.csv --output data/metadata_deduplicated.csv
```

调试时可使用 `--dry-run` 检查配置和输入而不发起下载：

```bash
python scripts/discover.py --config config/sources.yaml --dry-run
python scripts/download.py --input data/discovered.csv --dry-run
```

## 流水线

1. `discover.py`：访问配置的政府站点公开 HTML 列表页，跟踪限定深度的站内链接，按关键词筛选候选页面与 PDF。
2. `download.py`：下载候选 HTML/PDF，校验内容类型与大小，写入原始目录并更新 `metadata.csv`。
3. `extract.py`：从 HTML 或 PDF 中提取文本，生成可检索的 UTF-8 文本文件。
4. `deduplicate.py`：按 SHA-256 和规范化文本指纹去重，保留重复关系。

所有命令均支持 `--help`。网络请求带有可识别的 User-Agent、超时、重试、限速和域名约束。

## 测试

```bash
python -m unittest discover -s tests -v
python -m compileall scripts tests
```

## 目录

```text
config/                 来源与关键词配置
data/raw/html/          原始网页
data/raw/pdf/           原始 PDF
data/extracted/         提取文本
data/metadata.csv       数据目录与溯源字段
docs/                   政策清单、时间线和空间治理分析
scripts/                发现、下载、提取、去重脚本
tests/                  离线单元测试
```

## 维护建议

政策标题、发布日期和发文机构应优先从页面正文人工复核。自动提取结果只能作为初筛，不应替代政策解释或法律判断。
