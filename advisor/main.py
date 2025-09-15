# advisor/main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, requests, re

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Password Advisor Service")

# CORS - tillåt frontend-origin (begränsat)
origins = [
    "http://localhost:8080"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

CHECKER_URL = os.getenv("CHECKER_URL", "http://checker:8000/check")

class EvalRequest(BaseModel):
    password: str

def call_checker(pwd: str):
    try:
        resp = requests.post(CHECKER_URL, json={"password": pwd}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Checker error: {e}")

def simple_checks(pwd: str):
    checks = {}
    checks["length_8"] = len(pwd) >= 8
    checks["length_12"] = len(pwd) >= 12
    checks["has_lower"] = bool(re.search(r"[a-z]", pwd))
    checks["has_upper"] = bool(re.search(r"[A-Z]", pwd))
    checks["has_digit"] = bool(re.search(r"\d", pwd))
    checks["has_special"] = bool(re.search(r"[^\w\s]", pwd))
    low = pwd.lower()
    common = ["1234","12345","123456","password","qwerty","admin","letmein","1111","0000","abcd","solo"]
    checks["contains_common"] = any(c in low for c in common)
    checks["repeated_chars"] = not bool(re.search(r"(.)\1\1\1", pwd))
    checks["sequential"] = not bool(re.search(r"(?:0123|1234|2345|3456|4567|5678|6789|abcd|bcde|cdef|qwer|wert)", low))
    return checks

def compute_score(checks: dict, pwd: str):
    score = 0
    if checks.get("length_12"):
        score += 35
    elif checks.get("length_8"):
        score += 15
    if checks.get("has_lower"): score += 10
    if checks.get("has_upper"): score += 10
    if checks.get("has_digit"): score += 10
    if checks.get("has_special"): score += 10
    if checks.get("repeated_chars"): score += 5
    if checks.get("sequential"): score += 5
    if not checks.get("contains_common"): score += 5
    return max(0, min(100, score))

def recommendations_from_checks(checks):
    rec = []
    if not checks.get("length_12"):
        rec.append("Använd minst 12 tecken (helst längre).")
    if not checks.get("has_upper"):
        rec.append("Inkludera stora bokstäver (A-Z).")
    if not checks.get("has_lower"):
        rec.append("Inkludera små bokstäver (a-z).")
    if not checks.get("has_digit"):
        rec.append("Inkludera siffror (0-9).")
    if not checks.get("has_special"):
        rec.append("Inkludera specialtecken (t.ex. !@#€%&*).")
    if checks.get("contains_common"):
        rec.append("Använd inte vanliga ord eller sekvenser (t.ex. '123456' eller 'password').")
    if not checks.get("repeated_chars"):
        rec.append("Undvik långa upprepningar av samma tecken (t.ex. 'aaaa').")
    if not checks.get("sequential"):
        rec.append("Undvik enkla sekvenser (t.ex. 'abcd' eller '1234').")
    if not rec:
        rec.append("Bra jobbat — lösenordet uppfyller grundläggande krav.")
    return rec

@app.post("/evaluate")
def evaluate(req: EvalRequest):
    pwd = req.password or ""
    if len(pwd) == 0:
        raise HTTPException(status_code=400, detail="Password required")

    checker_result = {}
    try:
        checker_result = call_checker(pwd)
    except HTTPException as e:
        checker_result = {"error": str(e.detail)}

    checks = simple_checks(pwd)
    score = compute_score(checks, pwd)
    recs = recommendations_from_checks(checks)

    if isinstance(checker_result, dict) and checker_result.get("leaked") is True:
        message = "Det här lösenordet har läckt. Byt lösenord direkt och använd en längre, unik lösenfras."
    else:
        if score >= 80:
            message = "Starkt lösenord — bra jobbat!"
        elif score >= 50:
            message = "Måttligt starkt. Följ rekommendationerna för att förbättra styrkan."
        else:
            message = "Svagt lösenord. Byt till en längre och mer komplex lösenfras."

    response = {
        "leaked": bool(checker_result.get("leaked")) if isinstance(checker_result, dict) else False,
        "leaked_count": checker_result.get("count") if isinstance(checker_result, dict) else None,
        "score": score,
        "checks": checks,
        "recommendations": recs,
        "message": message
    }
    return response

@app.get("/health")
def health():
    return {"status":"ok"}
