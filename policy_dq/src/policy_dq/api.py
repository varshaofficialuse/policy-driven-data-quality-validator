import io

import pandas as pd
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from policy_dq.mcp.policies import get_rules_for_policy
from policy_dq.models import ValidationResult
from policy_dq.validators.engine import ValidationEngine

app = FastAPI(
    title="policy-dq",
    description="Policy-Driven Data Quality Validator API",
    version="0.1.0",
)


def _parse_upload(file: UploadFile) -> pd.DataFrame:
    """Read an uploaded CSV or JSON file into a DataFrame."""
    filename = file.filename or ""
    ext = filename.rsplit(".", 1)[-1].lower()
    content = file.file.read()
    if ext == "csv":
        return pd.read_csv(io.StringIO(content.decode("utf-8")))
    elif ext == "json":
        return pd.read_json(io.StringIO(content.decode("utf-8")))
    else:
        raise HTTPException(status_code=400, detail=f"Unsupported file type '.{ext}'.")


@app.post("/validate", response_model=ValidationResult)
async def validate(
    file: UploadFile = File(..., description="CSV or JSON data file."),
    policy_name: str = Form(..., description="Policy name (e.g. 'onboarding', 'financial')."),
) -> ValidationResult:
    """Validate an uploaded data file against a named policy."""
    try:
        df = _parse_upload(file)
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Failed to parse file: {exc}")

    try:
        rules = get_rules_for_policy(policy_name)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    return ValidationEngine(df, rules).run()
