SERVICE_UUID        = "0000fff0-0000-1000-8000-00805f9b34fb"
WRITE_UUID          = "0000fff3-0000-1000-8000-00805f9b34fb"
NOTIFY_UUID         = "0000fff4-0000-1000-8000-00805f9b34fb"
DEVICE_NAME_FILTER  = "BLEDDM"

# ELK-BLEDDM command protocol (7 bytes):
#   Power ON  : CC 23 33
#   Power OFF : CC 24 33
#   RGB colour: 56 RR GG BB 00 F0 AA
#   Warm white: 56 00 00 00 WW 0F AA
#
# Brightness is applied by scaling the RGB values (0–255).

CMD_ON  = bytes([0xCC, 0x23, 0x33])
CMD_OFF = bytes([0xCC, 0x24, 0x33])


def build_command(r: int, g: int, b: int, brightness: int) -> bytes:
    """
    Build a 7-byte colour command for ELK-BLEDDM devices.
    Brightness (0-255) scales all RGB channels proportionally.
    When the scaled output is all-zero (pure black or brightness=0),
    the device switches to warm-white mode with W=brightness.
    """
    scale = brightness / 255.0
    sr = int(r * scale) & 0xFF
    sg = int(g * scale) & 0xFF
    sb = int(b * scale) & 0xFF

    if sr == 0 and sg == 0 and sb == 0:
        # All channels zero — use warm-white mode with brightness as intensity
        w = brightness & 0xFF
        return bytes([0x56, 0x00, 0x00, 0x00, w, 0x0F, 0xAA])
    else:
        return bytes([0x56, sr, sg, sb, 0x00, 0xF0, 0xAA])


def build_off_command() -> bytes:
    return CMD_OFF
