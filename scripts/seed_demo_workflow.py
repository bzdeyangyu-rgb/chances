from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from backend.db import (  # noqa: E402
    DEFAULT_DB_PATH,
    add_application_event,
    create_import_review_candidates,
    create_job_task,
    initialize_database,
    save_job_materials,
    save_job_score_snapshot,
    save_search_preset,
    update_job_visual_summary,
    upsert_job_record,
)


def build_demo_records() -> dict[str, list[dict[str, Any]]]:
    """Build a full demo workflow without touching the database."""
    return {
        "search_presets": [
            {
                "name": "BOSS - AI 产品/工作流 - 南京",
                "platform": "boss",
                "city": "南京",
                "query": "AI 产品经理 AIGC 工作流",
                "salary": "15-25K",
                "filters_json": json.dumps(
                    {"experience": "3-5年", "degree": "本科", "stage": "成长型"},
                    ensure_ascii=False,
                ),
            }
        ],
        "jobs": [
            {
                "key": "high_match",
                "platform": "boss",
                "job_title": "AI 产品工作流负责人",
                "company_name": "南京智造云科技有限公司",
                "salary_raw": "18-25K",
                "location": "南京·建邺区",
                "education": "本科",
                "experience": "3-5年",
                "financing_stage": "B轮",
                "company_size": "100-499人",
                "industry": "人工智能 / 工业软件",
                "benefits": "五险一金、弹性办公、项目奖金",
                "published_at": "2026-06-08",
                "job_url": "https://www.zhipin.com/job_detail/demo-ai-workflow-lead.html",
                "skills": "AI产品规划, AIGC工作流, UE5, 3DGS, 项目统筹",
                "main_text": "负责 AI 工具链在三维内容生产、城市空间展示和工业场景中的落地，沉淀产品需求、交付 SOP 与客户解决方案。",
                "status": "准备沟通",
                "priority": "高",
                "next_action": "生成准备包后向招聘方沟通",
                "notes": "与目标方向高度相关，适合作为优先推进样例。",
                "source_type": "demo_seed",
                "capture_mode": "dom",
                "visual_summary": "页面突出 AI 工作流、工业软件和三维内容生产，岗位职责与候选人项目经验匹配。",
                "visual_summary_status": "ready",
                "raw_capture_title": "AI 产品工作流负责人招聘页",
            },
            {
                "key": "active_followup",
                "platform": "boss",
                "job_title": "AIGC 解决方案顾问",
                "company_name": "华东数字内容实验室",
                "salary_raw": "15-22K",
                "location": "杭州·余杭区",
                "education": "本科",
                "experience": "1-3年",
                "financing_stage": "未融资",
                "company_size": "20-99人",
                "industry": "数字内容 / 企业服务",
                "benefits": "绩效奖金、远程协作、培训预算",
                "published_at": "2026-06-07",
                "job_url": "https://www.zhipin.com/job_detail/demo-aigc-solution-consultant.html",
                "skills": "AIGC, 客户调研, 方案撰写, Codex, Claude Code",
                "main_text": "面向企业客户梳理 AIGC 提效场景，输出 PoC 方案、实施路径和交付复盘。",
                "status": "已沟通",
                "priority": "中",
                "next_action": "补充作品集链接并在 2 天后跟进",
                "notes": "偏咨询与交付，可作为求职漏斗中的跟进样例。",
                "source_type": "demo_seed",
                "capture_mode": "dom",
                "visual_summary": "岗位强调企业 AIGC 场景诊断和方案交付，适合展示跨工具整合能力。",
                "visual_summary_status": "ready",
                "raw_capture_title": "AIGC 解决方案顾问招聘页",
            },
        ],
        "scores": [
            {
                "job_key": "high_match",
                "score": 86,
                "recommendation": "优先沟通",
                "rubric_version": "demo-rubric-2026-06",
                "dimensions": {
                    "role_fit": 24,
                    "skill_fit": 22,
                    "growth": 20,
                    "risk": 20,
                },
                "summary": "岗位方向、项目经验和 AI 工具链能力匹配度高。",
            }
        ],
        "materials": [
            {
                "job_key": "high_match",
                "resume_angle": "突出 AI 工作流规划、UE5/3DGS 场景经验和跨团队交付能力。",
                "project_highlights": "1. AI 效能与业务拓展报告\n2. UE5 地编与材质流程优化\n3. Codex/Claude Code 辅助开发实践",
                "recruiter_questions": "团队当前最需要补齐的是产品规划、客户交付还是工具链落地？",
                "interview_prep": "准备 3 分钟项目复盘，说明从业务问题到 AI 工作流落地的路径。",
                "communication_draft": "你好，我关注到岗位需要 AI 工作流与三维内容生产经验，我有相关产品规划和项目统筹经历，想进一步了解团队方向。",
                "risk_response": "如被问到纯算法经验不足，转向强调需求拆解、工程协作和落地闭环。",
            }
        ],
        "application_events": [
            {
                "job_key": "high_match",
                "event_type": "准备沟通",
                "channel": "BOSS直聘",
                "note": "已生成准备包，准备发送首轮沟通话术。",
                "event_at": "2026-06-09 09:30:00",
            },
            {
                "job_key": "active_followup",
                "event_type": "已沟通",
                "channel": "BOSS直聘",
                "note": "招聘方已读，待补作品集链接。",
                "event_at": "2026-06-09 10:15:00",
            },
        ],
        "tasks": [
            {
                "job_key": "high_match",
                "title": "发送首轮沟通话术",
                "due_date": "2026-06-10",
            },
            {
                "job_key": "active_followup",
                "title": "补充作品集链接并二次跟进",
                "due_date": "2026-06-11",
            },
        ],
        "import_candidates": [
            {
                "platform": "boss",
                "job_title": "AI Agent 产品经理",
                "company_name": "上海灵犀智能科技",
                "salary_raw": "20-30K",
                "location": "上海·徐汇区",
                "education": "本科",
                "experience": "3-5年",
                "industry": "AI Agent / SaaS",
                "job_url": "https://www.zhipin.com/job_detail/demo-agent-product-manager.html",
                "skills": "AI Agent, 产品路线图, 数据分析, 客户访谈",
                "main_text": "负责 AI Agent 产品从需求发现、原型验证到商业化落地。",
                "status": "待评估",
                "priority": "高",
                "next_action": "在导入审查区确认是否加入岗位池",
            },
            {
                "platform": "boss",
                "job_title": "AI 应用项目经理",
                "company_name": "苏州云境数科",
                "salary_raw": "14-20K",
                "location": "苏州·工业园区",
                "education": "本科",
                "experience": "3-5年",
                "industry": "数字孪生 / 智慧城市",
                "job_url": "https://www.zhipin.com/job_detail/demo-ai-application-pm.html",
                "skills": "数字孪生, AIGC, 项目管理, 客户交付",
                "main_text": "推进 AI 应用在空间展示与智慧城市项目中的交付。",
                "status": "待评估",
                "priority": "中",
                "next_action": "核对薪资、城市和成长空间",
            },
        ],
    }


def seed_demo_workflow(db_path: Path | str) -> dict[str, Any]:
    db = Path(db_path)
    initialize_database(db)
    records = build_demo_records()

    for preset in records["search_presets"]:
        try:
            save_search_preset(preset, db)
        except ValueError:
            pass

    job_ids: dict[str, int] = {}
    for job in records["jobs"]:
        payload = {key: value for key, value in job.items() if key != "key"}
        result = upsert_job_record(payload, db)
        job_id = int(result["id"])
        job_ids[str(job["key"])] = job_id
        if payload.get("visual_summary"):
            update_job_visual_summary(
                job_id,
                str(payload["visual_summary"]),
                db,
                status=str(payload.get("visual_summary_status") or "ready"),
            )

    for score in records["scores"]:
        job_id = job_ids[str(score["job_key"])]
        save_job_score_snapshot(job_id, {key: value for key, value in score.items() if key != "job_key"}, db)

    for material in records["materials"]:
        job_id = job_ids[str(material["job_key"])]
        save_job_materials(job_id, {key: value for key, value in material.items() if key != "job_key"}, db)

    for event in records["application_events"]:
        job_id = job_ids[str(event["job_key"])]
        add_application_event(job_id, {key: value for key, value in event.items() if key != "job_key"}, db)

    for task in records["tasks"]:
        job_id = job_ids[str(task["job_key"])]
        create_job_task(job_id, {key: value for key, value in task.items() if key != "job_key"}, db)

    import_result = create_import_review_candidates(
        "demo_seed",
        records["import_candidates"],
        db,
    )

    return {
        "db_path": str(db),
        "jobs": len(records["jobs"]),
        "materials": len(records["materials"]),
        "application_events": len(records["application_events"]),
        "tasks": len(records["tasks"]),
        "import_candidates": int(import_result["created_count"]),
    }


def _is_default_db_path(path: Path) -> bool:
    try:
        return path.resolve() == DEFAULT_DB_PATH.resolve()
    except FileNotFoundError:
        return path.absolute() == DEFAULT_DB_PATH.absolute()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed an isolated end-to-end demo job-hunting workflow.")
    parser.add_argument("--apply", action="store_true", help="write demo records to the database")
    parser.add_argument("--db", type=Path, help="target SQLite database; required with --apply")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    records = build_demo_records()

    if not args.apply:
        print(
            "dry-run: "
            f"{len(records['jobs'])} jobs, "
            f"{len(records['materials'])} materials, "
            f"{len(records['application_events'])} application events, "
            f"{len(records['tasks'])} tasks, "
            f"{len(records['import_candidates'])} import candidates."
        )
        print("dry-run: add --apply --db <path> to write an isolated demo database.")
        return 0

    if args.db is None:
        print("error: --apply requires --db <path>; refusing to touch the default database.", file=sys.stderr)
        return 2

    if _is_default_db_path(args.db):
        print(f"error: refusing to seed the real default database: {DEFAULT_DB_PATH}", file=sys.stderr)
        return 2

    summary = seed_demo_workflow(args.db)
    print(
        "seeded demo workflow: "
        f"{summary['jobs']} jobs, "
        f"{summary['materials']} materials, "
        f"{summary['application_events']} application events, "
        f"{summary['tasks']} tasks, "
        f"{summary['import_candidates']} import candidates -> {summary['db_path']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
