from flask import Flask, render_template_string, request
import os
from google import genai
from dotenv import load_dotenv
import threading

# ---- Load environment variables ----
load_dotenv()

# ---- Configuration ----
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
  <style>
    :root {
      --purple: #7c3aed;
      --purple-light: #a78bfa;
      --grey: #6b7280;
      --light-grey: #f6f8fb;
      --white: #ffffff;
      --shadow: 0 8px 20px rgba(0, 0, 0, 0.08);
      --radius: 12px;
      --font: "Inter", system-ui, sans-serif;
    }

    * {
      box-sizing: border-box;
      transition: all 0.2s ease;
    }

    body {
      margin: 0;
      font-family: var(--font);
      background: var(--light-grey);
      color: var(--grey);
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }

    /* ---------- Form Container ---------- */
    form {
      background: var(--white);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 30px 32px;
      width: 400px;
      max-width: 90%;
      text-align: center;
    }

    h2 {
      color: var(--purple);
      margin-bottom: 15px;
      font-weight: 700;
    }

    /* ---------- Inputs ---------- */
    input[type="file"] {
      display: block;
      width: 100%;
      padding: 10px;
      border: 1px dashed var(--purple-light);
      border-radius: var(--radius);
      background: #faf9ff;
      cursor: pointer;
    }

    input[type="file"]:hover {
      background: #f3f0ff;
    }

    input[type="submit"] {
      background: linear-gradient(135deg, var(--purple), var(--purple-light));
      color: white;
      border: none;
      padding: 10px 18px;
      border-radius: var(--radius);
      cursor: pointer;
      font-weight: 600;
      margin-top: 12px;
      width: 100%;
    }

    input[type="submit"]:hover {
      opacity: 0.9;
      transform: translateY(-1px);
    }

    input[type="submit"]:active {
      transform: translateY(1px);
    }

    /* ---------- Results Box ---------- */
    .result {
      background: #fafafa;
      border-radius: var(--radius);
      margin-top: 20px;
      padding: 16px;
      box-shadow: inset 0 0 6px rgba(0, 0, 0, 0.04);
      text-align: left;
    }

    .result h3 {
      color: var(--purple);
      margin-bottom: 5px;
    }

    .result p {
      color: #333;
      font-size: 0.95rem;
    }

    /* ---------- Modal ---------- */
    .modal {
      display: {{ 'flex' if fact else 'none' }};
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.55);
      justify-content: center;
      align-items: center;
      z-index: 10;
      backdrop-filter: blur(2px);
    }

    .modal-content {
      background: var(--white);
      padding: 25px 20px;
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      width: 320px;
      text-align: center;
      animation: fadeIn 0.3s ease;
    }

    .modal-content h3 {
      color: var(--purple);
      margin-bottom: 10px;
    }

    .modal-content p {
      color: #333;
      margin-bottom: 15px;
    }

    .modal button {
      margin: 5px;
      padding: 8px 14px;
      border: none;
      border-radius: var(--radius);
      cursor: pointer;
      background: var(--purple);
      color: white;
      font-weight: 600;
    }

    .modal button:hover {
      background: var(--purple-light);
    }

    /* ---------- Animations ---------- */
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: scale(0.95);
      }
      to {
        opacity: 1;
        transform: scale(1);
      }
    }

    /* ---------- Responsive ---------- */
    @media (max-width: 500px) {
      form {
        width: 90%;
        padding: 20px;
      }
      .modal-content {
        width: 90%;
      }
    }
  </style>
</head>
<body>
  <form action="/" method="post" enctype="multipart/form-data">
    <h2>Food Allergen Identifier</h2>
    <input type="file" name="file" accept="image/*" required><br>
    <input type="submit" value="Analyze Food">
    {% if ingredients %}
      <div class="result" id="results">
        <h3>Ingredients:</h3>
        <p>{{ ingredients }}</p>
        <h3>Possible Allergens:</h3>
        <p>{{ allergens or 'Loading allergens...' }}</p>
      </div>
    {% endif %}
  </form>

  <div class="modal" id="factModal">
    <div class="modal-content">
      <h3>Did you know?</h3>
      <p>{{ fact }}</p>
      <button onclick="closeModal()">I knew that</button>
      <button onclick="closeModal()">No idea!</button>
    </div>
  </div>

  <script>
    function closeModal() {
      document.getElementById('factModal').style.display = 'none';
    }
  </script>
</body>
</html>
"""

# ---- Background function for allergen detection ----
def get_allergens_async(ingredients, result_holder):
    """Run allergen detection in background thread."""
    response2 = gemini_client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"Give a list of possible allergens that could result from this list of ingredients {ingredients}. "
            "Respond in the format {celiac, peanuts, ...} do not include any additional text in your response."
        )
    )
    result_holder["allergens"] = response2.text.strip()

# ---- Main route ----
@app.route("/", methods=["GET", "POST"])
def upload_and_process():
    ingredients = None
    allergens = None
    fact = None

    if request.method == "POST":
        uploaded_file = request.files["file"]
        if uploaded_file.filename != "":
            filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(filepath)

            # Step 1: Get random food allergy fact (Gemini)
            fact_response = gemini_client.models.generate_content(
                model="gemini-2.5-flash",
                contents="Write a random obscure statistical fact about a rare food allergy. Keep it short, witty, and a little sassy."
            )
            fact = fact_response.text.strip()

            # Step 2: Identify ingredients (Gemini)
            with open(filepath, "rb") as f:
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

            # Step 3: Load allergens in background
            result_holder = {}
            thread = threading.Thread(target=get_allergens_async, args=(ingredients, result_holder))
            thread.start()
            thread.join()  # You can remove this for async loading
            allergens = result_holder.get("allergens", "Loading allergens...")

    return render_template_string(HTML_PAGE, ingredients=ingredients, allergens=allergens, fact=fact)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
