import sys
print("Python Executable:", sys.executable)
try:
    import volcenginesdkarkruntime
    print("✅ Found 'volcenginesdkarkruntime' at:", volcenginesdkarkruntime.__file__)
except ImportError as e:
    print("❌ Failed to import 'volcenginesdkarkruntime':", e)

try:
    from volcenginesdkarkruntime import Ark
    print("✅ Successfully imported 'Ark' class")
except ImportError as e:
    print("❌ Failed to import 'Ark':", e)

try:
    import volcengine
    print("✅ Found 'volcengine' (standard sdk) at:", volcengine.__file__)
except ImportError as e:
    print("❌ Failed to import 'volcengine':", e)
