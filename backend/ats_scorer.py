import re

SKILL_TERMS = {
 "python","java","javascript","typescript","html","css","react","node.js","flask","django",
 "sql","postgresql","mysql","mongodb","supabase","git","github","api","rest api",
 "machine learning","deep learning","artificial intelligence","generative ai","data analysis",
 "pandas","numpy","scikit-learn","tensorflow","pytorch","excel","power bi","tableau",
 "communication","teamwork","leadership","problem solving","time management","adaptability",
 "project management","critical thinking","cloud","aws","azure","docker"
}

def normalize(text):
    return re.sub(r"[^a-z0-9+#. ]+", " ", (text or "").lower())

def terms_in(text, terms):
    haystack = " " + normalize(text) + " "
    found = []
    for term in terms:
        t = normalize(term).strip()
        if t and re.search(r"(?<![a-z0-9])" + re.escape(t) + r"(?![a-z0-9])", haystack):
            found.append(term)
    return sorted(set(found))

def calculate_score(resume_text, job_text):
    job_terms = terms_in(job_text, SKILL_TERMS)
    resume_terms = terms_in(resume_text, SKILL_TERMS)
    required = job_terms or terms_in(job_text, set(re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", job_text)))
    matched = sorted(set(required) & set(resume_terms))
    missing = sorted(set(required) - set(resume_terms))
    skill_pct = len(matched) / max(1, len(required)) * 100

    job_words = set(re.findall(r"[a-z0-9+#]{4,}", normalize(job_text)))
    resume_words = set(re.findall(r"[a-z0-9+#]{4,}", normalize(resume_text)))
    stop = {"with","this","that","from","will","your","have","work","role","team","years","using","about","good","able"}
    keywords = sorted(job_words - stop)
    matched_kw = sorted(set(keywords) & resume_words)
    missing_kw = sorted(set(keywords) - resume_words)
    keyword_pct = len(matched_kw) / max(1, len(keywords)) * 100

    lower = resume_text.lower()
    education_pct = 100 if any(x in lower for x in ["b.tech","bachelor","degree","university","college","education"]) else 35
    experience_pct = 100 if any(x in lower for x in ["project","internship","experience","developed","built"]) else 30
    structure_signals = ["education","skills","project","experience"]
    structure_pct = sum(x in lower for x in structure_signals) / len(structure_signals) * 100

    score = round(skill_pct*.40 + keyword_pct*.25 + education_pct*.10 + experience_pct*.15 + structure_pct*.10)
    return {
      "ats_score": max(0, min(100, score)),
      "breakdown": {"skills_matching": round(skill_pct), "keyword_matching": round(keyword_pct),
                    "education_matching": round(education_pct), "projects_experience": round(experience_pct),
                    "resume_structure": round(structure_pct)},
      "matched_skills": matched, "missing_skills": missing,
      "matched_keywords": matched_kw[:40], "missing_keywords": missing_kw[:40],
      "score_note": "Estimated compatibility only; different employers and ATS products use different criteria."
    }
