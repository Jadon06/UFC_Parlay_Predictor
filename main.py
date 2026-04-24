from fastapi import FastAPI
from agent import encode_image, extract_parlay
from predictions import get_fighter_data

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage, SystemMessage

from agent import ParlayLeg
app = FastAPI()

model = ChatOllama(
    model="qwen3",
    temperature=0,
    max_tokens=1000,
    timeout=30,
)

System_Prompt = """ You are an agent tasked with deciding which machine learning model is best ot use for each leg in a parlay.
                A parlay leg is defined by the class ParlayLeg, which has been imported to this file.
                You can choose which model you find best fits the context of the parlay leg in the models folder
                """

@app.post("/")
async def predict(parlay: str):
    extracted_parlay = extract_parlay(parlay)
    parlay_data = get_fighter_data(extracted_parlay)
    """
    probabilities translation:
        - 0.50 → coin flip
        - 0.60 → slight edge
        - 0.70 → strong favorite
        - 0.80+ → dominant mismatch
    """
    # Classify Parlays

    # new_fight = new_fight[features]

    # prob = model.predict_proba(new_fight)[0][1]

    # print(prob)
    return

