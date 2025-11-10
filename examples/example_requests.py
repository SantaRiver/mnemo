"""Example requests to the NLP service API."""

import asyncio
from datetime import date

import httpx


BASE_URL = "http://localhost:8000"


async def health_check() -> None:
    """Check service health."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Health check: {response.json()}")


async def analyze_simple_text() -> None:
    """Analyze simple text."""
    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 12345,
            "text": "Сходил в зал, потренировался 90 минут",
            "date": str(date.today())
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json=request_data,
            timeout=30.0
        )
        
        result = response.json()
        print(f"\n=== Simple Text Analysis ===")
        print(f"User: {result['user_id']}")
        print(f"Date: {result['date']}")
        print(f"Actions found: {len(result['actions'])}")
        
        for action in result['actions']:
            print(f"\n- {action['action']}")
            print(f"  Category: {action['category']}")
            print(f"  Type: {action['type']}")
            print(f"  Time: {action['estimated_time_minutes']} min ({action['time_source']})")
            print(f"  Points: {action['points']}")
            print(f"  Confidence: {action['confidence']:.2f}")


async def analyze_multiple_actions() -> None:
    """Analyze text with multiple actions."""
    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 12345,
            "text": "Сходил в зал, пожал сотку, приготовил курочку, почитал книгу про математику 2 часа",
            "date": "2025-11-10"
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json=request_data,
            timeout=30.0
        )
        
        result = response.json()
        print(f"\n=== Multiple Actions Analysis ===")
        print(f"Total actions: {len(result['actions'])}")
        print(f"Used LLM: {result['meta']['used_llm']}")
        print(f"Heuristic latency: {result['meta']['heuristic_latency_ms']}ms")
        
        total_points = sum(a['points'] for a in result['actions'])
        print(f"Total points: {total_points}")
        
        for i, action in enumerate(result['actions'], 1):
            print(f"\n{i}. {action['action']}")
            print(f"   {action['category']} → {action['points']} points")


async def analyze_achievement() -> None:
    """Analyze text with achievement."""
    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 12345,
            "text": "Впервые пробежал 10 км без остановок!",
            "date": str(date.today())
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json=request_data,
            timeout=30.0
        )
        
        result = response.json()
        print(f"\n=== Achievement Analysis ===")
        
        for action in result['actions']:
            if action['type'] == 'achievement':
                print(f"Achievement: {action['action']}")
                print(f"Weight: {action['achievement_weight']}")
                print(f"Points: {action['points']}")
                print(f"Confidence: {action['confidence']:.2f}")


async def get_user_stats() -> None:
    """Get user statistics."""
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/v1/stats/12345")
        
        stats = response.json()
        print(f"\n=== User Statistics ===")
        print(f"User ID: {stats['user_id']}")
        print(f"Total templates: {stats['total_templates']}")
        print(f"Total actions: {stats['total_actions']}")


async def analyze_with_explicit_time() -> None:
    """Analyze text with explicit time."""
    async with httpx.AsyncClient() as client:
        request_data = {
            "user_id": 12345,
            "text": "Читал книгу 3 часа, готовил 45 минут, убирался",
            "date": str(date.today())
        }
        
        response = await client.post(
            f"{BASE_URL}/api/v1/analyze",
            json=request_data,
            timeout=30.0
        )
        
        result = response.json()
        print(f"\n=== Explicit Time Analysis ===")
        
        for action in result['actions']:
            print(f"\n- {action['action']}")
            print(f"  Time: {action['estimated_time_minutes']} min")
            print(f"  Source: {action['time_source']}")


async def test_error_handling() -> None:
    """Test error handling."""
    async with httpx.AsyncClient() as client:
        # Invalid user_id
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/analyze",
                json={"user_id": -1, "text": "test"}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"\n=== Error Handling ===")
            print(f"Expected validation error: {e.response.status_code}")
        
        # Empty text
        try:
            response = await client.post(
                f"{BASE_URL}/api/v1/analyze",
                json={"user_id": 1, "text": ""}
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            print(f"Empty text error: {e.response.status_code}")


async def main() -> None:
    """Run all examples."""
    print("=" * 60)
    print("NLP Service API Examples")
    print("=" * 60)
    
    try:
        await health_check()
        await analyze_simple_text()
        await analyze_multiple_actions()
        await analyze_achievement()
        await analyze_with_explicit_time()
        await get_user_stats()
        await test_error_handling()
        
        print("\n" + "=" * 60)
        print("All examples completed successfully!")
        print("=" * 60)
        
    except httpx.ConnectError:
        print("\nError: Could not connect to service.")
        print("Make sure the service is running at http://localhost:8000")
    except Exception as e:
        print(f"\nError: {e}")


if __name__ == "__main__":
    asyncio.run(main())
