from agent import ParlayResult
from Data_Extraction_and_Cleaning import FighterInfo
from typing import List
import asyncio
from concurrent.futures import ThreadPoolExecutor

""" Get Fighter Data After Extraction From API Call, May take a while """
def get_fighters(parlay: ParlayResult):
    fighters = []
    for leg in parlay.legs:
        fighters.append((leg.fighter1, leg.fighter2))
    return fighters

executor = ThreadPoolExecutor(max_workers=2)

async def get_fighter_data(fighters: List):
    fighter_data = []
    loop = asyncio.get_event_loop()
    for fighter in fighters:
        data1, data2 = await asyncio.gather(
            loop.run_in_executor(executor, FighterInfo, fighter[0]),
            loop.run_in_executor(executor, FighterInfo, fighter[1])
        )
        if data2 is None:
            fighter_data.append((data1.run_all()))
        else:
            fighter_data.append((data1.run_all(), data2.run_all()))
    return fighter_data

""" classify parlay type """
