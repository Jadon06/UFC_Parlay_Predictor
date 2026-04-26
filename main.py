from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from agent import encode_image, extract_parlay
from predictions import get_fighters

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
import os
import tempfile

from agent import ParlayLeg
import joblib

from Data_Extraction_and_Cleaning import FighterInfo

from pydantic import BaseModel
from typing import Literal, List
import math
import numpy as np

app = FastAPI()
# NOTE - change to cloud based LLM in order to fix error
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ufc-parlay-predictor.vercel.app", "http://localhost:5173"],
    allow_credentials=True,           # Allow cookies/auth headers
    allow_methods=["*"],              # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],              # Allow all request headers
)

class modelReturn(BaseModel):
    model_name: List[Literal['ufc_outcome_model.pkl', 'ufc_round_prediction_model.pkl', 'ufc_WL_model.pkl']]

model = ChatAnthropic(
    model="claude-haiku-4-5-20251001",
    temperature=0,
    max_tokens=1000,
).with_structured_output(modelReturn)

system_prompt = """ You are an agent tasked with deciding which machine learning model is best to use for each leg in a parlay.
                A parlay leg is defined by the class ParlayLeg, which has been imported to this file. You will also be given an
                extracted parlay, following the Parlay schema. Use the 'bet' key's content to decide which of the following models
                to use.
                Your options are the following:
                    1. 'ufc_outcome_model.pkl' -> This model is best for predicting the method of victory for a given fight
                    2. 'ufc_round_prediction_model.pkl' -> This model is best for predicting the round the fight ends on which can be from 1-5
                    3. 'ufc_WL_model.pkl' -> This model is best for predicting win loss probability for a given fighter
                
                Return your choice for each leg of the parlay in a list.
                """

def load_models():
    features = {
        "ufc_outcome_model.pkl" : "ufc_outcome_features.pkl",
        "ufc_round_prediction_model.pkl" : "ufc_round_predictions_features.pkl",
        "ufc_WL_model.pkl" : "ufc_WL_features.pkl"
    }
    model = joblib.load(model)
    features = joblib.load(features[model])

    models = []
    for model, feature in features:
        models.append((model, feature))
        if model == "ufc_outcome_model.pkl":
            le = joblib.load("label_encoder.pkl")
            models.append((model, feature, le))
    return models

"""
probabilities translation:
- 0.50 → coin flip
- 0.60 → slight edge
- 0.70 → strong favorite
- 0.80+ → dominant mismatch
"""

class predictionsReturn(BaseModel):
    probability: float
    weakest_leg: ParlayLeg
    strongest_leg: ParlayLeg

def classify_bet(bet: str):
    text = bet.lower()
    if any(k in text for k in [
        "ko", "tko", "knockout", "technical knockout",
        "submission", "sub", "tap", "tapout",
        "choke", "rear naked", "rnc", "armbar", "triangle",
        "guillotine", "kimura", "americana", "heel hook",
        "kneebar", "darce", "d'arce", "anaconda", "calf slicer",
        "neck crank", "technical submission", "tsub",
        "decision", "dec", "unanimous", "split", "majority",
        "finish", "stoppage", "disqualification", "dq",
        "no contest", "nc", "doctor stoppage", "corner stoppage",
        "method",
    ]):
        return "method"
    if any(k in text for k in [
        "round", "r1", "r2", "r3", "r4", "r5",
        "1st round", "2nd round", "3rd round", "4th round", "5th round",
        "first round", "second round", "third round", "fourth round", "fifth round",
        "inside the distance", "itd",
        "goes the distance", "gtd", "distance",
        "over 1.5", "over 2.5", "over 3.5", "over 4.5",
        "under 1.5", "under 2.5", "under 3.5", "under 4.5",
        "ends in", "fight time", "total rounds",
    ]):
        return "round"
    if any(k in text for k in [
        "moneyline", "ml",
        "to win", "to beat", "to defeat",
        "wins", "beats", "defeats",
        "winner", "victory",
        "favorite", "underdog", "dog",
        "straight up", "outright",
    ]):
        return "wl"

@app.post("/predict", response_model=predictionsReturn)
async def predict(image: UploadFile = File(...)):
    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await image.read())
        tmp_path = tmp.name
    try:
        extracted_parlay = extract_parlay(tmp_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        os.unlink(tmp_path)
    fighters = get_fighters(extracted_parlay)
    bet_types = [classify_bet(leg["bet"]) for leg in extracted_parlay]

    models = load_models()
    outcomes_model = models[0][0]
    outcomes_features = models[0][1]
    le = models[0][2]
    round_model = models[1][0]
    round_features = models[1][1]
    wl_model = models[2][0]
    wl_features = models[2][1]

    probabilities = []
    for i in range(len(bet_types)):
        if bet_types[i] == "method":
            new_fight = fighters[i][outcomes_features]
            probs = outcomes_model.predict_proba(new_fight)[0]
            result = dict(zip(le.classes_, probs))
            probabilities.append(result[extracted_parlay[i]['method']])
        if bet_types[i] == "round":
            new_fight = fighters[i][round_features]
            probs = round_model.predict_proba(new_fight)[extracted_parlay["round"]]
            probabilities.append(probs)
        if bet_types[i] == "wl":
            new_fight = fighters[i][wl_features]
            probs = wl_model.predict_proba(new_fight)[1]
            probabilities.append(probs)
    
    legs_probs = dict(zip(probabilities, extracted_parlay))
    probability = math.prod(probabilities)
    weakest_leg = legs_probs[min(probabilities)]
    strongest_leg = legs_probs[max(probabilities)]

    # new_fight = new_fight[features]

    # prob = model.predict_proba(new_fight)[0][1]

    # print(prob)
    return {"probability": probability, "weakest_leg": weakest_leg, "strongest_leg": strongest_leg}

