import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import selector
from .const import DOMAIN, LLM_BASE_URL, LLM_MODEL
from .utils.logger import LOGGER
from .data_client import StateGridDataClient
from . import click_captcha_solver


class StateGridOnnxConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """国家电网集成的配置向导（手机号+邮箱降级登录）。"""

    VERSION = 12

    async def async_step_user(self, user_input=None):
        """配置步骤：输入手机号、邮箱（备用）、密码和 LLM 配置。"""
        LOGGER.debug("开始配置流程，user_input=%s", user_input)
        try:
            if self._async_current_entries():
                LOGGER.debug("已存在配置条目，中止")
                return self.async_abort(reason="single_instance_allowed")
            if self.hass.data.get(DOMAIN):
                LOGGER.debug("DOMAIN 已存在数据，中止")
                return self.async_abort(reason="single_instance_allowed")
        except Exception as e:
            LOGGER.debug("检查已存在配置时出错（可能首次配置）: %s", e)

        errors: dict[str, str] = {}
        phone: str = ""
        email: str = ""
        password: str = ""
        llm_api_key: str = ""
        llm_base_url: str = LLM_BASE_URL
        llm_model: str = LLM_MODEL

        if user_input is not None:
            phone = user_input.get("phone", "").strip()
            email = user_input.get("email", "").strip()
            password = user_input.get("password", "")
            llm_api_key = user_input.get("llm_api_key", "").strip()
            llm_base_url = user_input.get("llm_base_url", LLM_BASE_URL).strip()
            llm_model = user_input.get("llm_model", LLM_MODEL).strip()

            if not phone or not password:
                errors["base"] = "invalid_auth"
            elif not phone.isdigit():
                errors["base"] = "invalid_phone"
            elif email and "@" not in email:
                errors["base"] = "invalid_email"
            elif not llm_api_key:
                errors["base"] = "missing_llm_key"

            if not errors:
                dc = StateGridDataClient(hass=self.hass, config=None)
                dc.llm_api_key = llm_api_key
                dc.llm_base_url = llm_base_url
                dc.llm_model = llm_model
                dc.email_account = email

                click_captcha_solver.configure_llm(llm_api_key, llm_base_url, llm_model)

                try:
                    LOGGER.debug(
                        "开始登录国家电网，手机号=%s，备用邮箱=%s，LLM模型=%s",
                        phone, email or "未配置", llm_model,
                    )
                    result = await dc.password_login(phone, password, encode=False, retry=3)

                    # 如果手机号登录遇RK001流控，且配置了备用邮箱，自动降级到邮箱登录
                    if result.get("errcode") != 0 and email and (
                        result.get("rk001") or
                        "RK001" in (result.get("errmsg") or "") or
                        "流控" in (result.get("errmsg") or "")
                    ):
                        LOGGER.info("[配置流程] 手机号遇RK001流控，自动降级到邮箱登录: %s", email)
                        try:
                            import hashlib
                            pwd_md5 = hashlib.md5(password.encode()).hexdigest().upper()
                            result = await dc._login_with_email_fallback(pwd_md5, retry=2)
                        except Exception as fallback_exc:
                            LOGGER.exception("[配置流程] 邮箱降级登录异常: %s", fallback_exc)
                            result = {"errcode": 1, "errmsg": f"邮箱降级登录异常: {fallback_exc}"}

                except Exception as exc:
                    LOGGER.error("国家电网登录异常: %s", exc)
                    errors["base"] = "cannot_connect"
                else:
                    if result.get("errcode") == 0:
                        try:
                            await dc.save_data()
                        except Exception:
                            LOGGER.exception("保存 state_grid.config 失败，但登录成功。")
                        self.hass.data[DOMAIN] = dc
                        title = f"国家电网 - {phone}"
                        return self.async_create_entry(
                            title=title,
                            data={
                                "llm_api_key": llm_api_key,
                                "llm_base_url": llm_base_url,
                                "llm_model": llm_model,
                                "email_account": email,
                            },
                            options={
                                "billing_standard": "monthly_tiered",
                                "tier1_max": "240",
                                "tier2_max": "400",
                                "tier1_price": "0.4883",
                                "tier2_price": "0.5883",
                                "tier3_price": "0.7883",
                            },
                        )
                    else:
                        errmsg = (
                            result.get("errmsg")
                            or result.get("message")
                            or "登录失败，请检查账号密码或LLM配置"
                        )
                        LOGGER.warning("国家电网登录失败: %s", errmsg)
                        if "RK001" in errmsg or "流控" in errmsg or "日额度" in errmsg:
                            errors["base"] = "rk001_rate_limit"
                        else:
                            errors["base"] = "invalid_auth"

        data_schema = vol.Schema(
            {
                vol.Required("phone", default=phone): selector(
                    {"text": {"type": "text"}}
                ),
                vol.Optional("email", default=email): selector(
                    {"text": {"type": "text"}}
                ),
                vol.Required("password", default=password): selector(
                    {"text": {"type": "password"}}
                ),
                vol.Required("llm_api_key", default=llm_api_key): selector(
                    {"text": {"type": "password"}}
                ),
                vol.Optional("llm_base_url", default=llm_base_url): selector(
                    {"text": {"type": "text"}}
                ),
                vol.Optional("llm_model", default=llm_model): selector(
                    {"text": {"type": "text"}}
                ),
            }
        )
        return self.async_show_form(
            step_id="user",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "fallback_hint": "手机号登录遇RK001流控时，将自动降级为邮箱登录（需填写备用邮箱）"
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(entry: config_entries.ConfigEntry):
        """返回选项流程。"""
        return OptionsFlowHandler(entry)


BILLING_STANDARD_OPTIONS = [
    {"value": "monthly_tiered", "label": "月阶梯计费"},
    {"value": "yearly_tiered", "label": "年阶梯计费"},
    {"value": "average", "label": "平均单价"},
]


class OptionsFlowHandler(config_entries.OptionsFlow):
    """集成选项：LLM配置、刷新间隔、电费计费标准。"""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(self, user_input=None):
        """选项配置入口。"""
        current = {**(self._entry.data or {}), **(self._entry.options or {})}

        if user_input is not None:
            new_data = {}
            # LLM 配置
            for key in ("llm_api_key", "llm_base_url", "llm_model", "email_account"):
                raw_val = user_input.get(key)
                val = raw_val.strip() if isinstance(raw_val, str) else ""
                if val:
                    new_data[key] = val
                elif key in current and current[key]:
                    new_data[key] = current[key]

            # 刷新间隔
            refresh_interval = user_input.get("refresh_interval")
            if refresh_interval:
                try:
                    hours = int(str(refresh_interval).strip())
                    new_data["refresh_interval"] = max(12, min(48, hours))
                except (ValueError, TypeError):
                    pass

            # 电费计费标准
            billing_standard = user_input.get("billing_standard")
            if billing_standard:
                new_data["billing_standard"] = billing_standard

            # 阶梯参数
            for key in ("tier1_max", "tier2_max", "tier1_price", "tier2_price", "tier3_price"):
                val = user_input.get(key)
                if val is not None:
                    new_data[key] = str(val).strip()

            # 实时更新运行中的 data_client
            data_client = self.hass.data.get(DOMAIN)
            if data_client:
                for attr, key in (
                    ("llm_api_key", "llm_api_key"),
                    ("llm_base_url", "llm_base_url"),
                    ("llm_model", "llm_model"),
                    ("email_account", "email_account"),
                    ("refresh_interval", "refresh_interval"),
                ):
                    if key in new_data:
                        setattr(data_client, attr, new_data[key])
                if data_client.llm_api_key:
                    click_captcha_solver.configure_llm(
                        data_client.llm_api_key,
                        data_client.llm_base_url,
                        data_client.llm_model,
                    )

            return self.async_create_entry(title="", data=new_data)

        def _str(key, fallback=""):
            v = current.get(key)
            if v is None:
                return fallback
            if isinstance(v, str):
                return v
            return str(v)

        data_schema = vol.Schema(
            {
                vol.Optional(
                    "llm_api_key",
                    default="",
                ): selector({"text": {"type": "password"}}),
                vol.Optional(
                    "llm_base_url",
                    default=_str("llm_base_url", LLM_BASE_URL),
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "llm_model",
                    default=_str("llm_model", LLM_MODEL),
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "email_account",
                    default=_str("email_account", ""),
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "refresh_interval",
                    default=_str("refresh_interval", "12"),
                    description="刷新间隔（小时，填 12-48 之间的整数）",
                ): selector({"text": {"type": "text"}}),
                vol.Required(
                    "billing_standard",
                    default=_str("billing_standard", "monthly_tiered"),
                ): selector(
                    {
                        "select": {
                            "options": BILLING_STANDARD_OPTIONS,
                            "mode": "dropdown",
                        }
                    }
                ),
                vol.Optional(
                    "tier1_max",
                    default=_str("tier1_max", "240"),
                    description="第一阶梯档位（度）",
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "tier2_max",
                    default=_str("tier2_max", "400"),
                    description="第二阶梯档位（度）",
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "tier1_price",
                    default=_str("tier1_price", "0.4883"),
                    description="第一阶梯单价（元/度）",
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "tier2_price",
                    default=_str("tier2_price", "0.5883"),
                    description="第二阶梯单价（元/度）",
                ): selector({"text": {"type": "text"}}),
                vol.Optional(
                    "tier3_price",
                    default=_str("tier3_price", "0.7883"),
                    description="第三阶梯单价（元/度）",
                ): selector({"text": {"type": "text"}}),
            }
        )
        return self.async_show_form(step_id="init", data_schema=data_schema)
