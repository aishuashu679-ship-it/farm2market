from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from mysql.connector import Error
import mysql.connector
import math
import os
import getpass
from decimal import Decimal, InvalidOperation

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "please-set-a-secret-key")

# Set DB_PASSWORD in your environment before running this app.
DB_CONFIG = {
    "host": os.getenv("DB_HOST", "localhost"),
    "user": os.getenv("DB_USER", "root"),
    "password": os.getenv("DB_PASSWORD", "Akshaya@123"),
    "database": os.getenv("DB_NAME", "farmer_market"),
}


def get_db():
    return mysql.connector.connect(**DB_CONFIG)


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in first.", "warning")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    def decorator(view):
        @wraps(view)
        @login_required
        def wrapped(*args, **kwargs):
            if session.get("role") not in roles:
                flash("You do not have permission to open that page.", "warning")
                return redirect(url_for("dashboard"))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def get_farmer_id(cur):
    cur.execute(
        "SELECT farmer_id FROM farmers WHERE username = "
        "(SELECT email FROM users WHERE id = %s)",
        (session["user_id"],)
    )
    row = cur.fetchone()
    return row["farmer_id"] if row else None


def get_buyer_id(cur):
    cur.execute("SELECT buyer_id FROM buyers WHERE user_id = %s", (session["user_id"],))
    row = cur.fetchone()
    return row["buyer_id"] if row else None


def ensure_feature_tables():
    """Create only additional tables. Existing tables and records are not deleted."""
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS crop_listings (
                listing_id INT AUTO_INCREMENT PRIMARY KEY,
                farmer_id INT NOT NULL,
                crop_name VARCHAR(100) NOT NULL,
                category VARCHAR(50) NOT NULL,
                quantity_kg DECIMAL(10,2) NOT NULL,
                location VARCHAR(150) NOT NULL,
                expected_price DECIMAL(10,2) NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS app_messages (
                message_id INT AUTO_INCREMENT PRIMARY KEY,
                sender_id INT NOT NULL,
                receiver_id INT NOT NULL,
                message_text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                transaction_id INT AUTO_INCREMENT PRIMARY KEY,
                buyer_id INT NOT NULL,
                farmer_id INT NOT NULL,
                crop_name VARCHAR(100) NOT NULL,
                quantity_kg DECIMAL(10,2) NOT NULL,
                price_per_kg DECIMAL(10,2) NOT NULL,
                total_amount DECIMAL(12,2) NOT NULL,
                transport_cost DECIMAL(12,2) NOT NULL DEFAULT 0,
                net_amount DECIMAL(12,2) NOT NULL,
                status VARCHAR(30) NOT NULL DEFAULT 'Recorded',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS sample_requests (
                sample_id INT AUTO_INCREMENT PRIMARY KEY,
                farmer_id INT NOT NULL,
                crop_name VARCHAR(100) NOT NULL,
                status VARCHAR(40) NOT NULL DEFAULT 'Requested',
                report_notes TEXT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
    except Error:
        app.logger.exception("Could not create/check Farm2Market feature tables")
    finally:
        if conn and conn.is_connected():
            conn.close()


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        role = request.form.get("role", "farmer")
        location = request.form.get("location", "").strip()

        if not name or not email or len(password) < 6 or role not in ("farmer", "buyer"):
            flash("Enter all details. Password must have at least 6 characters.", "danger")
            return render_template("register.html")
        if role == "farmer" and not location:
            flash("Please enter your location.", "danger")
            return render_template("register.html")

        conn = None
        try:
            conn = get_db()
            cur = conn.cursor()
            password_hash = generate_password_hash(password)
            cur.execute(
                """INSERT INTO users (name, email, password_hash, role)
                   VALUES (%s, %s, %s, %s)""",
                (name, email, password_hash, role)
            )
            user_id = cur.lastrowid

            if role == "farmer":
                cur.execute(
                    """INSERT INTO farmers (name, username, password_hash, location)
                       VALUES (%s, %s, %s, %s)""",
                    (name, email, password_hash, location)
                )
            else:
                cur.execute(
                    """INSERT INTO buyers
                       (buyer_name, user_id, contact_name, business_name)
                       VALUES (%s, %s, %s, %s)""",
                    (name, user_id, name, name)
                )

            conn.commit()
            flash("Registration successful. You can now log in.", "success")
            return redirect(url_for("login"))
        except Error as exc:
            if conn:
                conn.rollback()
            if getattr(exc, "errno", None) == 1062:
                flash("This email is already registered.", "danger")
            else:
                app.logger.exception("Registration database error")
                flash("Could not register. Check your database setup.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                "SELECT id, name, email, password_hash, role FROM users WHERE email = %s",
                (email,)
            )
            user = cur.fetchone()
            if user and check_password_hash(user["password_hash"], password):
                session.clear()
                session["user_id"] = user["id"]
                session["name"] = user["name"]
                session["email"] = user["email"]
                session["role"] = user["role"]
                flash("Welcome, {}!".format(user["name"]), "success")
                return redirect(url_for("dashboard"))
            flash("Incorrect email or password.", "danger")
        except Error as exc:
            app.logger.exception("Login database error")
            flash(f"Login database error: {exc}", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have logged out.", "info")
    return redirect(url_for("home"))


@app.route("/dashboard")
@login_required
def dashboard():
    return render_template("dashboard.html")


@app.route("/profile")
@login_required
def profile():
    conn = None
    user = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT id, name, email, role FROM users WHERE id = %s", (session["user_id"],))
        user = cur.fetchone()
        if user and user["role"] == "farmer":
            cur.execute(
                "SELECT phone, location FROM farmers WHERE username = %s",
                (user["email"],)
            )
            extra = cur.fetchone()
            if extra:
                user.update(extra)
        elif user and user["role"] == "buyer":
            cur.execute(
                """SELECT phone, location, business_name, contact_name
                   FROM buyers WHERE user_id = %s""",
                (session["user_id"],)
            )
            extra = cur.fetchone()
            if extra:
                user.update(extra)
    except Error:
        app.logger.exception("Profile database error")
        flash("Could not load your profile.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("profile.html", user=user or {
        "name": session.get("name", ""),
        "email": session.get("email", ""),
        "role": session.get("role", "")
    })


@app.route("/crop-categories")
@login_required
def crop_categories():
    return render_template("crop_categories.html")


@app.route("/quality-grading")
@login_required
def quality_grading():
    role = (session.get("role") or "").strip().lower()
    conn = None

    if role not in ("farmer", "buyer", "lab"):
        flash("You do not have permission to open this page.", "warning")
        return redirect(url_for("dashboard"))

    listings = []
    samples = []

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        if role == "farmer":
            farmer_id = get_farmer_id(cur)

            if farmer_id:
                cur.execute(
                    """
                    SELECT listing_id, crop_name, variety, category,
                           quantity_kg, location
                    FROM crop_listings
                    WHERE farmer_id = %s
                    ORDER BY listing_id DESC
                    """,
                    (farmer_id,)
                )
                listings = cur.fetchall()

                cur.execute(
                    """
                    SELECT *
                    FROM sample_requests
                    WHERE farmer_id = %s
                    ORDER BY sample_id DESC
                    """,
                    (farmer_id,)
                )
                samples = cur.fetchall()

        elif role == "lab":
            cur.execute(
                """
                SELECT *
                FROM sample_requests
                ORDER BY sample_id DESC
                """
            )
            samples = cur.fetchall()

        elif role == "buyer":
            cur.execute(
                """
                SELECT *
                FROM sample_requests
                WHERE status = 'Completed'
                  AND quality_grade IS NOT NULL
                ORDER BY tested_at DESC
                """
            )
            samples = cur.fetchall()

    except Error:
        app.logger.exception("Quality grading database error")
        flash("Could not load laboratory information.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        "quality_grading.html",
        role=role,
        listings=listings,
        samples=samples
    )


@app.route("/request-sample", methods=["POST"])
@role_required("farmer")
def request_sample():
    conn = None

    try:
        listing_id = int(request.form.get("listing_id", "0"))

        if listing_id <= 0:
            flash("Please select a valid crop listing.", "danger")
            return redirect(url_for("quality_grading"))

        conn = get_db()
        cur = conn.cursor(dictionary=True)

        farmer_id = get_farmer_id(cur)

        if not farmer_id:
            flash("Farmer profile not found.", "danger")
            return redirect(url_for("dashboard"))

        # Confirm that this crop belongs to the logged-in farmer
        cur.execute(
            """
            SELECT listing_id, crop_name, variety
            FROM crop_listings
            WHERE listing_id = %s AND farmer_id = %s
            """,
            (listing_id, farmer_id)
        )

        crop = cur.fetchone()

        if not crop:
            flash("Selected crop listing was not found.", "danger")
            return redirect(url_for("quality_grading"))

        # Save the 500 g sample request
        cur.execute(
            """
            INSERT INTO sample_requests
            (farmer_id, listing_id, crop_name, variety,
             sample_weight_g, status)
            VALUES (%s, %s, %s, %s, 500, 'Requested')
            """,
            (
                farmer_id,
                listing_id,
                crop["crop_name"],
                crop["variety"]
            )
        )

        conn.commit()

        flash("Your 500 g sample testing request has been submitted!", "success")

    except (ValueError, TypeError):
        flash("Invalid crop listing selected.", "danger")

    except Error:
        if conn:
            conn.rollback()
        app.logger.exception("Sample request database error")
        flash("Could not submit sample request.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return redirect(url_for("quality_grading"))

@app.route("/submit-lab-report", methods=["POST"])
@role_required("lab")
def submit_lab_report():
    conn = None

    try:
        sample_id = int(request.form.get("sample_id", "0"))

        moisture = float(request.form.get("moisture_percent", ""))
        purity = float(request.form.get("purity_percent", ""))
        damaged = float(request.form.get("damaged_percent", ""))
        foreign = float(request.form.get("foreign_matter_percent", ""))

        grade = request.form.get("quality_grade", "").strip()
        lab_name = request.form.get("lab_name", "").strip()
        notes = request.form.get("report_notes", "").strip()

        measurements = [moisture, purity, damaged, foreign]

        if (
            sample_id <= 0
            or not all(math.isfinite(x) and 0 <= x <= 100
                       for x in measurements)
            or not grade
            or len(grade) > 20
            or not lab_name
            or len(lab_name) > 150
        ):
            flash("Please enter valid test results and report details.", "danger")
            return redirect(url_for("quality_grading"))

        conn = get_db()
        cur = conn.cursor()

        cur.execute(
            """
            UPDATE sample_requests
            SET moisture_percent = %s,
                purity_percent = %s,
                damaged_percent = %s,
                foreign_matter_percent = %s,
                quality_grade = %s,
                lab_name = %s,
                tested_by = %s,
                tested_at = NOW(),
                report_notes = %s,
                status = 'Completed'
            WHERE sample_id = %s
            """,
            (
                moisture, purity, damaged, foreign,
                grade, lab_name, session.get("name"),
                notes or None, sample_id
            )
        )

        if cur.rowcount == 0:
            conn.rollback()
            flash("Sample request not found.", "danger")
        else:
            conn.commit()
            flash("Laboratory report saved successfully!", "success")

    except (ValueError, TypeError):
        if conn:
            conn.rollback()
        flash("Please enter valid numerical test results.", "danger")

    except Error:
        if conn:
            conn.rollback()
        app.logger.exception("Laboratory report submission error")
        flash("Could not save laboratory report.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return redirect(url_for("quality_grading"))

@app.route("/nearby-farmers")
@role_required("buyer")
def nearby_farmers():
    location = request.args.get("location", "").strip()
    conn = None
    farmers = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        if location:
            cur.execute(
                """SELECT farmer_id, name, phone, location FROM farmers
                   WHERE location LIKE %s ORDER BY name""",
                ("%" + location + "%",)
            )
        else:
            cur.execute("SELECT farmer_id, name, phone, location FROM farmers ORDER BY name")
        farmers = cur.fetchall()
    except Error:
        app.logger.exception("Nearby farmers database error")
        flash("Could not load farmers.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("nearby_farmers.html", farmers=farmers, location=location)


@app.route("/nearby-buyers")
@role_required("farmer")
def nearby_buyers():
    crop = request.args.get("crop", "").strip()
    try:
        max_distance = float(request.args.get("max_distance", "100"))
        if not math.isfinite(max_distance) or max_distance <= 0:
            max_distance = 100
    except ValueError:
        max_distance = 100
    max_distance = min(max_distance, 100)
    conn = None
    buyers = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        query = """
            SELECT b.buyer_id, b.buyer_name, b.business_name, b.contact_name,
                   b.phone, b.location, o.crop_name, o.price_per_kg,
                   o.distance_km, o.notes
            FROM buyer_offers o
            JOIN buyers b ON b.buyer_id = o.buyer_id
            WHERE o.distance_km <= %s
        """
        params = [max_distance]
        if crop:
            query += " AND LOWER(o.crop_name) = LOWER(%s)"
            params.append(crop)
        query += " ORDER BY o.price_per_kg DESC"
        cur.execute(query, tuple(params))
        buyers = cur.fetchall()
    except Error:
        app.logger.exception("Nearby buyers database error")
        flash("Could not load buyer offers.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template(
        "nearby_buyers.html", buyers=buyers, crop=crop,
        max_distance=max_distance
    )


@app.route("/crop-details", methods=["GET", "POST"])
@role_required("farmer")
def crop_details():
    if request.method == "POST":
        crop_name = request.form.get("crop_name", "").strip()
        category = request.form.get("category", "").strip()
        location = request.form.get("location", "").strip()
        try:
            quantity = float(request.form.get("quantity", "0"))
            expected_raw = request.form.get("expected_price", "").strip()
            expected_price = float(expected_raw) if expected_raw else None
            valid = math.isfinite(quantity) and quantity > 0
            if expected_price is not None:
                valid = valid and math.isfinite(expected_price) and expected_price >= 0
        except ValueError:
            valid = False
            quantity = 0
            expected_price = None

        minimums = {
            "Commercial Crops": 50.01,
            "Spices": 20,
            "Cereals": 20,
            "Fruits": 10,
            "Vegetables": 10,
        }
        minimum = minimums.get(category)
        if (not crop_name or len(crop_name) > 100 or not location
                or category not in minimums or not valid or quantity < minimum):
            flash("Check the crop details. Minimum quantities: commercial crops above 50 kg; spices and cereals 20 kg; fruits and vegetables 10 kg.", "danger")
            return render_template("crop_details.html")

        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            farmer_id = get_farmer_id(cur)
            if not farmer_id:
                flash("Your farmer profile was not found. Please contact support.", "danger")
                return redirect(url_for("dashboard"))
            cur.execute(
                """INSERT INTO crop_listings
                   (farmer_id, crop_name, category, quantity_kg, location, expected_price)
                   VALUES (%s, %s, %s, %s, %s, %s)""",
                (farmer_id, crop_name, category, quantity, location, expected_price)
            )
            cur.execute("UPDATE farmers SET location = %s WHERE farmer_id = %s", (location, farmer_id))
            conn.commit()
            flash("Crop details submitted successfully.", "success")
            return redirect(url_for("nearby_buyers"))
        except Error:
            if conn:
                conn.rollback()
            app.logger.exception("Crop listing database error")
            flash("Could not save crop details.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template("crop_details.html")


@app.route("/compare", methods=["GET", "POST"])
@role_required("farmer")
def compare():
    results = []
    crop = ""
    location = ""
    quantity = 1.0
    transport_rate = 12.0
    if request.method == "POST":
        crop = request.form.get("crop", "").strip()
        location = request.form.get("location", "").strip()
        try:
            quantity = float(request.form.get("quantity", "1"))
            transport_rate = float(request.form.get("transport_rate", "12"))
            if (not crop or not math.isfinite(quantity) or not math.isfinite(transport_rate)
                    or quantity <= 0 or transport_rate < 0):
                raise ValueError
        except ValueError:
            flash("Enter a crop, a valid quantity and a non-negative transport rate.", "danger")
            return render_template("compare.html", results=[], crop=crop,
                                   quantity=quantity, location=location,
                                   transport_rate=transport_rate)
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT b.buyer_id AS id, b.buyer_name, b.business_name,
                          b.contact_name, b.phone, b.location, o.crop_name,
                          o.price_per_kg, o.distance_km, o.notes
                   FROM buyer_offers o
                   JOIN buyers b ON b.buyer_id = o.buyer_id
                   WHERE LOWER(o.crop_name) = LOWER(%s)
                     AND o.distance_km <= 100""",
                (crop,)
            )
            for offer in cur.fetchall():
                gross = float(offer["price_per_kg"]) * quantity
                transport = float(offer["distance_km"]) * transport_rate
                offer["business_name"] = offer.get("business_name") or offer.get("buyer_name")
                offer["gross_income"] = round(gross, 2)
                offer["transport_cost"] = round(transport, 2)
                offer["net_income"] = round(gross - transport, 2)
                offer["distance_km"] = round(float(offer["distance_km"]), 2)
                results.append(offer)
            results.sort(key=lambda item: item["net_income"], reverse=True)
        except Error:
            app.logger.exception("Offer comparison database error")
            flash("Could not load offers.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
        if not results:
            flash("No matching offers found within 100 km.", "info")
    return render_template("compare.html", results=results, crop=crop,
                           quantity=quantity, location=location,
                           transport_rate=transport_rate)


@app.route("/best-value", methods=["GET", "POST"])
@role_required("farmer")
def best_value():
    best_offer = None
    crop = ""
    quantity = ""
    searched = False
    if request.method == "POST":
        searched = True
        crop = request.form.get("crop", "").strip()
        try:
            quantity = float(request.form.get("quantity", "0"))
            if not crop or not math.isfinite(quantity) or quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Enter a valid crop name and quantity.", "danger")
            return render_template("best_value.html", best_offer=None,
                                   crop=crop, quantity=quantity, searched=searched)
        conn = None
        try:
            conn = get_db()
            cur = conn.cursor(dictionary=True)
            cur.execute(
                """SELECT b.buyer_name, b.business_name, b.contact_name, b.phone,
                          b.location, o.crop_name, o.price_per_kg, o.distance_km
                   FROM buyer_offers o JOIN buyers b ON b.buyer_id = o.buyer_id
                   WHERE LOWER(o.crop_name) = LOWER(%s) AND o.distance_km <= 100""",
                (crop,)
            )
            offers = cur.fetchall()
            for offer in offers:
                gross = float(offer["price_per_kg"]) * quantity
                transport = float(offer["distance_km"]) * 12.0
                offer["business_name"] = offer.get("business_name") or offer["buyer_name"]
                offer["gross_income"] = round(gross, 2)
                offer["transport_cost"] = round(transport, 2)
                offer["net_income"] = round(gross - transport, 2)
            if offers:
                best_offer = max(offers, key=lambda item: item["net_income"])
        except Error:
            app.logger.exception("Best value lookup error")
            flash("Could not calculate the best offer.", "danger")
        finally:
            if conn and conn.is_connected():
                conn.close()
    return render_template("best_value.html", best_offer=best_offer,
                           crop=crop, quantity=quantity, searched=searched)


@app.route("/transport-charges", methods=["GET", "POST"])
@role_required("farmer")
def transport_charges():
    distance = None
    rate = 12.0
    transport_cost = None
    if request.method == "POST":
        try:
            distance = float(request.form.get("distance", "0"))
            rate = float(request.form.get("rate", "12"))
            if (not math.isfinite(distance) or not math.isfinite(rate)
                    or distance < 0 or rate < 0):
                raise ValueError
            transport_cost = round(distance * rate, 2)
        except ValueError:
            flash("Enter valid non-negative distance and rate values.", "danger")
    return render_template("transport_charges.html", distance=distance,
                           rate=rate, transport_cost=transport_cost)


@app.route("/offers", methods=["GET", "POST"])
@role_required("buyer")
def offers():
    conn = None
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        buyer_id = get_buyer_id(cur)
        if not buyer_id:
            flash("Buyer account not found. Please register again or contact support.", "danger")
            return redirect(url_for("dashboard"))
        if request.method == "POST":
            business_name = request.form.get("business_name", "").strip()
            contact_name = request.form.get("contact_name", "").strip()
            phone = request.form.get("phone", "").strip()
            location = request.form.get("location", "").strip()
            crop_name = request.form.get("crop_name", "").strip()
            notes = request.form.get("notes", "").strip()
            try:
                price = float(request.form.get("price_per_kg", "0"))
                distance = float(request.form.get("distance_km", "0"))
                valid = (math.isfinite(price) and math.isfinite(distance)
                         and price > 0 and distance >= 0)
            except ValueError:
                valid = False
                price, distance = 0, 0
            if not all([business_name, contact_name, phone, location, crop_name]) or not valid:
                flash("Please enter valid offer details.", "danger")
            else:
                cur.execute(
                    """UPDATE buyers SET buyer_name=%s, business_name=%s,
                       contact_name=%s, phone=%s, location=%s WHERE buyer_id=%s""",
                    (business_name, business_name, contact_name, phone, location, buyer_id)
                )
                cur.execute(
                    """INSERT INTO buyer_offers
                       (buyer_id, crop_name, price_per_kg, distance_km, notes)
                       VALUES (%s, %s, %s, %s, %s)""",
                    (buyer_id, crop_name, price, distance, notes or None)
                )
                conn.commit()
                flash("Your buyer offer has been published.", "success")
                return redirect(url_for("offers"))
    except Error:
        if conn:
            conn.rollback()
        app.logger.exception("Publish offer database error")
        flash("Could not publish the offer. Check your database tables.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("offers.html")


@app.route("/contact-farmers")
@role_required("buyer")
def contact_farmers():
    conn = None
    farmers = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute("SELECT farmer_id, name, phone, location FROM farmers ORDER BY name")
        farmers = cur.fetchall()
    except Error:
        app.logger.exception("Contact farmers database error")
        flash("Could not load farmers.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("contact_farmers.html", farmers=farmers)


@app.route("/contact-buyers")
@role_required("farmer")
def contact_buyers():
    conn = None
    buyers = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        cur.execute(
            """SELECT buyer_id, buyer_name, business_name, contact_name, phone, location
               FROM buyers ORDER BY buyer_name"""
        )
        buyers = cur.fetchall()
    except Error:
        app.logger.exception("Contact buyers database error")
        flash("Could not load buyers.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("contact_buyers.html", buyers=buyers)


@app.route("/messages", methods=["GET", "POST"])
@login_required
def messages():
    conn = None
    contacts = []
    messages_list = []
    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)
        if request.method == "POST":
            try:
                receiver_id = int(request.form.get("receiver_id", "0"))
            except ValueError:
                receiver_id = 0
            message_text = request.form.get("message", "").strip()
            cur.execute(
                "SELECT id FROM users WHERE id=%s AND id<>%s",
                (receiver_id, session["user_id"])
            )
            recipient = cur.fetchone()
            if not recipient or not message_text or len(message_text) > 5000:
                flash("Choose a valid recipient and enter a message.", "danger")
            else:
                cur.execute(
                    """INSERT INTO app_messages (sender_id, receiver_id, message_text)
                       VALUES (%s, %s, %s)""",
                    (session["user_id"], receiver_id, message_text)
                )
                conn.commit()
                flash("Message sent.", "success")
                return redirect(url_for("messages"))

        cur.execute(
            """SELECT id, name, role FROM users
               WHERE id <> %s ORDER BY name""",
            (session["user_id"],)
        )
        contacts = cur.fetchall()
        cur.execute(
            """SELECT m.message_id, m.message_text AS message, m.created_at,
                      u.name AS sender_name, m.sender_id, m.receiver_id
               FROM app_messages m JOIN users u ON u.id = m.sender_id
               WHERE m.sender_id=%s OR m.receiver_id=%s
               ORDER BY m.created_at DESC""",
            (session["user_id"], session["user_id"])
        )
        messages_list = cur.fetchall()
    except Error:
        app.logger.exception("Messages database error")
        flash("Could not load messages.", "danger")
    finally:
        if conn and conn.is_connected():
            conn.close()
    return render_template("messages.html", contacts=contacts,
                           messages_list=messages_list)



@app.route("/-history")
@login_required
def transaction_history():
    conn = None
    transactions = [] transaction
    role = (session.get("role") or "").strip().lower()

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        if role == "farmer":
            farmer_id = get_farmer_id(cur)

            if farmer_id:
                cur.execute("""
                    SELECT transaction_id, crop_name, quantity_kg,
                           price_per_kg, total_amount, platform_fee,
                           transport_cost, net_amount, status,
                           payment_status, created_at
                    FROM transactions
                    WHERE farmer_id = %s
                    ORDER BY created_at DESC
                """, (farmer_id,))

                transactions = cur.fetchall()

        elif role == "buyer":
            buyer_id = get_buyer_id(cur)

            if buyer_id:
                cur.execute("""
                    SELECT transaction_id, crop_name, quantity_kg,
                           price_per_kg, total_amount, platform_fee,
                           transport_cost, net_amount, status,
                           payment_status, created_at
                    FROM transactions
                    WHERE buyer_id = %s
                    ORDER BY created_at DESC
                """, (buyer_id,))

                transactions = cur.fetchall()

        else:
            flash("Invalid account role.", "warning")
            return redirect(url_for("dashboard"))

    except Error:
        app.logger.exception("Transaction history database error")
        flash("Could not load transaction history.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        "transaction_history.html",
        transactions=transactions
    )

@app.route("/record-purchase", methods=["GET", "POST"])
@role_required("buyer")
def record_purchase():
    conn = None
    farmers = []

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        cur.execute(
            "SELECT farmer_id, name, location FROM farmers ORDER BY name"
        )
        farmers = cur.fetchall()

        buyer_id = get_buyer_id(cur)

        if not buyer_id:
            flash("Buyer account not found.", "danger")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            try:
                farmer_id = int(request.form.get("farmer_id", "0"))
                quantity = Decimal(request.form.get("quantity", "0"))
                price = Decimal(request.form.get("price", "0"))
                transport = Decimal(request.form.get("transport", "0"))

                valid = all(
                    value.is_finite()
                    for value in (quantity, price, transport)
                )

            except (ValueError, TypeError, InvalidOperation):
                valid = False
                farmer_id = 0
                quantity = Decimal("0")
                price = Decimal("0")
                transport = Decimal("0")

            crop_name = request.form.get("crop_name", "").strip()

            valid_farmer_ids = {
                farmer["farmer_id"] for farmer in farmers
            }

            if (
                not valid
                or farmer_id not in valid_farmer_ids
                or not crop_name
                or quantity <= 0
                or price <= 0
                or transport < 0
            ):
                flash("Please enter valid purchase details.", "danger")

            else:
                # Calculate crop amount
                crop_amount = (quantity * price).quantize(
                    Decimal("0.01")
                )

                # Farm2Market platform fee: 2% of crop amount only
                platform_fee = (
                    crop_amount * Decimal("0.02")
                ).quantize(Decimal("0.01"))

                # Total buyer payment
                payable = (
                    crop_amount + platform_fee + transport
                ).quantize(Decimal("0.01"))

                cur.execute(
                    """
                    INSERT INTO transactions
                    (
                        buyer_id,
                        farmer_id,
                        crop_name,
                        quantity_kg,
                        price_per_kg,
                        total_amount,
                        transport_cost,
                        platform_fee,
                        net_amount,
                        status,
                        payment_status
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        buyer_id,
                        farmer_id,
                        crop_name,
                        quantity,
                        price,
                        crop_amount,
                        transport,
                        platform_fee,
                        payable,
                        "Recorded",
                        "Pending"
                    )
                )

                conn.commit()

                flash(
                    "Purchase recorded successfully. "
                    "Payment is still pending.",
                    "success"
                )

                return redirect(url_for("transaction_history"))

    except Error:
        if conn:
            conn.rollback()

        app.logger.exception("Purchase recording database error")
        flash("Could not save the purchase.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        "record_purchase.html",
        farmers=farmers
    )

@app.route("/invoices")
@login_required
def invoices():
    conn = None
    invoices_list = []
    role = session.get("role")

    try:
        conn = get_db()
        cur = conn.cursor(dictionary=True)

        if role == "buyer":
            buyer_id = get_buyer_id(cur)

            if buyer_id:
                cur.execute("""
                    SELECT
                        t.transaction_id,
                        t.crop_name,
                        t.quantity_kg,
                        t.price_per_kg,
                        t.total_amount,
                        t.transport_cost,
                        t.net_amount,
                        t.status,
                        t.created_at,
                        f.name AS farmer_name
                    FROM transactions t
                    LEFT JOIN farmers f
                        ON t.farmer_id = f.farmer_id
                    WHERE t.buyer_id = %s
                    ORDER BY t.created_at DESC
                """, (buyer_id,))
                invoices_list = cur.fetchall()

        elif role == "farmer":
            farmer_id = get_farmer_id(cur)

            if farmer_id:
                cur.execute("""
                    SELECT
                        t.transaction_id,
                        t.crop_name,
                        t.quantity_kg,
                        t.price_per_kg,
                        t.total_amount,
                        t.transport_cost,
                        t.net_amount,
                        t.status,
                        t.created_at,
                        b.buyer_name
                    FROM transactions t
                    LEFT JOIN buyers b
                        ON t.buyer_id = b.buyer_id
                    WHERE t.farmer_id = %s
                    ORDER BY t.created_at DESC
                """, (farmer_id,))
                invoices_list = cur.fetchall()

        else:
            flash("Invalid account role.", "warning")
            return redirect(url_for("dashboard"))

    except Error:
        app.logger.exception("Invoice loading error")
        flash("Could not load invoices.", "danger")

    finally:
        if conn and conn.is_connected():
            conn.close()

    return render_template(
        "invoices.html",
        invoices=invoices_list,
        role=role
    )

if __name__ == "__main__":
    app.run(debug=True)
