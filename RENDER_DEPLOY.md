# Render deployment

Build Command:
pip install -r requirements.txt

Start Command:
gunicorn app:app

Required Environment Variable:
GEMINI_API_KEY

## Deployment steps
1. Create a Render Web Service.
2. Connect the GitHub repository for this project.
3. Select the main branch.
4. Set the Build Command to `pip install -r requirements.txt`.
5. Set the Start Command to `gunicorn app:app`.
6. Add `GEMINI_API_KEY` in the Render Environment settings.
7. Deploy the service.

## Notes
- Keep the Flask app object named `app`.
- Do not hardcode the API key in source files.
- Local development remains available with `python app.py`.
- Production can run with Gunicorn using `gunicorn app:app`.
