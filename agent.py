from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage
import base64
import os
from pydantic import BaseModel

class ParlayLeg(BaseModel):
    fighter1: str
    fighter2: str
    bet: str

class ParlayResult(BaseModel):
    legs: list[ParlayLeg]

_ollama_host = os.getenv("OLLAMA_HOST", "http://localhost:11434")

ocr_model = ChatOllama(
    model="llama3.2-vision",
    base_url=_ollama_host,
    temperature=0,
    max_tokens=2000,
    timeout=30,
)

model = ChatOllama(
    model="llama3.2-vision",
    base_url=_ollama_host,
    temperature=0,
    max_tokens=1000,
    timeout=30,
).with_structured_output(ParlayResult)

system_prompt = """You are an agent that extracts data from UFC Parlay screenshots.

You MUST return ONLY a JSON object with a single key "legs" containing an array of all parlay legs found in the image.

In addition, here are the bet types, with definitions, use these to classify the legs bets in the 'bet' key:
- Moneyline (Match Winner): Simply picking which fighter will win the fight.
- Method of Victory: Predicting exactly how a fighter will win (e.g., KO/TKO, Submission, or Decision).
- Total Rounds (Over/Under): Betting on whether the fight will last over or under a specific number of rounds (e.g., Over 1.5 rounds, Under 2.5 rounds).
- Inside the Distance (ITD): A bet that the fight will end by finish (KO/TKO or Submission) and not go to the judge's scorecards.
- Goes The Distance (GTD): A bet that the fight will last the full scheduled duration.
- Round Betting/Props: Specific props like "Fighter A to win in Round 2" or "Fight to end in Round 1".
- Alternative Total Rounds/Spreads: Betting on different round totals than the main line, such as "Over 0.5 rounds" for a quick finish, or alternative fight lines.
- Same-Game Parlay (SGP) Legs: Combining multiple wagers from a single fight, such as a fighter to win and the fight to go over 1.5 rounds. 

Parlay screenshots can vary in layout, but a common pattern is:
1. Large bold text: the selected fighter's name (fighter1) and odds
2. Smaller text below: the bet type (e.g. "MONEYLINE")
3. Even smaller subtext below that: the full matchup, often in the format "Fighter A v Fighter B" or "Fighter A vs Fighter B", sometimes followed by a time or date

If you see a subtext line with "v" or "vs" between two names, that is the full matchup — use it to identify both fighter1 and fighter2. This is ONE leg, not two. Do not create a separate leg for fighter2.

Example output format:
{
  "legs": [
    {"fighter1": "Bryan Battle", "fighter2": "NA", "bet": "Moneyline"},
    {"fighter1": "Marina Rodriguez", "fighter2": "Jessica Andrade", "bet": "Moneyline"}
  ]
}

Rules:
- Include ALL legs visible in the image in the "legs" array. A "Fighter A v Fighter B" subtext line is part of one leg — do NOT create a separate leg for the second fighter.
- ONLY extract text that is explicitly visible in the image. Do NOT guess, infer, or hallucinate any names or values.
- If a fighter name or any field is not clearly visible in the image, use "NA". It is better to use "NA" than to guess.
- Many parlay legs show only one fighter — if fighter2 is not explicitly written in the image, use "NA".
- Ignore betting odds entirely. Always set "betting_odds" to "NA".
- Do not include any text before or after the JSON object.
"""

def encode_image(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode('utf-8')

def extract_parlay(image_path):
    base64_image = encode_image(image_path)
    image_content = {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}

    # Step 1: read every line of text from the image
    ocr_response = ocr_model.invoke([
        HumanMessage(content=[
            {"type": "text", "text": "Read every single line of text visible in this image exactly as written. Do not skip any text, including small or faint text. Pay special attention to small subtext lines that appear below bet type labels — these often contain the full matchup in the format 'Fighter A v Fighter B' or 'Fighter A vs Fighter B' and must be included."},
            image_content
        ])
    ])

    # Step 2: parse the raw text into structured format (no vision needed)
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=f"Extract the parlay legs from this text:\n\n{ocr_response.content}")
    ])
    return response

# test = extract_parlay(r"C:\Users\aycja\git repos\UFC_Parlay_Predictor\parlayscreenshot_test.png")
# print(test)
# Usage: pass a local image path
# result = extract_parlay("screenshot.jpg")
# print(result)