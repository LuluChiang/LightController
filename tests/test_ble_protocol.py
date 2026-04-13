"""
Tests for core/ble_protocol.py — verifies every byte of each command.
Run with:  py -m pytest tests/ -v
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from core.ble_protocol import (
    build_command, build_off_command,
    CMD_ON, CMD_OFF,
    WRITE_UUID, NOTIFY_UUID, SERVICE_UUID,
)


# ── Power commands ─────────────────────────────────────────────────────────

def test_cmd_on_bytes():
    assert CMD_ON == bytes([0xCC, 0x23, 0x33])

def test_cmd_off_bytes():
    assert CMD_OFF == bytes([0xCC, 0x24, 0x33])

def test_build_off_command_returns_cmd_off():
    assert build_off_command() == CMD_OFF


# ── RGB colour command ─────────────────────────────────────────────────────

def test_rgb_full_white():
    # Full white at full brightness → R=255 G=255 B=255
    cmd = build_command(255, 255, 255, 255)
    assert cmd == bytes([0x56, 0xFF, 0xFF, 0xFF, 0x00, 0xF0, 0xAA])

def test_rgb_pure_red():
    cmd = build_command(255, 0, 0, 255)
    assert cmd == bytes([0x56, 0xFF, 0x00, 0x00, 0x00, 0xF0, 0xAA])

def test_rgb_pure_green():
    cmd = build_command(0, 255, 0, 255)
    assert cmd == bytes([0x56, 0x00, 0xFF, 0x00, 0x00, 0xF0, 0xAA])

def test_rgb_pure_blue():
    cmd = build_command(0, 0, 255, 255)
    assert cmd == bytes([0x56, 0x00, 0x00, 0xFF, 0x00, 0xF0, 0xAA])

def test_rgb_length_is_7():
    assert len(build_command(255, 128, 0, 255)) == 7

def test_rgb_header_and_footer():
    cmd = build_command(100, 200, 50, 255)
    assert cmd[0] == 0x56
    assert cmd[-1] == 0xAA

def test_rgb_mode_flag():
    cmd = build_command(255, 0, 0, 255)
    assert cmd[5] == 0xF0    # byte index 5 = mode flag for RGB

def test_rgb_brightness_scaling_half():
    # At 50% brightness (128/255 ≈ 0.502), R=255 → 255*0.502 ≈ 128
    cmd = build_command(255, 255, 255, 128)
    r, g, b = cmd[1], cmd[2], cmd[3]
    assert r == int(255 * (128 / 255))
    assert r == g == b

def test_rgb_brightness_zero_sends_black():
    cmd = build_command(255, 255, 255, 0)
    # brightness=0 → all channels scale to 0 → warm-white mode with W=0
    assert cmd == bytes([0x56, 0x00, 0x00, 0x00, 0x00, 0x0F, 0xAA])


# ── Warm-white command ─────────────────────────────────────────────────────

def test_warm_white_full():
    cmd = build_command(0, 0, 0, 255)
    assert cmd == bytes([0x56, 0x00, 0x00, 0x00, 0xFF, 0x0F, 0xAA])

def test_warm_white_mode_flag():
    cmd = build_command(0, 0, 0, 128)
    assert cmd[5] == 0x0F    # warm-white mode flag

def test_warm_white_length_is_7():
    assert len(build_command(0, 0, 0, 200)) == 7

def test_warm_white_zero_brightness():
    # R=G=B=0, brightness=0 → all off
    cmd = build_command(0, 0, 0, 0)
    assert cmd == bytes([0x56, 0x00, 0x00, 0x00, 0x00, 0x0F, 0xAA])


# ── UUIDs ──────────────────────────────────────────────────────────────────

def test_uuids_are_correct():
    assert SERVICE_UUID == "0000fff0-0000-1000-8000-00805f9b34fb"
    assert WRITE_UUID   == "0000fff3-0000-1000-8000-00805f9b34fb"
    assert NOTIFY_UUID  == "0000fff4-0000-1000-8000-00805f9b34fb"
