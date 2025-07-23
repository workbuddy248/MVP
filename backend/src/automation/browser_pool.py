# src/automation/browser_pool.py
"""
Browser Pool Management
Handles browser context creation and resource management
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class BrowserContext:
    """Browser context wrapper with metadata"""
    context: BrowserContext
    page: Page
    created_at: float
    last_used: float
    active: bool = True

class BrowserPool:
    """
    Browser Pool for managing browser contexts and resources
    Optimized for legacy Java applications
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.browser: Optional[Browser] = None
        self.contexts: List[BrowserContext] = []
        self.playwright = None
        self._initializing = False
        self._context_creation_lock = asyncio.Lock() if asyncio else None
        
    async def initialize(self):
        """Initialize browser pool"""
        
        # Prevent multiple simultaneous initializations
        if self._initializing:
            logger.info("Browser pool already initializing, waiting...")
            while self._initializing:
                await asyncio.sleep(0.1)
            return
            
        if self.browser:
            logger.info("Browser pool already initialized")
            return
            
        self._initializing = True
        logger.info("Initializing browser pool...")
        
        try:
            # Start Playwright
            self.playwright = await async_playwright().start()
            
            # Launch browser with legacy app optimizations
            browser_type = self.config.get("type", "chromium")
            launch_options = self._get_launch_options()
            
            if browser_type == "chromium":
                self.browser = await self.playwright.chromium.launch(**launch_options)
            elif browser_type == "firefox":
                self.browser = await self.playwright.firefox.launch(**launch_options)
            elif browser_type == "webkit":
                self.browser = await self.playwright.webkit.launch(**launch_options)
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
            
            logger.info(f"Browser {browser_type} launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize browser pool: {e}")
            raise
        finally:
            self._initializing = False
    
    async def get_browser_context(self) -> BrowserContext:
        """Get or create a browser context optimized for legacy applications"""
        
        if not self.browser:
            await self.initialize()
        
        # Use lock to prevent race conditions in context creation
        if self._context_creation_lock is None:
            self._context_creation_lock = asyncio.Lock()
            
        async with self._context_creation_lock:
            try:
                # Create new context with legacy app settings
                context_options = self._get_context_options()
                playwright_context = await self.browser.new_context(**context_options)
                
                # Configure context for legacy applications
                await self._configure_context_for_legacy_apps(playwright_context)
                
                # Create page
                page = await playwright_context.new_page()
                
                # Configure page for legacy applications
                await self._configure_page_for_legacy_apps(page)
                
                # Create wrapper
                browser_context = BrowserContext(
                    context=playwright_context,
                    page=page,
                    created_at=asyncio.get_event_loop().time(),
                    last_used=asyncio.get_event_loop().time()
                )
                
                self.contexts.append(browser_context)
                
                logger.info(f"Created new browser context. Total contexts: {len(self.contexts)}")
                return browser_context
                
            except Exception as e:
                logger.error(f"Failed to create browser context: {e}")
                raise
    
    def _get_launch_options(self) -> Dict[str, Any]:
        """Get browser launch options optimized for legacy applications"""
        
        base_options = {
            "headless": self.config.get("headless", False),  # Default to visible browser
            "slow_mo": self.config.get("slow_mo", 1000),  # Slow down for legacy apps
        }
        
        # Add legacy-specific arguments
        args = [
            "--disable-web-security",           # For legacy CORS issues
            "--ignore-certificate-errors",      # For self-signed certs
            "--allow-running-insecure-content", # For mixed content
            "--disable-features=VizDisplayCompositor", # Stability
            "--no-sandbox",                     # For containerized environments
            "--disable-dev-shm-usage",         # Reduce memory usage
        ]
        
        # Add custom args from config
        custom_args = self.config.get("launch_options", {}).get("args", [])
        args.extend(custom_args)
        
        base_options["args"] = args
        
        return base_options
    
    def _get_context_options(self) -> Dict[str, Any]:
        """Get context options for legacy applications"""
        
        viewport = self.config.get("viewport", {"width": 1920, "height": 1080})
        
        options = {
            "viewport": viewport,
            "ignore_https_errors": True,        # For legacy SSL
            "accept_downloads": False,          # Security
            "java_script_enabled": True,        # Required for most apps
            "user_agent": self._get_legacy_user_agent(),
        }
        
        # Add custom context options
        custom_options = self.config.get("context_options", {})
        options.update(custom_options)
        
        return options
    
    def _get_legacy_user_agent(self) -> str:
        """Get user agent string compatible with legacy applications"""
        
        # Use a stable, well-supported user agent
        return "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    async def _configure_context_for_legacy_apps(self, context: BrowserContext):
        """Configure context specifically for legacy Java applications"""
        
        try:
            # Set longer timeouts for legacy apps (3 minutes default, 5 minutes navigation)
            context.set_default_timeout(self.config.get("default_timeout", 180000))
            context.set_default_navigation_timeout(300000)  # 5 minutes for navigation
            
            # Handle dialogs automatically
            context.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            
            # Log console errors for debugging
            context.on("console", self._handle_console_message)
            
            # Handle page errors
            context.on("pageerror", self._handle_page_error)
            
            logger.info("Context configured for legacy applications")
            
        except Exception as e:
            logger.warning(f"Failed to configure context: {e}")
    
    async def _configure_page_for_legacy_apps(self, page: Page):
        """Configure page specifically for legacy Java applications"""
        
        try:
            # Extended timeouts for legacy apps (3 minutes default, 5 minutes navigation)
            page.set_default_timeout(self.config.get("default_timeout", 180000))
            page.set_default_navigation_timeout(300000)
            
            # Handle authentication dialogs
            page.on("dialog", lambda dialog: asyncio.create_task(dialog.accept()))
            
            # Block unnecessary resources to speed up loading
            await page.route("**/*.{png,jpg,jpeg,gif,svg,woff,woff2}", lambda route: route.abort())
            
            # Inject helper scripts for legacy app interaction
            await self._inject_legacy_helpers(page)
            
            logger.info("Page configured for legacy applications")
            
        except Exception as e:
            logger.warning(f"Failed to configure page: {e}")
    
    async def _inject_legacy_helpers(self, page: Page):
        """Inject JavaScript helpers for legacy application interaction"""
        
        helper_script = """
        // Helper functions for legacy Java applications
        window.legacyHelpers = {
            // Wait for element to be stable (not moving/changing)
            waitForStable: function(selector, timeout = 5000) {
                return new Promise((resolve, reject) => {
                    const element = document.querySelector(selector);
                    if (!element) {
                        reject(new Error('Element not found'));
                        return;
                    }
                    
                    let lastRect = element.getBoundingClientRect();
                    let stableCount = 0;
                    const requiredStableChecks = 5;
                    
                    const checkStability = () => {
                        const currentRect = element.getBoundingClientRect();
                        if (currentRect.x === lastRect.x && 
                            currentRect.y === lastRect.y &&
                            currentRect.width === lastRect.width &&
                            currentRect.height === lastRect.height) {
                            stableCount++;
                        } else {
                            stableCount = 0;
                        }
                        
                        lastRect = currentRect;
                        
                        if (stableCount >= requiredStableChecks) {
                            resolve(element);
                        } else if (timeout > 0) {
                            setTimeout(checkStability, 100);
                            timeout -= 100;
                        } else {
                            reject(new Error('Element not stable within timeout'));
                        }
                    };
                    
                    checkStability();
                });
            },
            
            // Check if page is ready (no loading indicators)
            isPageReady: function() {
                const loadingSelectors = [
                    '.loading', '.spinner', '[data-loading="true"]',
                    '.progress-bar', '.loading-overlay'
                ];
                
                for (const selector of loadingSelectors) {
                    if (document.querySelector(selector)) {
                        return false;
                    }
                }
                
                return document.readyState === 'complete';
            },
            
            // Scroll element into view smoothly
            scrollToElement: function(element) {
                element.scrollIntoView({
                    behavior: 'smooth',
                    block: 'center',
                    inline: 'center'
                });
                
                // Wait for scroll to complete
                return new Promise(resolve => setTimeout(resolve, 1000));
            }
        };
        """
        
        try:
            await page.add_init_script(helper_script)
        except Exception as e:
            logger.warning(f"Failed to inject helper scripts: {e}")
    
    def _handle_console_message(self, msg):
        """Handle console messages from the browser"""
        
        if msg.type == "error":
            logger.warning(f"Browser console error: {msg.text}")
        elif msg.type == "warning":
            logger.info(f"Browser console warning: {msg.text}")
    
    def _handle_page_error(self, error):
        """Handle page errors"""
        
        logger.error(f"Page error: {error}")
    
    async def close_context(self, browser_context: BrowserContext):
        """Close a specific browser context"""
        
        try:
            if browser_context in self.contexts:
                self.contexts.remove(browser_context)
            
            await browser_context.page.close()
            await browser_context.context.close()
            
            logger.info(f"Closed browser context. Remaining contexts: {len(self.contexts)}")
            
        except Exception as e:
            logger.error(f"Failed to close context: {e}")
    
    async def cleanup_all(self):
        """Clean up all browser resources"""
        
        logger.info("Cleaning up browser pool...")
        
        try:
            # Close all contexts
            for browser_context in self.contexts[:]:
                await self.close_context(browser_context)
            
            # Close browser
            if self.browser:
                await self.browser.close()
                
            # Stop Playwright
            if self.playwright:
                await self.playwright.stop()
                
            logger.info("Browser pool cleanup completed")
            
        except Exception as e:
            logger.error(f"Browser pool cleanup failed: {e}")
