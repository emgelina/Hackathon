from openai import OpenAI

client = OpenAI(
  api_key="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"
)

response = client.responses.create(
  model="gpt-4o",
  input="write a really random statistical obscure fact about an obscure food allergy. keep it short and sassy because i dont know the fact",
  store=True,
)

print(response.output_text)