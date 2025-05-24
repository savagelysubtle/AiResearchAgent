import os
from typing import (
    Any,
    Optional,
)

from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.base import (
    LanguageModelInput,
)
from langchain_core.messages import (
    AIMessage,
    SystemMessage,
)
from langchain_core.runnables import RunnableConfig
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_ibm import ChatWatsonx
from langchain_mistralai import ChatMistralAI
from langchain_ollama import ChatOllama
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from openai import OpenAI

from src.ai_research_assistant.utils.env_manager import env_manager


def _create_google_provider(**kwargs):
    """
    Create Google Generative AI provider with enhanced configuration support.

    This function implements the Google API migration plan Option 1:
    - Maintains LangChain integration
    - Uses latest langchain-google-genai package
    - Supports advanced configuration options

    Args:
        **kwargs: Configuration parameters including:
            - model_name: Model to use (default: gemini-2.0-flash-exp)
            - temperature: Temperature setting (default: 0.0)
            - max_tokens: Maximum output tokens
            - top_p, top_k: Sampling parameters
            - safety_settings: Google-specific safety settings
            - api_key: API key (retrieved from environment if not provided)

    Returns:
        ChatGoogleGenerativeAI: Configured Google provider instance
    """
    # Get API key from kwargs or environment
    api_key = kwargs.get("api_key", "") or env_manager.get_api_key("google")
    if not api_key:
        error_msg = env_manager.create_error_message("google")
        raise ValueError(error_msg)

    # Enhanced model configuration
    model_name = kwargs.get("model_name", "gemini-2.0-flash-exp")

    # Build generation configuration
    generation_config = {}
    if "max_tokens" in kwargs:
        generation_config["max_output_tokens"] = kwargs["max_tokens"]
    if "top_p" in kwargs:
        generation_config["top_p"] = kwargs["top_p"]
    if "top_k" in kwargs:
        generation_config["top_k"] = kwargs["top_k"]

    # Safety settings support
    safety_settings = kwargs.get("safety_settings", None)

    # Additional Google-specific configurations
    project_id = kwargs.get("project_id") or env_manager.get_provider_config(
        "google"
    ).get("project_id")

    provider_kwargs = {
        "model": model_name,
        "temperature": kwargs.get("temperature", 0.0),
        "api_key": api_key,
    }

    # Add optional configurations only if they exist
    if generation_config:
        provider_kwargs["generation_config"] = generation_config
    if safety_settings:
        provider_kwargs["safety_settings"] = safety_settings
    if project_id:
        provider_kwargs["project_id"] = project_id

    return ChatGoogleGenerativeAI(**provider_kwargs)


class DeepSeekR1ChatOpenAI(ChatOpenAI):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.client = OpenAI(
            base_url=kwargs.get("base_url"), api_key=kwargs.get("api_key")
        )

    async def ainvoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        message_history = []
        for input_ in input:
            if isinstance(input_, SystemMessage):
                message_history.append({"role": "system", "content": input_.content})
            elif isinstance(input_, AIMessage):
                message_history.append({"role": "assistant", "content": input_.content})
            else:
                message_history.append({"role": "user", "content": input_.content})

        response = self.client.chat.completions.create(
            model=self.model_name, messages=message_history
        )

        reasoning_content = response.choices[0].message.reasoning_content
        content = response.choices[0].message.content
        return AIMessage(content=content, reasoning_content=reasoning_content)

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        message_history = []
        for input_ in input:
            if isinstance(input_, SystemMessage):
                message_history.append({"role": "system", "content": input_.content})
            elif isinstance(input_, AIMessage):
                message_history.append({"role": "assistant", "content": input_.content})
            else:
                message_history.append({"role": "user", "content": input_.content})

        response = self.client.chat.completions.create(
            model=self.model_name, messages=message_history
        )

        reasoning_content = response.choices[0].message.reasoning_content
        content = response.choices[0].message.content
        return AIMessage(content=content, reasoning_content=reasoning_content)


class DeepSeekR1ChatOllama(ChatOllama):
    async def ainvoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        org_ai_message = await super().ainvoke(input=input)
        org_content = org_ai_message.content
        reasoning_content = org_content.split("</think>")[0].replace("<think>", "")
        content = org_content.split("</think>")[1]
        if "**JSON Response:**" in content:
            content = content.split("**JSON Response:**")[-1]
        return AIMessage(content=content, reasoning_content=reasoning_content)

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        *,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> AIMessage:
        org_ai_message = super().invoke(input=input)
        org_content = org_ai_message.content
        reasoning_content = org_content.split("</think>")[0].replace("<think>", "")
        content = org_content.split("</think>")[1]
        if "**JSON Response:**" in content:
            content = content.split("**JSON Response:**")[-1]
        return AIMessage(content=content, reasoning_content=reasoning_content)


def get_llm_model(provider: str, **kwargs):
    """
    Get LLM model
    :param provider: LLM provider
    :param kwargs:
    :return:
    """
    # Use environment manager for API key validation and retrieval
    if provider not in ["ollama", "bedrock"]:
        api_key = kwargs.get("api_key", "") or env_manager.get_api_key(provider)
        if not api_key:
            error_msg = env_manager.create_error_message(provider)
            raise ValueError(error_msg)
        kwargs["api_key"] = api_key

    if provider == "anthropic":
        if not kwargs.get("base_url", ""):
            base_url = env_manager.get_endpoint(provider) or "https://api.anthropic.com"
        else:
            base_url = kwargs.get("base_url")

        return ChatAnthropic(
            model=kwargs.get("model_name", "claude-3-5-sonnet-20241022"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "mistral":
        if not kwargs.get("base_url", ""):
            base_url = env_manager.get_endpoint(provider) or "https://api.mistral.ai/v1"
        else:
            base_url = kwargs.get("base_url")

        return ChatMistralAI(
            model=kwargs.get("model_name", "mistral-large-latest"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "openai":
        if not kwargs.get("base_url", ""):
            base_url = env_manager.get_endpoint(provider) or "https://api.openai.com/v1"
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "grok":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("GROK_ENDPOINT", "https://api.x.ai/v1")
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "grok-3"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "deepseek":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("DEEPSEEK_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")

        if kwargs.get("model_name", "deepseek-chat") == "deepseek-reasoner":
            return DeepSeekR1ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-reasoner"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
        else:
            return ChatOpenAI(
                model=kwargs.get("model_name", "deepseek-chat"),
                temperature=kwargs.get("temperature", 0.0),
                base_url=base_url,
                api_key=api_key,
            )
    elif provider == "google":
        return _create_google_provider(**kwargs)
    elif provider == "ollama":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("OLLAMA_ENDPOINT", "http://localhost:11434")
        else:
            base_url = kwargs.get("base_url")

        if "deepseek-r1" in kwargs.get("model_name", "qwen2.5:7b"):
            return DeepSeekR1ChatOllama(
                model=kwargs.get("model_name", "deepseek-r1:14b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                base_url=base_url,
            )
        else:
            return ChatOllama(
                model=kwargs.get("model_name", "qwen2.5:7b"),
                temperature=kwargs.get("temperature", 0.0),
                num_ctx=kwargs.get("num_ctx", 32000),
                num_predict=kwargs.get("num_predict", 1024),
                base_url=base_url,
            )
    elif provider == "azure_openai":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("AZURE_OPENAI_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        api_version = kwargs.get("api_version", "") or os.getenv(
            "AZURE_OPENAI_API_VERSION", "2025-01-01-preview"
        )
        return AzureChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o"),
            temperature=kwargs.get("temperature", 0.0),
            api_version=api_version,
            azure_endpoint=base_url,
            api_key=api_key,
        )
    elif provider == "alibaba":
        if not kwargs.get("base_url", ""):
            base_url = os.getenv(
                "ALIBABA_ENDPOINT", "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
        else:
            base_url = kwargs.get("base_url")

        return ChatOpenAI(
            model=kwargs.get("model_name", "qwen-plus"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=base_url,
            api_key=api_key,
        )
    elif provider == "ibm":
        parameters = {
            "temperature": kwargs.get("temperature", 0.0),
            "max_tokens": kwargs.get("num_ctx", 32000),
        }
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("IBM_ENDPOINT", "https://us-south.ml.cloud.ibm.com")
        else:
            base_url = kwargs.get("base_url")

        return ChatWatsonx(
            model_id=kwargs.get("model_name", "ibm/granite-vision-3.1-2b-preview"),
            url=base_url,
            project_id=os.getenv("IBM_PROJECT_ID"),
            apikey=os.getenv("IBM_API_KEY"),
            params=parameters,
        )
    elif provider == "moonshot":
        return ChatOpenAI(
            model=kwargs.get("model_name", "moonshot-v1-32k-vision-preview"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=os.getenv("MOONSHOT_ENDPOINT"),
            api_key=os.getenv("MOONSHOT_API_KEY"),
        )
    elif provider == "unbound":
        return ChatOpenAI(
            model=kwargs.get("model_name", "gpt-4o-mini"),
            temperature=kwargs.get("temperature", 0.0),
            base_url=os.getenv("UNBOUND_ENDPOINT", "https://api.getunbound.ai"),
            api_key=api_key,
        )
    elif provider == "siliconflow":
        if not kwargs.get("api_key", ""):
            api_key = os.getenv("SiliconFLOW_API_KEY", "")
        else:
            api_key = kwargs.get("api_key")
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("SiliconFLOW_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model_name=kwargs.get("model_name", "Qwen/QwQ-32B"),
            temperature=kwargs.get("temperature", 0.0),
        )
    elif provider == "modelscope":
        if not kwargs.get("api_key", ""):
            api_key = os.getenv("MODELSCOPE_API_KEY", "")
        else:
            api_key = kwargs.get("api_key")
        if not kwargs.get("base_url", ""):
            base_url = os.getenv("MODELSCOPE_ENDPOINT", "")
        else:
            base_url = kwargs.get("base_url")
        return ChatOpenAI(
            api_key=api_key,
            base_url=base_url,
            model_name=kwargs.get("model_name", "Qwen/QwQ-32B"),
            temperature=kwargs.get("temperature", 0.0),
        )
    else:
        raise ValueError(f"Unsupported provider: {provider}")
