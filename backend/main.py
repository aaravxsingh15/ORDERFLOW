"""ORDERFLOW API.  Run from backend/:  uvicorn main:app --port 8000"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, JSONResponse, Response

import config
from data_cleaner import ValidationError
from model_service import service
from report import build_pdf
from schemas import Health, OrderInput
from utils import delay_rule_text

VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(_: FastAPI):
    service.load()
    yield


app = FastAPI(title="ORDERFLOW API", version=VERSION, lifespan=lifespan,
              description="Food-delivery delay classification, ETA regression and bottleneck detection. " + config.DISCLAIMER)
app.add_middleware(GZipMiddleware, minimum_size=1024)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o for o in os.environ.get("ORDERFLOW_CORS_ORIGINS", "http://localhost:3000,http://127.0.0.1:3000").split(",") if o],
    allow_methods=["*"], allow_headers=["*"],
)


def _error(status: int, message: str, issues: list | None = None, summary: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"detail": {"message": message, "issues": issues or [], "summary": summary}})


@app.exception_handler(ValidationError)
async def _data_validation(_: Request, exc: ValidationError):
    return _error(422, exc.message, exc.issues, exc.summary)


@app.exception_handler(RequestValidationError)
async def _request_validation(_: Request, exc: RequestValidationError):
    issues = []
    for e in exc.errors():
        field = ".".join(str(p) for p in e["loc"] if p not in ("body", "query"))
        issues.append({"field": field or "request", "reason": e["msg"]})
    first = issues[0]
    return _error(422, f"Invalid input: {first['field']} - {first['reason']}", issues)


@app.get("/api/health", response_model=Health)
def health():
    return {"status": "ok", "models_loaded": service.ready, "delay_rule": delay_rule_text(), "version": VERSION}


@app.post("/api/order/analyze")
def analyze_order(order: OrderInput):
    return service.analyze_order(order.model_dump())


@app.post("/api/orders/batch")
async def analyze_batch(file: UploadFile = File(...)):
    data = await file.read(config.MAX_UPLOAD_BYTES + 1)
    if len(data) > config.MAX_UPLOAD_BYTES:
        return _error(413, f"File is larger than {config.MAX_UPLOAD_BYTES // (1024 * 1024)} MB.")
    return service.analyze_csv(data, file.filename)


@app.get("/api/model/metrics")
def model_metrics():
    return service.metrics


@app.get("/api/demo/orders")
def demo_orders():
    return service.demo_batch()


@app.get("/api/sample-csv")
def sample_csv(kind: str = Query("clean", pattern="^(clean|issues)$")):
    path = config.SAMPLE_CSV if kind == "clean" else config.SAMPLE_ISSUES_CSV
    if not path.exists():
        from synthetic_data import generate_orders, inject_issues
        config.DATA_DIR.mkdir(exist_ok=True)
        df = generate_orders(200, 314 if kind == "clean" else 99)
        (inject_issues(df) if kind == "issues" else df).to_csv(path, index=False)
    name = "orderflow_sample_orders.csv" if kind == "clean" else "orderflow_sample_orders_with_issues.csv"
    return FileResponse(path, media_type="text/csv", filename=name)


@app.post("/api/report/order")
def order_report(order: OrderInput):
    analysis = service.analyze_order(order.model_dump())
    return Response(build_pdf(analysis), media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="orderflow_{analysis["order_id"]}.pdf"'})
