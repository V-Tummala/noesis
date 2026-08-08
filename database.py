import sqlite3
import os
import boto3


DATABASE = "noesis.db"

R2_BUCKET = "noesis-files"
R2_DATABASE_KEY = "noesis.db"

R2_ENDPOINT = (
    "https://b84acb151b5757fff0502ce1f1d72f05.r2."
    "cloudflarestorage.com"
)


def ensure_database():

    # If Render already has the database, use it.
    if os.path.exists(DATABASE):
        return

    # Otherwise download the existing database from R2.
    access_key = os.environ.get("R2_ACCESS_KEY")
    secret_key = os.environ.get("R2_SECRET_KEY")

    if not access_key or not secret_key:
        raise RuntimeError(
            "noesis.db is missing and R2_ACCESS_KEY / "
            "R2_SECRET_KEY are not configured."
        )

    print("noesis.db not found.")
    print("Downloading existing database from R2...")

    r2 = boto3.client(
        "s3",
        endpoint_url=R2_ENDPOINT,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name="auto"
    )

    r2.download_file(
        R2_BUCKET,
        R2_DATABASE_KEY,
        DATABASE
    )

    print("noesis.db downloaded successfully.")


def connect():

    ensure_database()

    conn = sqlite3.connect(
        DATABASE
    )

    # Allows foreign keys and cascading deletes
    conn.execute(
        "PRAGMA foreign_keys = ON"
    )

    # Allows accessing columns by name
    conn.row_factory = sqlite3.Row

    return conn


def add_column_if_missing(
    conn,
    table,
    column,
    definition
):

    existing = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(" + table + ")"
        ).fetchall()
    ]

    if column not in existing:

        conn.execute(
            "ALTER TABLE " + table +
            " ADD COLUMN " + column + " " + definition
        )


def create_tables():

    conn = connect()

    cursor = conn.cursor()


    # =========================
    # USERS
    # =========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS users (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            username TEXT NOT NULL,

            email TEXT UNIQUE NOT NULL,

            password TEXT NOT NULL

        )
        """
    )


    # =========================
    # RESOURCES
    # =========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS resources (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            title TEXT NOT NULL,

            description TEXT,

            subject TEXT,

            syllabus TEXT,

            region TEXT,

            formula TEXT,

            filename TEXT NOT NULL,

            uploaded_by INTEGER,

            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY(uploaded_by)
            REFERENCES users(id)

        )
        """
    )


    # Existing databases predate the brain taxonomy

    add_column_if_missing(
        conn,
        "resources",
        "region",
        "TEXT"
    )

    add_column_if_missing(
        conn,
        "resources",
        "formula",
        "TEXT"
    )


    # =========================
    # RESOURCE LINKS
    # =========================

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS relationships (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            resource_one INTEGER,

            resource_two INTEGER,

            FOREIGN KEY(resource_one)
            REFERENCES resources(id)
            ON DELETE CASCADE,

            FOREIGN KEY(resource_two)
            REFERENCES resources(id)
            ON DELETE CASCADE

        )
        """
    )


    conn.commit()

    conn.close()

