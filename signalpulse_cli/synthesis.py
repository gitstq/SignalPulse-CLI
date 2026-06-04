"""
AI-powered briefing synthesis for SignalPulse-CLI.

Generates concise, structured briefings from aggregated signal data
using configurable LLM APIs (OpenAI, Anthropic, Ollama compatible).
"""

import json
from typing import Any, Dict, List, Optional

import requests

from .config import Config
from .sources.base import SignalItem
from .utils import format_relative_time, truncate_text


class Synthesizer:
    """AI briefing synthesis engine.

    Sends top-ranked signal items to a configured LLM API and
    generates a structured briefing with sections for key trends,
    hot topics, emerging signals, and recommended actions.

    Supports any OpenAI-compatible API endpoint, including:
    - OpenAI (gpt-3.5-turbo, gpt-4, etc.)
    - Anthropic (via compatible proxy)
    - Ollama (local models)
    - Any OpenAI-compatible server

    Attributes:
        config: Application configuration.
        api_key: API key for the LLM provider.
        api_base: Base URL for the API.
        model: Model name to use.
        max_tokens: Maximum tokens for the response.
        temperature: Sampling temperature.
    """

    # System prompt template for briefing generation
    SYSTEM_PROMPT: str = (
        "You are an expert technology analyst and trend spotter. "
        "Your task is to analyze a curated list of trending topics, "
        "projects, and discussions from major tech platforms (Hacker News, "
        "Reddit, GitHub, Product Hunt) and produce a concise, insightful "
        "briefing report.\n\n"
        "Analyze the provided items and identify:\n"
        "1. Cross-platform patterns and themes\n"
        "2. Emerging technologies or trends\n"
        "3. Notable projects gaining traction\n"
        "4. Community sentiment and discussion topics\n\n"
        "Write in a professional but accessible tone. Be specific and "
        "data-driven. Reference specific items by name when relevant. "
        "Format the output with clear section headers using markdown."
    )

    USER_PROMPT_TEMPLATE: str = (
        "Based on the following {count} trending items from across "
        "major tech platforms (fetched {fetched_time}), please "
        "generate a structured technology briefing.\n\n"
        "## Trending Items\n\n{items_text}\n\n"
        "## Required Briefing Sections\n\n"
        "Please organize your briefing into these sections:\n\n"
        "### 1. Key Trends ({trend_count} items)\n"
        "The most significant trends appearing across multiple platforms. "
        "What themes are dominating tech discussions?\n\n"
        "### 2. Hot Topics ({hot_count} items)\n"
        "Individual items generating the most engagement and attention. "
        "What specific topics are people most excited about?\n\n"
        "### 3. Emerging Signals ({emerging_count} items)\n"
        "Early-stage trends or lesser-known items that show promise. "
        "What might be the next big thing?\n\n"
        "### 4. Recommended Actions\n"
        "Based on the analysis, what should a tech professional "
        "pay attention to, explore, or act on?\n\n"
        "Keep the total briefing concise but informative. "
        "Use markdown formatting for readability."
    )

    def __init__(self, config: Config) -> None:
        """Initialize the synthesizer with configuration.

        Args:
            config: Application configuration object.
        """
        self.config = config
        ai_config = config.get("ai", {})
        self.provider: str = ai_config.get("provider", "openai")
        self.api_key: str = ai_config.get("api_key", "")
        self.api_base: str = ai_config.get(
            "api_base", "https://api.openai.com/v1"
        )
        self.model: str = ai_config.get("model", "gpt-3.5-turbo")
        self.max_tokens: int = ai_config.get("max_tokens", 2048)
        self.temperature: float = ai_config.get("temperature", 0.7)
        self.top_n: int = ai_config.get("top_n", 15)

    @property
    def is_configured(self) -> bool:
        """Check if the synthesizer has a valid API key configured.

        Returns:
            True if an API key is available.
        """
        return bool(self.api_key)

    def synthesize(self, items: List[SignalItem]) -> Optional[str]:
        """Generate an AI briefing from the given signal items.

        Takes the top N items by normalized score, formats them as
        context, and sends them to the LLM API for analysis.

        Args:
            items: List of scored SignalItem objects.

        Returns:
            Generated briefing text in markdown format, or None
            if synthesis fails or is not configured.
        """
        if not self.is_configured:
            print(
                "[info] AI synthesis is not configured. "
                "Set ai.api_key in your config or SIGNALPULSE_AI_API_KEY env var."
            )
            return None

        if not items:
            print("[warning] No items to synthesize")
            return None

        # Take top N items
        top_items = items[: self.top_n]

        # Format items as context text
        items_text = self._format_items_context(top_items)

        # Build the user prompt
        user_prompt = self.USER_PROMPT_TEMPLATE.format(
            count=len(top_items),
            fetched_time=format_relative_time(top_items[0].fetched_at)
            if top_items
            else "recently",
            items_text=items_text,
            trend_count=max(2, len(top_items) // 4),
            hot_count=max(3, len(top_items) // 3),
            emerging_count=max(2, len(top_items) // 5),
        )

        # Call the LLM API
        return self._call_llm(user_prompt)

    def _format_items_context(self, items: List[SignalItem]) -> str:
        """Format signal items as structured text for the LLM prompt.

        Creates a numbered list with source, title, score, and URL
        for each item.

        Args:
            items: List of SignalItem objects.

        Returns:
            Formatted text string suitable for inclusion in a prompt.
        """
        lines: List[str] = []
        for i, item in enumerate(items, 1):
            source_label = item.source.upper()
            score_str = f"{item.normalized_score:.2f}"
            time_str = format_relative_time(item.created_at)
            comments_str = str(item.comments)

            line = (
                f"{i}. [{source_label}] (score: {score_str}, "
                f"comments: {comments_str}, age: {time_str})\n"
                f"   {item.title}\n"
            )
            if item.url:
                line += f"   URL: {item.url}\n"

            # Add source-specific metadata
            if item.source == "github":
                lang = item.metadata.get("language", "Unknown")
                stars = item.metadata.get("stars", 0)
                line += f"   Language: {lang}, Stars: {stars}\n"
            elif item.source == "reddit":
                subreddit = item.metadata.get("subreddit", "")
                if subreddit:
                    line += f"   Subreddit: r/{subreddit}\n"
            elif item.source == "producthunt":
                topics = item.metadata.get("topics", [])
                if topics:
                    line += f"   Topics: {', '.join(topics[:3])}\n"

            lines.append(line)

        return "\n".join(lines)

    def _call_llm(self, user_prompt: str) -> Optional[str]:
        """Send a prompt to the configured LLM API and get a response.

        Supports OpenAI-compatible chat completion endpoints.
        Handles different providers by adjusting the request format.

        Args:
            user_prompt: The user message to send.

        Returns:
            LLM response text, or None if the call fails.
        """
        headers = {
            "Content-Type": "application/json",
        }

        # Set authorization based on provider
        if self.provider == "anthropic":
            headers["x-api-key"] = self.api_key
            headers["anthropic-version"] = "2023-06-01"
            return self._call_anthropic(user_prompt, headers)
        else:
            # OpenAI-compatible (OpenAI, Ollama, etc.)
            headers["Authorization"] = f"Bearer {self.api_key}"
            return self._call_openai_compatible(user_prompt, headers)

    def _call_openai_compatible(
        self, user_prompt: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Call an OpenAI-compatible chat completion endpoint.

        Works with OpenAI, Ollama, and any compatible server.

        Args:
            user_prompt: The user message.
            headers: HTTP headers including authorization.

        Returns:
            Response text, or None if the call fails.
        """
        url = f"{self.api_base}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            # Extract response text from OpenAI format
            choices = data.get("choices", [])
            if choices:
                message = choices[0].get("message", {})
                return message.get("content")

            return None

        except requests.exceptions.Timeout:
            print("[warning] AI synthesis request timed out (60s)")
            return None
        except requests.exceptions.ConnectionError:
            print(
                f"[warning] Could not connect to AI API at {url}. "
                "Check your api_base configuration."
            )
            return None
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code == 401:
                print("[warning] AI API authentication failed. Check your api_key.")
            elif status_code == 429:
                print("[warning] AI API rate limit exceeded. Try again later.")
            else:
                print(f"[warning] AI API HTTP error: {e}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"[warning] Failed to parse AI API response: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[warning] AI API request failed: {e}")
            return None

    def _call_anthropic(
        self, user_prompt: str, headers: Dict[str, str]
    ) -> Optional[str]:
        """Call the Anthropic Messages API.

        Uses the Anthropic-specific API format for Claude models.

        Args:
            user_prompt: The user message.
            headers: HTTP headers including x-api-key.

        Returns:
            Response text, or None if the call fails.
        """
        url = f"{self.api_base}/messages"
        payload = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": self.SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": user_prompt},
            ],
        }

        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()

            # Extract response text from Anthropic format
            content_blocks = data.get("content", [])
            for block in content_blocks:
                if block.get("type") == "text":
                    return block.get("text", "")

            return None

        except requests.exceptions.Timeout:
            print("[warning] Anthropic API request timed out (60s)")
            return None
        except requests.exceptions.ConnectionError:
            print(
                f"[warning] Could not connect to Anthropic API at {url}. "
                "Check your api_base configuration."
            )
            return None
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code if e.response is not None else 0
            if status_code == 401:
                print("[warning] Anthropic API authentication failed. Check your api_key.")
            elif status_code == 429:
                print("[warning] Anthropic API rate limit exceeded. Try again later.")
            else:
                print(f"[warning] Anthropic API HTTP error: {e}")
            return None
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            print(f"[warning] Failed to parse Anthropic API response: {e}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"[warning] Anthropic API request failed: {e}")
            return None
