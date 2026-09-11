import json
import logging
import os
import time
import uuid

from opentelemetry import context, trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
from opentelemetry.propagate import extract

import mysql.connector
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s"
)

logger = logging.getLogger("fastapi-app")


def log_event(event: str, severity: str = "INFO", **kwargs):
    log_data = {
        "severity": severity,
        "event": event,
        **kwargs
    }

    message = json.dumps(log_data)

    if severity == "ERROR":
        logger.error(message)
    elif severity == "WARNING":
        logger.warning(message)
    else:
        logger.info(message)

trace.set_tracer_provider(TracerProvider())

tracer = trace.get_tracer(__name__)

if os.getenv("INSTANCE_CONNECTION_NAME"):
    exporter = CloudTraceSpanExporter()

    span_processor = BatchSpanProcessor(exporter)

    trace.get_tracer_provider().add_span_processor(
        span_processor
    )

app = FastAPI()


class EmployeeCreate(BaseModel):
    name: str


def get_connection():
    connection_name = os.getenv("INSTANCE_CONNECTION_NAME")

    if connection_name:
        return mysql.connector.connect(
            unix_socket=f"/cloudsql/{connection_name}",
            user=os.getenv("DB_USER"),
            password=os.getenv("DB_PASSWORD"),
            database=os.getenv("DB_NAME")
        )

    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())

    request.state.request_id = request_id
    start_time = time.perf_counter()

    # Extract incoming W3C trace context from Cloud Run.
    carrier = dict(request.headers)
    extracted_context = extract(carrier)

    # Make the extracted trace context active for this request.
    token = context.attach(extracted_context)

    log_event(
        "request_started",
        request_id=request_id,
        method=request.method,
        path=request.url.path
    )

    try:
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        log_event(
            "request_completed",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            status=response.status_code,
            duration_ms=duration_ms
        )

        response.headers["X-Request-ID"] = request_id

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        log_event(
            "request_failed",
            severity="ERROR",
            request_id=request_id,
            method=request.method,
            path=request.url.path,
            duration_ms=duration_ms
        )

        logger.exception(
            "Unhandled exception request_id=%s",
            request_id
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id
            },
            headers={
                "X-Request-ID": request_id
            }
        )

    finally:
        context.detach(token)

@app.get("/")
def home():
    return {
        "message": "Docker CI/CD deployment v2 is working!"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy"
    }

@app.get("/ready")
def readiness(request: Request):
    request_id = request.state.request_id

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute("SELECT 1")
        cursor.fetchone()

        log_event(
            "readiness_check_passed",
            request_id=request_id
        )

        return {
            "status": "ready"
        }

    except Exception:
        log_event(
            "readiness_check_failed",
            severity="ERROR",
            request_id=request_id
        )

        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "request_id": request_id
            }
        )

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

@app.get("/employees")
def get_employees(request: Request):
    request_id = request.state.request_id

    log_event(
        "fetching_employees",
        request_id=request_id
    )

    connection = None
    cursor = None

    try:
        with tracer.start_as_current_span("db.connect") as span:
            connection = get_connection()

            span.set_attribute(
                "db.system",
                "mysql"
            )

        with tracer.start_as_current_span("db.query") as span:
            cursor = connection.cursor()

            cursor.execute(
                "SELECT id, name FROM employees"
            )

            rows = cursor.fetchall()

            span.set_attribute(
                "db.system",
                "mysql"
            )

            span.set_attribute(
                "db.operation",
                "SELECT"
            )

            span.set_attribute(
                "db.result_count",
                len(rows)
            )

        log_event(
            "employees_fetched",
            request_id=request_id,
            count=len(rows)
        )

        return [
            {
                "id": row[0],
                "name": row[1]
            }
            for row in rows
        ]

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()

@app.post("/employees")
def create_employee(
    employee: EmployeeCreate,
    request: Request
):
    request_id = request.state.request_id

    log_event(
        "employee_creating",
        request_id=request_id
    )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "INSERT INTO employees (name) VALUES (%s)",
            (employee.name,)
        )

        connection.commit()
        employee_id = cursor.lastrowid

        log_event(
            "employee_created",
            request_id=request_id,
            employee_id=employee_id
        )

        return {
            "id": employee_id,
            "name": employee.name
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    employee: EmployeeCreate,
    request: Request
):
    request_id = request.state.request_id

    log_event(
        "employee_updating",
        request_id=request_id,
        employee_id=employee_id
    )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "UPDATE employees SET name = %s WHERE id = %s",
            (employee.name, employee_id)
        )

        connection.commit()

        if cursor.rowcount == 0:
            log_event(
                "employee_not_found",
                severity="WARNING",
                request_id=request_id,
                employee_id=employee_id
            )

            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        log_event(
            "employee_updated",
            request_id=request_id,
            employee_id=employee_id
        )

        return {
            "id": employee_id,
            "name": employee.name
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()


@app.delete("/employees/{employee_id}")
def delete_employee(
    employee_id: int,
    request: Request
):
    request_id = request.state.request_id

    log_event(
        "employee_deleting",
        request_id=request_id,
        employee_id=employee_id
    )

    connection = None
    cursor = None

    try:
        connection = get_connection()
        cursor = connection.cursor()

        cursor.execute(
            "DELETE FROM employees WHERE id = %s",
            (employee_id,)
        )

        connection.commit()

        if cursor.rowcount == 0:
            log_event(
                "employee_not_found",
                severity="WARNING",
                request_id=request_id,
                employee_id=employee_id
            )

            raise HTTPException(
                status_code=404,
                detail="Employee not found"
            )

        log_event(
            "employee_deleted",
            request_id=request_id,
            employee_id=employee_id
        )

        return {
            "message": "Employee deleted"
        }

    finally:
        if cursor:
            cursor.close()

        if connection and connection.is_connected():
            connection.close()