import sys
sys.path.insert(0, '.')
from backend.core.hunter import RedditHunter, ProductHuntHunter, BaseHunter, RawSignal
print("✅ Import OK")
print(f"  RedditHunter: {RedditHunter}")
print(f"  ProductHuntHunter: {ProductHuntHunter}")
print(f"  BaseHunter: {BaseHunter}")
print(f"  RawSignal: {RawSignal}")
