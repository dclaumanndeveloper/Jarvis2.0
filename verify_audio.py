
import sys
import logging

logging.basicConfig(level=logging.INFO)

try:
    import comtypes
    from comtypes import CLSCTX_ALL
    comtypes.CoInitialize()
    print("COM Initialized")

    from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
    print("Imports successful")

    devices = AudioUtilities.GetSpeakers()
    
    with open('pycaw_debug.log', 'w') as f:
        f.write(f"Devices: {devices}\n")
        if hasattr(devices, 'EndpointVolume'):
            vol = devices.EndpointVolume
            f.write(f"Vol Type: {type(vol)}\n")
            f.write(f"Vol Dir: {dir(vol)}\n")
            try:
                f.write(f"Vol Scalar: {vol.GetMasterVolumeLevelScalar()}\n")
            except Exception as e:
                f.write(f"Error calling Scalar: {e}\n")
        
    print("Debug info written to pycaw_debug.log")
    
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
