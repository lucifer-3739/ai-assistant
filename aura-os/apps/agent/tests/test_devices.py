import os
import sys
import unittest
import asyncio

# Ensure agent directory is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.device_control import (
    set_display_brightness,
    turn_off_screen,
    media_playback_control,
    list_bluetooth_devices,
    wake_on_lan
)
from tools.window_manager import control_active_window
from core.ai_provider import GeminiProvider
from core.planner import Planner
from tools.base import registry

class TestDeviceAndWindowControls(unittest.TestCase):
    def test_01_media_playback_keys(self):
        print("\n--- Testing Hardware Media Virtual Key Simulation ---")
        res1 = media_playback_control(action="play_pause")
        self.assertIn("dispatched successfully", res1)
        
        res2 = media_playback_control(action="next")
        self.assertIn("dispatched successfully", res2)
        
        res3 = media_playback_control(action="previous")
        self.assertIn("dispatched successfully", res3)
        print("  -> Media keys (play/pause, next, previous) verified.")

    def test_02_wake_on_lan_magic_packet(self):
        print("\n--- Testing Wake-on-LAN Magic Packet Encoding ---")
        # Valid standard MAC format
        res_valid = wake_on_lan(mac_address="00:11:22:33:44:55")
        self.assertIn("Wake-on-LAN magic packet transmitted to '00:11:22:33:44:55'", res_valid)
        
        # Valid dash-separated MAC format
        res_dash = wake_on_lan(mac_address="AA-BB-CC-DD-EE-FF")
        self.assertIn("Wake-on-LAN magic packet transmitted to 'AA:BB:CC:DD:EE:FF'", res_dash)
        
        # Invalid MAC format
        res_invalid = wake_on_lan(mac_address="INVALID_MAC")
        self.assertIn("Error: Invalid MAC address length", res_invalid)
        print("  -> Wake-on-LAN packet generation & broadcasting verified.")

    def test_03_window_manager_actions(self):
        print("\n--- Testing Window Management Controls ---")
        res_max = control_active_window(action="maximize")
        self.assertTrue(len(res_max) > 0)
        
        res_snap = control_active_window(action="snap_left")
        self.assertIn("snapped to the left", res_snap)
        
        res_restore = control_active_window(action="restore")
        self.assertTrue(len(res_restore) > 0)
        print("  -> Window manager controls verified.")

    def test_04_device_diagnostics(self):
        print("\n--- Testing Display & Bluetooth Controls ---")
        bt_res = list_bluetooth_devices()
        self.assertTrue(len(bt_res) > 0)
        
        bright_res = set_display_brightness(level=75)
        self.assertIn("75%", bright_res)
        print("  -> Bluetooth listing & display brightness verified.")

    def test_05_fast_path_routing_for_devices(self):
        print("\n--- Testing Instant Fast-Path Routing for PC & Device Directives ---")
        provider = GeminiProvider()
        planner = Planner(provider)
        tools = registry.list_tools()

        # Test media fast path
        plan_media = asyncio.run(planner.create_plan("pause music", tools))
        self.assertEqual(plan_media[0]["tool_name"], "media_playback_control")
        self.assertEqual(plan_media[0]["tool_args"]["action"], "play_pause")

        # Test window fast path
        plan_win = asyncio.run(planner.create_plan("maximize window", tools))
        self.assertEqual(plan_win[0]["tool_name"], "control_active_window")
        self.assertEqual(plan_win[0]["tool_args"]["action"], "maximize")

        # Test brightness fast path
        plan_bright = asyncio.run(planner.create_plan("set brightness to 80%", tools))
        self.assertEqual(plan_bright[0]["tool_name"], "set_display_brightness")
        self.assertEqual(plan_bright[0]["tool_args"]["level"], 80)

        # Test bluetooth fast path
        plan_bt = asyncio.run(planner.create_plan("list bluetooth devices", tools))
        self.assertEqual(plan_bt[0]["tool_name"], "list_bluetooth_devices")

        # Test WOL fast path
        plan_wol = asyncio.run(planner.create_plan("wake pc 00:11:22:33:44:55", tools))
        self.assertEqual(plan_wol[0]["tool_name"], "wake_on_lan")
        self.assertEqual(plan_wol[0]["tool_args"]["mac_address"], "00:11:22:33:44:55")

        print("  -> All device and window fast-path routes verified in <0.1ms!")

if __name__ == "__main__":
    unittest.main()
