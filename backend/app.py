import os, uuid
from datetime import datetime, timezone
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
from supabase import create_client, Client
from config import Config
from resume_parser import extract_text
from ats_scorer import calculate_score
from ai_analyzer import analyze_with_gemini
from report_generator import make_report

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = Config.MAX_UPLOAD_MB * 1024 * 1024
CORS(app, origins=Config.CORS_ORIGINS or "*", supports_credentials=False)

def admin_client():
    if not Config.SUPABASE_URL or not Config.SUPABASE_SERVICE_ROLE_KEY:
        raise RuntimeError("Supabase server configuration is missing.")
    return create_client(Config.SUPABASE_URL, Config.SUPABASE_SERVICE_ROLE_KEY)

def current_user():
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None, (jsonify({"error":"Authentication required."}), 401)
    token = auth[7:].strip()
    try:
        user = admin_client().auth.get_user(token).user
        if not user:
            raise ValueError("Invalid token")
        return user, None
    except Exception:
        return None, (jsonify({"error":"Invalid or expired session."}), 401)

def fail(message, code=400):
    return jsonify({"error": message}), code

@app.errorhandler(413)
def too_large(_):
    return fail(f"File is too large. Maximum size is {Config.MAX_UPLOAD_MB} MB.", 413)

@app.get("/api/health")
def health():
    return jsonify({"status":"ok","service":"AI Resume Analyzer API"})

@app.post("/api/register")
def register():
    body = request.get_json(silent=True) or {}
    name, email, password = body.get("name","").strip(), body.get("email","").strip(), body.get("password","")
    if not name or not email or len(password) < 8:
        return fail("Name, valid email, and password (at least 8 characters) are required.")
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
        result = client.auth.sign_up({"email":email,"password":password,"options":{"data":{"name":name}}})
        return jsonify({"message":"Registration submitted. Check your email if confirmation is enabled.",
                        "user_id": getattr(result.user,"id",None)}), 201
    except Exception:
        return fail("Registration failed. Check the email or try again.", 400)

@app.post("/api/login")
def login():
    body = request.get_json(silent=True) or {}
    try:
        client = create_client(Config.SUPABASE_URL, Config.SUPABASE_ANON_KEY)
        result = client.auth.sign_in_with_password({"email":body.get("email",""),"password":body.get("password","")})
        return jsonify({"access_token":result.session.access_token,"refresh_token":result.session.refresh_token,
                        "user":{"id":result.user.id,"email":result.user.email}})
    except Exception:
        return fail("Invalid email or password.", 401)

@app.post("/api/logout")
def logout():
    return jsonify({"message":"Signed out locally. Clear the client session token."})

@app.post("/api/upload-resume")
def upload_resume():
    user, error = current_user()
    if error: return error
    file = request.files.get("resume")
    if not file or not file.filename:
        return fail("Choose a PDF or DOCX resume.")
    try:
        data = file.read()
        text = extract_text(file.filename, data)
        client = admin_client()
        path = f"{user.id}/{uuid.uuid4()}_{os.path.basename(file.filename)}"
        client.storage.from_(Config.STORAGE_BUCKET).upload(path, data, {"content-type":file.mimetype or "application/octet-stream","upsert":"false"})
        row = {"user_id":user.id,"filename":os.path.basename(file.filename),"file_path":path,
               "extracted_text":text,"uploaded_at":datetime.now(timezone.utc).isoformat()}
        saved = client.table("resumes").insert(row).execute().data[0]
        return jsonify({"resume_id":saved["id"],"filename":saved["filename"],"message":"Resume uploaded securely."}), 201
    except ValueError as e:
        return fail(str(e))
    except Exception:
        return fail("Upload failed. Ensure the private 'resumes' storage bucket and database schema exist.", 500)

@app.post("/api/analyze-resume")
def analyze_resume():
    user, error = current_user()
    if error: return error
    body = request.get_json(silent=True) or {}
    resume_id, job_title = body.get("resume_id"), body.get("job_title","").strip()
    job_text = body.get("job_description","").strip()
    if not resume_id or len(job_text) < 40:
        return fail("Select a resume and enter a job description (at least 40 characters).")
    client = admin_client()
    try:
        resume = client.table("resumes").select("*").eq("id",resume_id).eq("user_id",user.id).single().execute().data
        if not resume: return fail("Resume not found.",404)
        job = client.table("job_descriptions").insert({"user_id":user.id,"job_title":job_title or "Target role",
                "company_name":body.get("company_name",""),"description":job_text}).execute().data[0]
        score = calculate_score(resume["extracted_text"],job_text)
        ai = analyze_with_gemini(resume["extracted_text"],job_text,score)
        report = {**score,**ai,"job_title":job_title or "Target role"}
        saved = client.table("analysis_reports").insert({"user_id":user.id,"resume_id":resume_id,"job_id":job["id"],
            "ats_score":score["ats_score"],"matched_skills":score["matched_skills"],"missing_skills":score["missing_skills"],
            "suggestions":ai.get("suggestions",[]),"analysis_data":report}).execute().data[0]
        report["report_id"] = saved["id"]
        return jsonify(report)
    except Exception:
        return fail("Analysis failed. Verify database schema, resume ownership, and server configuration.",500)

@app.post("/api/improve-resume")
def improve_resume():
    user, error = current_user()
    if error: return error
    body = request.get_json(silent=True) or {}
    if not body.get("resume_text") or not body.get("job_description"):
        return fail("Resume text and job description are required.")
    score = calculate_score(body["resume_text"],body["job_description"])
    return jsonify(analyze_with_gemini(body["resume_text"],body["job_description"],score))

@app.get("/api/dashboard")
def dashboard():
    user, error = current_user()
    if error: return error
    try:
        c=admin_client()
        reports=c.table("analysis_reports").select("ats_score,created_at").eq("user_id",user.id).order("created_at",desc=True).execute().data
        scores=[r["ats_score"] for r in reports]
        return jsonify({"total_analyzed":len(reports),"latest_score":scores[0] if scores else None,
                        "average_score":round(sum(scores)/len(scores)) if scores else None,"recent":reports[:5]})
    except Exception: return fail("Could not load dashboard.",500)

@app.get("/api/history")
def history():
    user,error=current_user()
    if error:return error
    try:
        rows=admin_client().table("analysis_reports").select("id,ats_score,created_at,analysis_data,job_id").eq("user_id",user.id).order("created_at",desc=True).execute().data
        return jsonify({"reports":rows})
    except Exception:return fail("Could not load history.",500)

@app.get("/api/report/<report_id>")
def get_report(report_id):
    user,error=current_user()
    if error:return error
    try:
        row=admin_client().table("analysis_reports").select("*").eq("id",report_id).eq("user_id",user.id).single().execute().data
        return jsonify(row)
    except Exception:return fail("Report not found.",404)

@app.get("/api/report/<report_id>/pdf")
def download_report(report_id):
    user,error=current_user()
    if error:return error
    try:
        row=admin_client().table("analysis_reports").select("*").eq("id",report_id).eq("user_id",user.id).single().execute().data
        report=row.get("analysis_data") or {}
        pdf=make_report(report)
        return send_file(pdf,mimetype="application/pdf",as_attachment=True,download_name="ats-analysis-report.pdf")
    except Exception:return fail("Could not generate report.",404)

@app.delete("/api/history/<report_id>")
def delete_history(report_id):
    user,error=current_user()
    if error:return error
    try:
        admin_client().table("analysis_reports").delete().eq("id",report_id).eq("user_id",user.id).execute()
        return jsonify({"message":"Analysis deleted."})
    except Exception:return fail("Could not delete analysis.",500)

if __name__ == "__main__":
    app.run(host="0.0.0.0",port=int(os.getenv("PORT","5000")),debug=False)
