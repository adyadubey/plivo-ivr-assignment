import os
import re
import logging
from flask import Flask, request, Response, render_template_string
import plivo
from plivo import plivoxml

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# Set these in your environment; never commit credentials.
PLIVO_AUTH_ID = os.getenv("PLIVO_AUTH_ID", "")
PLIVO_AUTH_TOKEN = os.getenv("PLIVO_AUTH_TOKEN", "")
PLIVO_NUMBER = os.getenv("PLIVO_NUMBER", "")
# DDMM format. Example: March 15 => 1503. Set this to your own birthdate.
OTP_DDMM = os.getenv("OTP_DDMM", "")
ASSOCIATE_NUMBER = os.getenv("ASSOCIATE_NUMBER", "")
PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
AUDIO_URL = os.getenv("AUDIO_URL", "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3")

INDEX = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>InspireWorks IVR Demo</title>
<style>
body{font:16px system-ui,sans-serif;background:#f5f7fb;margin:0;color:#172033}
main{max-width:620px;margin:7vh auto;padding:28px;background:white;border-radius:16px;box-shadow:0 8px 32px #14213d12}
h1{margin-top:0}label{display:block;margin:16px 0 6px;font-weight:600}
input{box-sizing:border-box;width:100%;padding:12px;border:1px solid #ccd3df;border-radius:8px;font:inherit}
button{margin-top:20px;background:#315efb;color:white;border:0;border-radius:8px;padding:12px 18px;font:inherit;font-weight:700;cursor:pointer}
.note{color:#5c667a;font-size:.92rem}.error{color:#a11}
</style></head><body><main>
<h1>InspireWorks IVR Demo</h1>
<p>Trigger a test call and demonstrate OTP authentication and the two-level IVR.</p>
{% if error %}<p class="error">{{ error }}</p>{% endif %}
<form method="post" action="/call">
<label for="to">Your phone number (international format)</label>
<input id="to" name="to" placeholder="+91XXXXXXXXXX" required pattern="\\+[1-9][0-9]{7,14}">
<button type="submit">Start outbound call</button>
</form>
<p class="note">The caller must enter the configured birthdate OTP in DDMM format. Only call numbers you own or have permission to contact.</p>
</main></body></html>"""

def xml_response(root):
    return Response(root.to_string(), mimetype="application/xml")

def absolute(path):
    if not PUBLIC_BASE_URL:
        raise RuntimeError("PUBLIC_BASE_URL is not configured")
    return f"{PUBLIC_BASE_URL}{path}"

def say(root, text, language="en-US"):
    root.add(plivoxml.SpeakElement(text, language=language))

def gather(root, prompt, action, num_digits=1, language="en-US"):
    say(root, prompt, language)
    root.add(plivoxml.GetDigitsElement(
        action=absolute(action), method="POST", num_digits=num_digits,
        timeout=8, redirect=True
    ))
    say(root, "We did not receive an input. Goodbye.", language)
    root.add(plivoxml.HangupElement())

@app.get("/")
def index():
    return render_template_string(INDEX, error=None)

@app.post("/call")
def make_call():
    to_number = request.form.get("to", "").strip()
    if not re.fullmatch(r"\+[1-9]\d{7,14}", to_number):
        return render_template_string(INDEX, error="Enter a valid international number such as +919876543210."), 400
    missing = [name for name, value in {
        "PLIVO_AUTH_ID": PLIVO_AUTH_ID, "PLIVO_AUTH_TOKEN": PLIVO_AUTH_TOKEN,
        "PLIVO_NUMBER": PLIVO_NUMBER, "OTP_DDMM": OTP_DDMM,
        "ASSOCIATE_NUMBER": ASSOCIATE_NUMBER, "PUBLIC_BASE_URL": PUBLIC_BASE_URL
    }.items() if not value]
    if missing:
        return render_template_string(INDEX, error="Missing configuration: " + ", ".join(missing)), 500
    if not re.fullmatch(r"\d{4}", OTP_DDMM):
        return render_template_string(INDEX, error="OTP_DDMM must be exactly four digits in DDMM format."), 500
    try:
        client = plivo.RestClient(PLIVO_AUTH_ID, PLIVO_AUTH_TOKEN)
        result = client.calls.create(
            from_=PLIVO_NUMBER,
            to_=to_number,
            answer_url=absolute("/answer"),
            answer_method="POST"
        )
        call_uuid = getattr(result, "request_uuid", None) or str(result)
        return f"""<!doctype html><meta name="viewport" content="width=device-width"><h2>Call request submitted</h2>
<p>Plivo accepted the request. Request reference: <code>{call_uuid}</code></p><p><a href="/">Make another call</a></p>"""
    except Exception:
        app.logger.exception("Plivo call creation failed")
        return render_template_string(INDEX, error="Plivo could not start the call. Check server logs and credentials."), 502

@app.route("/answer", methods=["GET", "POST"])
def answer():
    root = plivoxml.ResponseElement()
    gather(root, "Welcome to InspireWorks. Please enter your four digit birthdate code, day then month.",
           "/otp", num_digits=4)
    return xml_response(root)

@app.route("/otp", methods=["GET", "POST"])
def otp():
    root = plivoxml.ResponseElement()
    entered = request.values.get("Digits", "")
    if entered == OTP_DDMM:
        say(root, "Authentication successful.")
        gather(root, "For English, press 1. Para español, oprima 2.",
               "/language", num_digits=1)
    else:
        say(root, "That code was incorrect.")
        gather(root, "Please enter your four digit birthdate code, day then month.",
               "/otp", num_digits=4)
    return xml_response(root)

@app.route("/language", methods=["GET", "POST"])
def language():
    root = plivoxml.ResponseElement()
    choice = request.values.get("Digits", "")
    if choice == "1":
        gather(root, "English selected. Press 1 to hear a short audio message. Press 2 to speak to a live associate.",
               "/action/en", num_digits=1)
    elif choice == "2":
        gather(root, "Español seleccionado. Oprima 1 para escuchar un mensaje de audio. Oprima 2 para hablar con un representante.",
               "/action/es", num_digits=1, language="es-ES")
    else:
        gather(root, "Invalid choice. For English, press 1. Para español, oprima 2.",
               "/language", num_digits=1)
    return xml_response(root)

@app.route("/action/<lang>", methods=["GET", "POST"])
def action(lang):
    root = plivoxml.ResponseElement()
    choice = request.values.get("Digits", "")
    language = "es-ES" if lang == "es" else "en-US"
    if lang not in ("en", "es"):
        say(root, "Invalid menu.")
        root.add(plivoxml.HangupElement())
    elif choice == "1":
        say(root, "Here is the InspireWorks audio message." if lang == "en" else
            "Este es el mensaje de audio de InspireWorks.", language)
        # Replace AUDIO_URL with a short MP3 you own or are permitted to use.
        root.add(plivoxml.PlayElement(AUDIO_URL))
        say(root, "Thank you for calling. Goodbye." if lang == "en" else
            "Gracias por llamar. Adiós.", language)
        root.add(plivoxml.HangupElement())
    elif choice == "2":
        say(root, "Please wait while we connect you." if lang == "en" else
            "Por favor espere mientras le conectamos.", language)
        dial = plivoxml.DialElement(action=absolute("/dial_status"), method="POST", timeout=25, caller_id=PLIVO_NUMBER)
        dial.add(plivoxml.NumberElement(ASSOCIATE_NUMBER))
        root.add(dial)
    else:
        gather(root, "Invalid choice. Press 1 for audio or 2 for a live associate."
               if lang == "en" else
               "Opción no válida. Oprima 1 para audio o 2 para un representante.",
               f"/action/{lang}", num_digits=1, language=language)
    return xml_response(root)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.route("/dial_status", methods=["GET", "POST"])
def dial_status():
    from flask import Response
    print("DIAL STATUS:", dict(request.values), flush=True)
    print("ASSOCIATE_NUMBER in use:", repr(ASSOCIATE_NUMBER), flush=True)
    print("ASSOCIATE_NUMBER in use:", repr(ASSOCIATE_NUMBER), flush=True)
    xml = ('<?xml version="1.0" encoding="UTF-8"?><Response>'
           '<Speak>Sorry, we could not connect you to an associate. Goodbye.</Speak>'
           '<Hangup/></Response>')
    return Response(xml, mimetype="text/xml")


if __name__ == "__main__":
    # Local development only. For public demos use a production WSGI server.
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=False)
