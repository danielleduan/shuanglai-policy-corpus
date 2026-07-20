# 莱西—莱阳一体化政策文件库

本项目从政府网站公开 HTML 页面和 PDF、DOCX、XLSX、TXT 等附件中，建立可审计的“莱西—莱阳跨域合作”政策与实施证据库。发现阶段采用宽口径，不要求标题出现“一体化”；分类阶段依据涉及主体、空间关系、任务安排和跨域治理内容进行 A–D 分级。项目不使用或虚构统一 API。

## 资料范围与输出

优先覆盖山东省、青岛、莱西、烟台、莱阳及相关发改部门官网、旧版栏目和附件服务器。系统输出：

- `policies.csv`：规划、方案、意见、通知、办法、行动计划、批复等正式政策；
- `evidence.csv`：工作报告、建议提案答复、项目进展、会议、签约和官方新闻等实施证据；
- `all_records.csv` / `all_records.jsonl`：全部候选及 A–D 相关性、判定理由和去重关系；
- `review_queue.csv`：相关性不确定、日期/机关缺失或解析失败记录；
- `coverage_report.md`：网站、年份、类型、主题、失败、排除和待核验统计。

每条记录保留原文/附件 URL、发现方式、抓取时间、正文哈希、解析状态、相关性分数与理由。转载不直接删除，而以 `duplicate_of` 和 `alternate_sources` 追溯。

## 安装

```bash
cd /path/to/shuanglai-policy-corpus
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Playwright 仅是普通请求失败后的可选后备，默认关闭；需要时另行安装并在配置中启用，不应借此绕过验证码或访问限制。

## 统一命令

```bash
# 只发现候选链接
python scripts/shuanglai.py discover --limit 20

# 下载并解析；每成功一条即更新断点
python scripts/shuanglai.py crawl --limit 10

# 规则调整后重新分类
python scripts/shuanglai.py classify

# 导出 CSV 和 JSONL
python scripts/shuanglai.py export

# 生成覆盖率审计
python scripts/shuanglai.py audit

# 从 checkpoint.json 继续
python scripts/shuanglai.py resume --limit 10

# 受控小规模全流程
python scripts/shuanglai.py run-all --limit 5
```

全量抓取前先以小 `--limit` 验证站点。真实运行会验证 `gov.cn` 域、遵守 `robots.txt`、限制同站频率，并记录失败；不会登录、绕过验证码或规避安全限制。遇到验证码时停止该来源，将记录送入人工复核，不尝试绕过。

## 配置

`config/sources.yaml` 配置目标网站、日期范围、请求间隔、超时、重试、最大页数、输出目录、Playwright、附件下载、重新抓取和日志级别。新增网站时：

1. 确认域名为政府官方网站并人工检查使用规则；
2. 在 `sources` 中增加入口与允许域；
3. 先以 `discover --limit 5` 验证重定向、编码和分页；
4. 将新地名组合加入 `config/keywords.txt`，不要把“一体化”设为硬门槛。

发现器会在允许的政府注册域内跟踪相关子域链接。搜索词同时覆盖莱西/莱阳、青岛/烟台、交界和上位区域战略，并与交通、产业、生态、公共服务、要素等主题组合。

## 相关性与人工复核

- A：两地直接合作、先行区、共同项目或任务分工；
- B：青烟协同、都市圈/经济圈/城市群、边界治理等重要背景；
- C：莱西向烟台或莱阳向青岛方向的单侧支撑材料；
- D：普通共现、企业/人员/地址、无关“一体化”等低相关或排除项。

分数与 `relevance_reason` 可解释，不以标题单独判断。人工复核应回到政府原文，核验标题、文号、发文机关、日期、附件和有效性；确认后更新 `review_status`。扫描 PDF 只标记 `needs_ocr` 并保存原文件，不进行大规模低质量 OCR；DOC/WPS 等无法解析格式保留原件并写明原因。

## 更新历史结果与避免重复

默认 `refetch: false`，`resume` 根据断点跳过已完成 URL。综合使用规范化 URL、标题+日期、文件名、正文 SHA-256 和正文相似度去重。规则或配置更新后运行 `classify`、`export`、`audit`，不要删除转载线索。

## 目录

```text
src/shuanglai_corpus/  数据模型、解析、分类、流水线和 CLI
config/                网站与检索配置
data/raw/              原始网页和附件（默认不提交）
data/text/             提取文本（默认不提交）
data/output/           CSV、JSONL、覆盖报告和小型样例
data/review/           候选、断点和人工复核队列
tests/                 离线测试与已核验小型页面快照
logs/                  运行日志
scripts/               CLI 启动与样例生成脚本
```

## 测试与已验证命令

```bash
python3 -m unittest discover -s tests -v
python3 -m compileall -q src scripts tests
python3 scripts/shuanglai.py --help
python3 scripts/build_trial_sample.py
```

## 数据真实性与完整性限制

网站改版、旧链接失效、站内搜索覆盖不完整、扫描件和动态页面都会造成遗漏。自动提取和评分仅用于发现与初筛，不构成政策解释或法律判断。示例结果来自已验证的政府公开页面快照，规模不代表完整覆盖；正式研究使用前必须再次访问原文并人工核验。
