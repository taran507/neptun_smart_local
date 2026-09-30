class NeptunSmartRegisters:
    module_config = 0
    input_line_1_2_config = 1
    input_line_3_4_config = 2
    status_wired_line = 3
    relay_config = 4
    count_of_connected_wireless_sensors = 6
    first_wireless_sensor_config = 7
    first_wireless_sensor_status = 57
    first_counter = 107
    first_counter_config = 123


# Holding register 0 on Smart SE / Smart+ / Dilwis Smart.
DEVICE_TYPE_SMART_SE = 0x4246
DEVICE_TYPE_SMART = 0x4346
DEVICE_TYPE_DILWIS_SMART = 0x4446
DEVICE_TYPE_SMART_PLUS = 0x4546

SE_DEVICE_TYPES = {
    DEVICE_TYPE_SMART_SE: "Neptun Smart SE",
    DEVICE_TYPE_SMART: "Neptun Smart",
    DEVICE_TYPE_DILWIS_SMART: "Dilwis Smart",
    DEVICE_TYPE_SMART_PLUS: "Neptun Smart+",
}

VALVE_STATUS_MAP = {
    0: "Неизвестно",
    1: "Исправен",
    2: "Обрыв линии",
    4: "Закисание",
}

EXPANSION_MODULE_MAP = {
    0: "Нет",
    1: "Радиомодуль LoRa",
    2: "RS-485",
    3: "Ethernet",
    4: "Импульсные счётчики",
    5: "Tuya",
    6: "Неизвестный",
    7: "Неизвестный",
}

DEVICE_ERROR_FLAGS = {
    0x0001: "Цифровой счётчик",
    0x0002: "Модуль Tuya",
    0x0004: "Трансивер LoRa",
    0x0008: "Неподдерживаемый Ethernet",
    0x0010: "Модуль импульсных счётчиков",
    0x0020: "Слот расширения",
    0x0040: "Дублирование модулей",
    0x0080: "Неизвестный модуль",
    0x0100: "Конфигурация модуля",
    0x0200: "Проводной датчик",
    0x0400: "Напряжение питания",
    0x0800: "Кран зоны 1",
    0x1000: "Кран зоны 2",
    0x2000: "Радиодатчик",
    0x4000: "Сохранение во Flash",
}

WIRED_LINE_ERROR_MAP = {
    0: "Нет",
    1: "Потеря датчика",
    2: "Лишний датчик",
    3: "Короткое замыкание",
}

SIGNAL_LEVEL_MAP = {
    0: "Нет связи",
    1: "Слабый",
    2: "Средний",
    3: "Хороший",
    4: "Отличный",
}


class NeptunSmartSERegisters:
    device_type = 0
    firmware = 4
    modbus_address = 5
    baud_rate = 6
    valve_status_group_1 = 7
    valve_status_group_2 = 8
    valve_power_time = 9
    relay_config = 10
    supply_voltage = 11
    line_1_type = 12
    line_1_group = 13
    line_2_type = 14
    line_2_group = 15
    line_3_type = 16
    line_3_group = 17
    line_4_type = 18
    line_4_group = 19
    wired_line_status = 20
    line_1_sensor_count = 21
    line_2_sensor_count = 22
    line_3_sensor_count = 23
    line_4_sensor_count = 24
    wired_line_errors = 25
    count_of_connected_wireless_sensors = 26
    first_wireless_sensor_config = 27
    first_wireless_sensor_status = 77
    first_wireless_sensor_address = 127
    first_pulse_counter = 177
    expansion_modules = 189
    elp_threshold = 193
    elp_interval = 194
    error_code = 195
    reboot = 196
    alarm_sound_time = 197
    first_digital_counter = 198

    coil_floor_washing = 0
    coil_dual_group = 1
    coil_valve_group_1 = 2
    coil_valve_group_2 = 3
    coil_close_on_lost_sensor = 4
    coil_close_on_low_voltage = 5
    coil_lock_buttons = 6
    coil_sensor_feedback = 7
    coil_reset_alarm = 8
    coil_pairing_wireless = 9
    coil_recalibrate = 10
    coil_pulse_counter_1_enable = 11
    coil_elp_mode = 26
    coil_close_on_elp = 27

    di_floor_washing = 0
    di_alarm_group_1 = 1
    di_alarm_group_2 = 2
    di_wireless_battery_low = 3
    di_wireless_lost = 4
    di_group_1_closed_lost_sensor = 5
    di_group_2_closed_lost_sensor = 6
    di_supply_voltage_problem = 7
    di_valve_group_1_open = 8
    di_valve_group_2_open = 9
    di_dual_group = 10
    di_lock_buttons = 11
    di_sensor_feedback = 12
    di_pairing_wireless = 29
    di_elp_leak = 180
    di_overconsumption_enabled = 181
    di_close_on_overconsumption = 182
    di_overconsumption = 183
