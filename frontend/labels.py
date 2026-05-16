# -*- coding: utf-8 -*-
from __future__ import annotations


COLUMN_ORDER = [
    "招聘网站",
    "岗位名称",
    "公司名称",
    "薪资",
    "工作地点",
    "学历",
    "技能要求",
    "经验",
    "融资情况",
    "公司规模",
    "行业",
    "福利待遇",
    "发布日期",
    "详情页",
    "主要信息",
]


STATUS_OPTIONS = [
    "待评估",
    "建议推进",
    "暂缓",
    "不推荐",
    "待准备材料",
    "待沟通",
    "已沟通",
    "待投递",
    "已投递",
    "待约面",
    "一面",
    "二面",
    "三面",
    "人事面",
    "终面",
    "待结果",
    "已拿到意向",
    "已拿到录用",
    "已拒绝",
    "已放弃",
    "已归档",
]


PRIORITY_OPTIONS = ["高", "普通", "低"]


CAPTURE_ASSET_LABELS = {
    "visible": "页面截图",
    "hero": "岗位摘要截图",
    "description": "职位描述截图",
    "company": "公司信息截图",
    "fullpage": "整页长截图",
}


DEFAULT_PROFILE_FORM = {
    "target_roles": "",
    "target_cities": "",
    "remote_preference": "",
    "salary_min": "",
    "salary_ideal": "",
    "core_skills": "",
    "project_highlights": "",
    "no_go_rules": "",
}


UI_TEXT = {
    "page_title": "求职作战台",
    "nav_home": "首页总览",
    "nav_jobs": "岗位池",
    "nav_profile": "个人画像",
    "home_metrics_title": "机会总览",
    "jobs_board_title": "岗位池",
    "profile_title": "个人画像",
    "api_error": "无法连接本地接口，请先启动 FastAPI 服务。",
    "save_profile": "保存画像",
    "refresh_jobs": "刷新岗位",
    "update_status": "更新状态",
    "download_excel": "下载 Excel 导出",
    "total_jobs": "岗位总数",
    "todo_jobs": "待推进岗位",
    "high_priority_jobs": "高优岗位",
    "applied_jobs": "已投递岗位",
    "today_focus": "今日重点推进",
    "jobs_timeline": "岗位时间线",
    "next_action": "下一步动作",
    "status_note": "备注",
    "profile_saved": "个人画像已保存。",
    "status_saved": "岗位状态已更新。",
    "job_detail_title": "岗位详情",
    "job_evaluation_title": "岗位评估",
    "no_evaluation": "该岗位还没有正式评估结果。",
    "no_timeline": "该岗位还没有时间线记录。",
}


STATUS_TEXT = {
    "workbook_caption_prefix": "当前 Excel 导出文件：",
}
