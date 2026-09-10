import logging
import os
import time
import uuid

import mysql.connector
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)

logger = logging.getLogger("fastapi-app")

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

    logger.info(
        "request_started request_id=%s method=%s path=%s",
        request_id,
        request.method,
        request.url.path
    )

    try:
        response = await call_next(request)

        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logger.info(
            "request_completed request_id=%s method=%s path=%s "
            "status=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms
        )

        response.headers["X-Request-ID"] = request_id

        return response

    except Exception:
        duration_ms = round(
            (time.perf_counter() - start_time) * 1000,
            2
        )

        logger.exception(
            "request_failed request_id=%s method=%s path=%s duration_ms=%s",
            request_id,
            request.method,
            request.url.path,
            duration_ms
        )

        return JSONResponse(
            status_code=500,
            content={
                "detail": "Internal server error",
                "request_id": request_id
            }
        )


@app.get("/")
def home():
    return {"message": "Docker CI/CD deployment v2 is working!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/employees")
def get_employees(request: Request):
    request_id = request.state.request_id

    logger.info(
        "fetching_employees request_id=%s",
        request_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, name FROM employees")
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    logger.info(
        "employees_fetched request_id=%s count=%s",
        request_id,
        len(rows)
    )

    return [
        {"id": row[0], "name": row[1]}
        for row in rows
    ]


@app.post("/employees")
def create_employee(employee: EmployeeCreate, request: Request):
    request_id = request.state.request_id

    logger.info(
        "creating_employee request_id=%s",
        request_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "INSERT INTO employees (name) VALUES (%s)",
        (employee.name,)
    )

    connection.commit()
    employee_id = cursor.lastrowid

    cursor.close()
    connection.close()

    logger.info(
        "employee_created request_id=%s employee_id=%s",
        request_id,
        employee_id
    )

    return {
        "id": employee_id,
        "name": employee.name
    }


@app.put("/employees/{employee_id}")
def update_employee(
    employee_id: int,
    employee: EmployeeCreate,
    request: Request
):
    request_id = request.state.request_id

    logger.info(
        "updating_employee request_id=%s employee_id=%s",
        request_id,
        employee_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "UPDATE employees SET name = %s WHERE id = %s",
        (employee.name, employee_id)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()

        logger.warning(
            "employee_not_found request_id=%s employee_id=%s",
            request_id,
            employee_id
        )

        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    cursor.close()
    connection.close()

    logger.info(
        "employee_updated request_id=%s employee_id=%s",
        request_id,
        employee_id
    )

    return {
        "id": employee_id,
        "name": employee.name
    }


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int, request: Request):
    request_id = request.state.request_id

    logger.info(
        "deleting_employee request_id=%s employee_id=%s",
        request_id,
        employee_id
    )

    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute(
        "DELETE FROM employees WHERE id = %s",
        (employee_id,)
    )

    connection.commit()

    if cursor.rowcount == 0:
        cursor.close()
        connection.close()

        logger.warning(
            "employee_not_found request_id=%s employee_id=%s",
            request_id,
            employee_id
        )

        raise HTTPException(
            status_code=404,
            detail="Employee not found"
        )

    cursor.close()
    connection.close()

    logger.info(
        "employee_deleted request_id=%s employee_id=%s",
        request_id,
        employee_id
    )

    return {
        "message": "Employee deleted"
    }