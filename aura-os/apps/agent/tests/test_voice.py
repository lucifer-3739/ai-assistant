import os
import sys
import unittest

# Ensure agent folder is in path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from voice.text_to_speech import gTTSProvider
from voice.wake_word import LocalWakeWordProvider, extract_command_after_wake_word

class TestVoiceSystem(unittest.TestCase):
    def test_wake_word_command_separation(self):
        print("\n--- Testing Continuous Wake Word & Task Command Separation ---")
        
        # Test 1: Standard wake word + command
        trig, cmd = extract_command_after_wake_word("friday open notepad")
        self.assertTrue(trig)
        self.assertEqual(cmd, "open notepad")
        
        # Test 2: "Hey Friday" prefix with polite fillers
        trig, cmd = extract_command_after_wake_word("hey friday, can you check my battery status")
        self.assertTrue(trig)
        self.assertEqual(cmd, "check my battery status")
        
        # Test 3: "Ok Friday" prefix with punctuation
        trig, cmd = extract_command_after_wake_word("ok friday: please take a screenshot")
        self.assertTrue(trig)
        self.assertEqual(cmd, "take a screenshot")
        
        # Test 4: Only wake word spoken
        trig, cmd = extract_command_after_wake_word("friday")
        self.assertTrue(trig)
        self.assertEqual(cmd, "")
        
        # Test 5: No wake word
        trig, cmd = extract_command_after_wake_word("play music on spotify")
        self.assertFalse(trig)
        self.assertEqual(cmd, "")
        
        print("  -> Continuous wake word & command separation verified successfully.")

    def test_text_to_speech_playback(self):
        print("\n--- Testing Text-to-Speech Vocalization ---")
        tts = gTTSProvider()
        try:
            tts.speak("FRIDAY online and ready.")
            success = True
        except Exception as e:
            print(f"TTS Failed: {e}")
            success = False
            
        self.assertTrue(success)

if __name__ == "__main__":
    unittest.main()
