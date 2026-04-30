import requests
from typing import Optional, List
import qonto_mcp
from qonto_mcp import mcp


@mcp.tool()
def get_qonto_transactions(
    bank_account_id: str,
    settled_at_from: Optional[str] = None,
    settled_at_to: Optional[str] = None,
    emitted_at_from: Optional[str] = None,
    emitted_at_to: Optional[str] = None,
    side: Optional[str] = None,
    status: Optional[List[str]] = None,
    iban: Optional[str] = None,
    sort_by: Optional[str] = None,
    current_page: Optional[int] = None,
    per_page: Optional[int] = None,
    includes: Optional[List[str]] = None,
):
    """
    Retrieves transactions from the Qonto API for a specific bank account, with full
    filtering, pagination, and sort support.

    Args:
        bank_account_id: UUID of the bank account.
        settled_at_from: ISO 8601 lower bound on settled_at (e.g. '2026-04-01T00:00:00Z').
        settled_at_to:   ISO 8601 upper bound on settled_at.
        emitted_at_from: ISO 8601 lower bound on emitted_at.
        emitted_at_to:   ISO 8601 upper bound on emitted_at.
        side: 'credit' (inbound only) or 'debit' (outbound only).
        status: list of statuses to filter by (e.g. ['completed','pending','declined','reversed']).
        iban: filter to a single IBAN on the bank_account.
        sort_by: e.g. 'settled_at:asc', 'settled_at:desc', 'emitted_at:asc'.
        current_page: 1-based page number; use to walk past the first 100 rows.
        per_page: number of rows per page (Qonto's default is 100, max 100).
        includes: optional related resources to embed; valid values: 'vat_details',
                  'labels', 'attachments'.

    Example:
        get_qonto_transactions(
            bank_account_id='0193f298-...',
            settled_at_from='2026-04-01T00:00:00Z',
            settled_at_to='2026-04-30T23:59:59Z',
            side='credit',
            sort_by='settled_at:asc',
            per_page=100,
            current_page=1,
        )
    """
    url = f"{qonto_mcp.thirdparty_host}/v2/transactions"
    params = {"bank_account_id": bank_account_id}

    if settled_at_from:
        params["settled_at_from"] = settled_at_from
    if settled_at_to:
        params["settled_at_to"] = settled_at_to
    if emitted_at_from:
        params["emitted_at_from"] = emitted_at_from
    if emitted_at_to:
        params["emitted_at_to"] = emitted_at_to
    if side:
        params["side"] = side
    if iban:
        params["iban"] = iban
    if sort_by:
        params["sort_by"] = sort_by
    if current_page is not None:
        params["current_page"] = current_page
    if per_page is not None:
        params["per_page"] = per_page
    if status:
        for st in status:
            params.setdefault("status[]", []).append(st)
    if includes:
        for inc in includes:
            params.setdefault("includes[]", []).append(inc)

    try:
        response = requests.get(url, headers=qonto_mcp.headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"Error fetching Qonto transactions: {str(e)}"


@mcp.tool()
def get_qonto_transaction(transaction_id: str, includes: list = None):
    """
    Retrieves a specific transaction from the Qonto API with optional related resources.

    This returns detailed information about a transaction including amounts, dates,
    counterparty details, and operation type.

    Args:
        transaction_id: UUID of the transaction to retrieve
        includes: Optional list of related resources to include. Valid options are:
                 'vat_details', 'labels', 'attachments'

    Example: get_qonto_transaction(
                transaction_id='7b7a5ed6-3903-4782-889d-b4f64bd7bef9',
                includes=['labels', 'attachments']
             )
    """
    url = f"{qonto_mcp.thirdparty_host}/v2/transactions/{transaction_id}"
    params = {}

    if includes:
        for include in includes:
            params.setdefault("includes[]", []).append(include)

    try:
        response = requests.get(url, headers=qonto_mcp.headers, params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return f"Error fetching transaction: {str(e)}"
