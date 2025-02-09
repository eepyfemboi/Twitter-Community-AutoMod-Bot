"""
Sleepy's Twitter Community AutoMod Bot Thingie

LICENSE
===================================================
# Sleepy's Open Source License v1.3 (OSLv1.3)

**1. Permission to Use, Modify, and Redistribute**  
Permission is hereby granted to use, modify, and redistribute the code ("Software"), provided that any modified versions of the Software are distributed under the same terms as this license.

**2. Attribution and Notification**  
Any individual or organization using, modifying, or redistributing the Software, in whole or in part, must provide clear notification that the Software is being used and must include a link to a relevant webpage or repository associated with the Software, if such a webpage or repository exists. If no such webpage or repository exists, this requirement is waived.

**3. Profit Sharing**  
Any individual or organization that generates revenue or profit from the use, modification, or redistribution of the Software, in whole or in part, is required to share 30% of the profits with the owner of the Software, provided that the total generated profit for a given payment period exceeds $100. Payments must be made on a quarterly basis, accompanied by a financial report detailing the revenue and profit generated from the Software. If the profit that would be collected by the original author is less than $30, the user is exempt from these terms for that period.

**4. Revocation of Rights**  
The owner of the Software reserves the right to revoke any individual's or organization's permission to use, modify, or redistribute the Software at any time, for any reason or no reason at all. Upon revocation, the individual or organization must cease all use, modification, and redistribution of the Software.

**5. Creator Exemption Clause**  
The creator of this license may exempt and/or un-exempt themselves from any terms of the license at any time and for any reason.

**6. Author's Rights to Modified Code**  
The author of the Software retains the right to use any code from modified versions of the Software in any way, without the knowledge or consent of the user who created the modified version.

**7. Scope of Terms**  
The terms outlined in this license apply to individuals or organizations that use the Software as part of their own products, not to end users of those products.

**8. Contact Requirement**  
Anyone using, modifying, or redistributing the Software must provide a valid contact method.

**9. Prohibition of Malicious Use**  
The Software, including any modified or redistributed versions, may not be used for any malicious purposes or in any way that could cause harm to any individual, organization, system, or entity. Malicious purposes include, but are not limited to, unauthorized access to systems, data breaches, distribution of malware, denial-of-service attacks, or any activity intended to exploit, damage, or disrupt services, devices, or personal safety.

**10. Legal Enforcement**  
The author of the Software reserves the right to take legal action, including but not limited to DMCA takedown notices, against anyone who violates the terms of this license.

**11. Disclaimer of Warranties and Liability**  
The Software is provided "as-is," without warranty of any kind, express or implied, including but not limited to the warranties of merchantability, fitness for a particular purpose, and noninfringement. In no event shall the owner of the Software be liable for any claim, damages, or other liability, whether in an action of contract, tort, or otherwise, arising from, out of, or in connection with the Software or the use or other dealings in the Software.
===================================================
"""


#idk what this does but it make things easier in my editor so i use it
from __future__ import annotations

import os
import asyncio
import concurrent
import concurrent.futures

os.system(command="title Sleepy's Twitter AutoMod Bot")
loop = asyncio.new_event_loop()

executor = concurrent.futures.ThreadPoolExecutor(max_workers=64)
high_executor = concurrent.futures.ProcessPoolExecutor(max_workers=8)

loop.set_default_executor(executor)

import datetime
import json
import random
import time
import traceback
import threading

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service
except ImportError:
    input("Failed to import selenium. Press enter to automatically install selenium and retry, or press Ctrl + C to quit...")
    os.system("pip install selenium --upgrade")
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.chrome.service import Service

try:
    import undetected_chromedriver as uc
except ImportError:
    input("Failed to import undetected_chromedriver. Press enter to automatically install undetected-chromedriver and retry, or press Ctrl + C to quit...")
    os.system("pip install undetected-chromedriver --upgrade")

import discord
from discord.ext import commands

with open("config.json") as f:
    data = json.loads(f.read())
    
    try:
        USER_DATA_DIR: str = data.get("USER_DATA_DIR", "twitter_community_automod_bot")
        TARGET_TWITTER_COMMUNITY_URL: str = data["TARGET_TWITTER_COMMUNITY_URL"]
        TARGET_HEADERS_EXTRACTION_FROM_REQUEST_URL_MATCH: str = data["TARGET_HEADERS_EXTRACTION_FROM_REQUEST_URL_MATCH"]
        USE_DISCORD_BOT: bool = data.get("USE_DISCORD_BOT", False)
        if USE_DISCORD_BOT:
            DISCORD_BOT_TOKEN: str = data["DISCORD_BOT_TOKEN"]
            DISCORD_LOG_CHANNEL: int = data.get("DISCORD_LOG_CHANNEL", None)
            DISCORD_MOD_ROLE: int = data.get("DISCORD_MOD_ROLE", None)
        USE_DISCORD_WEBHOOK: bool = data.get("USE_DISCORD_WEBHOOK", False)
        if USE_DISCORD_WEBHOOK:
            DISCORD_WEBHOOK_URL: str = data["DISCORD_WEBHOOK_URL"]
    except Exception as e:
        traceback.print_exception(e)
        print("\n\n\nErrors while setting up variables (likely a misconfigured config.json or corrupted)")

discord_bot: DiscordAlertsBot = None
twitter_automod: SleepysTwitterAutoModBot = None

class DiscordAlertsBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix = '_twitterautomod!', 
            intents = discord.Intents.all(),
            case_insensitive = True,
            strip_after_prefix = True,
            help_command = None,
            max_messages = 10000,
            chunk_guilds_at_startup = False,
            activity = discord.Activity(
                name='Starting Up...', 
                type=discord.ActivityType.custom
            ) 
        )
        
        self.synced = False
        
        self.loop = loop
        self.executor = executor
        self.high_executor = high_executor
        
        self.initialized = False

    async def on_ready(self):
        if not self.synced:
            self.loop.create_task(self.tree.sync())
            self.synced = True
        self.initialized = True


class SleepysTwitterAutoModBot:
    def __init__(self):
        self.driver: uc.Chrome = None
        self.community_url: str = TARGET_TWITTER_COMMUNITY_URL
        self.req_match: str = TARGET_HEADERS_EXTRACTION_FROM_REQUEST_URL_MATCH
        self.logged_network_data: list = []
        self.discord: DiscordAlertsBot = None
        self.driver_initialized = False
        self.get_posts_request_headers: dict = None
        self.loop: asyncio.AbstractEventLoop = loop
        self.initialized = False

    def get_driver(self):
        if not self.driver:
            options = uc.ChromeOptions()
            options.add_argument(f"--user-data-dir={USER_DATA_DIR}")
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_experimental_option('useAutomationExtension', False)
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_argument("--remote-debugging-port=9222") # for intercepting network requests to get the headers to pull post data on our own
            
            self.driver = uc.Chrome(options = options)

        return self.driver
    
    async def log(self, msg: str): # a filler function for now to make it less complicated to finish logging later
        ...

    async def initialize(self):
        driver = self.get_driver()
        driver.get(self.community_url)
        await asyncio.sleep(10)
        self.loop.create_task(self.twitter_requests_listener())
        self.log("Finished startup..")
        self.driver_initialized = True
        return
    
    def check_req_url(self, url: str) -> bool:
        if self.req_match.lower() in url.lower():
            return True
        return False
    
    def update_self_request_headers_thingie_ig(self, data: dict):
        self.get_posts_request_headers = data["headers"]

    async def twitter_requests_listener(self):
        def handle_request(params):
            try:
                request_url = params["response"]["url"]
                if self.check_req_url(request_url):
                    request_id = params["requestId"]

                    request_headers = params["response"].get("headers", {})
                    response_body = self.driver.execute_cdp_cmd("Network.getResponseBody", {"requestId": request_id})
                    
                    request_data = {
                        "url": request_url,
                        "method": params["response"].get("requestHeadersText", "Unknown Method"),
                        "headers": request_headers,
                        "body": response_body.get("body", "")
                    }
                    
                    self.log("Network request matched. Updating headers.")
                    self.logged_network_data.append(request_data)
                    self.update_self_request_headers_thingie_ig(request_data)

            except Exception as e:
                traceback.print_exception(e)

        self.driver.execute_cdp_cmd("Network.enable", {})
        self.driver.execute_cdp_cmd("Page.enable", {})

        self.driver.execute_script("""
            (function() {
                window.devtoolsCallback = arguments[0];
                window.devtoolsConnection = new WebSocket('ws://127.0.0.1:9222/devtools/browser/');
                window.devtoolsConnection.onmessage = function(event) {
                    const message = JSON.parse(event.data);
                    if (message.method === 'Network.responseReceived') {
                        window.devtoolsCallback(message.params);
                    }
                };
            })();
        """, handle_request)






