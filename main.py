from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from agent import encode_image, extract_parlay
from predictions import get_fighters

from langchain_ollama import ChatOllama
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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://ufc-parlay-predictor.vercel.app", "http://localhost:5173"],
    allow_credentials=True,           # Allow cookies/auth headers
    allow_methods=["*"],              # Allow all HTTP methods (GET, POST, etc.)
    allow_headers=["*"],              # Allow all request headers
)

class modelReturn(BaseModel):
    model_name: List[Literal['ufc_outcome_model.pkl', 'ufc_round_prediction_model.pkl', 'ufc_WL_model.pkl']]

model = ChatOllama(
    model="qwen3",
    base_url=os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    temperature=0,
    max_tokens=1000,
    timeout=30,
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

@app.post("/predict", response_model=predictionsReturn)
async def predict(image: UploadFile = File(...)):
    suffix = os.path.splitext(image.filename or "")[1] or ".jpg"
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await image.read())
        tmp_path = tmp.name
    try:
        extracted_parlay = extract_parlay(tmp_path)
    finally:
        os.unlink(tmp_path)
    fighters = get_fighters(extracted_parlay)

    models = load_models()

    # choose and load models
    response = model.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content="Choose the predictive models based on the extracted parlay, models have been loaded as a list of tuples in this format (model, feature, le) 'le' only exists for ufc_outcome_model.pkl")
    ])

    to_predict = dict(zip(response, fighters))

    probabilities = []
    

    legs_probs = dict(zip(probabilities, extracted_parlay))
    probability = math.prod(probabilities)
    weakest_leg = legs_probs[min(probabilities)]
    strongest_leg = legs_probs[max(probabilities)]

    # new_fight = new_fight[features]

    # prob = model.predict_proba(new_fight)[0][1]

    # print(prob)
    return {"probability": probability, "weakest_leg": weakest_leg, "strongest_leg": strongest_leg}

