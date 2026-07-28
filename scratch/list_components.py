import inspect

import prefab_ui.components as components

print("Available components in prefab_ui.components:")
for name, obj in inspect.getmembers(components):
    if inspect.isclass(obj):
        print(f"  {name}")
