# FastAPI microservice that evaluates password strength using local rules
# and integrates breach-check results from the Checker service.

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import requests
import re

app = FastAPI(title="Password Advisor Service")

CHECKER_URL = os.getenv("CHECKER_URL", "http://checker:8000/check")

class EvalRequest(BaseModel):
    password: str

def call_checker(pwd: str):
    """Calls the Checker service to see if password is in breach DB."""
    try:
        resp = requests.post(CHECKER_URL, json={"password": pwd}, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=f"Checker error: {e}")

def simple_checks(pwd: str):
    """Runs local password strength checks (length, charset, patterns)."""
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
    """Computes a 0–100 strength score based on passed checks."""
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
    """Generates user-friendly improvement tips based on failed checks."""
    rec = []
    if not checks.get("length_12"):
        rec.append("Use at least 12 characters (longer is better).")
    if not checks.get("has_upper"):
        rec.append("Include uppercase letters (A-Z).")
    if not checks.get("has_lower"):
        rec.append("Include lowercase letters (a-z).")
    if not checks.get("has_digit"):
        rec.append("Include digits (0-9).")
    if not checks.get("has_special"):
        rec.append("Include special characters (e.g., !@#$%).")
    if checks.get("contains_common"):
        rec.append("Avoid common words or sequences (e.g., '123456', 'password').")
    if not checks.get("repeated_chars"):
        rec.append("Avoid long repeated characters (e.g., 'aaaa').")
    if not checks.get("sequential"):
        rec.append("Avoid simple sequences (e.g., 'abcd', '1234').")
    if not rec:
        rec.append("Great job — your password meets basic security requirements.")
    return rec

@app.post("/evaluate")
def evaluate(req: EvalRequest):
    """Main endpoint: returns breach status, score, checks, and recommendations."""
    pwd = req.password or ""
    if not pwd:
        raise HTTPException(status_code=400, detail="Password required")

    # Get breach info from Checker (gracefully handle errors)
    checker_result = {}
    try:
        checker_result = call_checker(pwd)
    except HTTPException:
        pass  # Continue with local checks even if Checker fails

    # Run local analysis
    checks = simple_checks(pwd)
    score = compute_score(checks, pwd)
    recs = recommendations_from_checks(checks)

    # Determine final message
    leaked = bool(checker_result.get("leaked")) if isinstance(checker_result, dict) else False
    if leaked:
        message = "This password has been breached. Change it immediately and use a unique, long passphrase."
    elif score >= 80:
        message = "Strong password — well done!"
    elif score >= 50:
        message = "Moderately strong. Follow recommendations to improve security."
    else:
        message = "Weak password. Switch to a longer, more complex passphrase."

    return {
        "leaked": leaked,
        "leaked_count": checker_result.get("count") if isinstance(checker_result, dict) else None,
        "score": score,
        "checks": checks,
        "recommendations": recs,
        "message": message
    }

@app.get("/health")
def health():
    """Health check endpoint for Kubernetes liveness/readiness probes."""
    return {"status": "ok"}