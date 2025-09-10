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
            
            # Test data info (no authentication required)
            print("\nTesting data info...")
            response = await client.get(f"{base_url}/api/admin/data-info")
            print(f"Data info status: {response.status_code}")
            print(f"Data info response: {response.json()}")
            
            # Test loan search (no authentication required)
            print("\nTesting loan search (if data is loaded)...")
            response = await client.get(f"{base_url}/api/loan/123456")
            print(f"Loan search status: {response.status_code}")
            print(f"Loan search response: {response.json()}")
            
            # Test available tools
            print("\nTesting available tools...")
            response = await client.get(f"{base_url}/api/tools/available")
            print(f"Tools status: {response.status_code}")
            print(f"Tools response: {response.json()}")
            
            # Test tools health
            print("\nTesting tools health...")
            response = await client.get(f"{base_url}/api/tools/health")
            print(f"Tools health status: {response.status_code}")
            print(f"Tools health response: {response.json()}")
                
        except httpx.ConnectError:
            print("API server is not running. Start it with:")
            print("uvicorn src.main:app --reload --host 0.0.0.0 --port 8000")


if __name__ == "__main__":
    asyncio.run(test_api())