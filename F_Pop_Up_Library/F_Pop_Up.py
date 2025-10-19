import os

def run_chat_gpt_home():
    os.system("python Chat_Gpt_Home.py")

global _score 
_score = 0

while True:
    run_chat_gpt_home()
    again = input("Did you know this fact already!? (yes/no): ").strip().lower()
    if again == "no":
        _score +=1
        break
