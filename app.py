import os
import sys

# Add project root to sys.path to ensure imports work correctly
root_dir = os.path.abspath(os.path.dirname(__file__))
if root_dir not in sys.path:
    sys.path.append(root_dir)

# Execute the main application file inside the app/ directory
main_app_path = os.path.join(root_dir, "app", "main.py")
if os.path.exists(main_app_path):
    with open(main_app_path, "r") as f:
        code = compile(f.read(), main_app_path, 'exec')
        exec(code, globals())
else:
    print(f"Error: Main application file not found at {main_app_path}")
