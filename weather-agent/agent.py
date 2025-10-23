import os
import random
from datetime import date, datetime, timedelta
from typing import Type

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import BaseTool
from dotenv import load_dotenv
from pydantic import BaseModel, Field

load_dotenv()

import os
import json

class WeatherToolInput(BaseModel):
    date: str = Field(
        ...,
        description="The date check for weather e.g., '2024-07-28' or '2024-07-28"
    )

class WeatherTool(BaseTool):
    name: str = "Weather Tool"
    description: str = (
        "Checks weather for a given date"
    )
    args_schema: Type[BaseModel] = WeatherToolInput

    def _run(self, date: str) -> str:
        try:
            script_dir = os.path.dirname(os.path.abspath(__file__))
            file_path = os.path.join(script_dir, "weather_data.json")
            
            with open(file_path, "r") as file:
                data = json.load(file)
            
            weather_data = [d for d in data if d["date"] == date]

            return weather_data.pop() if weather_data else {"error": "No data found for the given date."}
        except ValueError:
            return (
                "I couldn't understand the date. "
                "Please ask to check availability for a date like 'YYYY-MM-DD'."
            )

class WeatherAgent:

    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    def __init__(self):
        self.llm = LLM(
            model="gemini/gemini-2.0-flash",
            api_key=os.getenv("GOOGLE_API_KEY")
        )
        
        self.weather_agent = Agent(
            role="Weather",
            goal="Fetch weather for a given date.",
            backstory=(
                "You are a highly efficient and polite assistant. Your only job is "
                "to fetch the weather. You are an expert at using the "
                "WeatherTool to fetch weather data for specified date in format YYYY-MM-DD"
            ),
            verbose=True,
            allow_delegation=False,
            tools=[WeatherTool()],
            llm = self.llm
        )
    
    def invoke(self, question: str) -> str:
        task_description = (
            f"Answer the user's question weather. The user asked: '{question}'. "
            f"Today's date is {date.today().strftime('%Y-%m-%d')}."
        )

        check_availability_task = Task(
            description=task_description,
            agent=self.weather_agent,
            expected_output="A polite and concise answer to the user's question about weather based on the weather tool's output.",
        )

        crew = Crew(
            agents=[self.weather_agent],
            tasks=[check_availability_task],
            process=Process.sequential,
            verbose=True
        )
        result = crew.kickoff()
        return str(result)