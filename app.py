from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import mysql.connector
import os

app = FastAPI()


class EmployeeCreate(BaseModel):
    name: str


def get_connection():
    return mysql.connector.connect(
        host=os.getenv("DB_HOST"),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


@app.get("/")
def home():
    return {"message": "Docker application updated successfully!"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/employees")
def get_employees():
    connection = get_connection()
    cursor = connection.cursor()

    cursor.execute("SELECT id, name FROM employees")
    rows = cursor.fetchall()

    cursor.close()
    connection.close()

    return [{"id": row[0], "name": row[1]} for row in rows]


@app.post("/employees")
def create_employee(employee: EmployeeCreate):
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

    return {
        "id": employee_id,
        "name": employee.name
    }


@app.put("/employees/{employee_id}")
def update_employee(employee_id: int, employee: EmployeeCreate):
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
        raise HTTPException(status_code=404, detail="Employee not found")

    cursor.close()
    connection.close()

    return {
        "id": employee_id,
        "name": employee.name
    }


@app.delete("/employees/{employee_id}")
def delete_employee(employee_id: int):
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
        raise HTTPException(status_code=404, detail="Employee not found")

    cursor.close()
    connection.close()

    return {
        "message": "Employee deleted"
    }