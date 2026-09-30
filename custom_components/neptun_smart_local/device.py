from __future__ import annotations

import asyncio
import logging

import async_timeout
from asyncio.exceptions import InvalidStateError
from bitstring import BitArray
from homeassistant.core import HomeAssistant
from pymodbus import ModbusException
from pymodbus.exceptions import ModbusIOException

from .const import DEFAULT_DEVICE_ID, FALLBACK_DEVICE_IDS
from .hub import modbus_hub, registers_to_uint32, uint16_to_bits
from .registers import (
    DEVICE_ERROR_FLAGS,
    EXPANSION_MODULE_MAP,
    SE_DEVICE_TYPES,
    SIGNAL_LEVEL_MAP,
    VALVE_STATUS_MAP,
    WIRED_LINE_ERROR_MAP,
    NeptunSmartRegisters,
    NeptunSmartSERegisters,
)

_LOGGER = logging.getLogger(__name__)

MAX_WIRELESS_SENSORS = 50
COUNTER_SLOTS = 8
SE_PULSE_COUNTERS = 4
SE_DIGITAL_COUNTERS = 8
SE_HOLDING_HEADER_COUNT = 27
SE_COIL_COUNT = 28


class NeptunSmart:
    def __init__(
        self,
        hass: HomeAssistant,
        name,
        host_ip: str | None,
        host_port,
        device_id: int = DEFAULT_DEVICE_ID,
    ) -> None:
        self._name = name
        self._hass = hass
        self._preferred_device_id = int(device_id)
        self._hub = modbus_hub(hass=hass, host=host_ip, port=host_port, device_id=device_id)
        self._io_lock = asyncio.Lock()
        self._is_se = False
        self._protocol_detected = False
        self._device_type_code = None
        self._firmware = None
        self._pcb_version = None
        self._supply_voltage_mv = None
        self._error_code = 0
        self._expansion_modules = 0
        self._valve_status = [0, 0]
        self._close_valve_when_low_voltage = False
        self._sensor_feedback = False
        self._elp_mode = False
        self._close_on_elp = False
        self._elp_leak = False
        self._supply_voltage_problem = False
        self._group_closed_lost_sensor = [False, False, False]
        self._wired_line_errors = 0
        self._overconsumption = False
        self._line_type = [0, 0, 0, 0, 0]
        self._line_group = [0, 0, 0, 0, 0]
        self._line_status = [False, False, False, False, False]
        self.wireless_sensors = []
        self.counters = []
        self._wireless_sensors_connected = 0

        self._first_group_valve_is_open = False
        self._second_group_valve_is_open = False
        self._floor_washing_mode = False
        self._first_group_alarm = False
        self._second_group_alarm = False
        self._discharge_wireless_sensors = False
        self._lost_wireless_sensors = False
        self._connecting_wireless_sensors_mode = False
        self._dual_group_mode = False
        self._close_valve_when_loss_sensor = False
        self._lock_buttons = False
        self._switch_when_close_valve = 0
        self._switch_when_alert = 0

        self._config_bits = None
        self._config_line_1_2_bits = None
        self._config_line_3_4_bits = None
        self._status_wired_line_bits = None
        self._relay_config_bits = None

        self._connection_attempts = 0
        self._last_connection_attempt = 0
        self._is_connected = False

    def is_se(self) -> bool:
        return self._is_se

    def get_model(self) -> str:
        if self._device_type_code in SE_DEVICE_TYPES:
            return SE_DEVICE_TYPES[self._device_type_code]
        return "Neptun Smart"

    def get_firmware(self):
        return self._firmware

    def get_pcb_version(self):
        return self._pcb_version

    def get_supply_voltage(self):
        if self._supply_voltage_mv is None:
            return None
        return round(self._supply_voltage_mv / 1000, 3)

    def get_supply_voltage_problem(self) -> bool:
        return self._supply_voltage_problem

    def get_elp_leak(self) -> bool:
        return self._elp_leak

    def get_elp_mode(self) -> bool:
        return self._elp_mode

    def get_close_on_elp(self) -> bool:
        return self._close_on_elp

    def get_close_valve_when_low_voltage(self) -> bool:
        return self._close_valve_when_low_voltage

    def get_sensor_feedback(self) -> bool:
        return self._sensor_feedback

    def get_error_code(self) -> int:
        return int(self._error_code)

    def get_error_names(self) -> list[str]:
        code = int(self._error_code)
        if code == 0:
            return []
        return [name for flag, name in DEVICE_ERROR_FLAGS.items() if code & flag]

    def get_expansion_modules(self) -> dict[str, str]:
        value = int(self._expansion_modules)
        return {
            "слот_1": EXPANSION_MODULE_MAP.get(value & 0xFF, "Неизвестный"),
            "слот_2": EXPANSION_MODULE_MAP.get((value >> 8) & 0xFF, "Неизвестный"),
        }

    def get_valve_status(self, group: int) -> int:
        if group in (1, 2):
            return self._valve_status[group - 1]
        return 0

    def get_valve_status_text(self, group: int, valve: int = 1) -> str:
        status = self.get_valve_status(group)
        nibble = (status >> ((valve - 1) * 4)) & 0x0F
        return VALVE_STATUS_MAP.get(nibble, str(nibble))

    def get_wired_line_error(self, line_number: int) -> int:
        shift = (line_number - 1) * 2
        return (int(self._wired_line_errors) >> shift) & 0x03

    def get_wired_line_error_text(self, line_number: int) -> str:
        return WIRED_LINE_ERROR_MAP.get(self.get_wired_line_error(line_number), "Неизвестно")

    def get_group_closed_lost_sensor(self, group: int) -> bool:
        if group in (1, 2):
            return self._group_closed_lost_sensor[group]
        return False

    async def init_sensors(self):
        """Обнаружить протокол и загрузить сущности до запуска платформ HA."""
        try:
            await self._hub.connect()
        except (ValueError, asyncio.CancelledError) as e:
            _LOGGER.error(f"Не удалось подключиться к устройству {self._name}: {e}")
            return

        try:
            async with self._io_lock:
                if not await self._detect_protocol_unlocked():
                    _LOGGER.error(f"Не удалось определить тип модуля {self._name}")
                    return
                if self._is_se:
                    await self._init_se_sensors_unlocked()
                else:
                    await self._init_classic_sensors_unlocked()
        except Exception as e:
            _LOGGER.error(f"Ошибка при инициализации датчиков для {self._name}: {e}")

    async def _detect_protocol_unlocked(self) -> bool:
        """Проверить заданный Modbus ID, затем типичные адреса устройств."""
        ids_to_try = [self._preferred_device_id]
        for device_id in FALLBACK_DEVICE_IDS:
            if device_id not in ids_to_try:
                ids_to_try.append(device_id)

        for device_id in ids_to_try:
            self._hub.set_device_id(device_id)
            header = await self._hub.read_holding_registers(0, 1)
            if not header:
                continue
            self._protocol_detected = True
            type_code = header[0]
            if type_code in SE_DEVICE_TYPES:
                self._is_se = True
                self._device_type_code = type_code
                _LOGGER.info(
                    "Обнаружен %s (%s), Modbus id=%s",
                    SE_DEVICE_TYPES[type_code],
                    self._name,
                    device_id,
                )
            else:
                self._is_se = False
                self._device_type_code = None
                _LOGGER.info(
                    "Обнаружен классический Neptun Smart (%s), Modbus id=%s",
                    self._name,
                    device_id,
                )
            return True
        self._protocol_detected = False
        return False

    async def _init_classic_sensors_unlocked(self):
        count = await self._hub.read_holding_register_uint16(
            NeptunSmartRegisters.count_of_connected_wireless_sensors, 1)

        if count is None:
            _LOGGER.debug(
                "Не удалось получить количество подключенных беспроводных датчиков, используем значение по умолчанию 0")
            count = 0

        self._wireless_sensors_connected = min(int(count), MAX_WIRELESS_SENSORS)
        await self._update_wireless_sensors_unlocked()

        counter_configs = await self._hub.read_holding_registers(
            NeptunSmartRegisters.first_counter_config, COUNTER_SLOTS)
        counter_values = await self._hub.read_holding_registers(
            NeptunSmartRegisters.first_counter, COUNTER_SLOTS * 2)
        if counter_configs and counter_values:
            for i in range(COUNTER_SLOTS):
                bits = uint16_to_bits(counter_configs[i])
                if bits[15] == 1:
                    value = registers_to_uint32(
                        counter_values[i * 2], counter_values[i * 2 + 1])
                    self.counters.append(
                        Counter(
                            value,
                            NeptunSmartRegisters.first_counter + (i * 2),
                            self._hub,
                            high_first=True,
                            number=i + 1,
                            kind="pulse",
                        )
                    )
        else:
            _LOGGER.debug("Не удалось прочитать блок счетчиков")

    async def _init_se_sensors_unlocked(self):
        header = await self._hub.read_holding_registers(
            NeptunSmartSERegisters.device_type, SE_HOLDING_HEADER_COUNT)
        if header and len(header) >= SE_HOLDING_HEADER_COUNT:
            self._apply_se_holding_header(header)

        coils = await self._hub.read_coils(0, SE_COIL_COUNT)
        if coils:
            self._apply_se_coils(coils)
        discrete = await self._read_se_discrete_unlocked()
        if discrete:
            self._apply_se_discrete(discrete)

        await self._update_wireless_sensors_unlocked()

        pulse_values = await self._hub.read_holding_registers(
            NeptunSmartSERegisters.first_pulse_counter, SE_PULSE_COUNTERS * 3)
        if coils and pulse_values:
            for i in range(SE_PULSE_COUNTERS):
                enabled = coils[NeptunSmartSERegisters.coil_pulse_counter_1_enable + i * 2]
                if enabled:
                    low = pulse_values[i * 3]
                    high = pulse_values[i * 3 + 1]
                    self.counters.append(
                        Counter(
                            registers_to_uint32(high, low),
                            NeptunSmartSERegisters.first_pulse_counter + (i * 3),
                            self._hub,
                            high_first=False,
                            number=i + 1,
                            kind="pulse",
                        )
                    )

        digital_values = await self._hub.read_holding_registers(
            NeptunSmartSERegisters.first_digital_counter, SE_DIGITAL_COUNTERS * 6)
        if digital_values:
            for i in range(SE_DIGITAL_COUNTERS):
                base = i * 6
                if digital_values[base]:
                    low = digital_values[base + 4]
                    high = digital_values[base + 5]
                    self.counters.append(
                        Counter(
                            registers_to_uint32(high, low),
                            NeptunSmartSERegisters.first_digital_counter + base + 4,
                            self._hub,
                            high_first=False,
                            number=i + 1,
                            kind="digital",
                        )
                    )

        extra = await self._hub.read_holding_registers(NeptunSmartSERegisters.error_code, 1)
        if extra:
            self._error_code = extra[0]
        modules = await self._hub.read_holding_register_uint16(
            NeptunSmartSERegisters.expansion_modules)
        if modules is not None:
            self._expansion_modules = modules

    async def async_close(self):
        await self._hub.disconnect()

    async def _check_and_reconnect(self):
        """Проверяет подключение и пытается переподключиться при необходимости"""
        try:
            if hasattr(self._hub, '_client') and self._hub._client.connected:
                self._is_connected = True
                return True

            _LOGGER.info(f"Попытка подключения к устройству {self._name}")
            await self._hub.connect()
            await asyncio.sleep(0.2)

            self._is_connected = True
            _LOGGER.info(f"Успешно подключились к устройству {self._name}")
            return True
        except Exception as e:
            _LOGGER.error(f"Не удалось подключиться к устройству {self._name}: {e}")
            self._is_connected = False
            return False

    def _apply_module_config_bits(self, bits):
        self._config_bits = bits
        self._first_group_valve_is_open = bool(bits[7])
        self._second_group_valve_is_open = bool(bits[6])
        self._floor_washing_mode = bool(bits[15])
        self._first_group_alarm = bool(bits[14])
        self._second_group_alarm = bool(bits[13])
        self._discharge_wireless_sensors = bool(bits[12])
        self._lost_wireless_sensors = bool(bits[11])
        self._connecting_wireless_sensors_mode = bool(bits[8])
        self._dual_group_mode = bool(bits[5])
        self._close_valve_when_loss_sensor = bool(bits[4])
        self._lock_buttons = bool(bits[3])

    def _apply_line_1_2_bits(self, bits):
        self._config_line_1_2_bits = bits
        self._line_type[1] = int(bool(bits[5]))
        self._line_type[2] = int(bool(bits[13]))
        self._line_group[1] = BitArray([bits[6], bits[7]])._getuint()
        self._line_group[2] = BitArray([bits[14], bits[15]])._getuint()

    def _apply_line_3_4_bits(self, bits):
        self._config_line_3_4_bits = bits
        self._line_type[3] = int(bool(bits[5]))
        self._line_type[4] = int(bool(bits[13]))
        self._line_group[3] = BitArray([bits[6], bits[7]])._getuint()
        self._line_group[4] = BitArray([bits[14], bits[15]])._getuint()

    def _apply_wired_status_bits(self, bits):
        self._status_wired_line_bits = bits
        self._line_status[1] = bool(bits[15])
        self._line_status[2] = bool(bits[14])
        self._line_status[3] = bool(bits[13])
        self._line_status[4] = bool(bits[12])

    def _apply_relay_config_bits(self, bits):
        self._relay_config_bits = bits
        self._switch_when_close_valve = BitArray([bits[12], bits[13]])._getuint()
        self._switch_when_alert = BitArray([bits[14], bits[15]])._getuint()

    def _parse_firmware(self, value: int):
        patch = value & 0x0F
        minor = (value >> 4) & 0x0F
        major = (value >> 8) & 0x0F
        self._pcb_version = (value >> 12) & 0x0F
        self._firmware = f"{major}.{minor}.{patch}"

    def _apply_se_holding_header(self, registers):
        self._device_type_code = registers[NeptunSmartSERegisters.device_type]
        self._parse_firmware(registers[NeptunSmartSERegisters.firmware])
        self._valve_status[0] = registers[NeptunSmartSERegisters.valve_status_group_1]
        self._valve_status[1] = registers[NeptunSmartSERegisters.valve_status_group_2]
        relay = registers[NeptunSmartSERegisters.relay_config]
        self._switch_when_alert = relay & 0x03
        self._switch_when_close_valve = (relay >> 2) & 0x03
        self._supply_voltage_mv = registers[NeptunSmartSERegisters.supply_voltage]
        for line in range(1, 5):
            type_addr = NeptunSmartSERegisters.line_1_type + (line - 1) * 2
            group_addr = type_addr + 1
            self._line_type[line] = registers[type_addr] & 0x03
            self._line_group[line] = registers[group_addr] & 0x03
        status = registers[NeptunSmartSERegisters.wired_line_status]
        for line in range(1, 5):
            self._line_status[line] = bool(status & (1 << (line - 1)))
        self._wired_line_errors = registers[NeptunSmartSERegisters.wired_line_errors]
        self._wireless_sensors_connected = min(
            int(registers[NeptunSmartSERegisters.count_of_connected_wireless_sensors]),
            MAX_WIRELESS_SENSORS,
        )

    def _apply_se_coils(self, coils):
        se = NeptunSmartSERegisters
        self._floor_washing_mode = coils[se.coil_floor_washing]
        self._dual_group_mode = coils[se.coil_dual_group]
        self._first_group_valve_is_open = coils[se.coil_valve_group_1]
        self._second_group_valve_is_open = coils[se.coil_valve_group_2]
        self._close_valve_when_loss_sensor = coils[se.coil_close_on_lost_sensor]
        self._close_valve_when_low_voltage = coils[se.coil_close_on_low_voltage]
        self._lock_buttons = coils[se.coil_lock_buttons]
        self._sensor_feedback = coils[se.coil_sensor_feedback]
        self._connecting_wireless_sensors_mode = coils[se.coil_pairing_wireless]
        if len(coils) > se.coil_elp_mode:
            self._elp_mode = coils[se.coil_elp_mode]
        if len(coils) > se.coil_close_on_elp:
            self._close_on_elp = coils[se.coil_close_on_elp]

    def _apply_se_discrete(self, discrete):
        se = NeptunSmartSERegisters
        self._floor_washing_mode = discrete[se.di_floor_washing]
        self._first_group_alarm = discrete[se.di_alarm_group_1]
        self._second_group_alarm = discrete[se.di_alarm_group_2]
        self._discharge_wireless_sensors = discrete[se.di_wireless_battery_low]
        self._lost_wireless_sensors = discrete[se.di_wireless_lost]
        self._group_closed_lost_sensor[1] = discrete[se.di_group_1_closed_lost_sensor]
        self._group_closed_lost_sensor[2] = discrete[se.di_group_2_closed_lost_sensor]
        self._supply_voltage_problem = discrete[se.di_supply_voltage_problem]
        self._first_group_valve_is_open = discrete[se.di_valve_group_1_open]
        self._second_group_valve_is_open = discrete[se.di_valve_group_2_open]
        self._dual_group_mode = discrete[se.di_dual_group]
        self._lock_buttons = discrete[se.di_lock_buttons]
        self._sensor_feedback = discrete[se.di_sensor_feedback]
        if len(discrete) > se.di_pairing_wireless:
            self._connecting_wireless_sensors_mode = discrete[se.di_pairing_wireless]
        if len(discrete) > se.di_elp_leak:
            self._elp_leak = discrete[se.di_elp_leak]
        if len(discrete) > se.di_overconsumption:
            self._overconsumption = discrete[se.di_overconsumption]

    async def _read_se_discrete_unlocked(self):
        """Read SE discrete inputs in two chunks to stay within small PDU limits."""
        main = await self._hub.read_discrete_inputs(0, 32)
        if not main:
            return None
        discrete = list(main)
        extra = await self._hub.read_discrete_inputs(NeptunSmartSERegisters.di_elp_leak, 4)
        if extra:
            if len(discrete) < NeptunSmartSERegisters.di_elp_leak:
                discrete.extend([False] * (NeptunSmartSERegisters.di_elp_leak - len(discrete)))
            discrete.extend(extra)
        return discrete

    async def _update_wireless_sensors_unlocked(self) -> None:
        """Обновить известные слоты и создать объекты вновь зарегистрированных датчиков."""
        count = min(self._wireless_sensors_connected, MAX_WIRELESS_SENSORS)
        if count == 0:
            return
        # В классическом протоколе и Smart SE блоки датчиков имеют разные адреса.
        first_config = (
            NeptunSmartSERegisters.first_wireless_sensor_config
            if self._is_se
            else NeptunSmartRegisters.first_wireless_sensor_config
        )
        first_status = (
            NeptunSmartSERegisters.first_wireless_sensor_status
            if self._is_se
            else NeptunSmartRegisters.first_wireless_sensor_status
        )
        configs = await self._hub.read_holding_registers(first_config, count)
        statuses = await self._hub.read_holding_registers(first_status, count)
        if not configs or not statuses:
            _LOGGER.debug("Не удалось получить блок данных беспроводных датчиков")
            return
        for index in range(count):
            status_bits = uint16_to_bits(statuses[index])
            if index < len(self.wireless_sensors):
                self.wireless_sensors[index].update_data(configs[index], status_bits)
            else:
                self.wireless_sensors.append(
                    WirelessSensor(
                        self._hub,
                        self._io_lock,
                        first_config + index,
                        first_status + index,
                        configs[index],
                        status_bits,
                    )
                )

    async def _update_counters_unlocked(self):
        if not self.counters:
            return
        if self._is_se:
            pulse_values = await self._hub.read_holding_registers(
                NeptunSmartSERegisters.first_pulse_counter, SE_PULSE_COUNTERS * 3)
            digital_values = await self._hub.read_holding_registers(
                NeptunSmartSERegisters.first_digital_counter, SE_DIGITAL_COUNTERS * 6)
            for counter in self.counters:
                address = counter.get_address()
                if (
                    pulse_values
                    and NeptunSmartSERegisters.first_pulse_counter
                    <= address
                    < NeptunSmartSERegisters.first_pulse_counter + SE_PULSE_COUNTERS * 3
                ):
                    offset = address - NeptunSmartSERegisters.first_pulse_counter
                    if 0 <= offset < len(pulse_values) - 1:
                        counter.set_value(
                            registers_to_uint32(pulse_values[offset + 1], pulse_values[offset])
                        )
                elif digital_values:
                    offset = address - NeptunSmartSERegisters.first_digital_counter
                    if 0 <= offset < len(digital_values) - 1:
                        counter.set_value(
                            registers_to_uint32(digital_values[offset + 1], digital_values[offset])
                        )
            return

        values = await self._hub.read_holding_registers(
            NeptunSmartRegisters.first_counter, COUNTER_SLOTS * 2)
        if not values:
            _LOGGER.debug("Не удалось получить блок показаний счетчиков")
            return
        for counter in self.counters:
            offset = counter.get_address() - NeptunSmartRegisters.first_counter
            if 0 <= offset < len(values) - 1:
                counter.set_value(registers_to_uint32(values[offset], values[offset + 1]))

    async def _update_classic_unlocked(self) -> bool:
        registers = await self._hub.read_holding_registers(
            NeptunSmartRegisters.module_config, 7)
        if not registers or len(registers) < 7:
            _LOGGER.debug("Не удалось получить блок конфигурации модуля")
            self._is_connected = False
            return False

        self._is_connected = True
        self._apply_module_config_bits(uint16_to_bits(registers[0]))
        self._apply_line_1_2_bits(uint16_to_bits(registers[1]))
        self._apply_line_3_4_bits(uint16_to_bits(registers[2]))
        self._apply_wired_status_bits(uint16_to_bits(registers[3]))
        self._apply_relay_config_bits(uint16_to_bits(registers[4]))
        self._wireless_sensors_connected = registers[6]

        await self._update_wireless_sensors_unlocked()
        await self._update_counters_unlocked()
        return True

    async def _update_se_unlocked(self) -> bool:
        header = await self._hub.read_holding_registers(
            NeptunSmartSERegisters.device_type, SE_HOLDING_HEADER_COUNT)
        coils = await self._hub.read_coils(0, SE_COIL_COUNT)
        discrete = await self._read_se_discrete_unlocked()
        if not header or len(header) < SE_HOLDING_HEADER_COUNT or not discrete:
            _LOGGER.debug("Не удалось получить блок данных Smart SE")
            self._is_connected = False
            return False

        self._is_connected = True
        self._apply_se_holding_header(header)
        if coils:
            self._apply_se_coils(coils)
        self._apply_se_discrete(discrete)

        modules = await self._hub.read_holding_register_uint16(
            NeptunSmartSERegisters.expansion_modules)
        if modules is not None:
            self._expansion_modules = modules
        error_code = await self._hub.read_holding_register_uint16(
            NeptunSmartSERegisters.error_code)
        if error_code is not None:
            self._error_code = error_code

        await self._update_wireless_sensors_unlocked()
        await self._update_counters_unlocked()
        return True

    async def update(self) -> bool:
        async with self._io_lock:
            try:
                if not await self._check_and_reconnect():
                    _LOGGER.debug(f"Не удалось подключиться к устройству {self._name}, пропускаем обновление")
                    self._is_connected = False
                    return False

                timeout = 25 if (self._is_se or not self._protocol_detected) else 15
                async with async_timeout.timeout(timeout):
                    if not self._protocol_detected and not await self._detect_protocol_unlocked():
                        self._is_connected = False
                        return False
                    if self._is_se:
                        return await self._update_se_unlocked()
                    return await self._update_classic_unlocked()
            except TimeoutError:
                _LOGGER.warning(f"Polling timed out for {self._name} - устройство не отвечает")
                self._connection_attempts = 0
                self._is_connected = False
                return False
            except ModbusIOException as value_error:
                _LOGGER.warning(f"ModbusIOException for {self._name}: {value_error.string}")
                self._connection_attempts = 0
                self._is_connected = False
                return False
            except ModbusException as value_error:
                _LOGGER.warning(f"ModbusException for {self._name}: {value_error.string}")
                self._connection_attempts = 0
                self._is_connected = False
                return False
            except InvalidStateError:
                _LOGGER.error(f"InvalidStateError Exceptions for {self._name}")
                self._is_connected = False
                return False
            except Exception as e:
                _LOGGER.error(f"Неожиданная ошибка при обновлении {self._name}: {e}")
                self._is_connected = False
                return False

    def get_discharge_wireless_sensors(self) -> bool:
        return self._discharge_wireless_sensors

    def get_lost_wireless_sensors(self) -> bool:
        return self._lost_wireless_sensors

    def get_number_of_connected_wireless_sensors(self):
        return self._wireless_sensors_connected

    def get_name(self):
        return self._name

    def get_first_group_alarm(self):
        return self._first_group_alarm

    def get_second_group_alarm(self):
        return self._second_group_alarm

    def get_first_group_valve_state(self):
        return self._first_group_valve_is_open

    async def _read_module_config_bits_unlocked(self):
        bits = await self._hub.read_holding_register_bits(NeptunSmartRegisters.module_config, 1)
        if bits is None or len(bits) < 16:
            raise RuntimeError("Не удалось прочитать конфигурацию модуля перед записью")
        return bits

    async def _write_module_config_bits_unlocked(self, bits):
        await self._hub.write_holding_register_bits(NeptunSmartRegisters.module_config, bits)
        self._apply_module_config_bits(bits)

    async def _modify_module_config_unlocked(self, mutator):
        bits = await self._read_module_config_bits_unlocked()
        mutator(bits)
        await self._write_module_config_bits_unlocked(bits)

    async def _write_se_coil_unlocked(self, address, state):
        await self._hub.write_coil(address, bool(state))

    async def set_first_group_valve_state(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_valve_group_1, state)
                self._first_group_valve_is_open = bool(state)
                if not self._dual_group_mode:
                    await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_valve_group_2, state)
                    self._second_group_valve_is_open = bool(state)
                return

            def mutate(bits):
                bits[7] = int(state)
                # В режиме одной группы оба крана должны переключаться одной записью
                if not bits[5]:
                    bits[6] = int(state)

            await self._modify_module_config_unlocked(mutate)

    def get_second_group_valve_state(self):
        return self._second_group_valve_is_open

    async def set_second_group_valve_state(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_valve_group_2, state)
                self._second_group_valve_is_open = bool(state)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(6, int(state)))

    def get_floor_washing_mode(self):
        return self._floor_washing_mode

    async def set_floor_washing_mode(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_floor_washing, state)
                self._floor_washing_mode = bool(state)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(15, int(state)))

    def get_connecting_wireless_sensors_mode(self):
        return self._connecting_wireless_sensors_mode

    async def set_connecting_wireless_sensors_mode(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_pairing_wireless, state)
                self._connecting_wireless_sensors_mode = bool(state)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(8, int(state)))

    def get_dual_group_mode(self):
        return self._dual_group_mode

    def is_connected(self):
        """Возвращает состояние подключения к устройству"""
        return self._is_connected

    async def set_dual_group_mode(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_dual_group, state)
                self._dual_group_mode = bool(state)
                if state:
                    for i in (1, 2, 3, 4):
                        await self._set_line_group_unlocked(i, 3)
                    for sensor in self.wireless_sensors:
                        await sensor.set_group_config_unlocked(3)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(5, int(state)))
            # При включении двух групп привязываем линии и датчики к обеим зонам.
            # При выключении прежние привязки не трогаем.
            if state:
                for i in (1, 2, 3, 4):
                    await self._set_line_group_unlocked(i, 3)
                for sensor in self.wireless_sensors:
                    await sensor.set_group_config_unlocked(3)

    def get_close_valve_when_lost_sensors_mode(self):
        return self._close_valve_when_loss_sensor

    async def set_close_valve_when_lost_sensors_mode(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(
                    NeptunSmartSERegisters.coil_close_on_lost_sensor, state)
                self._close_valve_when_loss_sensor = bool(state)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(4, int(state)))

    def get_lock_buttons(self):
        return self._lock_buttons

    async def set_lock_buttons(self, state):
        async with self._io_lock:
            if self._is_se:
                await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_lock_buttons, state)
                self._lock_buttons = bool(state)
                return
            await self._modify_module_config_unlocked(lambda bits: bits.__setitem__(3, int(state)))

    async def set_close_valve_when_low_voltage(self, state):
        async with self._io_lock:
            await self._write_se_coil_unlocked(
                NeptunSmartSERegisters.coil_close_on_low_voltage, state)
            self._close_valve_when_low_voltage = bool(state)

    async def set_sensor_feedback(self, state):
        async with self._io_lock:
            await self._write_se_coil_unlocked(
                NeptunSmartSERegisters.coil_sensor_feedback, state)
            self._sensor_feedback = bool(state)

    async def set_elp_mode(self, state):
        async with self._io_lock:
            await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_elp_mode, state)
            self._elp_mode = bool(state)

    async def set_close_on_elp(self, state):
        async with self._io_lock:
            await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_close_on_elp, state)
            self._close_on_elp = bool(state)

    async def reset_alarm(self):
        async with self._io_lock:
            await self._write_se_coil_unlocked(NeptunSmartSERegisters.coil_reset_alarm, True)

    def get_line_config_type(self, line_number):
        return self._line_type[line_number]

    def _line_register_and_type_indices(self, line_number):
        if line_number == 1:
            return NeptunSmartRegisters.input_line_1_2_config, 4, 5
        if line_number == 2:
            return NeptunSmartRegisters.input_line_1_2_config, 12, 13
        if line_number == 3:
            return NeptunSmartRegisters.input_line_3_4_config, 4, 5
        if line_number == 4:
            return NeptunSmartRegisters.input_line_3_4_config, 12, 13
        raise ValueError(f"Неизвестный номер линии: {line_number}")

    def _line_register_and_group_indices(self, line_number):
        if line_number == 1:
            return NeptunSmartRegisters.input_line_1_2_config, 6, 7
        if line_number == 2:
            return NeptunSmartRegisters.input_line_1_2_config, 14, 15
        if line_number == 3:
            return NeptunSmartRegisters.input_line_3_4_config, 6, 7
        if line_number == 4:
            return NeptunSmartRegisters.input_line_3_4_config, 14, 15
        raise ValueError(f"Неизвестный номер линии: {line_number}")

    def _apply_line_bits_for_register(self, address, bits):
        if address == NeptunSmartRegisters.input_line_1_2_config:
            self._apply_line_1_2_bits(bits)
        else:
            self._apply_line_3_4_bits(bits)

    async def _read_line_bits_unlocked(self, address):
        bits = await self._hub.read_holding_register_bits(address, 1)
        if bits is None or len(bits) < 16:
            raise RuntimeError(f"Не удалось прочитать конфигурацию линий (регистр {address})")
        return bits

    def _se_line_type_address(self, line_number):
        return NeptunSmartSERegisters.line_1_type + (line_number - 1) * 2

    def _se_line_group_address(self, line_number):
        return self._se_line_type_address(line_number) + 1

    async def set_line_type(self, line_number, state):
        async with self._io_lock:
            value = int(state)
            if self._is_se:
                await self._hub.write_holding_register(self._se_line_type_address(line_number), value)
                self._line_type[line_number] = value
                return
            address, high_idx, low_idx = self._line_register_and_type_indices(line_number)
            bits = await self._read_line_bits_unlocked(address)
            bits[high_idx] = 0
            bits[low_idx] = int(bool(state))
            await self._hub.write_holding_register_bits(address, bits)
            self._apply_line_bits_for_register(address, bits)

    def get_line_group(self, line_number):
        return self._line_group[line_number]

    async def _set_line_group_unlocked(self, line_number, state):
        if self._is_se:
            await self._hub.write_holding_register(self._se_line_group_address(line_number), int(state))
            self._line_group[line_number] = int(state)
            return
        address, high_idx, low_idx = self._line_register_and_group_indices(line_number)
        bits = await self._read_line_bits_unlocked(address)
        if state == 1:
            bits[high_idx] = 0
            bits[low_idx] = 1
        elif state == 2:
            bits[high_idx] = 1
            bits[low_idx] = 0
        else:
            bits[high_idx] = 1
            bits[low_idx] = 1
        await self._hub.write_holding_register_bits(address, bits)
        self._apply_line_bits_for_register(address, bits)

    async def set_line_group(self, line_number, state):
        async with self._io_lock:
            await self._set_line_group_unlocked(line_number, state)

    def get_line_status(self, line_number):
        return self._line_status[line_number]

    def get_relay_config_valve(self) -> int:
        return int(self._switch_when_close_valve)

    def _encode_two_bit_value(self, bits, high_idx, low_idx, state):
        value = int(state) & 0x03
        bits[high_idx] = (value >> 1) & 1
        bits[low_idx] = value & 1

    async def _modify_relay_config_unlocked(self, mutator):
        bits = await self._hub.read_holding_register_bits(NeptunSmartRegisters.relay_config, 1)
        if bits is None or len(bits) < 16:
            raise RuntimeError("Не удалось прочитать конфигурацию реле перед записью")
        mutator(bits)
        await self._hub.write_holding_register_bits(NeptunSmartRegisters.relay_config, bits)
        self._apply_relay_config_bits(bits)

    async def _write_se_relay_unlocked(self):
        value = (int(self._switch_when_close_valve) & 0x03) << 2 | (int(self._switch_when_alert) & 0x03)
        await self._hub.write_holding_register(NeptunSmartSERegisters.relay_config, value)

    async def set_relay_config_valve(self, state):
        async with self._io_lock:
            if self._is_se:
                self._switch_when_close_valve = int(state)
                await self._write_se_relay_unlocked()
                return
            await self._modify_relay_config_unlocked(
                lambda bits: self._encode_two_bit_value(bits, 12, 13, state)
            )

    def get_relay_config_alert(self) -> int:
        return int(self._switch_when_alert)

    async def set_relay_config_alert(self, state):
        async with self._io_lock:
            if self._is_se:
                self._switch_when_alert = int(state)
                await self._write_se_relay_unlocked()
                return
            await self._modify_relay_config_unlocked(
                lambda bits: self._encode_two_bit_value(bits, 14, 15, state)
            )


class WirelessSensor:
    def __init__(self, hub: modbus_hub, io_lock: asyncio.Lock, address_config, address_value, config, status_bits):
        self._hub = hub
        self._io_lock = io_lock
        self._address_config = address_config
        self._address_value = address_value
        self.update_data(config, status_bits)

    def update_data(self, config, status_bits):
        self._config = config
        self._status_bits = status_bits
        self._battery_level = BitArray(
            [self._status_bits[0], self._status_bits[1], self._status_bits[2], self._status_bits[3],
             self._status_bits[4], self._status_bits[5], self._status_bits[6], self._status_bits[7]])._getuint()
        self._alert = bool(self._status_bits[15])
        self._discharge = bool(self._status_bits[14])
        self._lost_sensor = bool(self._status_bits[13])
        # Биты 5–3 регистра статуса, MSB = бит 5
        self._signal_level = BitArray(
            [self._status_bits[10], self._status_bits[11], self._status_bits[12]])._getuint()

    def get_group_config(self):
        return self._config

    async def set_group_config_unlocked(self, config):
        await self._hub.write_holding_register(address=self._address_config, value=config)
        self._config = config

    async def set_group_config(self, config):
        async with self._io_lock:
            await self.set_group_config_unlocked(config)

    def get_battery_level(self):
        return self._battery_level

    def get_signal_level(self):
        return self._signal_level

    def get_signal_level_text(self):
        return SIGNAL_LEVEL_MAP.get(self._signal_level, str(self._signal_level))

    def get_alert_status(self):
        return self._alert

    def get_lost_sensor_status(self):
        return self._lost_sensor

    def get_discharge_status(self):
        return self._discharge

    def get_address(self):
        return self._address_config


class Counter:
    def __init__(
        self,
        value,
        address,
        hub: modbus_hub,
        high_first: bool = True,
        number: int = 1,
        kind: str = "pulse",
    ):
        self._value = value
        self._address = address
        self._hub = hub
        self._high_first = high_first
        self._number = number
        self._kind = kind

    def set_value(self, value):
        self._value = value

    def get_value(self):
        return self._value

    def get_address(self):
        return self._address

    def get_number(self):
        return self._number

    def get_kind(self):
        return self._kind

    def get_title(self):
        if self._kind == "digital":
            return f"Цифровой счётчик {self._number}"
        return f"Счётчик {self._number}"

    def get_model_name(self):
        if self._kind == "digital":
            return "Цифровой счётчик воды"
        return "Импульсный счётчик воды"
