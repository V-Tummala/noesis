import sqlite3


DATABASE = "noesis.db"



def connect():

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

            filename TEXT NOT NULL,

            uploaded_by INTEGER,

            created TIMESTAMP DEFAULT CURRENT_TIMESTAMP,


            FOREIGN KEY(uploaded_by)

            REFERENCES users(id)

        )
        """
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