"""
Simple script to test the KratorAI Agent locally.
"""

import requests
import json
import sys
import time

BASE_URL = "http://localhost:8000"

def print_step(step):
    print(f"\n{'='*50}")
    print(f"--- {step}")
    print(f"{'='*50}")

def test_health():
    print_step("Checking API Health")
    try:
        response = requests.get(f"{BASE_URL}/health")
        if response.status_code == 200:
            print("API is online")
            return True
        else:
            print(f"API returned status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("Could not connect to API. Is the server running?")
        return False

def test_agent_flow():
    # 1. Create Session
    print_step("Creating Agent Session")
    try:
        response = requests.post(f"{BASE_URL}/agent/session")
        response.raise_for_status()
        session_data = response.json()
        session_id = session_data["session_id"]
        print(f"Session created: {session_id}")
    except Exception as e:
        print(f"Failed to create session: {e}")
        return

    # 2. Send Chat Message
    print_step("Sending Chat Message")
    message = "Hi, I need a professional headshot for my LinkedIn profile. Can you help?"
    print(f"Sending: '{message}'")
    
    payload = {
        "session_id": session_id,
        "message": message
    }
    
    try:
        start_time = time.time()
        response = requests.post(f"{BASE_URL}/agent/chat", json=payload)
        response.raise_for_status()
        duration = time.time() - start_time
        
        data = response.json()
        print(f"Response received in {duration:.2f}s")
        print(f"Agent: {data['message']}")
        
        if data.get("tool_calls"):
            print("\nTools Used:")
            for tool in data["tool_calls"]:
                print(f"   - {tool['name']}: {tool['args']}")
                
    except Exception as e:
        print(f"Chat failed: {e}")

if __name__ == "__main__":
    print("Starting Local Agent Test")
    if test_health():
        test_agent_flow()
    else:
        print("\nPlease start the server first:")
        print("   uvicorn src.api.main:app --reload")
