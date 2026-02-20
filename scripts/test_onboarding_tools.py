import asyncio
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# Mock the dependencies
mock_websocket = AsyncMock()
mock_realtime_client = AsyncMock()
mock_realtime_client.enabled = True
mock_realtime_client.sessions = {}

# Use patch to inject mocks
async def test_tool_parsing_v2():
    from src.api.routes.onboarding_realtime import onboarding_realtime
    
    print("Starting verification test for Onboarding Spec v2...")
    
    # 1. Setup mocks
    mock_ws_connection = AsyncMock()
    mock_realtime_client.sessions = MagicMock()
    mock_realtime_client.sessions.get.return_value = mock_ws_connection
    
    # Define a sequence of events from the realtime API
    events = [
        # 1. Profile update tool call (Page 1)
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "name": "update_profile",
                "call_id": "call_1",
                "arguments": json.dumps({"field_name": "company_name", "value": "KratorAI"})
            }
        },
        # 2. Status update tool call (Page 1)
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "name": "update_onboarding_status",
                "call_id": "call_2",
                "arguments": json.dumps({
                    "page_completed": False,
                    "highlight_fields": ["industry"],
                    "missing_required_fields": ["industry", "team_size"],
                    "suggested_options": ["Tech", "Design", "Retail"]
                })
            }
        },
        # 3. Profile update for Page 3 (Tags)
        {
            "type": "response.output_item.done",
            "item": {
                "type": "function_call",
                "name": "update_profile",
                "call_id": "call_3",
                "arguments": json.dumps({"field_name": "target_audience_tags", "value": "[\"Gen Z\", \"Founders\"]"})
            }
        },
        # 4. Farewell
        {
            "type": "response.audio_transcript.done",
            "transcript": "Perfect. Welcome aboard KratorAI"
        }
    ]
    
    # Mock the listen iterator
    async def mock_listen(session_id):
        for event in events:
            yield event
            
    mock_realtime_client.listen = mock_listen
    
    with patch("src.api.routes.onboarding_realtime.get_realtime_client", return_value=mock_realtime_client):
        # We need to mock websocket.receive_json to stop after one loop
        mock_websocket.receive_json.side_effect = ["Stop loop"] # Doesn't matter, it's a list but we check exception
        
        try:
            # We need to make gather return or the test hangs
            # But the client_to_server will hang on receive_json
            # Let's mock receive_json to raise an exception that we catch
            mock_websocket.receive_json.side_effect = Exception("End Test")
            await onboarding_realtime(mock_websocket)
        except Exception as e:
            if str(e) != "End Test":
                print(f"Unexpected error: {e}")

    # 2. Verify results
    sent_messages = [call.args[0] for call in mock_websocket.send_json.call_args_list]
    
    # Check onboarding.update events
    updates = [m for m in sent_messages if m.get("type") == "onboarding.update"]
    assert len(updates) >= 2
    
    # Check first update contains company_name
    assert updates[0]["prefill_fields"]["company_name"] == "KratorAI"
    print("✅ Real-time field extraction verified (company_name)")
    
    # Check status update
    status_update = updates[1]
    assert status_update["page_completed"] is False
    assert "industry" in status_update["highlight_fields"]
    assert "industry" in status_update["missing_required_fields"]
    assert "Tech" in status_update["suggested_options"]
    print("✅ UI Status update verified (highlights/missing fields)")
    
    # Check tag extraction (Page 3)
    assert updates[2]["prefill_fields"]["target_audience_tags"] == '["Gen Z", "Founders"]'
    print("✅ Tag extraction verified")
    
    # Check completion
    assert any(m.get("type") == "onboarding.complete" for m in sent_messages)
    print("✅ Final completion event verified")
    
    print("\nVerification successful! Onboarding Spec v2 is correctly implemented.")

if __name__ == "__main__":
    asyncio.run(test_tool_parsing_v2())
