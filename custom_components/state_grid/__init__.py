from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.const import Platform
from .const import DOMAIN
from .utils.store import async_load_from_store
from .data_client import StateGridDataClient
from . import click_captcha_solver

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """当用户在 UI 里点击"添加集成"并完成配置时调用。"""
    config = await async_load_from_store(hass, "state_grid.config") or None
    data_client = StateGridDataClient(hass=hass, config=config)

    # 如果 entry.data 中有 LLM 配置，优先使用
    if entry.data:
        llm_key = entry.data.get("llm_api_key", "")
        if llm_key and not data_client.llm_api_key:
            data_client.llm_api_key = llm_key
            data_client.llm_base_url = entry.data.get("llm_base_url", data_client.llm_base_url)
            data_client.llm_model = entry.data.get("llm_model", data_client.llm_model)
        # 备用邮箱（流控降级用）
        email_account = entry.data.get("email_account", "")
        if email_account:
            data_client.email_account = email_account

    # 确保至少有 LLM 配置（从 entry.data 或 config 中获取）
    if data_client.llm_api_key:
        click_captcha_solver.configure_llm(
            data_client.llm_api_key,
            data_client.llm_base_url,
            data_client.llm_model,
        )

    hass.data[DOMAIN] = data_client
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """卸载集成时调用。"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data.pop(DOMAIN, None)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """移除集成时不删除存储文件。"""
    return None
