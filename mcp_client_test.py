# client.py
import asyncio
from mcp.client.stdio import StdioClient

async def main():
    client = StdioClient(["python", "server.py"])
    await client.start()

    # Call first tool
    stock_result = await client.call_tool("get_stock_price", {"symbol": "AAPL"})
    price = stock_result["price"]

    # Call second tool using result of first
    convert_result = await client.call_tool("convert_currency", {
        "amount": price,
        "from_currency": "USD",
        "to_currency": "EUR"
    })

    print("Stock Result:", stock_result)
    print("Converted Result:", convert_result)

asyncio.run(main())
