"""Explainable relevance, material, topic, and duplicate classification."""

from __future__ import annotations

import difflib
import hashlib
import re

LOCATION_TERMS = ["莱西", "莱阳", "青岛", "烟台", "胶东经济圈", "青岛都市圈", "山东半岛城市群", "五龙河", "大沽河", "青烟发展轴"]
RELATION_TERMS = ["合作", "协同", "联动", "共建", "共享", "衔接", "互联互通", "跨域通办", "融合", "一体化", "对接"]
BOUNDARY_TERMS = ["跨市域", "毗邻县域", "交界地区", "边界地区", "青烟交界", "青烟发展轴"]
EXCLUSIONS = ["化工一体化", "城乡公交一体化"]
TOPICS = {
    "规划与空间布局": ["规划", "空间布局", "国土空间"], "体制机制": ["领导小组", "联席会议", "机制"],
    "产业协同": ["产业协同", "产业链"], "园区共建": ["园区", "一区多园"], "平台公司": ["平台公司"],
    "交通互联": ["交通", "公路", "铁路", "公交", "互联互通"], "公共服务": ["教育", "医疗", "养老", "公共服务"],
    "政务服务跨域通办": ["跨域通办", "政务服务"], "生态环境": ["生态环境", "生态保护"],
    "水资源治理": ["水资源", "流域治理", "五龙河", "大沽河"], "人才与就业": ["人才", "就业"],
    "科技创新": ["科技", "创新"], "财政支持": ["财政", "资金支持"], "土地和要素保障": ["土地", "要素保障"],
    "招商引资": ["招商", "投资促进"], "城乡融合": ["城乡融合"], "山东半岛城市群": ["山东半岛城市群"],
    "胶东经济圈": ["胶东经济圈"], "青岛都市圈": ["青岛都市圈"], "重大项目": ["重大项目", "重点项目"],
}


def _hits(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term in text]


def score_relevance(title: str, text: str) -> dict:
    body = text or ""
    combined = title + "\n" + body
    locations, relations, boundaries = _hits(combined, LOCATION_TERMS), _hits(combined, RELATION_TERMS), _hits(combined, BOUNDARY_TERMS)
    score, reasons = 0, []
    if "莱西" in title and "莱阳" in title: score += 40; reasons.append("标题同时出现莱西和莱阳 +40")
    if "莱西" in body and "莱阳" in body: score += 25; reasons.append("正文同时出现莱西和莱阳 +25")
    qingyan_pair = "青岛" in combined and "烟台" in combined
    strategic_terms = _hits(combined, ["青岛都市圈", "胶东经济圈", "山东半岛城市群"])
    if "青岛" in title and "烟台" in title: score += 15; reasons.append("标题同时出现青岛和烟台 +15")
    if "青岛" in body and "烟台" in body: score += 10; reasons.append("正文同时出现青岛和烟台 +10")
    if relations: score += 15; reasons.append("出现跨域关系词 +15")
    if boundaries: score += 20; reasons.append("出现边界治理词 +20")
    if any(term in combined for term in ("先行区", "双莱", "莱西莱阳一体化", "莱阳莱西一体化")): score += 30; reasons.append("出现双莱/先行区高价值词 +30")
    if any(term in combined for term in ("共同项目", "共同园区", "交通互联", "跨域公共服务")): score += 20; reasons.append("出现共同项目或跨域服务 +20")
    if strategic_terms: score += 10; reasons.append("出现上位区域战略 +10")
    excluded = any(term in combined for term in EXCLUSIONS) and not ({"莱西", "莱阳"} <= set(locations))
    accidental = bool(re.search(r"(?:地址|名单|籍贯|注册地).{0,20}(?:莱西|莱阳)", combined))
    if excluded or accidental:
        return {"level":"D", "score":0, "reason":"排除：无关一体化或偶然地名共现", "locations":locations, "relations":relations, "cross_boundary":""}
    if {"莱西", "莱阳"} <= set(locations) and relations: level = "A"
    elif score >= 35 and (boundaries or strategic_terms): level = "B"
    elif score >= 15 and locations: level = "C"
    elif qingyan_pair or strategic_terms:
        level = "C"
        reasons.append("宽口径纳入青烟组合或上位区域战略候选")
    else: level = "D"
    return {"level":level, "score":min(score, 100), "reason":"；".join(reasons) or "缺少实质跨域关系", "locations":locations, "relations":relations, "cross_boundary":"|".join(boundaries)}


def classify_topics(text: str) -> list[str]:
    return [topic for topic, terms in TOPICS.items() if any(term in text for term in terms)]


def classify_material(title: str, text: str) -> tuple[str, str, str]:
    combined = title + " " + text[:2000]
    policies = [term for term in ("规划", "实施方案", "意见", "通知", "办法", "政策", "行动计划", "责任分工", "工作要点", "批复", "公报") if term in title]
    evidence = [term for term in ("工作报告", "计划报告", "建议答复", "提案答复", "工作总结", "项目进展", "新闻", "会议", "签约", "跨域通办") if term in combined]
    if policies: return "policy", policies[0], "true"
    return "evidence", evidence[0] if evidence else "官方实施材料", "false"


def mark_duplicates(records: list[dict], threshold: float = 0.96) -> list[dict]:
    primary = []
    for record in records:
        duplicate = ""
        for existing in primary:
            same_url = record.get("source_page_url") == existing.get("source_page_url")
            same_hash = record.get("content_sha256") and record.get("content_sha256") == existing.get("content_sha256")
            same_identity = record.get("title") == existing.get("title") and record.get("publication_date") == existing.get("publication_date")
            similarity = difflib.SequenceMatcher(None, record.get("full_text", "")[:10000], existing.get("full_text", "")[:10000]).ratio()
            if same_url or same_hash or same_identity or similarity >= threshold:
                duplicate = existing["record_id"]
                break
        record["duplicate_of"] = duplicate
        if not duplicate: primary.append(record)
    return records


def content_hash(text: str) -> str:
    return hashlib.sha256(re.sub(r"\s+", "", text).encode("utf-8")).hexdigest()
