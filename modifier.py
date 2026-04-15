from openai import OpenAI
import json

client = OpenAI()


def modify_page(ad_data: dict, page_data: dict) -> dict:
    """
    Core personalization function.
    Sends only text fields to LLM — never raw HTML.
    Returns structured result with changes, confidence, reasoning, and A/B variants.
    """

    page_summary = {
        "h1": page_data.get("h1", ""),
        "h2": page_data.get("h2", ""),
        "cta": page_data.get("cta", "")
    }

    prompt = f"""
You are a senior CRO (Conversion Rate Optimization) strategist.

Your job is to align a landing page with an ad creative to improve conversion.
You will modify ONLY these fields: headline, subheadline, cta.
DO NOT change structure, layout, images, or add new sections.

RULES:
- Headline: max 10 words, match the core promise of the ad
- Subheadline: max 20 words, support the headline with benefit or urgency
- CTA: max 5 words, action-oriented, match the offer
- Preserve brand tone — do not make it sound like a different brand
- Never invent claims not present in the ad

AD DATA:
{json.dumps(ad_data, indent=2)}

CURRENT PAGE ELEMENTS:
{json.dumps(page_summary, indent=2)}

Return ONLY this JSON structure, nothing else:

{{
  "original": {{
    "headline": "{page_summary.get('h1', '')}",
    "subheadline": "{page_summary.get('h2', '')}",
    "cta": "{page_summary.get('cta', '')}"
  }},
  "personalized": {{
    "headline": "...",
    "subheadline": "...",
    "cta": "..."
  }},
  "variants": [
    {{
      "label": "Version A – Urgency",
      "headline": "...",
      "subheadline": "...",
      "cta": "...",
      "strategy": "explain the conversion strategy behind this version"
    }},
    {{
      "label": "Version B – Benefit",
      "headline": "...",
      "subheadline": "...",
      "cta": "...",
      "strategy": "explain the conversion strategy behind this version"
    }}
  ],
  "changes": [
    {{
      "field": "headline",
      "original": "{page_summary.get('h1', '')}",
      "updated": "...",
      "reason": "explain CRO reasoning behind this specific change"
    }},
    {{
      "field": "subheadline",
      "original": "{page_summary.get('h2', '')}",
      "updated": "...",
      "reason": "explain CRO reasoning behind this specific change"
    }},
    {{
      "field": "cta",
      "original": "{page_summary.get('cta', '')}",
      "updated": "...",
      "reason": "explain CRO reasoning behind this specific change"
    }}
  ],
  "confidence": "high or medium or low",
  "confidence_reason": "explain what drove this confidence level — tone match, offer clarity, audience alignment"
}}
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        # Safety: ensure all required keys exist
        result = _validate_result(result, page_summary)
        return result

    except json.JSONDecodeError:
        return _fallback_result(page_summary, "LLM returned invalid JSON")

    except Exception as e:
        return _fallback_result(page_summary, str(e))


def apply_changes(page_data: dict, result: dict) -> str:
    """
    Injects personalized text into original HTML.
    Only modifies text nodes — never touches structure, layout, or attributes.
    """
    soup = page_data.get("soup")
    if not soup:
        return ""

    h1_tag = page_data.get("h1_tag")
    cta_tag = page_data.get("cta_tag")
    personalized = result.get("personalized", {})

    # Modify headline
    if h1_tag and personalized.get("headline"):
        h1_tag.string = personalized["headline"]

    # Modify subheadline — find h2 tag
    h2_tag = soup.find("h2")
    if h2_tag and personalized.get("subheadline"):
        h2_tag.string = personalized["subheadline"]

    # Modify CTA
    if cta_tag and personalized.get("cta"):
        cta_tag.string = personalized["cta"]

    return str(soup)


def build_hero_card(page_data: dict, result: dict) -> str:
    """
    Builds a clean side-by-side hero card when full page proxy is blocked.
    Uses only extracted text elements — no iframe, no external dependencies.
    Always renders correctly regardless of target site security policy.
    Includes A/B variants panel below the main comparison.
    """

    logo_url = page_data.get("logo_url")
    base_url = page_data.get("base_url", "")

    if logo_url:
        logo_html = f'<img src="{logo_url}" style="height:36px;margin-bottom:20px;object-fit:contain;" onerror="this.style.display:none">'
    else:
        domain = base_url.replace("https://", "").replace("http://", "").replace("www.", "")
        logo_html = f'<div style="font-size:18px;font-weight:800;color:#333;margin-bottom:20px;">{domain}</div>'

    original = result.get("original", {})
    personalized = result.get("personalized", {})
    variants = result.get("variants", [])
    confidence = result.get("confidence", "medium")
    confidence_reason = result.get("confidence_reason", "")

    # confidence badge color
    confidence_colors = {
        "high": ("#dcfce7", "#16a34a"),
        "medium": ("#fef9c3", "#ca8a04"),
        "low": ("#fee2e2", "#dc2626")
    }
    conf_bg, conf_color = confidence_colors.get(confidence, ("#f3f4f6", "#374151"))

    # build variants HTML
    variants_html = ""
    if variants:
        variant_cards = ""
        for v in variants:
            variant_cards += f"""
            <div style="background:white;border-radius:12px;padding:24px;border:1px solid #e5e7eb;">
                <div style="font-size:11px;font-weight:700;color:#6366f1;text-transform:uppercase;
                            letter-spacing:0.08em;margin-bottom:12px;">{v.get('label', '')}</div>
                <div style="font-size:18px;font-weight:700;color:#111827;margin-bottom:8px;">
                    {v.get('headline', '')}</div>
                <div style="font-size:13px;color:#6b7280;margin-bottom:12px;">
                    {v.get('subheadline', '')}</div>
                <button style="background:#6366f1;color:white;border:none;padding:10px 20px;
                               border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;">
                    {v.get('cta', '')}</button>
                <div style="margin-top:12px;font-size:12px;color:#9ca3af;font-style:italic;">
                    Strategy: {v.get('strategy', '')}</div>
            </div>
            """

        variants_html = f"""
        <div style="width:100%;max-width:860px;margin-top:24px;">
            <div style="font-size:13px;font-weight:700;color:#374151;margin-bottom:12px;
                        text-transform:uppercase;letter-spacing:0.05em;">
                A/B Variants — Test these against each other
            </div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:16px;">
                {variant_cards}
            </div>
        </div>
        """

    return f"""
<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
      background: #f4f4f5;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 32px 16px;
      gap: 0;
    }}
    .notice {{
      font-size: 12px;
      color: #888;
      margin-bottom: 20px;
      background: #fff8e1;
      border: 1px solid #ffe082;
      border-radius: 6px;
      padding: 8px 16px;
      text-align: center;
      max-width: 860px;
      width: 100%;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
      width: 100%;
      max-width: 860px;
    }}
    .card {{
      background: white;
      border-radius: 16px;
      padding: 36px 32px;
      border: 2px solid #e5e7eb;
    }}
    .card.personalized {{
      border-color: #22c55e;
      box-shadow: 0 8px 32px rgba(34,197,94,0.12);
    }}
    .badge {{
      display: inline-block;
      font-size: 11px;
      font-weight: 700;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: #9ca3af;
      margin-bottom: 20px;
      padding: 4px 10px;
      background: #f3f4f6;
      border-radius: 20px;
    }}
    .card.personalized .badge {{
      color: #16a34a;
      background: #dcfce7;
    }}
    .headline {{
      font-size: 26px;
      font-weight: 800;
      color: #111827;
      line-height: 1.3;
      margin-bottom: 12px;
    }}
    .subheadline {{
      font-size: 15px;
      color: #6b7280;
      line-height: 1.6;
      margin-bottom: 28px;
      min-height: 48px;
    }}
    .cta-btn {{
      display: inline-block;
      padding: 13px 28px;
      border-radius: 8px;
      font-size: 15px;
      font-weight: 600;
      border: none;
      cursor: pointer;
      background: #374151;
      color: white;
    }}
    .card.personalized .cta-btn {{
      background: #16a34a;
    }}
    @media (max-width: 600px) {{
      .grid {{ grid-template-columns: 1fr; }}
    }}
  </style>
</head>
<body>

  <div class="notice">
    ⚠ Full page preview unavailable — site blocked server access.
    Showing hero section reconstruction.
  </div>

  <div class="grid">
    <div class="card">
      <div class="badge">Original</div>
      {logo_html}
      <div class="headline">{original.get('headline', '')}</div>
      <div class="subheadline">{original.get('subheadline', '')}</div>
      <button class="cta-btn">{original.get('cta', '')}</button>
    </div>
    <div class="card personalized">
      <div class="badge">✦ Personalized</div>
      {logo_html}
      <div class="headline">{personalized.get('headline', '')}</div>
      <div class="subheadline">{personalized.get('subheadline', '')}</div>
      <button class="cta-btn">{personalized.get('cta', '')}</button>
    </div>
  </div>

  <!-- Confidence -->
  <div style="width:100%;max-width:860px;margin-top:16px;padding:14px 20px;
              background:{conf_bg};border-radius:10px;border:1px solid {conf_color}20;">
    <span style="font-size:12px;font-weight:700;color:{conf_color};text-transform:uppercase;">
      Confidence: {confidence}
    </span>
    <span style="font-size:12px;color:#6b7280;margin-left:12px;">{confidence_reason}</span>
  </div>

  {variants_html}

</body>
</html>
"""


# ── Internal helpers ─────────────────────────────────────────────

def _validate_result(result: dict, page_summary: dict) -> dict:
    """Ensures all required keys exist — prevents KeyErrors downstream"""
    if "original" not in result:
        result["original"] = {
            "headline": page_summary.get("h1", ""),
            "subheadline": page_summary.get("h2", ""),
            "cta": page_summary.get("cta", "")
        }
    if "personalized" not in result:
        result["personalized"] = result["original"].copy()
    if "changes" not in result:
        result["changes"] = []
    if "confidence" not in result:
        result["confidence"] = "medium"
    if "confidence_reason" not in result:
        result["confidence_reason"] = ""
    if "variants" not in result:
        result["variants"] = []
    return result


def _fallback_result(page_summary: dict, error: str) -> dict:
    """Safe fallback when LLM call fails entirely"""
    original = {
        "headline": page_summary.get("h1", ""),
        "subheadline": page_summary.get("h2", ""),
        "cta": page_summary.get("cta", "")
    }
    return {
        "original": original,
        "personalized": original.copy(),
        "changes": [],
        "confidence": "low",
        "confidence_reason": f"Personalization failed: {error}",
        "variants": [],
        "error": error
    }