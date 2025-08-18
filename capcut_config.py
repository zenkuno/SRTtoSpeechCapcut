# modules/capcut_config.py

# --- API Configuration ---
DEFAULT_SPEAKER_ID = "BV421_vivn_streaming"
DEFAULT_SPEAKER_NAME = "Nguồn nhỏ ngọt ngào"

# --- Polling Configuration ---
DEFAULT_MAX_POLL_RETRIES = 12
DEFAULT_POLL_INTERVAL_SEC = 5

# --- Speaker Voices ---
CAPCUT_SPEAKERS = {
    "BV421_vivn_streaming": "Nguồn nhỏ ngọt ngào",
    "BV074_streaming": "Giọng nữ dễ thương",
    "BV075_streaming": "Thanh niên tự tin",
    "BV560_streaming": "Anh Dũng",
    "BV562_streaming": "Chí Mai (nữ)",
    "vi_female_huong": "Giọng nữ phổ thông"
}

def get_speaker_name(speaker_id):
    return CAPCUT_SPEAKERS.get(speaker_id, "Không rõ")

def get_default_speaker_id():
    return DEFAULT_SPEAKER_ID

def get_default_speaker_name():
    return CAPCUT_SPEAKERS.get(DEFAULT_SPEAKER_ID, "Không rõ")