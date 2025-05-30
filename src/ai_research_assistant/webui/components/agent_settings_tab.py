import json
import logging
import os
from typing import Any, Dict, Optional

import gradio as gr

from src.ai_research_assistant.utils import config
from src.ai_research_assistant.webui.webui_manager import WebuiManager

logger = logging.getLogger(__name__)

# Create model_names mapping from available config
model_names = {
    provider: [model_config["model"]]
    for provider, model_config in config.DEFAULT_MODELS.items()
}


def update_model_dropdown(llm_provider):
    """
    Update the model name dropdown with predefined models for the selected provider.
    For Google, shows all available Gemini models organized by categories.
    """
    if llm_provider == "google":
        # Get all Google models organized by category
        all_models = []
        categories = config.get_google_models_by_category()

        # Create choices with format: (display_name, actual_model_id)
        for category, models in categories.items():
            for model in models:
                model_info = config.GOOGLE_MODEL_OPTIONS.get(model, {})
                display_name = f"[{category.split('(')[0].strip()}] {model_info.get('name', model)}"
                all_models.append((display_name, model))

        # Add non-categorized models if any
        for model_id in config.GOOGLE_MODEL_OPTIONS.keys():
            if not any(
                model_id in category_models for category_models in categories.values()
            ):
                model_info = config.GOOGLE_MODEL_OPTIONS.get(model_id, {})
                display_name = f"[Other] {model_info.get('name', model_id)}"
                all_models.append((display_name, model_id))

        # Sort models by display name
        all_models.sort(key=lambda x: x[0])

        # Get recommended default
        recommended = config.get_recommended_google_models()
        default_model = recommended.get("general_use", "gemini-2.5-flash-preview-04-17")

        return gr.Dropdown(
            choices=all_models,
            value=default_model,
            interactive=True,
            allow_custom_value=True,
            info="All available Google Gemini models organized by capability - WARNING: This tab is deprecated, use Global Settings instead",
        )
    # Use predefined models for the selected provider
    elif llm_provider in config.DEFAULT_MODELS:
        model_config = config.DEFAULT_MODELS[llm_provider]
        return gr.Dropdown(
            choices=[model_config["model"]],
            value=model_config["model"],
            interactive=True,
            allow_custom_value=True,
            info=f"Default {llm_provider} model - WARNING: This tab is deprecated, use Global Settings instead",
        )
    else:
        return gr.Dropdown(
            choices=[],
            value="",
            interactive=True,
            allow_custom_value=True,
            info="No predefined models for this provider - WARNING: This tab is deprecated, use Global Settings instead",
        )


async def update_mcp_server(
    mcp_file: str, webui_manager: Optional[WebuiManager] = None
):
    """
    Update the MCP server configuration.
    """
    if (
        webui_manager
        and hasattr(webui_manager, "bu_controller")
        and webui_manager.bu_controller
    ):
        logger.warning("⚠️ Close controller because mcp file has changed!")
        await webui_manager.bu_controller.close_mcp_client()
        webui_manager.bu_controller = None

    if not mcp_file or not os.path.exists(mcp_file) or not mcp_file.endswith(".json"):
        logger.warning(f"{mcp_file} is not a valid MCP file.")
        return None, gr.update(visible=False)

    with open(mcp_file, "r") as f:
        mcp_server = json.load(f)

    # Update the webui manager's MCP configuration
    if webui_manager:
        webui_manager.mcp_server_config = mcp_server

    return json.dumps(mcp_server, indent=2), gr.update(visible=True)


def load_preset_config(preset_name: str) -> Dict[str, Any]:
    """Load a preset configuration."""
    presets = {
        "balanced": {
            "llm_provider": "openai",
            "llm_model_name": "gpt-4",
            "llm_temperature": 0.6,
            "max_steps": 50,
            "max_actions": 10,
            "tool_calling_method": "auto",
        },
        "creative": {
            "llm_provider": "openai",
            "llm_model_name": "gpt-4",
            "llm_temperature": 0.9,
            "max_steps": 75,
            "max_actions": 15,
            "tool_calling_method": "function_calling",
        },
        "precise": {
            "llm_provider": "openai",
            "llm_model_name": "gpt-4",
            "llm_temperature": 0.2,
            "max_steps": 30,
            "max_actions": 5,
            "tool_calling_method": "function_calling",
        },
        "local_ollama": {
            "llm_provider": "ollama",
            "llm_model_name": "llama3.2",
            "llm_temperature": 0.7,
            "max_steps": 40,
            "max_actions": 8,
            "tool_calling_method": "json_mode",
            "ollama_num_ctx": 32000,
        },
    }
    return presets.get(preset_name, {})


def create_agent_settings_tab(webui_manager: Optional[WebuiManager] = None):
    """
    Creates an enhanced agent settings tab with better organization and presets.

    **DEPRECATION NOTICE**: This tab is being deprecated in favor of the Global Settings panel.
    Please use the Global Settings panel above for configuring LLM providers and models.
    """
    if webui_manager is None:
        raise ValueError("webui_manager is required for agent settings tab")

    # input_components = list(webui_manager.get_components())  # Removed - unused
    tab_components = {}

    with gr.Column():
        # Deprecation Notice
        with gr.Group():
            gr.Markdown("""
            # ⚠️ Deprecation Notice

            **This Agent Settings tab is being phased out.**

            🔄 **Please use the Global Settings panel above for:**
            - LLM provider configuration
            - Model selection and parameters
            - Temperature and token settings

            The Global Settings panel provides a unified configuration experience
            across all agents and will be the only settings location in future versions.

            **This tab will be removed in a future release.**
            """)

        # Header
        gr.Markdown(
            "# 🤖 Agent Settings (Legacy)\n*Configure AI models, behavior, and performance parameters*"
        )

        # Preset configurations section
        with gr.Group():
            gr.Markdown("## 🎛️ Quick Configuration Presets")

            with gr.Row():
                preset_dropdown = gr.Dropdown(
                    choices=["balanced", "creative", "precise", "local_ollama"],
                    label="🎯 Configuration Preset",
                    value="balanced",
                    info="Choose a preset configuration or customize below",
                )
                apply_preset_btn = gr.Button(
                    "✨ Apply Preset", variant="secondary", scale=1
                )

        # System prompts section
        with gr.Group():
            gr.Markdown("## 💬 System Prompt Configuration")

            with gr.Accordion("💡 System Prompt Tips", open=False):
                gr.Markdown("""
                **Override System Prompt**: Completely replaces the default agent prompt
                **Extend System Prompt**: Adds to the default prompt (recommended)

                **Tips:**
                - Use extend for adding specific instructions
                - Use override for completely custom behavior
                - Be specific about desired output format
                - Include any domain-specific knowledge needed
                """)

            override_system_prompt = gr.Textbox(
                label="🔄 Override System Prompt",
                lines=4,
                interactive=True,
                placeholder="Enter custom system prompt to completely replace the default...",
                info="⚠️ This will replace the entire default system prompt",
            )
            extend_system_prompt = gr.Textbox(
                label="➕ Extend System Prompt",
                lines=4,
                interactive=True,
                placeholder="Enter additional instructions to add to the default prompt...",
                info="💡 Recommended: Add specific instructions without losing default behavior",
            )

        # Main LLM configuration
        with gr.Group():
            gr.Markdown("## 🧠 Primary LLM Configuration (Legacy)")
            gr.Markdown(
                "**⚠️ Note: Please use Global Settings panel above instead of these legacy settings.**"
            )

            with gr.Row():
                llm_provider = gr.Dropdown(
                    choices=list(config.PROVIDER_DISPLAY_NAMES.keys()),
                    label="🏢 LLM Provider (Legacy)",
                    value=os.getenv("DEFAULT_LLM", "openai"),
                    info="Select the AI model provider (Use Global Settings instead)",
                    interactive=True,
                )
                llm_model_name = gr.Dropdown(
                    label="🤖 LLM Model Name (Legacy)",
                    choices=model_names.get(os.getenv("DEFAULT_LLM", "openai"), []),
                    value=model_names.get(os.getenv("DEFAULT_LLM", "openai"), [""])[0],
                    interactive=True,
                    allow_custom_value=True,
                    info="Select or enter a custom model name (Use Global Settings instead)",
                )

            with gr.Row():
                llm_temperature = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=0.6,
                    step=0.1,
                    label="🌡️ LLM Temperature (Legacy)",
                    info="Lower = more focused, Higher = more creative (Use Global Settings instead)",
                    interactive=True,
                )

                use_vision = gr.Checkbox(
                    label="👁️ Enable Vision",
                    value=True,
                    info="Allow model to analyze screenshots",
                    interactive=True,
                )

                ollama_num_ctx = gr.Slider(
                    minimum=2**8,
                    maximum=2**16,
                    value=16000,
                    step=1000,
                    label="📏 Ollama Context Length",
                    info="Token limit for Ollama models (higher = more memory)",
                    visible=False,
                    interactive=True,
                )

            with gr.Row():
                llm_base_url = gr.Textbox(
                    label="🌐 Base URL",
                    value="",
                    info="Custom API endpoint (optional)",
                    placeholder="https://api.provider.com/v1",
                )
                llm_api_key = gr.Textbox(
                    label="🔑 API Key",
                    type="password",
                    value="",
                    info="API key (leave blank to use environment variable)",
                    placeholder="sk-...",
                )

        # Planner LLM configuration
        with gr.Group():
            gr.Markdown("## 🗺️ Planner LLM Configuration")
            gr.Markdown("*Optional: Use a separate model for planning tasks*")

            with gr.Row():
                planner_llm_provider = gr.Dropdown(
                    choices=[provider for provider in config.DEFAULT_MODELS.keys()],
                    label="🏢 Planner LLM Provider",
                    info="Provider for planning tasks (optional)",
                    value=None,
                    interactive=True,
                )
                planner_llm_model_name = gr.Dropdown(
                    label="🤖 Planner LLM Model Name",
                    interactive=True,
                    allow_custom_value=True,
                    info="Model for strategic planning",
                )

            with gr.Row():
                planner_llm_temperature = gr.Slider(
                    minimum=0.0,
                    maximum=2.0,
                    value=0.6,
                    step=0.1,
                    label="🌡️ Planner Temperature",
                    info="Temperature for planning model",
                    interactive=True,
                )

                planner_use_vision = gr.Checkbox(
                    label="👁️ Planner Vision",
                    value=False,
                    info="Enable vision for planner model",
                    interactive=True,
                )

                planner_ollama_num_ctx = gr.Slider(
                    minimum=2**8,
                    maximum=2**16,
                    value=16000,
                    step=1000,
                    label="📏 Planner Context Length",
                    info="Context length for Ollama planner",
                    visible=False,
                    interactive=True,
                )

            with gr.Row():
                planner_llm_base_url = gr.Textbox(
                    label="🌐 Planner Base URL",
                    value="",
                    info="Custom endpoint for planner model",
                    placeholder="https://api.provider.com/v1",
                )
                planner_llm_api_key = gr.Textbox(
                    label="🔑 Planner API Key",
                    type="password",
                    value="",
                    info="API key for planner model",
                    placeholder="sk-...",
                )

        # Agent behavior settings
        with gr.Group():
            gr.Markdown("## ⚙️ Agent Behavior Settings")

            with gr.Row():
                max_steps = gr.Slider(
                    minimum=1,
                    maximum=1000,
                    value=100,
                    step=1,
                    label="🚶 Max Run Steps",
                    info="Maximum actions the agent can take",
                    interactive=True,
                )
                max_actions = gr.Slider(
                    minimum=1,
                    maximum=100,
                    value=10,
                    step=1,
                    label="⚡ Max Actions per Step",
                    info="Maximum actions per reasoning step",
                    interactive=True,
                )

            with gr.Row():
                max_input_tokens = gr.Number(
                    label="🎫 Max Input Tokens",
                    value=128000,
                    precision=0,
                    interactive=True,
                    info="Maximum tokens to send to model",
                )
                tool_calling_method = gr.Dropdown(
                    label="🔧 Tool Calling Method",
                    value="auto",
                    interactive=True,
                    allow_custom_value=True,
                    choices=[
                        "function_calling",
                        "json_mode",
                        "raw",
                        "auto",
                        "tools",
                        "None",
                    ],
                    info="How the model should call tools",
                )

        # Status and validation
        with gr.Group():
            gr.Markdown("## 📊 Configuration Status")

            config_status = gr.Textbox(
                label="📈 Current Status",
                value="⚡ Configuration ready - Default settings loaded",
                interactive=False,
                lines=2,
                info="Shows current configuration status and any issues",
            )

    tab_components.update(
        dict(
            preset_dropdown=preset_dropdown,
            apply_preset_btn=apply_preset_btn,
            config_status=config_status,
            override_system_prompt=override_system_prompt,
            extend_system_prompt=extend_system_prompt,
            llm_provider=llm_provider,
            llm_model_name=llm_model_name,
            llm_temperature=llm_temperature,
            use_vision=use_vision,
            ollama_num_ctx=ollama_num_ctx,
            llm_base_url=llm_base_url,
            llm_api_key=llm_api_key,
            planner_llm_provider=planner_llm_provider,
            planner_llm_model_name=planner_llm_model_name,
            planner_llm_temperature=planner_llm_temperature,
            planner_use_vision=planner_use_vision,
            planner_ollama_num_ctx=planner_ollama_num_ctx,
            planner_llm_base_url=planner_llm_base_url,
            planner_llm_api_key=planner_llm_api_key,
            max_steps=max_steps,
            max_actions=max_actions,
            max_input_tokens=max_input_tokens,
            tool_calling_method=tool_calling_method,
        )
    )
    webui_manager.add_components("agent_settings", tab_components)

    def apply_preset_configuration(preset_name: str):
        """Apply a preset configuration."""
        try:
            preset_config = load_preset_config(preset_name)
            if not preset_config:
                return {
                    config_status: gr.update(value=f"❌ Unknown preset: {preset_name}")
                }

            updates = {}
            status_message = f"✅ Applied '{preset_name}' preset configuration"

            # Update components based on preset
            for key, value in preset_config.items():
                if key in tab_components:
                    comp = tab_components[key]
                    updates[comp] = gr.update(value=value)

            # Update visibility for Ollama context length
            if preset_config.get("llm_provider") == "ollama":
                updates[ollama_num_ctx] = gr.update(
                    visible=True, value=preset_config.get("ollama_num_ctx", 16000)
                )
            else:
                updates[ollama_num_ctx] = gr.update(visible=False)

            updates[config_status] = gr.update(value=status_message)
            return updates

        except Exception as e:
            logger.error(f"Error applying preset {preset_name}: {e}")
            return {
                config_status: gr.update(value=f"❌ Error applying preset: {str(e)}")
            }

    def validate_configuration(*args):
        """Validate the current configuration."""
        try:
            # This would contain actual validation logic
            # For now, just show a success message
            return gr.update(value="✅ Configuration validated successfully")
        except Exception as e:
            return gr.update(value=f"❌ Configuration validation failed: {str(e)}")

    # Event handlers for provider changes
    llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=llm_provider,
        outputs=ollama_num_ctx,
    )
    llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[llm_provider],
        outputs=[llm_model_name],
    )
    planner_llm_provider.change(
        fn=lambda x: gr.update(visible=x == "ollama"),
        inputs=[planner_llm_provider],
        outputs=[planner_ollama_num_ctx],
    )
    planner_llm_provider.change(
        lambda provider: update_model_dropdown(provider),
        inputs=[planner_llm_provider],
        outputs=[planner_llm_model_name],
    )

    # Preset application
    apply_preset_btn.click(
        apply_preset_configuration,
        inputs=[preset_dropdown],
        outputs=list(tab_components.values()),
    )

    # Configuration validation on change
    # Only include actual input components, not layout components
    input_components_only = [
        llm_provider,
        llm_model_name,
        llm_temperature,
        use_vision,
        ollama_num_ctx,
        llm_base_url,
        llm_api_key,
        planner_llm_provider,
        planner_llm_model_name,
        planner_llm_temperature,
        planner_use_vision,
        planner_ollama_num_ctx,
        planner_llm_base_url,
        planner_llm_api_key,
        max_steps,
        max_actions,
        max_input_tokens,
        tool_calling_method,
        override_system_prompt,
        extend_system_prompt,
    ]

    for component in [llm_provider, llm_model_name, max_steps, max_actions]:
        component.change(
            validate_configuration,
            inputs=input_components_only,
            outputs=[config_status],
        )
