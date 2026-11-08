import json
from config import Config

def analyze_with_gemini(resume_text, job_text, score_data):
    if not Config.GEMINI_API_KEY:
        return {"summary": "Rule-based analysis completed. Add a Gemini API key to enable tailored AI feedback.",
                "strengths": [], "weaknesses": [], "suggestions": [
                  "Add relevant skills only when you genuinely have them.",
                  "Use measurable outcomes in project descriptions where accurate.",
                  "Keep section headings clear and consistent."
                ], "improved_summary": ""}
    try:
        import google.generativeai as genai
        genai.configure(api_key=Config.GEMINI_API_KEY)
        model = genai.GenerativeModel(Config.GEMINI_MODEL)
        prompt = f"""You are a careful resume coach. Compare the resume with the job description.
Never invent qualifications, experience, metrics, certifications, or skills. Return valid JSON only:
{{"summary":"","strengths":[],"weaknesses":[],"suggestions":[],"improved_summary":""}}
The improved summary must use only facts present in the resume. ATS score is calculated separately by code; do not return a score.
RESUME:
{resume_text[:18000]}
JOB DESCRIPTION:
{job_text[:10000]}
MATCH DATA:
{json.dumps(score_data, ensure_ascii=False)}"""
        response = model.generate_content(prompt)
        raw = response.text.strip().replace("```json", "").replace("```", "")
        data = json.loads(raw)
        for key, default in [("summary",""),("strengths",[]),("weaknesses",[]),("suggestions",[]),("improved_summary","")]:
            if not isinstance(data.get(key, default), type(default)):
                data[key] = default
        return data
    except Exception:
        return {"summary": "AI feedback is temporarily unavailable. The rule-based ATS analysis is still available.",
                "strengths": [], "weaknesses": [], "suggestions": ["Review missing keywords and add only truthful, relevant details."],
                "improved_summary": ""}
