"""Constants for the ETA integration."""

from homeassistant.components import calendar

DOMAIN = "eta_webservices"


FLOAT_DICT = "FLOAT_DICT"
SWITCHES_DICT = "SWITCHES_DICT"
TEXT_DICT = "TEXT_DICT"
WRITABLE_DICT = "WRITABLE_DICT"
PENDING_DICT = "PENDING_DICT"
CHOSEN_FLOAT_SENSORS = "chosen_float_sensors"
CHOSEN_SWITCHES = "chosen_switches"
CHOSEN_TEXT_SENSORS = "chosen_text_sensors"
CHOSEN_WRITABLE_SENSORS = "chosen_writable_sensors"
CHOSEN_PENDING_SENSORS = "chosen_pending_sensors"

# Frozen per-entry id; anchor of entity unique_ids (independent of IP + node names).
STABLE_ID = "stable_id"

FORCE_LEGACY_MODE = "force_legacy_mode"
ENABLE_DEBUG_LOGGING = "enable_debug_logging"
AUTO_SELECT_ALL_ENTITIES = "auto_select_all_entities"

OPTIONS_UPDATE_ACTION = "options_update_action"
OPTIONS_ACTION_PARALLEL_ONLY = "update_parallel_requests"
OPTIONS_ACTION_UPDATE_SELECTED = "update_selected_entities"
OPTIONS_ACTION_REDISCOVER_AND_UPDATE = "rediscover_and_update_entities"
OPTIONS_ACTION_RENAME_ENTITIES = "rename_entities_to_named_scheme"
OPTIONS_ACTION_SIDEBAR = "sidebar_panel"
# sidebar panel on/off (on unless switched off in the options)
SIDEBAR_PANEL = "sidebar_panel"
# Old stable id, staged by the opt-in migration; consumed once in async_setup_entry.
RENAME_PENDING_FROM = "rename_pending_from"
ADVANCED_OPTIONS_IGNORE_DECIMAL_PLACES_RESTRICTION = (
    "ignore_decimal_places_restriction_for_writable_entities"
)

ERROR_UPDATE_COORDINATOR = "error_update_coordinator"
WRITABLE_UPDATE_COORDINATOR = "writable_update_coordinator"
SENSOR_UPDATE_COORDINATOR = "sensor_update_coordinator"
PENDING_UPDATE_COORDINATOR = "pending_update_coordinator"
FAST_UPDATE_COORDINATOR = "fast_update_coordinator"
# hass.data key of the stored card settings (panel.py)
PANEL_DATA = f"{DOMAIN}_panel_data"
LAST_COORDINATOR_WARNING_TIMESTAMP = "last_coordinator_warning_timestamp"

CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT = "minutes_since_midnight"
CUSTOM_UNIT_TIMESLOT = "timeslot"
CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE = "timeslot_plus_temperature"
CUSTOM_UNIT_UNITLESS = "unitless"
CUSTOM_UNIT_DATETIME = "datetime"
CUSTOM_UNITS = [
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    CUSTOM_UNIT_UNITLESS,
    CUSTOM_UNIT_DATETIME,
]

# Supported features for ETA entities
# We have to use pre-defined events here because otherwise the services wouldn't show up in the UI
SUPPORT_WRITE_TIMESLOT = calendar.const.CalendarEntityFeature.CREATE_EVENT
SUPPORT_WRITE_TIMESLOT_WITH_TEMPERATURE = (
    calendar.const.CalendarEntityFeature.DELETE_EVENT
)

# Internal units which should not be shown to the user
INVISIBLE_UNITS = [
    CUSTOM_UNIT_MINUTES_SINCE_MIDNIGHT,
    CUSTOM_UNIT_TIMESLOT,
    CUSTOM_UNIT_TIMESLOT_PLUS_TEMPERATURE,
    CUSTOM_UNIT_UNITLESS,
    CUSTOM_UNIT_DATETIME,
]

MAX_PARALLEL_REQUESTS = "max_parallel_requests"
REQUEST_SEMAPHORE = "request_semaphore"
UPDATE_INTERVAL = "update_interval"
FAST_UPDATE_INTERVAL = "fast_update_interval"
# one read at a time per entry: slow and fast polling never overlap
READ_LOCK = "read_lock"
PAUSE_COORDINATORS_START_TIMESTAMP = "pause_coordinators_start_timestamp"
PAUSE_COORDINATORS_MAX_DURATION = 10 * 60  # seconds

# Defaults
REQUEST_TIMEOUT = 60
DEFAULT_MAX_PARALLEL_REQUESTS = 5
DEFAULT_UPDATE_INTERVAL = 60  # seconds
DEFAULT_FAST_UPDATE_INTERVAL = 10  # seconds, values shown on the plant card
# entities with this label are polled fast as well (label id = slug of the name)
FAST_UPDATE_LABEL_ID = "eta_fast_update"
FAST_UPDATE_LABEL_NAME = "ETA Fast Update"
# more fast values than this load the terminal noticeably: warn once
FAST_UPDATE_WARN_COUNT = 50
COORDINATOR_WARNING_INTERVAL = (
    30 * 60
)  # seconds between coordinator performance warnings
