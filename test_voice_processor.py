import sys
import traceback

print("Testing VoiceProcessorV2 initialization...")
try:
    from services.voice_processor_v2 import VoiceProcessorV2
    processor = VoiceProcessorV2()
    print("VoiceProcessorV2 initialized SUCCESSFULLY.")
except Exception as e:
    print(f"Failed to initialize VoiceProcessorV2: {e}")
    traceback.print_exc()
