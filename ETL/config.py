"""
Configuration Management for Cambridge ODP Evaluation Pipeline

This module handles:
- Loading environment variables from .env file
- Providing LLM client abstraction (supports multiple providers)
- Validating configuration on import

Usage:
    from config import get_llm_client, get_config

    llm = get_llm_client()
    response = llm.evaluate(prompt)
"""

import os
from typing import Dict, Any
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load .env file from the same directory as this script
dotenv_path = os.path.join(os.path.dirname(__file__), '.env')
load_dotenv(dotenv_path)

# ────────────────────────────────────────────────────────────
# CONFIGURATION GETTERS
# ────────────────────────────────────────────────────────────

def get_config() -> Dict[str, Any]:
    """
    Get all configuration values from environment.

    Returns:
        Dictionary with configuration keys including:
        - llm_provider: Which LLM service to use ('openai' or 'anthropic')
        - API keys for each provider
        - Model names
        - LLM parameters (temperature, max_tokens)
    """
    return {
        'llm_provider': os.getenv('LLM_PROVIDER', 'openai'),
        'openai_api_key': os.getenv('OPENAI_API_KEY'),
        'anthropic_api_key': os.getenv('ANTHROPIC_API_KEY'),
        'openai_model': os.getenv('OPENAI_MODEL', 'gpt-4'),
        'anthropic_model': os.getenv('ANTHROPIC_MODEL', 'claude-3-sonnet-20240229'),
        'temperature': float(os.getenv('LLM_TEMPERATURE', '0.3')),
        'max_tokens': int(os.getenv('LLM_MAX_TOKENS', '1000')),
    }

# ────────────────────────────────────────────────────────────
# LLM CLIENT ABSTRACTION
# ───────────────────────────────────────────────────────────

class BaseLLMClient:
    """
    Base class for LLM clients.

    All LLM provider implementations should inherit from this class
    and implement the evaluate() method.
    """

    def evaluate(self, prompt: str) -> Dict[str, Any]:
        """
        Send evaluation prompt to LLM and parse response.

        Args:
            prompt: The evaluation prompt (formatted by evaluate.py)

        Returns:
            Dictionary with evaluation scores:
            {
                'ai_description_score': float (0.0-1.0),
                'ai_tag_relevance_score': float (0.0-1.0),
                'ai_category_fit_score': float (0.0-1.0),
                'ai_suggestions': str
            }

        Raises:
            NotImplementedError: If subclass doesn't implement this method
        """
        raise NotImplementedError("Subclass must implement evaluate()")


class OpenAIClient(BaseLLMClient):
    """
    OpenAI GPT client for dataset metadata evaluation.

    This client uses OpenAI's API to evaluate dataset quality.
    Developers should implement the evaluate() method to:
    1. Call the OpenAI API with the provided prompt
    2. Parse the JSON response
    3. Return the structured evaluation result
    """

    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        """
        Initialize OpenAI client.

        Args:
            api_key: OpenAI API key
            model: Model name (e.g., 'gpt-4')
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
        """
        # TODO: Implement OpenAI client initialization
        #
        # IMPLEMENTATION GUIDE:
        # 1. Import the openai library:
        #    from openai import OpenAI
        #
        # 2. Create client instance:
        #    self.client = OpenAI(api_key=api_key)
        #
        # 3. Store model parameters:
        #    self.model = model
        #    self.temperature = temperature
        #    self.max_tokens = max_tokens
        #
        # PLACEHOLDER IMPLEMENTATION (stores parameters for now):

        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info(f"OpenAI client initialized (model: {model})")

    def evaluate(self, prompt: str) -> Dict[str, Any]:
        """
        Call OpenAI API with evaluation prompt.

        Args:
            prompt: The evaluation prompt

        Returns:
            Dictionary with evaluation scores
        """
        # TODO: Implement OpenAI API call
        #
        # IMPLEMENTATION GUIDE:
        # 1. Call the OpenAI ChatCompletion API:
        #    response = self.client.chat.completions.create(
        #        model=self.model,
        #        messages=[
        #            {"role": "system", "content": "You are a metadata quality evaluator."},
        #            {"role": "user", "content": prompt}
        #        ],
        #        temperature=self.temperature,
        #        max_tokens=self.max_tokens,
        #        response_format={"type": "json_object"}  # Request JSON response
        #    )
        #
        # 2. Extract the response content:
        #    content = response.choices[0].message.content
        #
        # 3. Parse the JSON response:
        #    import json
        #    result = json.loads(content)
        #
        # 4. Return the structured result (ensure keys match expected format):
        #    return {
        #        'ai_description_score': result['description_score'],
        #        'ai_tag_relevance_score': result['tag_score'],
        #        'ai_category_fit_score': result['category_score'],
        #        'ai_suggestions': result['suggestions']
        #    }
        #
        # PLACEHOLDER: Return dummy scores until implemented
        logger.debug("OpenAI evaluation called (not yet implemented)")
        return {
            'ai_description_score': 0.75,
            'ai_tag_relevance_score': 0.80,
            'ai_category_fit_score': 0.70,
            'ai_suggestions': "OpenAI evaluation not yet implemented. Replace this with actual LLM analysis."
        }


class AnthropicClient(BaseLLMClient):
    """
    Anthropic Claude client for dataset metadata evaluation.

    This client uses Anthropic's API to evaluate dataset quality.
    Developers should implement the evaluate() method to:
    1. Call the Anthropic API with the provided prompt
    2. Parse the JSON response
    3. Return the structured evaluation result
    """

    def __init__(self, api_key: str, model: str, temperature: float, max_tokens: int):
        """
        Initialize Anthropic client.

        Args:
            api_key: Anthropic API key
            model: Model name (e.g., 'claude-3-sonnet-20240229')
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum response tokens
        """
        # TODO: Implement Anthropic client initialization
        #
        # IMPLEMENTATION GUIDE:
        # 1. Import the anthropic library:
        #    from anthropic import Anthropic
        #
        # 2. Create client instance:
        #    self.client = Anthropic(api_key=api_key)
        #
        # 3. Store model parameters:
        #    self.model = model
        #    self.temperature = temperature
        #    self.max_tokens = max_tokens
        #
        # PLACEHOLDER IMPLEMENTATION (stores parameters for now):

        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_tokens = max_tokens
        logger.info(f"Anthropic client initialized (model: {model})")

    def evaluate(self, prompt: str) -> Dict[str, Any]:
        """
        Call Anthropic API with evaluation prompt.

        Args:
            prompt: The evaluation prompt

        Returns:
            Dictionary with evaluation scores
        """
        # TODO: Implement Anthropic API call
        #
        # IMPLEMENTATION GUIDE:
        # 1. Call the Anthropic Messages API:
        #    message = self.client.messages.create(
        #        model=self.model,
        #        max_tokens=self.max_tokens,
        #        temperature=self.temperature,
        #        messages=[
        #            {
        #                "role": "user",
        #                "content": prompt
        #            }
        #        ]
        #    )
        #
        # 2. Extract the response content:
        #    content = message.content[0].text
        #
        # 3. Parse the JSON response:
        #    import json
        #    result = json.loads(content)
        #
        # 4. Return the structured result (ensure keys match expected format):
        #    return {
        #        'ai_description_score': result['description_score'],
        #        'ai_tag_relevance_score': result['tag_score'],
        #        'ai_category_fit_score': result['category_score'],
        #        'ai_suggestions': result['suggestions']
        #    }
        #
        # PLACEHOLDER: Return dummy scores until implemented
        logger.debug("Anthropic evaluation called (not yet implemented)")
        return {
            'ai_description_score': 0.75,
            'ai_tag_relevance_score': 0.80,
            'ai_category_fit_score': 0.70,
            'ai_suggestions': "Anthropic evaluation not yet implemented. Replace this with actual LLM analysis."
        }


def get_llm_client() -> BaseLLMClient:
    """
    Get configured LLM client based on environment settings.

    This factory function reads the LLM_PROVIDER environment variable
    and returns the appropriate client instance (OpenAI or Anthropic).

    Returns:
        Configured LLM client instance

    Raises:
        ValueError: If provider is unsupported or API key is missing

    Example:
        >>> llm = get_llm_client()
        >>> result = llm.evaluate("Evaluate this dataset...")
    """
    config = get_config()
    provider = config['llm_provider'].lower()

    if provider == 'openai':
        api_key = config['openai_api_key']
        if not api_key or api_key == 'sk-your-openai-api-key-here':
            raise ValueError(
                "OPENAI_API_KEY not set in .env file. "
                "Copy .env.example to .env and add your API key."
            )

        return OpenAIClient(
            api_key=api_key,
            model=config['openai_model'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )

    elif provider == 'anthropic':
        api_key = config['anthropic_api_key']
        if not api_key or api_key == 'sk-ant-your-anthropic-api-key-here':
            raise ValueError(
                "ANTHROPIC_API_KEY not set in .env file. "
                "Copy .env.example to .env and add your API key."
            )

        return AnthropicClient(
            api_key=api_key,
            model=config['anthropic_model'],
            temperature=config['temperature'],
            max_tokens=config['max_tokens']
        )

    else:
        raise ValueError(
            f"Unsupported LLM provider: {provider}. "
            f"Must be 'openai' or 'anthropic'."
        )


# ────────────────────────────────────────────────────────────
# CONFIGURATION VALIDATION
# ────────────────────────────────────────────────────────────

# Validate configuration on module import
try:
    config = get_config()
    logger.info(f"Configuration loaded (LLM provider: {config['llm_provider']})")
except Exception as e:
    logger.warning(f"Configuration validation failed: {e}")
    logger.warning("Make sure to create .env file from .env.example before running evaluations")
