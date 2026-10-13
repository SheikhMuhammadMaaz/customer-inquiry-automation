import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from typing import Literal

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

DB_NAME = "inquiries.db"

app = FastAPI(title="Customer Inquiry Automation API")


def get_connection():
    connection = sqlite3.connect(DB_NAME)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with closing(get_connection()) as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS inquiries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                message TEXT NOT NULL,
                source TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                created_at TEXT NOT NULL
            )
        """)
        connection.commit()


init_db()

class InquiryCreate(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    contact: str = Field(min_length=3, max_length=150)
    message: str = Field(min_length=5, max_length=2000)
    source: str = Field(default="website", max_length=50)


class StatusUpdate(BaseModel):
    status: Literal["new", "contacted", "closed"]


@app.get("/")
def home():
    return {"message": "Customer Inquiry API is running"}


@app.post("/inquiries", status_code=201)
def create_inquiry(inquiry: InquiryCreate):
    created_at = datetime.now(timezone.utc).isoformat()

    with closing(get_connection()) as connection:
        cursor = connection.execute(
            """
            INSERT INTO inquiries
            (name, contact, message, source, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                inquiry.name,
                inquiry.contact,
                inquiry.message,
                inquiry.source,
                created_at,
            ),
        )
        connection.commit()

        row = connection.execute(
            "SELECT * FROM inquiries WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()

        return dict(row)


@app.get("/inquiries")
def get_inquiries():
    with closing(get_connection()) as connection:
        rows = connection.execute(
            "SELECT * FROM inquiries ORDER BY id DESC"
        ).fetchall()

        return [dict(row) for row in rows]


@app.get("/inquiries/{inquiry_id}")
def get_inquiry(inquiry_id: int):
    with closing(get_connection()) as connection:
        row = connection.execute(
            "SELECT * FROM inquiries WHERE id = ?",
            (inquiry_id,),
        ).fetchone()

        if row is None:
            raise HTTPException(
                status_code=404,
                detail="Inquiry not found",
            )

        return dict(row)


@app.patch("/inquiries/{inquiry_id}/status")
def update_status(
    inquiry_id: int,
    update: StatusUpdate,
):
    with closing(get_connection()) as connection:
        cursor = connection.execute(
            "UPDATE inquiries SET status = ? WHERE id = ?",
            (update.status, inquiry_id),
        )
        connection.commit()

        if cursor.rowcount == 0:
            raise HTTPException(
                status_code=404,
                detail="Inquiry not found",
            )

        row = connection.execute(
            "SELECT * FROM inquiries WHERE id = ?",
            (inquiry_id,),
        ).fetchone()

        return dict(row)
