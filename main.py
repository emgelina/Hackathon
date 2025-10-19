from flask import Flask, render_template_string, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
import os
from google import genai
from dotenv import load_dotenv

# ---- Load environment variables ----
load_dotenv()

# ---- Configuration ----
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "gif", "webp"}

# Initialize Gemini client
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# ---- HTML Template ----
HTML_PAGE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Food Allergen Identifier</title>
  <meta name="viewport" content="width=device-width,initial-scale=1" />
  <style>
    :root {
      --bg: #f6f6fa;
      --card: #ffffff;
      --primary: #512888; /* K-State Purple */
      --primary-light: #6f42c1;
      --primary-hover: #3d1f66;
      --text-dark: #1e1a2d;
      --text-light: #5c5776;
      --radius: 14px;
      --shadow: 0 8px 28px rgba(81, 40, 136, 0.12);
      --transition: 0.22s ease;
    }
    * { box-sizing: border-box; font-family: "Segoe UI", Roboto, sans-serif; }
    /* Center the whole layout vertically and horizontally */
    body {
      background: linear-gradient(180deg, #fbfbfd 0%, #f2f1f6 100%);
      margin: 0;
      padding: 1.6rem;               /* smaller padding so centering is exact */
      color: var(--text-dark);
      display: flex;
      justify-content: center;
      align-items: center;           /* <-- changed to center vertically */
      min-height: 100vh;
      gap: 1.2rem;
    }

    /* Layout container */
    .container {
      display: grid;
      grid-template-columns: 520px 360px;
      gap: 1rem;
      align-items: start;
      width: 100%;
      max-width: 940px;             /* keep a max width so centering is consistent */
    }

    /* Left: form card */
    .card {
      background: var(--card);
      padding: 2rem;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      border-top: 6px solid var(--primary);
      transition: transform var(--transition);
    }
    .card:hover { transform: translateY(-4px); }

    h2 { margin: 0 0 0.35rem 0; color: var(--primary); font-size: 1.6rem; }
    p.subtitle { color: var(--text-light); margin: 0 0 1rem 0; }

    .form-row { margin-top: 0.8rem; display:flex; gap:0.6rem; align-items:center; }
    input[type=file] { flex: 1; padding: 0.6rem; border-radius: 10px; border: 1px solid #e6e1ef; }
    .btn { background: var(--primary); color: #fff; border: none; padding: 0.7rem 1rem; border-radius: 10px; cursor: pointer; font-weight:600;}
    .btn:disabled { opacity: 0.7; cursor: not-allowed; }

    /* Results box */
    .result {
      margin-top: 1.2rem;
      text-align: left;
      background: #faf8ff;
      padding: 1rem;
      border-radius: 10px;
      border: 1px solid #ece1fb;
      box-shadow: inset 0 0 6px rgba(81,40,136,0.04);
    }
    .result h3 { color: var(--primary-light); margin: 0 0 0.4rem 0; font-size: 1rem; }
    .result p { margin: 0; color: var(--text-light); white-space: pre-wrap; word-break: break-word; }

    /* Right column: preview and info */
    .preview-card {
      background: linear-gradient(180deg, #fff, #fbfbff);
      padding: 1rem;
      border-radius: 12px;
      box-shadow: var(--shadow);
      border: 1px solid #efe9fb;
      display: flex;
      flex-direction: column;
      gap: 0.8rem;
      min-height: 280px;
      align-items: center;
    }
    .preview-placeholder {
      border: 2px dashed #efe6f8;
      width: 100%;
      height: 220px;
      border-radius: 10px;
      display:flex; align-items:center; justify-content:center; color: #a99fe0;
      font-size: 0.95rem;
    }
    .preview-img { max-width: 100%; max-height: 220px; border-radius: 8px; object-fit: cover; }

    /* Modal for fact */
    .modal { display:none; position:fixed; inset:0; background: rgba(34,25,50,0.5); justify-content:center; align-items:center; z-index:1200; }
    .modal.show { display:flex; }
    .modal-box { background:var(--card); padding:1.4rem; border-radius:12px; box-shadow:var(--shadow); width:340px; text-align:center; }
    .modal-box h3 { margin:0 0 0.6rem 0; color:var(--primary); }
    .modal-actions { margin-top:0.8rem; display:flex; gap:0.6rem; justify-content:center; }

    /* Loading overlay */
    .loading-overlay {
      display:none;
      position: fixed;
      inset:0;
      background: rgba(255,255,255,0.65);
      z-index:1300;
      align-items:center;
      justify-content:center;
      backdrop-filter: blur(2px);
      transition: opacity 0.2s;
    }
    .loading-overlay.show { display:flex; }

    /* Spinner and thinking dots */
    .spinner {
      width: 64px; height: 64px; border-radius: 50%;
      border: 6px solid rgba(81,40,136,0.12);
      border-top-color: var(--primary);
      animation: spin 1s linear infinite;
      margin-bottom: 0.6rem;
    }
    @keyframes spin { to { transform: rotate(360deg); } }
    .thinking {
      text-align:center;
      font-weight:600;
      color:var(--primary);
      letter-spacing:0.4px;
    }
    .dots::after {
      content: ' .';
      animation: dots 1s steps(3, end) infinite;
    }
    @keyframes dots { 0%{content:''} 33%{content:'.'} 66%{content:'..'} 100%{content:'...'} }

    /* Powered by Gemini badge */
    .gemini-badge {
      position: fixed;
      right: 14px;
      bottom: 14px;
      background: linear-gradient(180deg,#ffffff,#fbf8ff);
      border: 1px solid #e9e3fb;
      padding: 6px 10px;
      border-radius: 999px;
      display:flex; gap:8px; align-items:center;
      box-shadow: 0 6px 18px rgba(81,40,136,0.08);
      font-size: 0.85rem; color:var(--text-light); z-index:1500;
      text-decoration: none;
    }
    .gemini-logo { width:18px; height:18px; display:inline-block; border-radius:4px; background: linear-gradient(45deg,#6f42c1,#512888); box-shadow: inset 0 -2px 6px rgba(255,255,255,0.06); }

    /* small responsive tweaks */
    @media (max-width: 980px) {
      .container { grid-template-columns: 1fr; }
      .preview-card { order: -1; }
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="card">
      <h2>💜 Food Allergen Identifier</h2>
      <p class="subtitle">Upload an image of your meal to identify base ingredients and possible allergens.</p>

      <form id="analyzeForm">
        <div class="form-row">
          <input id="fileInput" type="file" name="file" accept="image/*" required>
          <button id="analyzeBtn" class="btn" type="submit">Analyze</button>
        </div>
      </form>

      <div id="resultsArea" class="result" style="display:none;">
        <div id="ingredientsBlock"><h3>Ingredients:</h3><p id="ingredientsText"></p></div>
        <div id="allergensBlock" style="margin-top:8px;"><h3>Possible Allergens:</h3><p id="allergensText"></p></div>
      </div>
    </div>

    <div class="preview-card">
      <div id="previewBox" class="preview-placeholder">Image preview will appear here</div>
      <div style="width:100%; display:flex; justify-content:space-between; align-items:center;">
        <div style="font-size:0.92rem; color:var(--text-light);">Preview & quick details</div>
        <div style="font-size:0.82rem; color:#9b92b9;">K-State style 💜</div>
      </div>
    </div>
  </div>

  <!-- Fact modal -->
  <div id="factModal" class="modal" role="dialog" aria-modal="true">
    <div class="modal-box">
      <h3>Did you know?</h3>
      <div id="factText" style="color:var(--text-light);"></div>
      <div class="modal-actions">
        <button class="btn" onclick="closeFact()">Yes</button>
        <button class="btn" onclick="closeFact()">No</button>
      </div>
    </div>
  </div>

  <!-- Loading overlay -->
  <div id="loadingOverlay" class="loading-overlay" aria-hidden="true">
    <div style="text-align:center;">
      <div class="spinner" role="status" aria-hidden="true"></div>
      <div class="thinking">AI is thinking<span class="dots"></span></div>
    </div>
  </div>

  <!-- Powered by Gemini badge -->
  <a class="gemini-badge" href="https://developers.google.com/experimental/generative-ai" target="_blank" rel="noopener noreferrer" title="Powered by Gemini">
    <span class="gemini-logo" aria-hidden="true"></span>
    <span>Powered by Gemini</span>
  </a>

  <script>
    const form = document.getElementById('analyzeForm');
    const fileInput = document.getElementById('fileInput');
    const previewBox = document.getElementById('previewBox');
    const loadingOverlay = document.getElementById('loadingOverlay');
    const analyzeBtn = document.getElementById('analyzeBtn');
    const resultsArea = document.getElementById('resultsArea');
    const ingredientsText = document.getElementById('ingredientsText');
    const allergensText = document.getElementById('allergensText');
    const factModal = document.getElementById('factModal');
    const factText = document.getElementById('factText');

    // Show image preview immediately when user selects a file
    fileInput.addEventListener('change', (e) => {
      const file = e.target.files[0];
      if (!file) {
        previewBox.innerHTML = 'Image preview will appear here';
        return;
      }
      const url = URL.createObjectURL(file);
      previewBox.innerHTML = `<img class="preview-img" src="${url}" alt="Preview">`;
    });

    // Close fact modal
    function closeFact() {
      factModal.classList.remove('show');
    }

    // Form submission via fetch (AJAX) so we can show a loader while server runs Gemini calls
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const file = fileInput.files[0];
      if (!file) return alert('Please select an image first.');

      // show loader
      loadingOverlay.classList.add('show');
      analyzeBtn.disabled = true;

      const fd = new FormData();
      fd.append('file', file);

      try {
        const resp = await fetch('/analyze', { method: 'POST', body: fd });
        if (!resp.ok) {
          const txt = await resp.text();
          throw new Error(txt || 'Server error');
        }
        const data = await resp.json();

        // update preview if server returned a public URL
        if (data.image_url) {
          previewBox.innerHTML = `<img class="preview-img" src="${data.image_url}" alt="Uploaded preview">`;
        }

        // update results
        ingredientsText.textContent = data.ingredients || 'No ingredients found.';
        allergensText.textContent = data.allergens || 'No allergens identified.';
        resultsArea.style.display = 'block';

        // show fact modal if present
        if (data.fact) {
          factText.textContent = data.fact;
          factModal.classList.add('show');
        }
      } catch (err) {
        console.error('Error:', err);
        alert('An error occurred: ' + (err.message || 'unknown'));
      } finally {
        loadingOverlay.classList.remove('show');
        analyzeBtn.disabled = false;
      }
    });
  </script>
</body>
</html>
"""

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS

# ---- Routes ----
@app.route("/", methods=["GET"])
def index():
    return render_template_string(HTML_PAGE)

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    # serve uploaded files (careful if exposing in production; consider a CDN or protected route)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route("/analyze", methods=["POST"])
def analyze():
    # This endpoint is called via AJAX and will return JSON.
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400

    uploaded_file = request.files['file']
    if uploaded_file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if not allowed_file(uploaded_file.filename):
        return jsonify({"error": "File type not allowed"}), 400

    filename = secure_filename(uploaded_file.filename)
    save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    uploaded_file.save(save_path)

    try:
        # 1) Get a small sassy fact
        fact_response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents="Write a random obscure statistical fact about a rare food allergy. Keep it short, witty, and a little sassy."
        )
        fact = fact_response.text.strip()

        # 2) Identify ingredients from image
        with open(save_path, "rb") as f:
            image_data = f.read()

        response = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                {
                    "role": "user",
                    "parts": [
                        {"text": (
                            "Give me only the breakdown of the base level ingredients of the food in the image "
                            "in the format {bread, apple, ...}. Keep things basic such as bread instead of buns. "
                            "Do not include any additional text in your response."
                        )},
                        {"inline_data": {"mime_type": "image/jpeg", "data": image_data}}
                    ]
                }
            ]
        )
        ingredients = response.text.strip()

        # 3) Get allergens (synchronous here so frontend loader covers it)
        response2 = gemini_client.models.generate_content(
            model="gemini-2.5-flash",
            contents=(
                f"Give a list of possible allergens that could result from this list of ingredients {ingredients}. "
                "Respond in the format {celiac, peanuts, ...} do not include any additional text in your response."
            )
        )
        allergens = response2.text.strip()

        # Build the URL for preview (served by /uploads/<filename>)
        image_url = f"/uploads/{filename}"

        return jsonify({
            "ingredients": ingredients,
            "allergens": allergens,
            "fact": fact,
            "image_url": image_url
        })

    except Exception as exc:
        # log in real app
        return jsonify({"error": str(exc)}), 500


if __name__ == "__main__":
    # debug server for local testing
    app.run(host="127.0.0.1", port=5000, debug=True)
