import google.generativeai as genai
import os
from typing import List

# Configure API Key
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

def generate_macro_plan(athlete_profile: str, a_race: str, priorities: str, athlete_context: dict, weeks_to_race: int):
    """Generates a high-level periodized training block leading up to the A-Race."""
    
    model = genai.GenerativeModel('gemini-2.5-flash') 
    
    prompt = f"""
    You are an elite triathlon coach. Create a {weeks_to_race}-week high-level macro plan leading up to the athlete's A-Race.
    
    Athlete Profile: {athlete_profile}
    A-Race/Main Goal: {a_race}
    Key Training Priorities: {priorities}
    
    Current Biological Baseline:
    - FTP: {athlete_context.get('ftp', 'Unknown')} W
    - LTHR: {athlete_context.get('lthr', 'Unknown')} bpm
    - Current Fitness (CTL): {athlete_context.get('fitness', 0)}
    
    Requirements:
    - Apply progressive overload (building TSS).
    - Include recovery weeks (lower TSS) every 3-4 weeks.
    - End with a proper Taper phase.
    
    CRITICAL INSTRUCTION: You must return ONLY raw, valid JSON. Do not include markdown blocks, greetings, or explanations. 
    
    Use this EXACT JSON schema:
    {{
      "plan": [
        {{
          "week_number": 1,
          "phase": "Base",
          "focus": "Aerobic endurance",
          "target_tss": 350
        }}
      ]
    }}
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.2}
    )
    return response.text

def generate_micro_plan(athlete_context: dict, macro_week_focus: str, macro_week_tss: int, week_dates: List[str]):
    """Generates specific daily workouts for a 7-day period aligned with the macro goal."""
    
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    You are an elite triathlon coach. Generate a 7-day training plan.
    
    Biological Baseline:
    - FTP: {athlete_context.get('ftp', 'Unknown')} W
    - LTHR: {athlete_context.get('lthr', 'Unknown')} bpm
    - Current Fitness (CTL): {athlete_context.get('fitness', 0)}
    - Current Fatigue (ATL): {athlete_context.get('fatigue', 0)}
    
    This Week's Goal:
    - Phase/Focus: {macro_week_focus}
    - Target Total TSS: ~{macro_week_tss}
    
    Requirements:
    - Provide exactly 7 entries using these EXACT dates in order: {week_dates}.
    - Include Swim, Ride, Run, Strength, and Mobility.
    - Factor in at least 1 Rest day.
    - NEW STRICT RULE: The `description` field MUST be structured into specific sets (e.g., Warm-up, Main Set, Cool-down). 
    - For EVERY active segment in the description, explicitly state the target intensity utilizing the provided Biological Baseline. Output approximate HR Zones, exact BPM targets based on the LTHR ({athlete_context.get('lthr', 'Unknown')} bpm), and exact Power targets based on the FTP ({athlete_context.get('ftp', 'Unknown')} W).
    
    CRITICAL INSTRUCTION: You must return ONLY raw, valid JSON. Do not include markdown blocks, greetings, or explanations.
    
    Use this EXACT JSON schema:
    {{
      "workouts": [
        {{
          "date": "YYYY-MM-DD",
          "type": "Ride",
          "title": "Zone 2 Endurance",
          "duration": 90,
          "trainingLoad": 65,
          "description": "Warm-up: 15m steady ramp.\nMain Set: 60m @ 180W (Zone 2, ~135 bpm).\nCool-down: 15m easy spin."
        }}
      ]
    }}
    """
    
    response = model.generate_content(
        prompt,
        generation_config={"temperature": 0.4}
    )
    return response.text


async def stream_chat_response(messages_history: list, system_prompt: str):
    """Streams the response from Gemini for the interactive coach chat."""
    
    # Pointing to the currently active model endpoint
    model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_prompt)
    
    formatted_history = []
    for msg in messages_history:
        role = "user" if msg.role == "user" else "model"
        formatted_history.append({"role": role, "parts": [msg.content]})
        
    chat = model.start_chat(history=formatted_history[:-1]) 
    
    latest_message = messages_history[-1].content
    response = chat.sendMessageStream(latest_message)
    
    for chunk in response:
        yield f"data: {chunk.text}\n\n"