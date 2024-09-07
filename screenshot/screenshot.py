import io
import logging
import platform
import subprocess
from typing import List

import discord
from redbot.core import commands
from Star_Utils import Cog
from selenium import webdriver
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import asyncio

log = logging.getLogger("star.screenshot")

class Screenshot(Cog):
    """
    A cog for taking detailed screenshots of websites.
    """

    def __init__(self, bot):
        self.bot = bot
        self.ensure_chrome_installed()

    def ensure_chrome_installed(self):
        """
        Ensures that Google Chrome is installed on the host machine.
        """
        os_name = platform.system()

        if os_name == "Linux":
            try:
                subprocess.run(["google-chrome", "--version"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                log.info("Google Chrome not found. Installing...")
                subprocess.run([
                    "wget", "https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb"
                ], check=True)
                subprocess.run(["sudo", "apt", "install", "./google-chrome-stable_current_amd64.deb", "-y"], check=True)
                subprocess.run(["rm", "google-chrome-stable_current_amd64.deb"], check=True)

        elif os_name == "Darwin":
            try:
                subprocess.run(["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome", "--version"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                log.info("Google Chrome not found. Please install it manually from https://www.google.com/chrome/")

        elif os_name == "Windows":
            try:
                subprocess.run(["chrome", "--version"], check=True)
            except (subprocess.CalledProcessError, FileNotFoundError):
                log.info("Google Chrome not found. Please install it manually from https://www.google.com/chrome/")

    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, attach_files=True)
    @commands.command(name="screenshot", aliases=["ss"])
    async def screenshot(self, ctx: commands.Context, url: str):
        """
        Takes a screenshot of the specified URL.
        """
        # Ensure the URL starts with http:// or https://
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        async with ctx.typing():
            loop = asyncio.get_event_loop()
            site_name, screenshot = await loop.run_in_executor(None, self.take_screenshot, url)

            if screenshot is None:
                await ctx.send("An error occurred while taking the screenshot.")
                return

            file_ = io.BytesIO(screenshot)
            file_.seek(0)
            file = discord.File(file_, "screenshot.png")
            file_.close()

            embed = discord.Embed(
                description=f"[*{site_name}*]({url})", color=discord.Color.blue()
            )
            embed.set_image(url="attachment://screenshot.png")

            await ctx.send(embed=embed, file=file)

    def take_screenshot(self, url: str):
        """
        Takes a screenshot of the given URL using Selenium.
        """
        chrome_options = Options()
        chrome_options.add_argument("--headless")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-popup-blocking")
        chrome_options.add_argument("--ignore-certificate-errors")
        chrome_options.add_argument("--disable-software-rasterizer")

        driver = webdriver.Chrome(
            service=ChromeService(ChromeDriverManager().install()), options=chrome_options
        )

        try:
            driver.get(url)
            self.handle_cookies(driver)
            self.wait_for_dynamic_content(driver)
            site_name = driver.title
            screenshot = driver.get_screenshot_as_png()
            return site_name, screenshot
        except Exception as e:
            log.error(f"Error during screenshot: {e}")
            return None, None
        finally:
            driver.quit()

    def handle_cookies(self, driver):
        """
        Attempts to handle cookie consent prompts using JavaScript and clicking common buttons.
        """
        try:
            # Set cookies and local storage for consent
            driver.execute_script("""
                document.cookie = 'cookieconsent_status=allow; path=/; domain=' + document.domain;
                localStorage.setItem('cookieconsent_status', 'allow');
                if (document.domain.includes('google')) {
                    document.cookie = 'CONSENT=YES+cb; path=/; domain=.google.com';
                }
            """)

            # Common selectors for cookie consent buttons
            cookie_selectors = [
                "button[aria-label='Accept all']",
                "button[title='Accept all']",
                "#cookie-accept-button",
                ".cookie-consent-accept",
                "[data-testid='cookie-accept']",
                "[id^='accept']",
                "[class*='accept']",
                "button:contains('Accept')",
                "button:contains('I agree')",
            ]

            for selector in cookie_selectors:
                try:
                    WebDriverWait(driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                    ).click()
                    log.info(f"Clicked cookie consent button with selector: {selector}")
                    break
                except Exception as e:
                    log.debug(f"Selector {selector} not found or clickable: {e}")
        except Exception as e:
            log.error(f"Error handling cookies: {e}")

    def wait_for_dynamic_content(self, driver):
        """
        Waits for dynamic content to load by checking for common elements.
        """
        try:
            # Wait for common dynamic content indicators
            dynamic_content_selectors = [
                "body",  # Wait for the body to be fully loaded
                "img",   # Wait for images to load
                "div",   # Wait for divs that might load content
            ]

            for selector in dynamic_content_selectors:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                )
                log.info(f"Dynamic content loaded for selector: {selector}")
        except Exception as e:
            log.warning(f"Dynamic content may not be fully loaded: {e}")
