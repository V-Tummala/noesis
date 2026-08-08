from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session
)

from werkzeug.utils import secure_filename
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import os
import uuid
import boto3

from datetime import date

from database import (
    create_tables,
    connect
)

from regions import (
    REGIONS,
    REGION_BY_ID,
    region_name,
    region_colour
)


app = Flask(__name__)

app.secret_key = os.environ.get(
    "SECRET_KEY",
    "change-this-secret-key"
)


# =========================
# CLOUDFLARE R2 CONFIG
# =========================

R2_BUCKET = "noesis-files"

r2 = boto3.client(
    "s3",
    endpoint_url=
    "https://b84acb151b5757fff0502ce1f1d72f05.r2.cloudflarestorage.com",

    aws_access_key_id=
    os.environ["R2_ACCESS_KEY"],

    aws_secret_access_key=
    os.environ["R2_SECRET_KEY"],

    region_name="auto"
)


# =========================
# CONFIGURATION
# =========================

ALLOWED_EXTENSIONS = {
    "pdf",
    "docx",
    "pptx",
    "txt",
    "md",
    "png",
    "jpg",
    "jpeg"
}


app.config["MAX_CONTENT_LENGTH"] = (
    50 * 1024 * 1024
)


# ESAT sitting, used for the countdown on the landing page

EXAM_DATE = date(2026, 10, 9)


# Where each region label sits on the brain, as a percentage of the
# 1000 x 660 viewBox in templates/index.html

LABEL_POS = {
    "pure":   { "left": 4.0,  "top": 18.2, "cls": "" },
    "mech":   { "left": 47.0, "top": 7.0,  "cls": "mid" },
    "waves":  { "left": 96.8, "top": 32.1, "cls": "end" },
    "em":     { "left": 4.0,  "top": 90.3, "cls": "" },
    "thermo": { "left": 96.8, "top": 90.3, "cls": "end" },
    "aero":   { "left": 47.0, "top": 98.5, "cls": "mid" }
}


create_tables()



# =========================
# HELPERS
# =========================

def allowed_file(filename):

    return (
        "." in filename
        and
        filename.rsplit(".", 1)[1].lower()
        in ALLOWED_EXTENSIONS
    )



def link_counts(conn):

    rows = conn.execute(
        """
        SELECT resource_one AS id,
               COUNT(*) AS n

        FROM relationships

        GROUP BY resource_one
        """
    ).fetchall()

    return {
        row["id"]: row["n"]
        for row in rows
    }



@app.context_processor
def inject_globals():

    username = None

    if "user" in session:

        conn = connect()

        row = conn.execute(
            """
            SELECT username
            FROM users
            WHERE id=?
            """,
            (session["user"],)
        ).fetchone()

        conn.close()

        if row:
            username = row["username"]

    return {
        "regions": REGIONS,
        "region_name": region_name,
        "region_colour": region_colour,
        "username": username,
        "active": None
    }



# =========================
# HOME — BRAIN
# =========================

@app.route("/")
def index():

    conn = connect()

    resources = conn.execute(
        """
        SELECT *
        FROM resources
        ORDER BY created DESC
        """
    ).fetchall()

    counts = link_counts(conn)

    total_links = conn.execute(
        "SELECT COUNT(*) AS n FROM relationships"
    ).fetchone()["n"]

    conn.close()


    stats = {}

    for r in REGIONS:

        rows = [
            row
            for row in resources
            if row["region"] == r["id"]
        ]

        stats[r["id"]] = {
            "count": len(rows),

            "links": sum(
                counts.get(row["id"], 0)
                for row in rows
            ),

            "exam": len([
                row
                for row in rows
                if row["syllabus"] in ("ESAT", "TMUA")
            ]),

            "concepts": [
                {
                    "id": row["id"],
                    "title": row["title"],
                    "syllabus": row["syllabus"] or "Neither",
                    "links": counts.get(row["id"], 0),
                    "created": (row["created"] or "")[:10]
                }
                for row in rows
            ]
        }


    brain_data = {
        "regions": REGIONS,
        "stats": stats,
        "default_region": "mech"
    }


    return render_template(
        "index.html",
        active="brain",
        label_pos=LABEL_POS,
        brain_data=brain_data,
        total_concepts=len(resources),
        total_links=total_links // 2,
        days_to_exam=max(
            (EXAM_DATE - date.today()).days,
            0
        )
    )



# =========================
# REGISTER
# =========================

@app.route(
    "/register",
    methods=["GET", "POST"]
)

def register():

    if request.method == "POST":

        username = request.form["username"]

        email = request.form["email"]

        password = generate_password_hash(
            request.form["password"]
        )


        conn = connect()

        try:

            conn.execute(
                """
                INSERT INTO users
                (
                username,
                email,
                password
                )

                VALUES (?,?,?)
                """,

                (
                    username,
                    email,
                    password
                )
            )

            conn.commit()


        except:

            return "Account already exists"


        finally:

            conn.close()


        return redirect(
            url_for("login")
        )


    return render_template(
        "register.html"
    )



# =========================
# LOGIN
# =========================

@app.route(
    "/login",
    methods=["GET", "POST"]
)

def login():

    if request.method == "POST":

        email = request.form["email"]

        password = request.form["password"]


        conn = connect()


        user = conn.execute(
            """
            SELECT *
            FROM users
            WHERE email=?
            """,

            (email,)

        ).fetchone()


        conn.close()



        if user and check_password_hash(
            user["password"],
            password
        ):

            session["user"] = user["id"]


            return redirect(
                url_for("library")
            )


        return "Invalid login"



    return render_template(
        "login.html"
    )



# =========================
# LOGOUT
# =========================

@app.route("/logout")

def logout():

    session.clear()


    return redirect(
        url_for("index")
    )



# =========================
# UPLOAD TO CLOUDFLARE R2
# =========================

@app.route(
    "/upload",
    methods=["GET", "POST"]
)

def upload():

    if "user" not in session:

        return redirect(
            url_for("login")
        )



    if request.method == "POST":


        file = request.files["file"]


        if file.filename == "":

            return "No file selected"



        if not allowed_file(
            file.filename
        ):

            return "File type not allowed"



        # Create unique filename

        filename = (
            str(uuid.uuid4())
            + "_"
            + secure_filename(file.filename)
        )



        # Upload directly to R2

        r2.upload_fileobj(
            file,
            R2_BUCKET,
            filename
        )



        region = request.form.get("region", "")

        if region not in REGION_BY_ID:
            region = ""



        conn = connect()


        conn.execute(
            """
            INSERT INTO resources
            (
            title,
            description,
            subject,
            syllabus,
            region,
            formula,
            filename,
            uploaded_by
            )

            VALUES (?,?,?,?,?,?,?,?)
            """,

            (

            request.form["title"],

            request.form["description"],

            request.form["subject"],

            request.form["syllabus"],

            region,

            request.form.get("formula", ""),

            filename,

            session["user"]

            )

        )


        conn.commit()

        conn.close()



        return redirect(
            url_for("library")
        )



    return render_template(
        "upload.html",
        active="upload"
    )



# =========================
# LIBRARY SEARCH
# =========================

@app.route("/library")

def library():


    search = request.args.get(
        "search",
        ""
    )


    region = request.args.get(
        "region",
        ""
    )


    syllabus = request.args.get(
        "syllabus",
        ""
    )



    conn = connect()



    query = """

    SELECT *

    FROM resources

    WHERE (title LIKE ? OR description LIKE ?)

    """



    params = [
        "%" + search + "%",
        "%" + search + "%"
    ]



    if region:

        query += """
        AND region=?
        """

        params.append(region)



    if syllabus:

        query += """
        AND syllabus=?
        """

        params.append(syllabus)



    query += """
    ORDER BY created DESC
    """



    resources = conn.execute(
        query,
        params
    ).fetchall()


    counts = link_counts(conn)


    conn.close()



    return render_template(
        "library.html",
        active="library",
        resources=resources,
        link_counts=counts,
        current_region=region,
        current_syllabus=syllabus
    )



# =========================
# CONNECTION MAP
# =========================

@app.route("/graph")

def graph():

    conn = connect()

    resources = conn.execute(
        """
        SELECT id, title, region
        FROM resources
        """
    ).fetchall()

    links = conn.execute(
        """
        SELECT resource_one, resource_two
        FROM relationships
        """
    ).fetchall()

    conn.close()


    region_of = {
        row["id"]: row["region"]
        for row in resources
    }


    nodes = [
        {
            "id": row["id"],
            "title": row["title"],
            "region": row["region"] or "",
            "colour": region_colour(row["region"])
        }
        for row in resources
    ]


    edges = []

    seen = set()

    for row in links:

        a = row["resource_one"]
        b = row["resource_two"]

        key = (min(a, b), max(a, b))

        if key in seen:
            continue

        seen.add(key)

        edges.append({
            "from": a,
            "to": b,
            "cross": region_of.get(a) != region_of.get(b),
            "colour": region_colour(region_of.get(a))
        })


    return render_template(
        "graph.html",
        active="graph",
        graph_data={
            "regions": REGIONS,
            "nodes": nodes,
            "edges": edges
        }
    )



# =========================
# RESOURCE PAGE
# =========================

@app.route(
    "/resource/<int:id>"
)

def resource(id):


    conn = connect()



    resource = conn.execute(

        """
        SELECT *

        FROM resources

        WHERE id=?

        """,

        (id,)

    ).fetchone()



    related = conn.execute(

        """
        SELECT
        resources.id,
        resources.title,
        resources.region

        FROM resources

        JOIN relationships

        ON resources.id =
        relationships.resource_two

        WHERE relationships.resource_one=?

        """,

        (id,)

    ).fetchall()



    conn.close()



    return render_template(

        "resource.html",

        resource=resource,

        related=related

    )



# =========================
# DOWNLOAD FROM CLOUDFLARE R2
# =========================

@app.route(
    "/download/<filename>"
)

def download(filename):

    url = r2.generate_presigned_url(
        "get_object",

        Params={
            "Bucket": R2_BUCKET,
            "Key": filename
        },

        ExpiresIn=300
    )


    return redirect(url)



# =========================
# LINK RESOURCES
# =========================

@app.route(
    "/link/<int:id>",
    methods=["GET", "POST"]
)

def link_resource(id):


    if "user" not in session:

        return redirect(
            url_for("login")
        )



    conn = connect()



    if request.method == "POST":


        other = request.form["resource"]



        conn.execute(

            """
            INSERT INTO relationships
            (
            resource_one,
            resource_two
            )

            VALUES (?,?),
                   (?,?)

            """,

            (
                id,
                other,
                other,
                id
            )

        )



        conn.commit()

        conn.close()



        return redirect(

            url_for(
                "resource",
                id=id
            )

        )




    resources = conn.execute(

        """

        SELECT id,title

        FROM resources

        WHERE id != ?

        """,

        (id,)

    ).fetchall()



    conn.close()



    return render_template(

        "link.html",

        id=id,

        resources=resources

    )



# =========================
# DELETE RESOURCE
# =========================

@app.route(
    "/delete/<int:id>",
    methods=["POST"]
)

def delete_resource(id):


    if "user" not in session:

        return redirect(
            url_for("login")
        )



    conn = connect()



    resource = conn.execute(

        """

        SELECT filename, uploaded_by

        FROM resources

        WHERE id=?

        """,

        (id,)

    ).fetchone()



    if resource is None:

        conn.close()

        return "Resource not found"




    # Only uploader can delete

    if resource["uploaded_by"] != session["user"]:

        conn.close()

        return "Not authorised"




    filename = resource["filename"]



    # Delete from Cloudflare R2

    try:

        r2.delete_object(

            Bucket=R2_BUCKET,

            Key=filename

        )

    except Exception as e:

        print(e)




    # Delete database entry

    conn.execute(

        """

        DELETE FROM resources

        WHERE id=?

        """,

        (id,)

    )



    conn.commit()

    conn.close()



    return redirect(

        url_for("library")

    )



# =========================
# START APP
# =========================

if __name__ == "__main__":

    app.run(
        debug=True
    )
