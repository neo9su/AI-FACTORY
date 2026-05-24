import asyncio
import httpx
import sys

async def validate_flow():
    base_url = "http://localhost:8000/api/v1"
    product_id = "prod-test-123"
    
    print(f"🚀 Starting End-to-End Validation for Product: {product_id}")

    async with httpx.AsyncClient(base_url=base_url, timeout=10.0) as client:
        # 1. Track View Event
        print(f"1. [Action] Sending 'view' event...")
        event_payload = {
            "product_id": product_id,
            "event_type": "view",
            "session_id": "test-session-999",
            "event_metadata": {"source": "test_script"}
        }
        resp = await client.post("/events", json=event_payload)
        if resp.status_code in [200, 201]:
            print("   ✅ Event sent successfully.")
        else:
            print(	f"   ❌ Failed to send event: {resp.text}")
            return

        # 2. Verify Stats via API
        print(f"2. [Action] Checking product stats...")
        stats_resp = await client.get(f"/analytics/products/{product_id}/stats")
        if stats_resp.status_code == 200:
            stats = stats_resp.json()
            views = stats.get("views", 0)
            print(f"   ✅ Current views for product: {views}")
            if views > 0:
                print("   ✅ Success: View count incremented!")
            else:
                print("   ❌ Error: View count did not increment.")
        else:
            print(f"   ❌ Failed to fetch stats: {stats_resp.text}")
            return

        # 3. Check Opportunity Score (Check if any score exists)
        print(f"3. [Action] Checking Top Opportunities...")
        opp_resp = await client.get("/analytics/top-opportunities?limit=5")
        if opp_resp.status_code == 200:
            opps = opp_resp.json()
            if opps:
                print(f"   ✅ Found {len(opps)} top opportunities.")
                print(f"   ✅ Top Topic: {opps[0].get('topic')}")
            else:
                print("   ❌ No opportunities found in analytics.")
        else:
            print(f"   ❌ Failed to fetch top opportunities: {opp_resp.text}")

    print("\n✨ Phase 5-A Validation Complete!")

if __name__ == "__main__":
    asyncio.run(validate_flow())
