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

from database import (
    create_tables,
    connect
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

# =========================
# HOME
# =========================

@app.route("/")
def index():

    return render_template(
        "index.html"
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
            user[3],
            password
        ):

            session["user"] = user[0]


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



        conn = connect()


        conn.execute(
            """
            INSERT INTO resources
            (
            title,
            description,
            subject,
            syllabus,
            filename,
            uploaded_by
            )

            VALUES (?,?,?,?,?,?)
            """,

            (

            request.form["title"],

            request.form["description"],

            request.form["subject"],

            request.form["syllabus"],

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
        "upload.html"
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


    subject = request.args.get(
        "subject",
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

    WHERE title LIKE ?

    """



    params = [
        "%" + search + "%"
    ]



    if subject:

        query += """
        AND subject=?
        """

        params.append(subject)



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



    conn.close()



    return render_template(
        "library.html",
        resources=resources
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
        resources.title

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

    if resource[1] != session["user"]:

        conn.close()

        return "Not authorised"




    filename = resource[0]



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