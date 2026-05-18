from backend.core.hunter import MBTIHunter, HealingHunter, SideHustleHunter, RawSignal, BaseHunter

print("MBTIHunter.CATEGORY      =", MBTIHunter.CATEGORY)
print("HealingHunter.CATEGORY   =", HealingHunter.CATEGORY)
print("SideHustleHunter.CATEGORY=", SideHustleHunter.CATEGORY)

# Verify all are subclasses of BaseHunter
assert issubclass(MBTIHunter, BaseHunter)
assert issubclass(HealingHunter, BaseHunter)
assert issubclass(SideHustleHunter, BaseHunter)

# Verify hunt method signatures exist
import inspect
for cls in (MBTIHunter, HealingHunter, SideHustleHunter):
    assert inspect.iscoroutinefunction(cls.hunt), f"{cls.__name__}.hunt must be async"

print("All imports and assertions OK ✓")
