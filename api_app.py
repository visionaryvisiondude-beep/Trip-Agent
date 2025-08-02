# main_app.py

# Standard Library Imports
import os
import json
from datetime import date, datetime
from typing import Optional, Type
from textwrap import dedent
from functools import lru_cache

# Third-Party Imports
import requests
from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from unstructured.partition.html import partition_html

# CrewAI Imports (using LLM class as requested)
from crewai import Agent, Task, Crew, LLM
from crewai.tools import BaseTool

# --- Load Environment Variables ---
# Ensure a .env file exists with:
# GEMINI_API_KEY, SERPER_API_KEY, BROWSERLESS_API_KEY
load_dotenv()

# --- Custom Tool Definitions ---

class CalculationInput(BaseModel):
    operation: str = Field(..., description="The mathematical expression to evaluate")

class CalculatorTools(BaseTool):
    name: str = "Make a calculation"
    description: str = """Useful to perform any mathematical calculations, 
    like sum, minus, multiplication, division, etc.
    The input should be a mathematical expression, e.g. '200*7' or '5000/2*10'"""
    args_schema: Type[BaseModel] = CalculationInput

    def _run(self, operation: str) -> str:
        try:
            return f"The result is {eval(operation)}"
        except Exception as e:
            return f"Error performing calculation: {e}"

class SearchQuery(BaseModel):
    query: str = Field(..., description="The search query to look up")

class SearchTools(BaseTool):
    name: str = "Search the internet"
    description: str = "Useful to search the internet about a given topic and return relevant results"
    args_schema: Type[BaseModel] = SearchQuery

    def _run(self, query: str) -> str:
        try:
            url = "https://google.serper.dev/search"
            payload = json.dumps({"q": query})
            headers = {
                'X-API-KEY': os.getenv('SERPER_API_KEY'),
                'content-type': 'application/json'
            }
            response = requests.request("POST", url, headers=headers, data=payload)
            
            if response.status_code != 200:
                return f"Error: Search API request failed. Status: {response.status_code}"
            
            data = response.json().get('organic', [])
            if not data:
                return "No results found."
            
            strings = []
            for result in data[:4]:
                strings.append('\n'.join([
                    f"Title: {result.get('title', 'N/A')}",
                    f"Link: {result.get('link', 'N/A')}",
                    f"Snippet: {result.get('snippet', 'N/A')}",
                    "-----------------"
                ]))
            return '\n'.join(strings)
        except Exception as e:
            return f"Error during search: {e}"

class WebsiteInput(BaseModel):
    website_url: str = Field(..., description="The website URL to scrape")

class BrowserTools(BaseTool):
    name: str = "Scrape website content"
    description: str = "Useful to scrape and summarize a website's content"
    args_schema: Type[BaseModel] = WebsiteInput

    def _run(self, website_url: str) -> str:
        try:
            url = f"https://chrome.browserless.io/content?token={os.getenv('BROWSERLESS_API_KEY')}"
            payload = json.dumps({"url": website_url})
            headers = {'cache-control': 'no-cache', 'content-type': 'application/json'}
            response = requests.post(url, headers=headers, data=payload)

            if response.status_code != 200:
                return f"Error fetching website. Status: {response.status_code} {response.text}"

            elements = partition_html(text=response.text)
            content = "\n\n".join([str(el) for el in elements])
            chunks = [content[i:i + 8000] for i in range(0, len(content), 8000)]
            summaries = []

            # Using the LLM class as requested
            summarizer_llm = LLM(model="gemini/gemini-2.0-flash")

            summarizer_agent = Agent(
                role='Principal Researcher',
                goal='Provide concise and relevant summaries of text content.',
                backstory="You are an expert researcher, skilled at extracting the most important information from any text.",
                allow_delegation=False,
                llm=summarizer_llm
            )

            for chunk in chunks:
                task = Task(
                    description=f'Analyze and summarize the following content. Focus on the most relevant information. Return only the summary.\n\nCONTENT:\n{chunk}',
                    expected_output='A concise summary of the provided text.',
                    agent=summarizer_agent
                )
                summary = task.execute()
                summaries.append(summary)
            
            return "\n\n".join(summaries)
        except Exception as e:
            return f"Error while processing website: {e}"


# --- Agent Definitions ---

class TripAgents:
    def __init__(self):
        # Using the LLM class as requested
        self.llm = LLM(model="gemini/gemini-2.0-flash")

    def city_selection_agent(self) -> Agent:
        return Agent(
            role='City Selection Expert',
            goal='Select the best city for a trip based on weather, season, and prices.',
            backstory='An expert in analyzing travel data to pick ideal destinations.',
            tools=[SearchTools(), BrowserTools()],
            allow_delegation=False, llm=self.llm, verbose=True
        )

    def local_expert(self) -> Agent:
        return Agent(
            role='Local Expert',
            goal='Provide the best local insights for a given city.',
            backstory="A knowledgeable local guide with extensive information about the city's attractions, customs, and hidden gems.",
            tools=[SearchTools(), BrowserTools()],
            allow_delegation=False, llm=self.llm, verbose=True
        )

    def travel_concierge(self) -> Agent:
        return Agent(
            role='Amazing Travel Concierge',
            goal='Create a detailed, personalized travel itinerary with budget and packing suggestions.',
            backstory='A specialist in travel planning with decades of experience creating memorable trips.',
            tools=[SearchTools(), BrowserTools(), CalculatorTools()],
            allow_delegation=False, llm=self.llm, verbose=True
        )

# --- Task Definitions ---

class TripTasks:
    def __tip_section(self) -> str:
        return "If you do your BEST WORK, I'll tip you $100!"

    def identify_task(self, agent: Agent, origin: str, destination: str, interests: str, date_range: str) -> Task:
        return Task(
            description=dedent(f"""
                Analyze and select the best city for a trip based on the user's criteria.
                While the user suggested {destination}, you can recommend a different city if it's a better fit.
                Your final answer must be a detailed report on the chosen city, including flight costs, weather forecast, and top attractions.
                {self.__tip_section()}
                **Trip Details:**
                - From: {origin}, To: {destination}, Dates: {date_range}, Interests: {interests}
            """),
            expected_output="A detailed report on the chosen city with flight costs, weather, and attractions.",
            agent=agent
        )

    def gather_task(self, agent: Agent, interests: str, date_range: str) -> Task:
        return Task(
            description=dedent(f"""
                Compile an in-depth guide for the city chosen in the previous step.
                Focus on key attractions, local customs, and daily activities matching the traveler's interests. Find hidden gems.
                The final answer must be a comprehensive city guide rich in cultural insights and practical tips.
                {self.__tip_section()}
                **Trip Details:**
                - Dates: {date_range}, Interests: {interests}
            """),
            expected_output="A comprehensive city guide with cultural insights and practical tips.",
            agent=agent
        )

    def plan_task(self, agent: Agent, interests: str, date_range: str) -> Task:
        return Task(
            description=dedent(f"""
                Expand the city guide into a full, day-by-day travel itinerary.
                Include detailed plans, weather forecasts, restaurant recommendations, packing suggestions, and a complete budget breakdown.
                You MUST suggest actual places, hotels, and restaurants, explaining why each choice fits the traveler's interests.
                Your final answer MUST be a complete travel plan, formatted as markdown.
                {self.__tip_section()}
                **Trip Details:**
                - Dates: {date_range}, Interests: {interests}
            """),
            expected_output="A complete markdown travel plan with a daily schedule, budget, and packing list.",
            agent=agent
        )

# --- FastAPI Application Setup ---

app = FastAPI(title="VacAIgent API", description="AI-powered travel planning API using CrewAI", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# --- Pydantic Models for API ---

class TripRequest(BaseModel):
    origin: str = Field(..., example="Bangalore, India")
    destination: str = Field(..., example="Krabi, Thailand")
    start_date: date = Field(..., example="2025-09-10")
    end_date: date = Field(..., example="2025-09-20")
    interests: str = Field(..., example="2 adults who love swimming, hiking, local food, and water sports.")

class TripResponse(BaseModel):
    status: str
    message: str
    itinerary: Optional[str] = None
    error: Optional[str] = None

# --- Settings and Dependency Injection ---

class Settings:
    def __init__(self):
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
        self.SERPER_API_KEY = os.getenv("SERPER_API_KEY")
        self.BROWSERLESS_API_KEY = os.getenv("BROWSERLESS_API_KEY")

@lru_cache()
def get_settings():
    return Settings()

def validate_api_keys(settings: Settings = Depends(get_settings)):
    required = {
        'GEMINI_API_KEY': settings.GEMINI_API_KEY,
        'SERPER_API_KEY': settings.SERPER_API_KEY,
        'BROWSERLESS_API_KEY': settings.BROWSERLESS_API_KEY
    }
    missing_keys = [key for key, value in required.items() if not value]
    if missing_keys:
        raise HTTPException(status_code=500, detail=f"Missing API keys: {', '.join(missing_keys)}")
    return settings

# --- Crew Execution Logic ---

class TripCrew:
    def __init__(self, origin: str, destination: str, date_range: str, interests: str):
        self.origin = origin
        self.destination = destination
        self.date_range = date_range
        self.interests = interests

    def run(self) -> str:
        agents = TripAgents()
        tasks = TripTasks()
        city_selector, local_expert, travel_concierge = agents.city_selection_agent(), agents.local_expert(), agents.travel_concierge()
        
        identify_task = tasks.identify_task(city_selector, self.origin, self.destination, self.interests, self.date_range)
        gather_task = tasks.gather_task(local_expert, self.interests, self.date_range)
        plan_task = tasks.plan_task(travel_concierge, self.interests, self.date_range)

        gather_task.context = [identify_task]
        plan_task.context = [gather_task]

        crew = Crew(
            agents=[city_selector, local_expert, travel_concierge], 
            tasks=[identify_task, gather_task, plan_task], 
            verbose=True
        )
        return crew.kickoff()

# --- API Endpoints ---

@app.get("/", summary="Root Endpoint")
async def root():
    return {"message": "Welcome to VacAIgent API", "docs_url": "/docs"}

@app.post("/api/v1/plan-trip", response_model=TripResponse, summary="Generate a Trip Plan")
async def plan_trip(trip_request: TripRequest, settings: Settings = Depends(validate_api_keys)):
    if trip_request.end_date <= trip_request.start_date:
        raise HTTPException(status_code=400, detail="End date must be after start date.")

    date_range = f"{trip_request.start_date.strftime('%B %d, %Y')} to {trip_request.end_date.strftime('%B %d, %Y')}"
    
    try:
        trip_crew = TripCrew(trip_request.origin, trip_request.destination, date_range, trip_request.interests)
        itinerary = trip_crew.run()
        return TripResponse(status="success", message="Trip plan generated successfully.", itinerary=str(itinerary))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate trip plan: {e}")

@app.get("/api/v1/health", summary="Health Check")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# --- Main Execution Block ---

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)