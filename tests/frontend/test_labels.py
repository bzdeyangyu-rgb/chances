from frontend import app
from frontend.data_store import COLUMN_ORDER


EXPECTED_COLUMN_ORDER = [
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


EXPECTED_UI_TEXT = {
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
}


def test_column_order_uses_expected_chinese_headers():
    assert COLUMN_ORDER == EXPECTED_COLUMN_ORDER


def test_skill_column_is_positioned_right_after_education():
    assert COLUMN_ORDER.index("技能要求") == COLUMN_ORDER.index("学历") + 1


def test_app_exposes_expected_chinese_ui_text():
    for key, value in EXPECTED_UI_TEXT.items():
        assert app.UI_TEXT[key] == value
