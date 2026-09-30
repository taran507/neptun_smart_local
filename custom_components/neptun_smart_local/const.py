from datetime import timedelta

DOMAIN = "neptun_smart_local"
SCAN_INTERVAL = timedelta(seconds=10)

CONF_NAME = "name"
CONF_HOST_IP = "host_ip"
CONF_HOST_PORT = "host_port"
CONF_DEVICE_ID = "device_id"

DEFAULT_NAME = "Neptun_Smart"
DEFAULT_PORT = "503"
DEFAULT_DEVICE_ID = 240
FALLBACK_DEVICE_IDS = (240, 1)
