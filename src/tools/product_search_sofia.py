from .class_product_search_full import MCPService

product_search = MCPService(channel_id="1")
tool_product_search = product_search.get_tool()