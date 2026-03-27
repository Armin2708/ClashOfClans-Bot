import sys
sys.path.insert(0, ".")

from Quartz import CGWindowListCopyWindowInfo, kCGWindowListOptionOnScreenOnly, kCGNullWindowID

windows = CGWindowListCopyWindowInfo(kCGWindowListOptionOnScreenOnly, kCGNullWindowID)
seen = set()
for w in windows:
    name = w.get("kCGWindowOwnerName", "")
    if name and name not in seen:
        seen.add(name)
        print(name)
