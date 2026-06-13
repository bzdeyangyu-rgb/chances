# -*- coding: utf-8 -*-
from __future__ import annotations

from subprocess import TimeoutExpired
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from backend.browser_import import canonicalize_job_url, detect_platform, import_page_capture, upsert_job
from backend.boss_agent_bridge import parse_boss_agent_envelope, run_boss_search
from backend.db import (
    DEFAULT_CAPTURES_DIR,
    accept_import_review_candidate,
    add_application_event,
    add_job_action,
    build_visual_summary,
    build_weekly_review,
    bulk_update_job_status,
    complete_job_task,
    create_job_task,
    create_import_review_candidates,
    delete_search_preset,
    get_job,
    get_job_evaluation,
    get_job_materials,
    get_latest_job_score_snapshot,
    initialize_database,
    list_job_actions,
    list_application_events,
    list_job_capture_assets,
    list_job_score_snapshots,
    list_job_tasks,
    list_jobs,
    list_jobs_page,
    list_import_review_candidates,
    list_search_presets,
    load_profile,
    save_job_capture_assets,
    save_job_evaluation,
    save_job_materials,
    save_job_score_snapshot,
    save_profile,
    save_search_preset,
    reject_import_review_candidate,
    update_job_status,
    update_job_visual_summary,
    upsert_job_record,
)
from backend.evaluation import evaluate_job_against_profile
from backend.materials import build_preparation_pack
from backend.profile_tools import build_profile_match, derive_profile_from_resume, extract_resume_text
from backend.visual_summary import build_structured_visual_summary
from frontend.data_store import DEFAULT_WORKBOOK, load_or_initialize_jobs


class JobPayload(BaseModel):
    platform: str
    job_title: str
    company_name: str = ""
    salary_raw: str = ""
    location: str = ""
    education: str = ""
    experience: str = ""
    financing_stage: str = ""
    company_size: str = ""
    industry: str = ""
    benefits: str = ""
    published_at: str = ""
    job_url: str
    skills: str = ""
    main_text: str = ""
    status: str = ""
    priority: str = ""
    next_action: str = ""
    notes: str = ""


class PageCapturePayload(BaseModel):
    url: str
    title: str = ""
    body_lines: list[str] = []
    extracted_job: JobPayload | None = None


class ScreenshotPayload(BaseModel):
    asset_type: str = "visible"
    data_url: str
    mime_type: str = "image/png"
    text_excerpt: str = ""


class VisualPageCapturePayload(BaseModel):
    url: str
    title: str = ""
    body_lines: list[str] = []
    extracted_job: JobPayload | None = None
    screenshots: list[ScreenshotPayload] = []


class ProfilePayload(BaseModel):
    target_roles: str = ""
    target_cities: str = ""
    remote_preference: str = ""
    salary_min: str = ""
    salary_ideal: str = ""
    core_skills: str = ""
    project_highlights: str = ""
    no_go_rules: str = ""


class ResumeImportPayload(BaseModel):
    resume_path: str


class JobStatusPayload(BaseModel):
    status: str
    next_action: str = ""
    note: str = ""


class JobEvaluationPayload(BaseModel):
    match_score: int = 0
    recommendation: str = ""
    reasoning: str = ""
    highlights: str = ""
    risks: str = ""
    next_step_hint: str = ""


class JobMaterialsPayload(BaseModel):
    resume_angle: str = ""
    project_highlights: str = ""
    recruiter_questions: str = ""
    interview_prep: str = ""
    communication_draft: str = ""
    risk_response: str = ""


class ApplicationEventPayload(BaseModel):
    event_type: str
    channel: str = ""
    note: str = ""
    event_at: str = ""


class JobTaskPayload(BaseModel):
    title: str
    due_date: str = ""


class ImportReviewPayload(BaseModel):
    source: str = "manual"
    items: list[dict[str, object]]


class RejectImportCandidatePayload(BaseModel):
    reason: str = ""


class BulkJobStatusPayload(BaseModel):
    job_ids: list[int]
    status: str
    next_action: str = ""
    note: str = ""


class SearchPresetPayload(BaseModel):
    name: str
    platform: str = ""
    city: str = ""
    query: str = ""
    salary: str = ""
    filters_json: str = ""


class SearchPresetRunPayload(BaseModel):
    limit: int = 20


def build_visual_fallback_job(url: str, title: str, body_lines: list[str]) -> dict[str, str]:
    canonical_url = canonicalize_job_url(url)
    cleaned_lines = [str(line).strip() for line in body_lines if str(line).strip()]
    title_parts = [part.strip() for part in title.replace("_", "-").split("-") if part.strip()]
    job_title = cleaned_lines[0] if cleaned_lines else (title_parts[0] if title_parts else "")
    company_name = title_parts[1] if len(title_parts) > 1 else ""
    salary_raw = next((line for line in cleaned_lines if "K" in line or "k" in line), "")
    location = next((line for line in cleaned_lines if any(token in line for token in ["南京", "上海", "北京", "杭州", "深圳", "苏州", "广州"])), "")
    return {
        "platform": detect_platform(canonical_url),
        "job_title": job_title,
        "company_name": company_name,
        "salary_raw": salary_raw,
        "location": location,
        "education": "",
        "experience": "",
        "financing_stage": "",
        "company_size": "",
        "industry": "",
        "benefits": "",
        "published_at": "",
        "job_url": canonical_url,
        "skills": "",
        "main_text": "\n".join(cleaned_lines[:120]),
    }


def create_app(
    workbook_path: Path | str = DEFAULT_WORKBOOK,
    db_path: Path | str | None = None,
    captures_dir: Path | str = DEFAULT_CAPTURES_DIR,
) -> FastAPI:
    app = FastAPI(title="求职作战台 API")
    app.state.workbook_path = Path(workbook_path)
    app.state.db_path = Path(db_path) if db_path is not None else app.state.workbook_path.with_suffix(".db")
    app.state.captures_dir = Path(captures_dir)
    initialize_database(app.state.db_path)

    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r"(chrome-extension://.*|http://localhost(:\d+)?|http://127\.0\.0\.1(:\d+)?)",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health")
    def get_health() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "chances-api",
            "database": "ready",
        }

    @app.get("/api/jobs")
    def get_jobs(
        page: int | None = None,
        page_size: int | None = None,
        status: str = "",
        priority: str = "",
        keyword: str = "",
        platform: str = "",
        has_screenshots: bool | None = None,
    ) -> list[dict[str, object]] | dict[str, object]:
        load_or_initialize_jobs(app.state.workbook_path)
        if any(
            [
                page is not None,
                page_size is not None,
                status,
                priority,
                keyword,
                platform,
                has_screenshots is not None,
            ]
        ):
            return list_jobs_page(
                app.state.db_path,
                page=page or 1,
                page_size=page_size or 50,
                status=status,
                priority=priority,
                keyword=keyword,
                platform=platform,
                has_screenshots=has_screenshots,
            )
        return list_jobs(app.state.db_path)

    @app.get("/api/jobs/{job_id}")
    def get_job_detail(job_id: int) -> dict[str, object]:
        job = get_job(job_id, app.state.db_path)
        if job is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        profile = load_profile(app.state.db_path)
        return {
            "job": job,
            "timeline": list_job_actions(job_id, app.state.db_path),
            "evaluation": get_job_evaluation(job_id, app.state.db_path),
            "score_history": list_job_score_snapshots(job_id, app.state.db_path),
            "assets": list_job_capture_assets(job_id, app.state.db_path),
            "materials": get_job_materials(job_id, app.state.db_path),
            "application_events": list_application_events(job_id, app.state.db_path),
            "tasks": list_job_tasks(app.state.db_path, job_id=job_id),
            "profile_match": build_profile_match(profile, job),
        }

    @app.post("/api/jobs")
    def post_job(payload: JobPayload) -> dict[str, str | int]:
        result = upsert_job_record(payload.model_dump(), app.state.db_path)
        upsert_job(payload.model_dump(), app.state.workbook_path)
        if result["result"] == "created":
            created_job = get_job(int(result["id"]), app.state.db_path)
            if created_job is not None:
                add_job_action(
                    int(result["id"]),
                    str(created_job["status"]),
                    str(created_job["next_action"]),
                    "岗位已进入机会池",
                    app.state.db_path,
                )
        return result

    @app.post("/api/jobs/{job_id}/status")
    def post_job_status(job_id: int, payload: JobStatusPayload) -> dict[str, object]:
        updated = update_job_status(
            job_id=job_id,
            status=payload.status,
            next_action=payload.next_action,
            note=payload.note,
            db_path=app.state.db_path,
        )
        if updated is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return updated

    @app.post("/api/jobs/bulk-status")
    def post_bulk_job_status(payload: BulkJobStatusPayload) -> dict[str, object]:
        return bulk_update_job_status(
            job_ids=payload.job_ids,
            status=payload.status,
            next_action=payload.next_action,
            note=payload.note,
            db_path=app.state.db_path,
        )

    @app.get("/api/search-presets")
    def get_search_presets() -> list[dict[str, object]]:
        return list_search_presets(app.state.db_path)

    @app.post("/api/search-presets")
    def post_search_preset(payload: SearchPresetPayload) -> dict[str, object]:
        try:
            return save_search_preset(payload.model_dump(), app.state.db_path)
        except ValueError as exc:
            detail = str(exc)
            status_code = 409 if "已存在" in detail else 400
            raise HTTPException(status_code=status_code, detail=detail) from exc

    @app.post("/api/search-presets/{preset_id}/run")
    def post_run_search_preset(preset_id: int, payload: SearchPresetRunPayload) -> dict[str, object]:
        preset = next((item for item in list_search_presets(app.state.db_path) if int(item["id"]) == preset_id), None)
        if preset is None:
            raise HTTPException(status_code=404, detail="搜索预设不存在")
        if str(preset.get("platform") or "").strip().lower() != "boss":
            raise HTTPException(status_code=400, detail="当前只支持运行 BOSS 搜索预设")

        try:
            envelope = run_boss_search(preset, limit=max(1, min(int(payload.limit), 100)))
        except FileNotFoundError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc
        except TimeoutExpired as exc:
            raise HTTPException(status_code=504, detail="boss-agent-cli search timed out") from exc
        except (RuntimeError, ValueError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        return create_import_review_candidates(
            source="boss_agent",
            items=parse_boss_agent_envelope(envelope),
            db_path=app.state.db_path,
        )

    @app.delete("/api/search-presets/{preset_id}")
    def delete_search_preset_endpoint(preset_id: int) -> dict[str, object]:
        return {"deleted": delete_search_preset(preset_id, app.state.db_path)}

    @app.post("/api/import-review/candidates")
    def post_import_review_candidates(payload: ImportReviewPayload) -> dict[str, object]:
        return create_import_review_candidates(
            source=payload.source,
            items=[dict(item) for item in payload.items],
            db_path=app.state.db_path,
        )

    @app.post("/api/import-review/boss-agent-envelope")
    def post_boss_agent_envelope(payload: dict[str, object]) -> dict[str, object]:
        return create_import_review_candidates(
            source="boss_agent",
            items=parse_boss_agent_envelope(payload),
            db_path=app.state.db_path,
        )

    @app.get("/api/import-review/candidates")
    def get_import_review_candidates(decision: str = "pending") -> list[dict[str, object]]:
        return list_import_review_candidates(app.state.db_path, decision=decision)

    @app.post("/api/import-review/candidates/{candidate_id}/accept")
    def post_accept_import_candidate(candidate_id: int) -> dict[str, object]:
        accepted = accept_import_review_candidate(candidate_id, app.state.db_path)
        if accepted is None:
            raise HTTPException(status_code=404, detail="导入候选不存在")
        upsert_job(dict(accepted["normalized_job"]), app.state.workbook_path)
        if accepted.get("job_id"):
            job = get_job(int(accepted["job_id"]), app.state.db_path)
            if job is not None:
                add_job_action(
                    int(accepted["job_id"]),
                    str(job["status"]),
                    str(job["next_action"]),
                    "通过导入审查加入岗位池",
                    app.state.db_path,
                )
        return accepted

    @app.post("/api/import-review/candidates/{candidate_id}/reject")
    def post_reject_import_candidate(
        candidate_id: int,
        payload: RejectImportCandidatePayload,
    ) -> dict[str, object]:
        rejected = reject_import_review_candidate(candidate_id, payload.reason, app.state.db_path)
        if rejected is None:
            raise HTTPException(status_code=404, detail="导入候选不存在")
        return rejected

    @app.get("/api/jobs/{job_id}/timeline")
    def get_job_timeline(job_id: int) -> list[dict[str, object]]:
        if get_job(job_id, app.state.db_path) is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return list_job_actions(job_id, app.state.db_path)

    @app.post("/api/jobs/{job_id}/evaluate")
    def post_job_evaluation(job_id: int, payload: JobEvaluationPayload) -> dict[str, object]:
        saved = save_job_evaluation(job_id, payload.model_dump(), app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return saved

    @app.post("/api/jobs/{job_id}/score")
    def post_job_score(job_id: int) -> dict[str, object]:
        job = get_job(job_id, app.state.db_path)
        if job is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        profile = load_profile(app.state.db_path)
        result = evaluate_job_against_profile(profile, job)
        saved = save_job_score_snapshot(job_id, result, app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return {**result, "snapshot_id": saved["id"], "created_at": saved["created_at"]}

    @app.get("/api/jobs/{job_id}/score-history")
    def get_job_score_history(job_id: int) -> list[dict[str, object]]:
        if get_job(job_id, app.state.db_path) is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return list_job_score_snapshots(job_id, app.state.db_path)

    @app.post("/api/jobs/{job_id}/materials")
    def post_job_materials(job_id: int, payload: JobMaterialsPayload) -> dict[str, object]:
        saved = save_job_materials(job_id, payload.model_dump(), app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return saved

    @app.post("/api/jobs/{job_id}/materials/generate")
    def post_generated_job_materials(job_id: int) -> dict[str, object]:
        job = get_job(job_id, app.state.db_path)
        if job is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        profile = load_profile(app.state.db_path)
        latest_score = get_latest_job_score_snapshot(job_id, app.state.db_path)
        score_result = latest_score["result"] if latest_score else None
        pack = build_preparation_pack(profile, job, score_result)
        saved = save_job_materials(job_id, pack, app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return saved

    @app.post("/api/jobs/{job_id}/visual-summary/regenerate")
    def post_regenerated_visual_summary(job_id: int) -> dict[str, object]:
        job = get_job(job_id, app.state.db_path)
        if job is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        assets = list_job_capture_assets(job_id, app.state.db_path)
        visual_summary = build_structured_visual_summary(job, assets)
        updated = update_job_visual_summary(job_id, visual_summary, app.state.db_path)
        if updated is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return {
            "job_id": job_id,
            "visual_summary": updated["visual_summary"],
            "visual_summary_status": updated["visual_summary_status"],
        }

    @app.post("/api/jobs/{job_id}/application-events")
    def post_application_event(job_id: int, payload: ApplicationEventPayload) -> dict[str, object]:
        saved = add_application_event(job_id, payload.model_dump(), app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return saved

    @app.get("/api/jobs/{job_id}/application-events")
    def get_application_events(job_id: int) -> list[dict[str, object]]:
        if get_job(job_id, app.state.db_path) is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return list_application_events(job_id, app.state.db_path)

    @app.post("/api/jobs/{job_id}/tasks")
    def post_job_task(job_id: int, payload: JobTaskPayload) -> dict[str, object]:
        saved = create_job_task(job_id, payload.model_dump(), app.state.db_path)
        if saved is None:
            raise HTTPException(status_code=404, detail="岗位不存在")
        return saved

    @app.get("/api/tasks")
    def get_tasks(status: str = "") -> list[dict[str, object]]:
        return list_job_tasks(app.state.db_path, status=status)

    @app.post("/api/tasks/{task_id}/complete")
    def post_complete_task(task_id: int) -> dict[str, object]:
        task = complete_job_task(task_id, app.state.db_path)
        if task is None:
            raise HTTPException(status_code=404, detail="任务不存在")
        return task

    @app.get("/api/profile")
    def get_profile() -> dict[str, str]:
        return load_profile(app.state.db_path)

    @app.post("/api/profile")
    def post_profile(payload: ProfilePayload) -> dict[str, str]:
        return save_profile(payload.model_dump(), app.state.db_path)

    @app.post("/api/profile/import-resume")
    def post_import_resume(payload: ResumeImportPayload) -> dict[str, object]:
        text = extract_resume_text(payload.resume_path)
        current = load_profile(app.state.db_path)
        profile, keywords = derive_profile_from_resume(text, current)
        saved = save_profile(profile, app.state.db_path)
        return {
            "profile": saved,
            "keywords": keywords,
            "resume_excerpt": text[:1200],
        }

    @app.post("/api/import-page")
    def post_import_page(payload: PageCapturePayload) -> dict[str, object]:
        try:
            result, job = import_page_capture(
                url=payload.url,
                title=payload.title,
                body_lines=payload.body_lines,
                extracted_job=payload.extracted_job.model_dump() if payload.extracted_job else None,
                workbook_path=app.state.workbook_path,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        sqlite_result = upsert_job_record(job, app.state.db_path)
        if sqlite_result["result"] == "created":
            created_job = get_job(int(sqlite_result["id"]), app.state.db_path)
            if created_job is not None:
                add_job_action(
                    int(sqlite_result["id"]),
                    str(created_job["status"]),
                    str(created_job["next_action"]),
                    "通过页面采集导入岗位",
                    app.state.db_path,
                )
        return {**sqlite_result, "job": job, "import_result": result}

    @app.post("/api/import-visual-page")
    def post_import_visual_page(payload: VisualPageCapturePayload) -> dict[str, object]:
        try:
            import_result, job = import_page_capture(
                url=payload.url,
                title=payload.title,
                body_lines=payload.body_lines,
                extracted_job=payload.extracted_job.model_dump() if payload.extracted_job else None,
                workbook_path=app.state.workbook_path,
            )
        except ValueError as exc:
            if "岗位名称" not in str(exc):
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            job = build_visual_fallback_job(payload.url, payload.title, payload.body_lines)
            import_result = {"result": "visual_fallback"}

        job["capture_mode"] = "visual"
        job["raw_capture_title"] = payload.title
        job["visual_summary_status"] = "ready" if payload.screenshots else "pending"
        screenshot_payloads = [item.model_dump() for item in payload.screenshots]
        job["visual_summary"] = build_visual_summary(job, screenshot_payloads)

        sqlite_result = upsert_job_record(job, app.state.db_path)
        job_id = int(sqlite_result["id"])
        saved_assets = save_job_capture_assets(
            job_id=job_id,
            screenshots=screenshot_payloads,
            db_path=app.state.db_path,
            captures_dir=app.state.captures_dir,
        )

        if sqlite_result["result"] == "created":
            created_job = get_job(job_id, app.state.db_path)
            if created_job is not None:
                add_job_action(
                    job_id,
                    str(created_job["status"]),
                    str(created_job["next_action"]),
                    "通过视觉截图导入岗位",
                    app.state.db_path,
                )

        final_job = get_job(job_id, app.state.db_path)
        return {
            **sqlite_result,
            "job": final_job,
            "assets": saved_assets,
            "import_result": import_result,
        }

    @app.get("/api/reviews/weekly")
    def get_weekly_review() -> dict[str, object]:
        return build_weekly_review(app.state.db_path)

    return app


app = create_app()
