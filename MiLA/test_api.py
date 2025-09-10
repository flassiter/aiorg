"""
Simple API integration test script.
"""
import asyncio
import httpx
import time
from pathlib import Path


async def test_api():
    """Test the API endpoints."""
    # Start the server manually or assume it's running
    base_url = "http://localhost:8000"
    
    async with httpx.AsyncClient() as client:
        try:
            # Test health check
            print("Testing health check...")
            response = await client.get(f"{base_url}/api/health")
            print(f"Health check status: {response.status_code}")
            print(f"Health check response: {response.json()}")
            
            # Test authentication
            print("\nTesting authentication...")
            auth_data = {
                "username": "loan_agent",
                "password": "agent123"
            }
            response = await client.post(f"{base_url}/api/auth/login", json=auth_data)
            print(f"Login status: {response.status_code}")
            auth_response = response.json()
            print(f"Login response: {auth_response}")
            
            if auth_response.get("success"):
                api_key = auth_response["api_key"]
                headers = {"Authorization": f"Bearer {api_key}"}
                
                # Test data info
                print("\nTesting data info...")
                response = await client.get(f"{base_url}/api/admin/data-info", headers=headers)
                print(f"Data info status: {response.status_code}")
                print(f"Data info response: {response.json()}")
                
                # Test loan search
                print("\nTesting loan search (if data is loaded)...")
                response = await client.get(f"{base_url}/api/loan/123456", headers=headers)
                print(f"Loan search status: {response.status_code}")
                print(f"Loan search response: {response.json()}")
                
                # Test user info
                print("\nTesting user info...")
                response = await client.get(f"{base_url}/api/user/info", headers=headers)
                print(f"User info status: {response.status_code}")
                print(f"User info response: {response.json()}")
                
        except httpx.ConnectError:
            print("API server is not running. Start it with:")
            print("uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(test_api())