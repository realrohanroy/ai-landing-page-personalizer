from openai import OpenAI
import json

client = OpenAI()

def extract_ad(ad_text):
    prompt = f"""
Extract structured insights from this ad:

Fields:
- core_promise
- audience
- emotional_trigger
- offer
- tone

Ad:
{ad_text}

Return JSON only.
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        response_format={"type": "json_object"},
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )

    return json.loads(res.choices[0].message.content)