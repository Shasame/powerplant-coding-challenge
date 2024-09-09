from bottle import Bottle, request, response
from pydantic import BaseModel, ValidationError, Field
import json, math

app = Bottle()

class Fuel(BaseModel):
    gas: float = Field(alias="gas(euro/MWh)")
    kerosine: float = Field(alias="kerosine(euro/MWh)")
    co2: float = Field(alias="co2(euro/ton)")
    wind: float = Field(alias="wind(%)")

class PowerPlant(BaseModel):
    name: str
    type: str
    efficiency: float
    pmin: float
    pmax: float

class InputData(BaseModel):
    load: float
    fuels: Fuel
    powerplants: list[PowerPlant]


def calculateCost(plant, fuels):
    match plant.type:
        case "windturbine":
            return 0
        case "gasfired":
            return fuels.gas / plant.efficiency
        case "turbojet":
            return fuels.kerosine / plant.efficiency
        case _:
            response.status = 400
            return json.dumps({'message': 'Invalid powerplant type'})

def createMeritOrder(powerplants, fuels):
    powerplants.sort(key=lambda plant: calculateCost(plant, fuels))
    return powerplants

def adjustWindPmax(powerplants, fuels):
    for plant in powerplants:
        if plant.type == "windturbine":
            plant.pmax = plant.pmax * (fuels.wind / 100)
    return powerplants

def alocatePowerProduction(powerplants, load):
    power_allocation = []
    remaining_load = load

    for plant in powerplants:
        allocated = 0
        if remaining_load <= 0 or plant.pmin > remaining_load:
            allocated = 0
        elif plant.pmin == remaining_load:
            allocated = plant.pmin
        else:
            allocated = min(plant.pmax, remaining_load)
        
        allocated = math.floor(allocated*10) / 10.0
        power_allocation.append({'name': plant.name, 'p': allocated, 'pmax': plant.pmax, 'pmin': plant.pmin})
        remaining_load -= allocated
    
    # ldiff = load - sum([plant['p'] for plant in power_allocation])
    # if ldiff != 0:
    #     for i in range(len(power_allocation)):
    #         for j in range(i+1, len(power_allocation)):
    #             if power_allocation[i]['p'] == power_allocation[i]['pmax'] and power_allocation[j]['p'] < power_allocation[j]['pmax']:
    #                 diff = min(ldiff, power_allocation[i]['pmax'] - power_allocation[i]['p'])
    #                 power_allocation[i]['p'] += diff
    #                 ldiff -= diff
    #                 if ldiff == 0:
    #                     break
    #             elif power_allocation[i]['p'] > power_allocation[i]['pmin'] and power_allocation[j]['p'] < power_allocation[j]['pmax']:
    #                 diff = max(ldiff, power_allocation[i]['pmin'] - power_allocation[i]['p'])
    #                 power_allocation[i]['p'] += diff
    #                 ldiff -= diff
    #                 if ldiff == 0:
    #                     break

    return power_allocation


@app.post('/productionplan')
def productionPlan():
    try:
        input_data = InputData(**request.json)
    except ValidationError as e:
        response.status = 400
        response.content_type = 'application/json'
        return json.dumps({'message': e.errors()})
    
    orderdPlants = createMeritOrder(input_data.powerplants, input_data.fuels)
    adjustedPlants = adjustWindPmax(orderdPlants, input_data.fuels)
    power_allocation = alocatePowerProduction(adjustedPlants, input_data.load)
    response.status = 200
    response.content_type = 'application/json'
    return json.dumps(power_allocation)

if __name__ == '__main__' :
    app.run(host='0.0.0.0', port=8888)