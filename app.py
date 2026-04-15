import streamlit as st
import requests
BACKEND_URL = "https://ai-backend-2z89.onrender.com"

st.set_page_config(page_title="AI Landing Page Personalizer", layout="wide")
st.title("🚀 AI Landing Page Personalizer")
st.caption("Aligns your landing page with ad intent to improve conversion rates")

# ── Inputs ───────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    input_type = st.radio("Ad Input Type", ["Text", "Image Upload", "URL"])
    ad_text = ""

    if input_type == "Text":
        ad_text = st.text_area("Enter Ad Creative", height=120,
                               placeholder="e.g. Get 50% off premium skincare. Limited time offer.")

    elif input_type == "Image Upload":
        uploaded_file = st.file_uploader("Upload Ad Image", type=["png", "jpg", "jpeg"])
        if uploaded_file:
            st.image(uploaded_file, caption="Uploaded Ad", use_column_width=True)
            ad_text = "Image-based ad: premium skincare discount offer"
            st.info("Image uploaded — using extracted intent for demo.")

    elif input_type == "URL":
        ad_url = st.text_input("Enter Ad URL")
        if ad_url:
            ad_text = f"Ad from URL: {ad_url}"

with col2:
    url = st.text_input("Landing Page URL",
                        placeholder="e.g. https://books.toscrape.com")
    st.caption("The system will fetch, parse, and personalize this page based on your ad.")

st.divider()

# ── Generate ─────────────────────────────────────────────────────
if st.button("⚡ Generate Personalized Page", type="primary", use_container_width=True):

    if not ad_text or not url:
        st.warning("Please provide both Ad input and Landing Page URL.")
        st.stop()

    with st.spinner("Extracting ad intent and personalizing page..."):
        try:
            res = requests.post(
                f"{BACKEND_URL}/generate",
                json={"ad_text": ad_text, "url": url},
                timeout=30
            )
            data = res.json()
        except requests.exceptions.Timeout:
            st.error("Request timed out. The target page may be slow to load.")
            st.stop()
        except Exception as e:
            st.error(f"Could not reach backend: {e}")
            st.stop()

    # ── Error state ───────────────────────────────────────────────
    if data.get("mode") == "error":
        st.error(f"⚠ {data.get('error', 'Unknown error')}")
        st.caption(data.get("detail", ""))
        st.stop()

    st.success("✅ Personalization applied successfully!")

    # ── Fallback notice ───────────────────────────────────────────
    if data.get("fallback"):
        st.warning(f"ℹ {data.get('fallback_reason', 'Showing hero section preview.')}")

    # ── Ad Intent Panel ───────────────────────────────────────────
    ad_intent = data.get("ad_intent", {})
    if ad_intent:
        st.markdown("### 🧠 Ad Intent Extracted")
        st.caption("What the system understood from your ad before making any changes")
        
        cols = st.columns(5)
        labels = ["core_promise", "audience", "emotional_trigger", "offer", "tone"]
        icons  = ["🎯", "👤", "💡", "🎁", "🗣"]

        for i, (label, icon) in enumerate(zip(labels, icons)):
            with cols[i]:
                val = ad_intent.get(label, "—")
                st.markdown(f"**{icon} {label.replace('_', ' ').title()}**")
                st.markdown(f"<div style='font-size:14px;color:#e2e8f0;padding:8px 0'>{val}</div>",unsafe_allow_html=True)

    st.divider()

    # ── Original vs Personalized ──────────────────────────────────
    st.markdown("### 🔄 Before vs After")
    
    orig = data.get("original", {})
    pers = data.get("personalized", {})

    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**Original**")
        st.markdown(f"**Headline:** {orig.get('headline', '—')}")
        st.markdown(f"**Subheadline:** {orig.get('subheadline', '—')}")
        st.markdown(f"**CTA:** {orig.get('cta', '—')}")

    with c2:
        st.markdown("**✦ Personalized**")
        st.markdown(f"**Headline:** {pers.get('headline', '—')}")
        st.markdown(f"**Subheadline:** {pers.get('subheadline', '—')}")
        st.markdown(f"**CTA:** {pers.get('cta', '—')}")

    st.divider()

    # ── Changes + Reasoning ───────────────────────────────────────
    st.markdown("### 📋 Changes Applied")
    st.caption("Every change has a CRO reason — the AI never modifies without justification")

    changes = data.get("changes", [])
    if changes:
        for change in changes:
            with st.expander(f"**{change.get('field', '').upper()}** — click to see reasoning"):
                c1, c2 = st.columns(2)
                with c1:
                    st.markdown(f"**Before:** {change.get('original', '—')}")
                with c2:
                    st.markdown(f"**After:** {change.get('updated', '—')}")
                st.info(f"💡 {change.get('reason', '—')}")
    else:
        st.write("No changes recorded.")

    st.divider()

    # ── Confidence ────────────────────────────────────────────────
    st.markdown("### 📊 Confidence Score")
    
    confidence = data.get("confidence", "low")
    confidence_reason = data.get("confidence_reason", "")

    if confidence == "high":
        st.success(f"🟢 Confidence: HIGH — {confidence_reason}")
    elif confidence == "medium":
        st.warning(f"🟡 Confidence: MEDIUM — {confidence_reason}")
    else:
        st.error(f"🔴 Confidence: LOW — {confidence_reason}")

    st.divider()

    # ── A/B Variants ──────────────────────────────────────────────
    variants = data.get("variants", [])
    if variants:
        st.markdown("### 🧪 A/B Variants")
        st.caption("Two strategic versions for testing — run both and measure which converts better")

        for i, variant in enumerate(variants):
            with st.container():
                c1, c2 = st.columns([4, 1])
                with c1:
                    st.markdown(f"**{variant.get('label', f'Variant {i+1}')}**")
                    st.markdown(f"Headline: `{variant.get('headline', '—')}`")
                    st.markdown(f"Subheadline: `{variant.get('subheadline', '—')}`")
                    st.markdown(f"CTA: `{variant.get('cta', '—')}`")
                    st.caption(f"Strategy: {variant.get('strategy', '—')}")
                with c2:
                    if st.button(f"Apply Variant {i+1}", key=f"variant_{i}"):
                        # Store selected variant in session state
                        st.session_state["selected_variant"] = variant
                        st.success(f"Variant {i+1} selected — use this in your next test")
            st.divider()

    # ── Page Preview ──────────────────────────────────────────────
    st.markdown("### 🖥 Page Preview")

    preview_url = data.get("preview_url", "")
    mode = data.get("mode", "")

    if mode == "full_page":
        st.caption("Showing full modified page served from your backend — no iframe blocking")
    else:
        st.caption("Showing hero section reconstruction — full page was blocked by site security policy")

    if preview_url:
        full_preview_url = f"{BACKEND_URL}{preview_url}"
        st.components.v1.iframe(full_preview_url, height=650, scrolling=True)
    else:
        st.warning("No preview available.")