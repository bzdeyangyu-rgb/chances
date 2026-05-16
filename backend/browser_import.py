# -*- coding: utf-8 -*-
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from frontend.data_store import DEFAULT_WORKBOOK, load_or_initialize_jobs, save_jobs


PLATFORM_LABELS = {
    "boss": "Boss直聘",
    "zhipin": "Boss直聘",
    "liepin": "猎聘",
    "lagou": "拉勾",
    "zhaopin": "智联招聘",
}

ROW_KEYS = {
    "platform_label": "招聘网站",
    "job_title": "岗位名称",
    "company_name": "公司名称",
    "salary_raw": "薪资",
    "location": "工作地点",
    "education": "学历",
    "experience": "经验",
    "financing_stage": "融资情况",
    "company_size": "公司规模",
    "industry": "行业",
    "benefits": "福利待遇",
    "published_at": "发布日期",
    "job_url": "详情页",
    "skills": "技能要求",
    "main_text": "主要信息",
}

BOSS_DETAIL_FIXTURE = json.dumps(
    {
        "zpData": {
            "jobInfo": {
                "jobName": "AI应用工程师",
                "salaryDesc": "20-35K·14薪",
                "locationName": "南京",
                "experienceName": "3-5年",
                "degreeName": "本科",
                "skills": ["Python", "LangChain", "RAG"],
                "jobDescription": "负责企业 AI 应用落地",
                "encryptId": "example",
                "encryptUserId": "example-user",
            },
            "brandComInfo": {
                "brandName": "南京示例科技有限公司",
                "industry": "人工智能",
                "stageName": "A轮",
                "scaleName": "100-499人",
            },
        }
    },
    ensure_ascii=False,
)

BOSS_ANTI_DETECTION_SCRIPT = r"""
(() => {
  const nativeToString = Function.prototype.toString;
  const nativeSourceMap = new WeakMap();
  const registerNativeSource = (fn, source) => {
    try { nativeSourceMap.set(fn, source); } catch (_) {}
  };

  Object.defineProperty(Function.prototype, "toString", {
    configurable: true,
    writable: true,
    value: function toString() {
      if (nativeSourceMap.has(this)) {
        return nativeSourceMap.get(this);
      }
      return nativeToString.call(this);
    },
  });

  registerNativeSource(Function.prototype.toString, nativeToString.toString());

  const stealthify = (obj, prop, handler) => {
    const original = obj[prop];
    if (typeof original !== "function") return;
    const wrapped = function (...args) {
      return handler.call(this, original, args);
    };
    registerNativeSource(wrapped, nativeToString.call(original));
    Object.defineProperty(obj, prop, {
      configurable: true,
      writable: true,
      value: wrapped,
    });
  };

  ["log", "debug", "info", "warn", "error"].forEach((name) => {
    stealthify(console, name, (original, args) => {
      return original.apply(console, args.map((arg) => (arg && typeof arg === "object" ? {} : arg)));
    });
  });
})();
"""


def normalize_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "")).strip()


def normalize_main_text(value: Any) -> str:
    if isinstance(value, list):
        lines = [normalize_text(str(item)) for item in value if normalize_text(str(item))]
        return "\n".join(lines)
    return str(value or "").strip()


def normalize_skill_value(value: Any) -> str:
    if isinstance(value, list):
        return ", ".join(normalize_text(str(item)) for item in value if normalize_text(str(item)))
    return normalize_text(value)


def platform_label(platform: str) -> str:
    return PLATFORM_LABELS.get(platform.strip().lower(), platform.strip())


def detect_platform(url: str) -> str:
    lowered = (url or "").lower()
    if "zhipin.com" in lowered:
        return "boss"
    if "liepin.com" in lowered:
        return "liepin"
    if "lagou.com" in lowered:
        return "lagou"
    if "zhaopin.com" in lowered:
        return "zhaopin"
    return ""


def canonicalize_job_url(url: str) -> str:
    cleaned = normalize_text(url)
    if not cleaned:
        return ""
    parts = urlsplit(cleaned)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, "", ""))


def is_verification_page(title: str, text: str, url: str) -> bool:
    title_text = normalize_text(title)
    body_text = normalize_text(text)[:600]
    lowered_url = (url or "").lower()
    return any(
        [
            "security-check" in lowered_url,
            title_text == "滑动验证页面",
            title_text == "访问验证",
            title_text == "Security Verification",
            "滑动滑块进行验证" in body_text,
            "请按住滑块，拖动到最右边" in body_text,
            "验证失败，点击框体重试" in body_text,
            "访问验证" in body_text,
            "正在验证连接安全性" in body_text,
            "Protected by Tencent Cloud EdgeOne" in body_text,
        ]
    )


def empty_job_payload(platform: str, job_url: str) -> dict[str, str]:
    return {
        "platform": platform,
        "job_title": "",
        "company_name": "",
        "salary_raw": "",
        "location": "",
        "education": "",
        "experience": "",
        "financing_stage": "",
        "company_size": "",
        "industry": "",
        "benefits": "",
        "published_at": "",
        "job_url": job_url,
        "skills": "",
        "main_text": "",
    }


EDUCATION_PATTERN = re.compile(r"(本科|大专|硕士|博士|学历不限)")
EXPERIENCE_PATTERN = re.compile(r"((\d+[-~]\d+年)|(\d+年(以上)?经验)|经验不限|应届|在校)")
PUBLISHED_AT_PATTERN = re.compile(r"(\d{1,2}月\d{1,2}日更新|更新于\s*\d{1,2}月\d{1,2}日|\d{1,2}月\d{1,2}日)")


def extract_summary_fields(summary: str) -> dict[str, str]:
    payload = {
        "location": "",
        "experience": "",
        "education": "",
        "published_at": "",
    }
    tokens = [token for token in re.split(r"[|/·\s]+", normalize_text(summary)) if token]
    if not tokens:
        return payload

    experience_index = next((index for index, token in enumerate(tokens) if EXPERIENCE_PATTERN.search(token)), None)
    education_index = next((index for index, token in enumerate(tokens) if EDUCATION_PATTERN.search(token)), None)
    published_index = next((index for index, token in enumerate(tokens) if PUBLISHED_AT_PATTERN.search(token)), None)

    if experience_index is not None:
        payload["experience"] = tokens[experience_index]
        payload["location"] = " ".join(tokens[:experience_index]).strip()
    if education_index is not None:
        payload["education"] = tokens[education_index]
    if published_index is not None:
        payload["published_at"] = tokens[published_index]

    return payload


def line_value_after_prefix(lines: list[str], prefix: str) -> str:
    for line in lines:
        if line.startswith(prefix):
            return normalize_text(line.split("：", 1)[1] if "：" in line else line[len(prefix) :])
    return ""


def build_main_text(lines: list[str], max_lines: int = 200) -> str:
    cleaned_lines = [normalize_text(line) for line in lines if normalize_text(line)]
    return "\n".join(cleaned_lines[:max_lines])


def sanitize_job_payload(payload: dict[str, Any] | None, platform: str, job_url: str) -> dict[str, str]:
    sanitized = empty_job_payload(platform, job_url)
    if not payload:
        return sanitized

    for key in sanitized:
        if key == "main_text":
            sanitized[key] = normalize_main_text(payload.get(key))
        else:
            sanitized[key] = normalize_text(payload.get(key))
    sanitized["platform"] = normalize_text(payload.get("platform")) or platform
    sanitized["job_url"] = canonicalize_job_url(normalize_text(payload.get("job_url")) or job_url)
    return sanitized


def merge_job_payload(preferred: dict[str, str], fallback: dict[str, str]) -> dict[str, str]:
    merged = fallback.copy()
    for key, value in preferred.items():
        if normalize_text(value):
            merged[key] = normalize_text(value)
    return merged


def parse_boss_detail_json(raw_json: str, job_url: str = "https://www.zhipin.com/job_detail/example.html") -> dict[str, str]:
    root = json.loads(raw_json)
    zp_data = root.get("zpData", {})
    job_info = zp_data.get("jobInfo", {})
    brand = zp_data.get("brandComInfo", {})

    payload = empty_job_payload("boss", job_url)
    payload["job_title"] = normalize_text(job_info.get("jobName"))
    payload["company_name"] = normalize_text(brand.get("brandName") or brand.get("companyName"))
    payload["salary_raw"] = normalize_text(job_info.get("salaryDesc"))
    payload["location"] = normalize_text(job_info.get("locationName"))
    payload["experience"] = normalize_text(job_info.get("experienceName"))
    payload["education"] = normalize_text(job_info.get("degreeName"))
    payload["industry"] = normalize_text(brand.get("industry"))
    payload["financing_stage"] = normalize_text(brand.get("stageName"))
    payload["company_size"] = normalize_text(brand.get("scaleName"))
    payload["skills"] = normalize_skill_value(job_info.get("skills"))
    payload["benefits"] = normalize_text(job_info.get("welfareList"))
    payload["published_at"] = normalize_text(job_info.get("publishTime"))
    return payload


def parse_zhaopin_visible_lines(title: str, lines: list[str], job_url: str) -> dict[str, str]:
    payload = empty_job_payload("zhaopin", job_url)
    cleaned_lines = [normalize_text(line) for line in lines if normalize_text(line)]

    title_match = re.search(r"_\d{4}年(.+?)招聘-智联招聘$", normalize_text(title))
    payload["company_name"] = normalize_text(title_match.group(1) if title_match else "")

    job_title = ""
    for line in cleaned_lines:
        if "招聘" not in line and not re.search(r"(登录|注册|首页|职位推荐|南京站|APP|举报)$", line):
            if "工程师" in line or "经理" in line or "开发" in line or "产品" in line:
                job_title = line
                break
    payload["job_title"] = job_title

    try:
        start_index = cleaned_lines.index(job_title) + 1 if job_title else 0
    except ValueError:
        start_index = 0
    tail = cleaned_lines[start_index : start_index + 8]

    payload["salary_raw"] = next((line for line in tail if re.search(r"[0-9].*(万|K|k|薪)", line)), "")
    payload["location"] = next((line for line in tail if re.search(r".+(市|区|县)$", line) or "南京" in line), "")
    payload["experience"] = next((line for line in tail if re.search(r"(经验|年)", line)), "")
    payload["education"] = next((line for line in tail if re.search(r"(本科|大专|硕士|博士|学历不限)", line)), "")
    payload["published_at"] = next((line for line in cleaned_lines if re.search(r"(更新于|发布于|月\d+日|月日)", line)), "")

    return payload


def parse_liepin_visible_lines(lines: list[str], job_url: str) -> dict[str, str]:
    payload = empty_job_payload("liepin", job_url)
    cleaned_lines = [normalize_text(line) for line in lines if normalize_text(line)]

    payload["job_title"] = next((line for line in cleaned_lines if "工程师" in line or "经理" in line or "开发" in line), "")
    payload["salary_raw"] = next((line for line in cleaned_lines if re.search(r"[0-9].*(k|K|万)", line)), "")
    summary = next(
        (line for line in cleaned_lines if re.search(r"(本科|大专|硕士|博士|学历不限)", line) and re.search(r"(年|经验)", line)),
        "",
    )

    try:
        company_info_index = cleaned_lines.index("公司信息")
    except ValueError:
        company_info_index = -1
    if company_info_index >= 0 and company_info_index + 1 < len(cleaned_lines):
        payload["company_name"] = cleaned_lines[company_info_index + 1]
    else:
        payload["company_name"] = next(
            (line.split("·", 1)[1].strip() for line in cleaned_lines if "·" in line and "公司" in line),
            "",
        )

    if summary:
        payload.update(extract_summary_fields(summary))

    payload["industry"] = line_value_after_prefix(cleaned_lines, "企业行业：")
    payload["financing_stage"] = line_value_after_prefix(cleaned_lines, "融资阶段：")
    payload["company_size"] = line_value_after_prefix(cleaned_lines, "人数规模：")
    return payload


def parse_lagou_visible_lines(title: str, lines: list[str], job_url: str) -> dict[str, str]:
    payload = empty_job_payload("lagou", job_url)
    cleaned_lines = [normalize_text(line) for line in lines if normalize_text(line)]
    title_text = normalize_text(title)

    payload["job_title"] = next((line for line in cleaned_lines if "工程师" in line or "经理" in line or "开发" in line), "")
    payload["salary_raw"] = next((line for line in cleaned_lines if re.search(r"[0-9].*(k|K|万)", line)), "")
    summary = next(
        (line for line in cleaned_lines if re.search(r"(本科|大专|硕士|博士|学历不限)", line) and re.search(r"(年|经验)", line)),
        "",
    )

    if payload["job_title"]:
        company_match = re.search(
            rf"{re.escape(payload['job_title'])}招聘-\d{{4}}年(?P<company>.+?){re.escape(payload['job_title'])}招聘求职信息",
            title_text,
        )
        if company_match:
            payload["company_name"] = normalize_text(company_match.group("company"))
    if not payload["company_name"]:
        payload["company_name"] = next((line for line in cleaned_lines if "有限公司" in line or "科技" in line), "")

    if summary:
        summary_match = re.search(
            r"^(?P<location>.+?)经验(?P<experience>\d+[-~]\d+年|\d+年|经验不限|应届)"
            r"(?P<education>本科及以上|本科|大专|硕士|博士|学历不限)",
            summary,
        )
        if summary_match:
            payload["location"] = normalize_text(summary_match.group("location"))
            payload["experience"] = normalize_text(summary_match.group("experience"))
            payload["education"] = normalize_text(summary_match.group("education"))
        else:
            parts = [part for part in re.split(r"\s{2,}|[·/|]", summary) if part]
            payload["location"] = parts[0] if len(parts) > 0 else ""
            payload["experience"] = next((part for part in parts if re.search(r"(年|经验)", part)), "")
            payload["education"] = next((part for part in parts if re.search(r"(本科|大专|硕士|博士|学历不限)", part)), "")
    return payload


def parse_page_capture(url: str, title: str, body_lines: list[str]) -> dict[str, str]:
    canonical_url = canonicalize_job_url(url)
    platform = detect_platform(canonical_url)
    if not platform:
        raise ValueError("当前页面不在支持的网站范围内。")

    cleaned_lines = [normalize_text(line) for line in body_lines if normalize_text(line)]
    page_text = "\n".join(cleaned_lines)
    if is_verification_page(title, page_text, canonical_url):
        raise ValueError("当前页面触发了网站验证，无法可靠提取岗位数据。")

    if platform == "boss":
        payload = empty_job_payload("boss", canonical_url)
    elif platform == "liepin":
        payload = parse_liepin_visible_lines(cleaned_lines, canonical_url)
    elif platform == "lagou":
        payload = parse_lagou_visible_lines(title, cleaned_lines, canonical_url)
    else:
        payload = parse_zhaopin_visible_lines(title, cleaned_lines, canonical_url)
    payload["main_text"] = build_main_text(cleaned_lines)
    return payload


def import_page_capture(
    url: str,
    title: str,
    body_lines: list[str],
    extracted_job: dict[str, Any] | None = None,
    workbook_path: Path | str = DEFAULT_WORKBOOK,
) -> tuple[dict[str, str], dict[str, str]]:
    canonical_url = canonicalize_job_url(url)
    platform = detect_platform(canonical_url)
    if not platform:
        raise ValueError("当前页面不在支持的网站范围内。")

    parsed_job = parse_page_capture(canonical_url, title, body_lines)
    structured_job = sanitize_job_payload(extracted_job, platform, canonical_url)
    merged_job = merge_job_payload(structured_job, parsed_job)

    if not merged_job["job_title"]:
        raise ValueError("未提取到岗位名称，请确认当前是岗位详情页。")

    result = upsert_job(merged_job, workbook_path)
    return result, row_to_api_job(payload_to_row(merged_job))


def payload_to_row(payload: dict[str, str]) -> dict[str, str]:
    return {
        ROW_KEYS["platform_label"]: platform_label(payload["platform"]),
        ROW_KEYS["job_title"]: normalize_text(payload.get("job_title")),
        ROW_KEYS["company_name"]: normalize_text(payload.get("company_name")),
        ROW_KEYS["salary_raw"]: normalize_text(payload.get("salary_raw")),
        ROW_KEYS["location"]: normalize_text(payload.get("location")),
        ROW_KEYS["education"]: normalize_text(payload.get("education")),
        ROW_KEYS["experience"]: normalize_text(payload.get("experience")),
        ROW_KEYS["financing_stage"]: normalize_text(payload.get("financing_stage")),
        ROW_KEYS["company_size"]: normalize_text(payload.get("company_size")),
        ROW_KEYS["industry"]: normalize_text(payload.get("industry")),
        ROW_KEYS["benefits"]: normalize_text(payload.get("benefits")),
        ROW_KEYS["published_at"]: normalize_text(payload.get("published_at")),
        ROW_KEYS["job_url"]: canonicalize_job_url(payload.get("job_url")),
        ROW_KEYS["skills"]: normalize_text(payload.get("skills")),
        ROW_KEYS["main_text"]: normalize_main_text(payload.get("main_text")),
    }


def row_to_api_job(row: dict[str, Any]) -> dict[str, str]:
    return {
        "platform_label": normalize_text(row[ROW_KEYS["platform_label"]]),
        "job_title": normalize_text(row[ROW_KEYS["job_title"]]),
        "company_name": normalize_text(row[ROW_KEYS["company_name"]]),
        "salary_raw": normalize_text(row[ROW_KEYS["salary_raw"]]),
        "location": normalize_text(row[ROW_KEYS["location"]]),
        "education": normalize_text(row[ROW_KEYS["education"]]),
        "experience": normalize_text(row[ROW_KEYS["experience"]]),
        "financing_stage": normalize_text(row[ROW_KEYS["financing_stage"]]),
        "company_size": normalize_text(row[ROW_KEYS["company_size"]]),
        "industry": normalize_text(row[ROW_KEYS["industry"]]),
        "benefits": normalize_text(row[ROW_KEYS["benefits"]]),
        "published_at": normalize_text(row[ROW_KEYS["published_at"]]),
        "job_url": normalize_text(row[ROW_KEYS["job_url"]]),
        "skills": normalize_text(row[ROW_KEYS["skills"]]),
        "main_text": normalize_main_text(row[ROW_KEYS["main_text"]]),
    }


def upsert_job(payload: dict[str, str], workbook_path: Path | str = DEFAULT_WORKBOOK) -> dict[str, str]:
    path = Path(workbook_path)
    jobs = load_or_initialize_jobs(path)
    row = payload_to_row(payload)
    target_job_url = canonicalize_job_url(row[ROW_KEYS["job_url"]])
    row[ROW_KEYS["job_url"]] = target_job_url
    existing_urls = jobs[ROW_KEYS["job_url"]].fillna("").map(canonicalize_job_url)
    matches = jobs.index[existing_urls == target_job_url].tolist()

    if not matches:
        updated_jobs = jobs.copy()
        updated_jobs.loc[len(updated_jobs)] = row
        save_jobs(updated_jobs, path)
        return {"result": "created", "job_url": row[ROW_KEYS["job_url"]]}

    row_index = matches[0]
    current_row = jobs.loc[row_index].to_dict()
    if all(normalize_text(current_row[key]) == normalize_text(value) for key, value in row.items()):
        return {"result": "duplicate", "job_url": row[ROW_KEYS["job_url"]]}

    updated_jobs = jobs.copy()
    for key, value in row.items():
        updated_jobs.at[row_index, key] = value
    save_jobs(updated_jobs, path)
    return {"result": "updated", "job_url": row[ROW_KEYS["job_url"]]}
