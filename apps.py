def calculate_risk_score(...):
    # existing code ...
    total_paid_invoices = ...

    # Guard clause for division
    if total_paid_invoices == 0:
        return 0  # or some default/risk value
    risk_score = ... / total_paid_invoices
    # existing code ...


def clean_data(data):
    # existing code ...
    data['payment_date'] = pd.to_datetime(data['payment_date'], errors='coerce')
    if data['payment_date'].isnull().any():
        ...  # handle NaT values gracefully
    # Perform additional checks & replacements
    # existing code ...