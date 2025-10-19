from google import genai

client = genai.Client(api_key="AIzaSyCCKqbL567RK4BAhCNDcz8tu2rN1IWPC4s")

response = client.models.generate_content(
    model="gemini-2.5-flash",
    contents=[
        {
            "role": "user",
            "parts": [
                {"text": "Give me only the breakdown of the base level ingredients of the food in the image in the format {bread, apple, ...}. Keep things basic such as bread instead of buns. do not include any additional text in your response."},
                {"inline_data": {
                    "mime_type": "image/jpeg",
                    "data": open("food.jpg", "rb").read()
                }}
            ]
        }
    ]
)

print(response.text)

response2 = client.models.generate_content( model="gemini-2.5-flash", contents=f"Give a list of possible allergens that could result from this list of ingredients {response.text}." + " Respond in the format {celiac, peanuts, ...} do not include any additional text in your response." )

print(response2.text)