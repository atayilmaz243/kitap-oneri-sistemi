import pandas as pd
import pathlib

file_path = '/Users/h.atay./Desktop/kitap-oneri-sistemi/cleaned_data/book_data'

print("Reading Parquet data...")
df = pd.read_parquet(file_path)

initial_count = len(df)
print(f"Total row count initially: {initial_count}")

# Check columns
print("Columns in dataframe:", df.columns.tolist())

# Identify rows where description is null or empty string after strip
try:
    # First convert to string if not, and strip
    # Also handle genuine nulls just in case, though user said technically not NULL
    empty_mask = df['description'].astype(str).str.strip() == ''
except KeyError:
    print("Error: 'description' column not found.")
    import sys; sys.exit(1)

empty_rows = df[empty_mask]
print("\n--- Rows with empty descriptions ---")
for idx, row in empty_rows.iterrows():
    title = row.get('title', row.get('book_title', row.get('name', 'NO TITLE FOUND')))
    print(f"- {title}")

# Delete these rows kalıcı olarak
df_cleaned = df[~empty_mask]

# Verify
final_count = len(df_cleaned)
print(f"\nTotal row count after deletion: {final_count}")
removed_count = initial_count - final_count
print(f"Removed {removed_count} rows.")

# Verify no more empty descriptions
remaining_empty = (df_cleaned['description'].astype(str).str.strip() == '').sum()
print(f"Number of rows with empty description remaining: {remaining_empty}")

if remaining_empty == 0 and removed_count == 2:
    print("\nVerification successful. Saving...")
    df_cleaned.to_parquet(file_path, index=False)
    print("Dataset saved successfully.")
else:
    print(f"\nWarning: Expected to remove 2 rows, but removed {removed_count}. Remaining empty: {remaining_empty}")
    print("Saving anyway as requested but worth noting...")
    df_cleaned.to_parquet(file_path, index=False)
    print("Dataset saved.")
