
from comandos import abrir, IS_WINDOWS
import platform

print(f"IS_WINDOWS: {IS_WINDOWS}")
print(f"Platform: {platform.system()}")

print("Testing 'abrir inexistente'...")
result = abrir("abrir aplicativo_inexistente_xyz")
print(f"Result: {result}")
