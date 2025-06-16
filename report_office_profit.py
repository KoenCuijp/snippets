import pandas as pd
import warnings

from datetime import datetime

warnings.filterwarnings(
    "ignore",
    message="Workbook contains no default style, apply openpyxl's default",
    module="openpyxl"
)

def report_office_profit_loss(income_xlsx, costs_xlsx, year):
    # --- Income ---
    df_income = pd.read_excel(income_xlsx)
    df_income = df_income[df_income['Status'].str.lower() == 'betaald']
    df_income = df_income[~df_income['Relatie'].str.lower().str.contains('milswaeft|debhoelai', na=False)]
    df_income['Datum'] = pd.to_datetime(df_income['Datum'], errors='coerce')
    df_income = df_income[df_income['Datum'].dt.year == year]

    total_rent_income_incl_vat = df_income['Totaal incl. btw'].sum()
    total_rent_income_excl_vat = df_income['Totaal excl. btw'].sum()

    # Add fixed monthly amounts
    today = datetime.today()
    months = 12 if year < today.year else today.month
    total_rent_income_incl_vat += months * 327.91
    total_rent_income_excl_vat += months * 271.00

    # --- Costs ---
    df_costs = pd.read_excel(costs_xlsx)
    df_costs['Datum'] = pd.to_datetime(df_costs['Datum'], errors='coerce')
    df_costs = df_costs[df_costs['Datum'].dt.year == year]

    # Monthly costs
    monthly_mask = (
        (df_costs['Categorie'] == '4601 Kantoor kosten maandelijks') |
        ((df_costs['Categorie'] == '4800 Softwarekosten') & df_costs['Omschrijving'].str.lower().str.contains('knab', na=False))
    )
    total_monthly_costs_incl_vat = df_costs[monthly_mask]['Totaal incl. btw'].sum()
    total_monthly_costs_excl_vat = df_costs[monthly_mask]['Totaal excl. btw'].sum()

    # One-time costs
    onetime_mask = df_costs['Categorie'] == '4602 Kantoor kosten eenmalig'
    total_ontime_costs_incl_vat = df_costs[onetime_mask]['Totaal incl. btw'].sum()
    total_onetime_costs_excl_vat = df_costs[onetime_mask]['Totaal excl. btw'].sum()

    # Profit/loss calculations
    profit_loss_without_1time_incl_vat = total_rent_income_incl_vat - total_monthly_costs_incl_vat
    profit_loss_without_1time_excl_vat = total_rent_income_excl_vat - total_monthly_costs_excl_vat
    profit_loss_with_1time_incl_vat = profit_loss_without_1time_incl_vat - total_ontime_costs_incl_vat
    profit_loss_with_1time_excl_vat = profit_loss_without_1time_excl_vat - total_onetime_costs_excl_vat

    # Print table
    print(f"{'':35} | {'Incl. VAT':>15} | {'Excl. VAT':>15}")
    print('-'*72)
    print(f"{'Total monthly income':35} | {total_rent_income_incl_vat:15.2f} | {total_rent_income_excl_vat:15.2f}")
    print(f"{'Total monthly costs':35} | {total_monthly_costs_incl_vat:15.2f} | {total_monthly_costs_excl_vat:15.2f}")
    print(f"{'Profit / Loss without 1time costs':35} | {profit_loss_without_1time_incl_vat:15.2f} | {profit_loss_without_1time_excl_vat:15.2f}")
    print()
    print(f"{'1time costs':35} | {total_ontime_costs_incl_vat:15.2f} | {total_onetime_costs_excl_vat:15.2f}")
    print(f"{'Profit / Loss with 1time costs':35} | {profit_loss_with_1time_incl_vat:15.2f} | {profit_loss_with_1time_excl_vat:15.2f}")

if __name__ == "__main__":
    # Example usage:
    # report_office_profit_loss('invoices.xlsx', 'costs.xlsx', 2024)
    import sys
    if len(sys.argv) != 4:
        print("Usage: python script.py <invoices.xlsx> <costs.xlsx> <year>")
    else:
        report_office_profit_loss(sys.argv[1], sys.argv[2], int(sys.argv[3]))
        print("\n--------------------- DISCLAIMERS ---------------------")
        print("1. Pakt alleen facturen met status 'Betaald'")
        print("   BELANGRIJK:  Zet alles op betaald en check of er nog creditfacturen zijn die er af moeten")
        print("2. Pakt alleen kosten met categorie 'Kantoor kosten maandelijks' of 'Kantoor kosten eenmalig'")
        print("   Alle kosten ingevoerd in die catogorieen?")