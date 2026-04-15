from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from ad_extractor import extract_ad
from page_parser import parse_page
from modifier import modify_page, apply_changes, build_hero_card
import uuid

app = FastAPI()

# ── In-memory session store ─────────────────────────────────────
# Stores modified HTML by session ID
# In production this would be Redis, but for demo this is fine
previews = {}

# ── Input Model ─────────────────────────────────────────────────
class Input(BaseModel):
    ad_text: str
    url: str

# ── Main Generate Endpoint ──────────────────────────────────────
@app.post("/generate")
def generate(data: Input):

    # Step 1: Extract ad intent
    try:
        ad_data = extract_ad(data.ad_text)
    except Exception as e:
        return _error_response("Failed to extract ad intent", str(e))

    # Step 2: Parse landing page
    page_data = parse_page(data.url)

    # Step 3: Route based on parse result
    # ── MODE A: Page fetched successfully → try full proxy ──────
    if not page_data["parse_failed"]:
        try:
            result = modify_page(ad_data, page_data)

            if not result or "personalized" not in result:
                raise ValueError("LLM returned invalid output")

            # Inject changes into real HTML
            modified_html = apply_changes(page_data, result)

            # Fix relative URLs so assets load correctly
            modified_html = fix_relative_urls(modified_html, page_data["base_url"])

            # Store with session ID
            session_id = str(uuid.uuid4())
            previews[session_id] = modified_html

            return {
                "mode": "full_page",
                "preview_url": f"/preview/{session_id}",
                "original": result["original"],
                "personalized": result["personalized"],
                "changes": result["changes"],
                "confidence": result.get("confidence", "medium"),
                "confidence_reason": result.get("confidence_reason", ""),
                "ad_intent": ad_data,
                "variants": result.get("variants", []),
                "fallback": False
            }

        except Exception as e:
            # Full page failed → fall through to hero card
            page_data["parse_failed"] = True
            page_data["fetch_status"] = f"modification_error: {str(e)}"

    # ── MODE B: Page blocked or modification failed → hero card ─
    try:
        result = modify_page(ad_data, page_data)

        if not result or "personalized" not in result:
            raise ValueError("LLM returned invalid output")

        # Build hero card instead of full page
        hero_html = build_hero_card(page_data, result)

        session_id = str(uuid.uuid4())
        previews[session_id] = hero_html

        return {
            "mode": "hero_preview",
            "preview_url": f"/preview/{session_id}",
            "original": result["original"],
            "personalized": result["personalized"],
            "changes": result["changes"],
            "confidence": result.get("confidence", "medium"),
            "confidence_reason": result.get("confidence_reason", ""),
            "ad_intent": ad_data,
            "variants": result.get("variants", []),
            "fallback": True,
            "fallback_reason": f"Site blocked server access ({page_data['fetch_status']}). Showing hero section preview."
        }

    except Exception as e:
        return _error_response("Personalization failed", str(e))


# ── Preview Endpoint ─────────────────────────────────────────────
# Frontend iframe points here, not to original site
# This is how we avoid X-Frame-Options blocking
@app.get("/preview/{session_id}")
def preview(session_id: str):
    html = previews.get(session_id)
    if not html:
        return HTMLResponse("""
            <div style='font-family:sans-serif;padding:40px;text-align:center;color:#888'>
                Preview expired or not found.<br>
                Please generate again.
            </div>
        """)
    return HTMLResponse(html)


# ── Helper: Fix relative URLs ────────────────────────────────────
# Adds <base> tag so images/CSS load from original domain
def fix_relative_urls(html: str, base_url: str) -> str:
    if not base_url:
        return html
    base_tag = f'<base href="{base_url}">'
    if "<head>" in html:
        return html.replace("<head>", f"<head>{base_tag}", 1)
    return base_tag + html


# ── Helper: Structured error response ───────────────────────────
def _error_response(message: str, detail: str = "") -> dict:
    return {
        "mode": "error",
        "error": message,
        "detail": detail,
        "original": {"headline": "", "cta": ""},
        "personalized": {"headline": "", "cta": ""},
        "changes": [],
        "confidence": "low",
        "confidence_reason": "System error occurred",
        "ad_intent": {},
        "variants": [],
        "fallback": True,
        "fallback_reason": message
    }