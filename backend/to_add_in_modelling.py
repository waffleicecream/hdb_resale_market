# ─────────────────────────────────────────────────────────────────────────────
# MODELLING FILTER — apply this in your modelling notebook, not here.
# This cell is a DEMONSTRATION ONLY. The saved hdb_with_amenities_macro.csv is
# always the full dataset with the original resale_price_real (2017-Q1 base) preserved.
#
# Steps:
#   1. Filter to post-COVID data (Jan 2021 onwards) for cleaner price prediction.
#   2. Re-index resale_price_real to a 2021-Q1 base so that all real prices in
#      df_model are expressed in "2021-Q1 dollars" — more interpretable for a
#      post-2021 model than the original 2017-Q1 base.
# ─────────────────────────────────────────────────────────────────────────────

df_model = df[df['month'] >= '2021-01-01'].copy()
print(f"Full dataset:              {len(df):,} rows")
print(f"Modelling dataset (2021+): {len(df_model):,} rows")

# Re-index resale_price_real to 2021-Q1 base.
# Formula: resale_price_real_2021Q1 = resale_price * (rpi_2021Q1 / rpi_transaction)
rpi_2021q1 = df.loc[df['quarter'] == '2021-Q1', 'rpi'].iloc[0]
print(f"\nRPI at 2021-Q1: {rpi_2021q1:.1f}")
df_model['resale_price_real'] = (
    df_model['resale_price'] * (rpi_2021q1 / df_model['rpi'])
).round(2)
print("resale_price_real overwritten in df_model with 2021-Q1 base.")
print(f"  Mean real price (2021-Q1 $): {df_model['resale_price_real'].mean():,.0f}")

# Sanity check: ensure all towns still have sufficient observations
town_counts = df_model.groupby('town').size().sort_values()
print("\nRow count by town (check for thin coverage):")
print(town_counts.to_string())