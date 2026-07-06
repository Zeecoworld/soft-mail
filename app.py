import os
import re
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests

app = Flask(__name__, static_folder=".", static_url_path="")
CORS(app)

BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"
MAX_PER_CALL = 500  # safety ceiling per request, well under Brevo's per-call limit


def fill_template(text, recipient):
    if not text:
        return text
    text = re.sub(r"\{\{\s*firstname\s*\}\}", recipient.get("firstname") or "there", text, flags=re.IGNORECASE)
    text = re.sub(r"\{\{\s*email\s*\}\}", recipient.get("email") or "", text, flags=re.IGNORECASE)
    return text


@app.route("/")
def index():
    return send_from_directory(".", "index.html")


@app.route("/send-batch", methods=["POST"])
def send_batch():
    api_key = os.environ.get("BREVO_API_KEY")
    if not api_key:
        return jsonify({"error": "BREVO_API_KEY is not set in Render environment variables."}), 500

    payload = request.get_json(silent=True)
    if payload is None:
        return jsonify({"error": "Invalid JSON body."}), 400

    sender_name = payload.get("senderName")
    sender_email = payload.get("senderEmail")
    subject = payload.get("subject")
    html_body = payload.get("htmlBody")
    recipients = payload.get("recipients")

    if not sender_email or not subject or not html_body or not isinstance(recipients, list) or len(recipients) == 0:
        return jsonify({"error": "Missing senderEmail, subject, htmlBody, or recipients."}), 400

    if len(recipients) > MAX_PER_CALL:
        return jsonify({
            "error": f"This tool caps a single send at {MAX_PER_CALL} recipients. "
                     f"You sent {len(recipients)}. Split into another batch."
        }), 400

    # One messageVersion per recipient so each person gets their own
    # rendered subject + body and only ever sees their own address in "to".
    message_versions = []
    for r in recipients:
        email = r.get("email")
        firstname = r.get("firstname")
        to_entry = {"email": email}
        if firstname:
            to_entry["name"] = firstname
        message_versions.append({
            "to": [to_entry],
            "subject": fill_template(subject, r),
            "htmlContent": fill_template(html_body, r),
        })

    body = {
        "sender": {"name": sender_name or sender_email, "email": sender_email},
        # Top-level subject/htmlContent act as fallback defaults; every
        # version above overrides them anyway.
        "subject": subject,
        "htmlContent": html_body,
        "messageVersions": message_versions,
    }

    try:
        resp = requests.post(
            BREVO_API_URL,
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                "api-key": api_key,
            },
            json=body,
            timeout=30,
        )
        data = resp.json()
    except Exception as e:
        return jsonify({"error": "Request to Brevo failed", "details": str(e)}), 500

    if not resp.ok:
        return jsonify({"error": "Brevo API error", "details": data}), resp.status_code

    return jsonify({
        "success": True,
        "sent": len(recipients),
        "messageIds": data.get("messageIds", data),
    }), 200


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))