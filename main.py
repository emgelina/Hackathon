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
    body {
      font-family: sans-serif;
      background: #f6f8fb;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }
    form {
      background: white;
      padding: 20px;
      border-radius: 12px;
      box-shadow: 0 4px 10px rgba(0,0,0,0.1);
      width: 400px;
      text-align: center;
    }
    input[type=file], input[type=submit] {
      margin: 10px 0;
    }
    .result {
      margin-top: 20px;
      text-align: left;
      background: #f9f9f9;
      padding: 15px;
      border-radius: 8px;
    }
    .modal {
      display: {{ 'flex' if fact else 'none' }};
      position: fixed;
      top: 0; left: 0;
      width: 100%; height: 100%;
      background: rgba(0,0,0,0.6);
      justify-content: center;
      align-items: center;
    }
    .modal-content {
      background: white;
      padding: 20px;
      border-radius: 10px;
      width: 300px;
      text-align: center;
    }
    .modal button {
      margin: 10px;
      padding: 5px 10px;
      border: none;
      background: #007BFF;
      color: white;
      border-radius: 5px;
      cursor: pointer;
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
