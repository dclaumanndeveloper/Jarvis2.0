import asyncio
import logging
from typing import Optional, List, Dict
from playwright.async_api import async_playwright

logger = logging.getLogger(__name__)

class WebAgentService:
    """
    Autonomous service for web navigation and information extraction.
    Uses Playwright for browser automation.
    """
    def __init__(self):
        self.browser = None
        self.context = None
        logger.info("WebAgentService: Initialized.")

    async def _ensure_browser(self):
        if not self.browser:
            self.playwright = await async_playwright().start()
            self.browser = await self.playwright.chromium.launch(headless=True)
            self.context = await self.browser.new_context()

    async def research_topic(self, topic: str) -> str:
        """Perform market research or search for a specific topic"""
        try:
            await self._ensure_browser()
            page = await self.context.new_page()
            
            # Navigate to search engine
            logger.info(f"WebAgentService: Researching '{topic}'...")
            await page.goto(f"https://www.google.com/search?q={topic}")
            await page.wait_for_timeout(2000)
            
            # Extract main snippets
            results = await page.query_selector_all('div.g')
            summaries = []
            for res in results[:3]:
                text = await res.inner_text()
                if text:
                    summaries.append(text.split('\n')[0] + ": " + " ".join(text.split('\n')[1:3]))
            
            await page.close()
            
            if not summaries:
                return "Não consegui encontrar resultados detalhados."
            
            return "\n".join(summaries)
        except Exception as e:
            logger.error(f"WebAgentService Error: {e}")
            return f"Erro na pesquisa autônoma: {e}"

    async def get_product_price(self, product_name: str) -> str:
        """Find prices for a specific product"""
        # Simplified example
        return await self.research_topic(f"preço {product_name}")

    async def stop(self):
        if self.browser:
            await self.browser.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()
