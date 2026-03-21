"""Config flow for Anova Sous Vide."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult

from .client import AnovaSousVideClient
from .const import CONF_COOKER_ID, CONF_DEVICE_TYPE, CONF_PAT, DOMAIN

_LOGGER = logging.getLogger(__name__)


class AnovaSousVideConfigFlow(ConfigFlow, domain=DOMAIN):
    """Config flow for Anova Sous Vide integration."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._client: AnovaSousVideClient | None = None
        self._pat: str | None = None

    async def async_step_user(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle the PAT input step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            pat = user_input[CONF_PAT]

            if not pat.startswith("anova-"):
                errors["base"] = "invalid_token_format"
            else:
                client = AnovaSousVideClient()
                try:
                    await client.connect(pat)
                    devices = await client.discover_devices()
                except Exception:
                    _LOGGER.exception("Failed to connect to Anova")
                    errors["base"] = "cannot_connect"
                else:
                    if not devices:
                        await client.disconnect()
                        errors["base"] = "no_devices"
                    elif len(devices) == 1:
                        # Single device — auto-select
                        device = devices[0]
                        await self.async_set_unique_id(device.cooker_id)
                        self._abort_if_unique_id_configured()
                        await client.disconnect()
                        return self.async_create_entry(
                            title=device.name,
                            data={
                                CONF_PAT: pat,
                                CONF_COOKER_ID: device.cooker_id,
                                CONF_DEVICE_TYPE: device.device_type,
                            },
                        )
                    else:
                        # Multiple devices — let user pick
                        self._client = client
                        self._pat = pat
                        return await self.async_step_select_device()

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_PAT): str}),
            errors=errors,
        )

    async def async_step_select_device(
        self, user_input: dict[str, str] | None = None
    ) -> ConfigFlowResult:
        """Handle device selection when multiple devices are found."""
        assert self._client is not None
        assert self._pat is not None

        devices = self._client.discovered_devices

        if user_input is not None:
            cooker_id = user_input[CONF_COOKER_ID]
            device = next(d for d in devices if d.cooker_id == cooker_id)
            await self.async_set_unique_id(device.cooker_id)
            self._abort_if_unique_id_configured()
            await self._client.disconnect()
            return self.async_create_entry(
                title=device.name,
                data={
                    CONF_PAT: self._pat,
                    CONF_COOKER_ID: device.cooker_id,
                    CONF_DEVICE_TYPE: device.device_type,
                },
            )

        device_options = {d.cooker_id: d.name for d in devices}

        return self.async_show_form(
            step_id="select_device",
            data_schema=vol.Schema(
                {vol.Required(CONF_COOKER_ID): vol.In(device_options)}
            ),
        )
