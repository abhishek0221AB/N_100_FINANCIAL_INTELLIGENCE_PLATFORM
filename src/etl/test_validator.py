from src.etl.loader import load_all_raw
from src.etl.validator import DataValidator

print("Step 1: Loading datasets...")
datasets = load_all_raw()

print("Step 2: Creating validator...")
validator = DataValidator()

print("Step 3: Running validation...")
report = validator.validate_all(datasets)
print("\nValidation Summary")
print("=" * 60)

print(
    report.groupby(["rule_id", "severity"])
          .size()
          .reset_index(name="count")
          .sort_values("count", ascending=False)
)
print("\nFailures by Dataset")
print("=" * 60)

print(
    report.groupby("dataset")
          .size()
          .sort_values(ascending=False)
)

print("Step 4: Validation finished")
print(report)

print("Step 5: Saving report...")
validator.save_report()

print("Step 6: Done")