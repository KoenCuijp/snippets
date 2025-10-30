# Can you write a Python script for me that does the following?
#
# It loads an excel sheet named "inkomsten.xslx" and does the following:
# - Group all rows on the column "Contactpersoon"
# - Count how many rows this person has, name this "Aantal facturen"
# - Sum the column "Totaal incl. btw" for those rows and name this "Totaal incl. btw"
# - Sum the column "Totaal excl. btw" for those rows and name this "Totaal excl. btw"
# - Output for every person: Aantal facturen and the totals
# - Output the totals summarized over all persons
#
# Then load an excel sheet named "kosten.xslx" and do the following:
# - Take all rows with Categorie=4601 Kantoor kosten maandelijks or (categorie=4800 Softwarekosten and knab in omschrijving.lower())
# - Sum the column Totaal incl. btw for all rows, output as total_monthly_costs_incl_vat
# - Sum the column Totaal excl. btw for all rows, output as total_monthly_costs_excl_vat
# - Take all rows with Categorie 4602 Kantoor kosten eenmalig
# - Sum the column Totaal incl. btw for all rows, output as total_onetime_costs_incl_vat
# - Sum the column Totaal excl. btw for all rows, output as total_onetime_costs_excl_vat
#
# Then output:
# - Total income excl tax - total_monthly_costs_excl_vat (name this profit_on_recurring_invoices_excl_vat)
# - Total income incl tax - total_monthly_costs_incl_vat (name this profit_on_recurring_invoices_incl_vat)
#
# The output:
# - profit_on_recurring_invoices_excl_vat - total_onetime_costs_excl_vat (name this total_profit_excl_vat)
# - profit_on_recurring_invoices_incl_vat - total_onetime_costs_incl_vat (name this total_profit_incl_vat)
#



import pandas as pd
import warnings

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    module="openpyxl"
)

# Load inkomsten.xlsx (Note: facturen downloaden, niet factuurregels)
df_income = pd.read_excel('~/inkomsten.xlsx')
# Determine number of unique months in inkomsten.xlsx
df_income['Datum'] = pd.to_datetime(df_income['Datum'])
amount_of_months = df_income['Datum'].dt.to_period('M').nunique()

# Group by Contactpersoon and sort by Aantal_facturen descending
grouped = df_income.groupby('Contactpersoon').agg(
    Aantal_facturen=('Contactpersoon', 'count'),
    Totaal_incl_btw=('Totaal incl. btw', 'sum'),
    Totaal_excl_btw=('Totaal excl. btw', 'sum')
).reset_index().sort_values(by='Aantal_facturen', ascending=False)

print("\n========== Inkomen per persoon ==========")
print(grouped)

# Totals over all persons
print("\n========== Inkomen totaal ==========")
total_incl_btw = grouped['Totaal_incl_btw'].sum()
total_excl_btw = grouped['Totaal_excl_btw'].sum()
print(f"Totaal excl. btw: {total_excl_btw:.2f}")
# print(f"Totaal incl. btw: {total_incl_btw:.2f}")

# Load kosten.xlsx (Note: factuurregels downloaden, niet facturen)
df_costs = pd.read_excel('~/kosten.xlsx')

# Monthly costs
monthly_mask = (
        (df_costs['Categorie'] == '4601 Kantoor kosten maandelijks') |
        ((df_costs['Categorie'] == '4800 Softwarekosten') & df_costs['Omschrijving'].str.lower().str.contains('knab', na=False))
)
grouped_monthly = df_costs[monthly_mask].groupby('Relatie').agg(
    Aantal_factuurregels=('Relatie', 'count'),
    Totaal_incl_btw=('Totaal incl. btw', 'sum'),
    Totaal_excl_btw=('Totaal excl. btw', 'sum')
).reset_index().sort_values(by='Aantal_factuurregels', ascending=False)

# Add cleaning costs to grouped_monthly
cleaning_total = amount_of_months * 75.83
cleaning_row = pd.DataFrame({
    'Relatie': ['Schoonmaakkosten'],
    'Aantal_factuurregels': [amount_of_months],
    'Totaal_incl_btw': [cleaning_total],
    'Totaal_excl_btw': [cleaning_total]
})
grouped_monthly = pd.concat([grouped_monthly, cleaning_row], ignore_index=True)
total_monthly_costs_incl_vat = df_costs[monthly_mask]['Totaal incl. btw'].sum() + cleaning_total
total_monthly_costs_excl_vat = df_costs[monthly_mask]['Totaal excl. btw'].sum() + cleaning_total

# One-time costs
onetime_mask = df_costs['Categorie'] == '4602 Kantoor kosten eenmalig'
total_onetime_costs_incl_vat = df_costs[onetime_mask]['Totaal incl. btw'].sum()
total_onetime_costs_excl_vat = df_costs[onetime_mask]['Totaal excl. btw'].sum()
onetime_overview = df_costs.loc[onetime_mask, ['Relatie', 'Omschrijving', 'Totaal incl. btw', 'Totaal excl. btw']]
onetime_overview = onetime_overview.sort_values(by='Totaal incl. btw', ascending=False)

print("\n========== Maandelijkse kosten ==========")
print(grouped_monthly)
print(f"Totaal excl. btw: {total_monthly_costs_excl_vat:.2f}")
# print(f"Totaal incl. btw: {total_monthly_costs_excl_vat:.2f}")

print("\n========== Eenmalige kosten ==========")
print(onetime_overview)
print(f"Totaal excl. btw: {total_onetime_costs_excl_vat:.2f}")
#print(f"Totaal incl. btw: {total_onetime_costs_incl_vat:.2f}")

# Profit calculations
profit_on_recurring_invoices_excl_vat = total_excl_btw - total_monthly_costs_excl_vat
profit_on_recurring_invoices_incl_vat = total_incl_btw - total_monthly_costs_incl_vat

print("\n========== Winst (zonder aftrek eenmalige kosten) ==========")
print(f"Excl. VAT: {profit_on_recurring_invoices_excl_vat:.2f}")
# print(f"Incl. VAT: {profit_on_recurring_invoices_incl_vat:.2f}")

total_profit_excl_vat = profit_on_recurring_invoices_excl_vat - total_onetime_costs_excl_vat
total_profit_incl_vat = profit_on_recurring_invoices_incl_vat - total_onetime_costs_incl_vat

print("\n========== Winst (met aftrek eenmalige kosten) ==========")
print(f"Excl. VAT: {total_profit_excl_vat:.2f}")
# print(f"Incl. VAT: {total_profit_incl_vat:.2f}")