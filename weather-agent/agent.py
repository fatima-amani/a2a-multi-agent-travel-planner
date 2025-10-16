from fastapi import FastAPI
import uvicorn


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello Weather Agent"}

# agent card
@app.get("/.well-known/agent-card.json")
def get_agent_card():
    return {
        "name": "Weather Agent",
        "description": "Provides weather data for a given date.",
        "endpoints": {
            "get_weather": {
                "path": "/weather/{date}",
                "method": "GET",
                "description": "Get weather data for the specified date."
            }
        }
    }

@app.get("/weather/{date}")
def get_weather(date: str):
    from service import get_weather_data
    return get_weather_data(date)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)