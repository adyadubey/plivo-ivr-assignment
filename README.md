# InspireWorks Plivo IVR Demo

A small Flask application for the FDE assignment. It initiates an outbound Plivo call, authenticates the recipient with a four-digit `DDMM` code, and provides a two-level IVR in English and Spanish.

## Features

- Web form to start an outbound call.
- Plivo XML call flow and DTMF input using `GetDigits`.
- Incorrect OTP loops back to the OTP prompt; IVR is only available after successful authentication.
- English/Spanish language selection.
- MP3 playback and transfer to a live associate.
- Environment-based credentials; no database required.

## Requirements

- Python 3.10+
- A Plivo account with Voice API access and an enabled/verified caller ID/number as required by your account.
- A publicly reachable HTTPS deployment/tunnel for Plivo callbacks. Plivo must be able to reach `/answer`, `/otp`, `/language`, and `/action/...`.
- Permission to call the destination phone number.

## Setup

1. Create and activate a virtual environment:

   ```bash
   python -m venv .venv
   # macOS/Linux
   source .venv/bin/activate
   # Windows PowerShell
   .venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Copy `.env.example` to `.env`, then export the values into your shell (Flask does not automatically load `.env` in this starter):

   ```bash
   export PLIVO_AUTH_ID="..."
   export PLIVO_AUTH_TOKEN="..."
   export PLIVO_NUMBER="+918035454161"
   export OTP_DDMM="DDMM"
   export ASSOCIATE_NUMBER="02264236412"
   export PUBLIC_BASE_URL="https://your-public-host"
   export AUDIO_URL="https://your-public-mp3-url.mp3"
   ```

   On Windows PowerShell, use `$env:NAME="value"` for each variable. Replace `DDMM` with your own birthdate in day-then-month format. Do not commit secrets.

4. Run locally:

   ```bash
   python app.py
   ```

   The UI is at `http://localhost:5000`. Localhost alone is not reachable by Plivo; configure an HTTPS public host or a tunnel and set `PUBLIC_BASE_URL` to that public base URL. Keep the app running.

5. Open the UI, enter your own phone number in E.164 format (for example `+919876543210`), and start the call.

## Call flow

1. `/call` calls Plivo's REST API with `/answer` as the answer URL.
2. `/answer` asks for the four-digit birthdate code.
3. `/otp` checks the code. Incorrect input loops to `/otp`; correct input opens the language menu.
4. `/language`: 1 selects English; 2 selects Spanish.
5. `/action/en` or `/action/es`: 1 plays the configured MP3; 2 dials the configured associate number. Invalid input repeats the current action menu.

## Demo checklist (3–5 minutes)

- Show the web page and trigger a call to your own phone.
- Enter a deliberately incorrect four-digit code and show that it re-prompts.
- Enter your correct `DDMM` code.
- Press 1 for English, then 1 for audio playback.
- Trigger a second call, authenticate, press 2 for Spanish, then 2 for the associate transfer.
- Mention that the MP3 and associate destination are configurable.

## Before submission

- [ ] Confirm your `PLIVO_NUMBER` is voice-enabled and usable as the caller ID in your Plivo account.
- [ ] Confirm the associate destination is in E.164 format if required by Plivo; the assignment's `02264236412` is kept as supplied, but may need country code (for example `+912264236412`) depending on account routing.
- [ ] Use a short MP3 you control or have permission to use.
- [ ] Test callback URLs from an external network.
- [ ] Record the 3–5 minute demo.
- [ ] Attach the receiver's phone number used in the submission email, as requested by the assignment.

## Security notes

- The PDF included credentials. Rotate the Plivo Auth Token in the Plivo console before using this code, and keep the new token in environment variables only.
- Do not publish `.env`, tokens, personal birthdate, or call logs in your repository/video.
- The assignment's birthdate OTP is suitable only for a demo, not production authentication.
- This starter has no rate limiting or call authorization beyond validating the destination number. Keep it private during testing and add authentication/rate limits before any public deployment.
