from flask import Flask, request, jsonify
from google import genai
import base64

app = Flask(__name__)

client = genai.Client(api_key="YOUR_API_KEY_HERE")

@app.route("/analyze", methods=["POST"])
def analyze_image():
    # Expect a JSON body with "image" as base64 string
    data = request.get_json()
    image_data_url = data.get("image")

    if not image_data_url or not image_data_url.startswith("data:image/"):
        return jsonify({"error": "Invalid image data"}), 400

    # Extract the Base64 part
    base64_str = image_data_url.split(",", 1)[1]
    image_bytes = base64.b64decode(base64_str)

    # Step 1: Identify ingredients
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=[
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Give me only the breakdown of the base level ingredients "
                            "of the food in the image in the format {bread, apple, ...}. "
                            "Keep things basic such as bread instead of buns. "
                            "Do not include any additional text in your response."
                        )
                    },
                    {
                        "inline_data": {
                            "mime_type": "image/jpeg",
                            "data": image_bytes
                        }
                    }
                ],
            }
        ],
    )

    ingredients = response.text.strip()

    # Step 2: Identify allergens
    response2 = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=(
            f"Give a list of possible allergens that could result from this list of ingredients {ingredients}. "
            "Respond in the format {celiac, peanuts, ...} do not include any additional text in your response."
        ),
    )

    allergens = response2.text.strip()

    return jsonify({"ingredients": ingredients, "allergens": allergens})


if __name__ == "__main__":
    app.run(debug=True)
