from flask import Flask, render_template_string, request
import os
from google import genai

# ---- Configuration ----
app = Flask(__name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
client = genai.Client(api_key="AIzaSyCCKqbL567RK4BAhCNDcz8tu2rN1IWPC4s")

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
  </style>
</head>
<body>
  <form action="/" method="post" enctype="multipart/form-data">
    <h2>Food Allergen Identifier</h2>
    <input type="file" name="file" accept="image/*" required><br>
    <input type="submit" value="Analyze Food">
    {% if ingredients %}
      <div class="result">
        <h3>Ingredients:</h3>
        <p>{{ ingredients }}</p>
        <h3>Possible Allergens:</h3>
        <p>{{ allergens }}</p>
      </div>
    {% endif %}
  </form>
</body>
</html>
"""

# ---- Routes ----
@app.route("/", methods=["GET", "POST"])
def upload_and_process():
    ingredients = None
    allergens = None

    if request.method == "POST":
        uploaded_file = request.files["file"]
        if uploaded_file.filename != "":
            filepath = os.path.join(UPLOAD_FOLDER, uploaded_file.filename)
            uploaded_file.save(filepath)

            # --- Send to Gemini ---
            with open(filepath, "rb") as f:
                image_data = f.read()

            # Step 1: Identify base ingredients
            response = client.models.generate_content(
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
                            {"inline_data": {
                                "mime_type": "image/jpeg",
                                "data": image_data
                            }}
                        ]
                    }
                ]
            )
            ingredients = response.text.strip()

            # Step 2: Identify possible allergens
            response2 = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=(
                    f"Give a list of possible allergens that could result from this list of ingredients {ingredients}. "
                    "Respond in the format {celiac, peanuts, ...} do not include any additional text in your response."
                )
            )
            allergens = response2.text.strip()

    return render_template_string(HTML_PAGE, ingredients=ingredients, allergens=allergens)


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=True)
