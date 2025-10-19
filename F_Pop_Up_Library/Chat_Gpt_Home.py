from openai import OpenAI

client = OpenAI(
  api_key=""
)

response = client.responses.create(
  model="gpt-4o",
  input="write a really random statistical obscure fact about an obscure food allergy. keep it short and sassy because i dont know the fact",
  store=True,
)

print(response.output_text)
