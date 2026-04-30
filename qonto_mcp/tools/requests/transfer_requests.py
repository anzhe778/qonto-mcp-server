"""
Write-side tool: stage a single SEPA transfer as a Qonto request that needs in-app
approval by an admin membership.

Endpoint shape: POST {thirdparty_host}/v2/requests/transfers
Body:
  {
    "request": {
      "beneficiary_id": "<uuid>" | null,
      "credit_iban":     "<IBAN>"  | null,    # required if no beneficiary_id
      "credit_account_name": "<Name>" | null, # required if no beneficiary_id
      "amount":          "<decimal string>",  # in EUR
      "currency":        "EUR",
      "reference":       "<<=140 chars>>",
      "note":            "<optional internal note>",
      "scheduled_date":  "<YYYY-MM-DD>",
      "debit_iban":      "<IBAN of source account>",
      "attachment_ids":  [<list of attachment uuids>]
    }
  }

If your Qonto account/role does not allow creating transfer requests (e.g. you are
the sole Admin/Owner with no superior to approve them), this endpoint may return
422/403; in that case use Qonto's web/mobile app to initiate the transfer, or extend
this tool to call POST /v2/sepa_transfers (which performs an immediate transfer
gated by SCA push to your phone).
"""

from datetime import date
from decimal import Decimal
from typing import Dict, List, Optional

import requests
from requests.exceptions import RequestException

import qonto_mcp
from qonto_mcp import mcp


@mcp.tool()
def create_transfer_request(
    amount: str,
    reference: str,
    debit_iban: str,
    beneficiary_id: Optional[str] = None,
    credit_iban: Optional[str] = None,
    credit_account_name: Optional[str] = None,
    currency: str = "EUR",
    note: Optional[str] = None,
    scheduled_date: Optional[str] = None,
    attachment_ids: Optional[List[str]] = None,
) -> Dict:
    """
    Stage a single SEPA transfer as a Qonto request requiring in-app admin approval.

    This does NOT move money on its own. It creates a pending request which must be
    approved by an authorized membership in the Qonto mobile/web app before the
    transfer is executed. Always-on safe staging — the human in the loop is required.

    Either supply a known beneficiary via `beneficiary_id`, OR a new beneficiary's
    `credit_iban` + `credit_account_name`. One or the other.

    Args:
        amount: Amount as a decimal string in EUR, e.g. '1234.56'.
        reference: SEPA reference (max ~140 chars). Shown on the recipient's statement.
        debit_iban: IBAN of the Qonto bank account to debit. Required.
        beneficiary_id: UUID of an existing Qonto beneficiary. Use this OR the IBAN+name pair.
        credit_iban: IBAN of the recipient (when not using beneficiary_id).
        credit_account_name: Name of the recipient (when not using beneficiary_id).
        currency: Currency code, default 'EUR'.
        note: Optional internal note (not shown to recipient).
        scheduled_date: Optional execution date 'YYYY-MM-DD'. Defaults to next business day.
        attachment_ids: For amounts > 30,000 EUR, a list of uploaded attachment UUIDs is required.

    Examples:
        # To an existing beneficiary:
        create_transfer_request(
            amount='250.00',
            reference='Invoice 2026-04-001',
            debit_iban='DE11100101234954186203',
            beneficiary_id='aab86d8a-0d4c-4749-9a49-0ada88a9c423',
        )
        # To a new beneficiary:
        create_transfer_request(
            amount='1500.00',
            reference='Salary April 2026',
            debit_iban='DE11100101234954186203',
            credit_iban='DE89370400440532013000',
            credit_account_name='Jane Doe',
            scheduled_date='2026-05-01',
        )
    """
    if not beneficiary_id and not (credit_iban and credit_account_name):
        return {
            "error": "Provide either beneficiary_id, OR both credit_iban and credit_account_name."
        }
    if beneficiary_id and (credit_iban or credit_account_name):
        return {
            "error": "Provide beneficiary_id OR credit_iban+credit_account_name, not both."
        }

    # validate amount string is a positive number
    try:
        amt = Decimal(amount)
        if amt <= 0:
            return {"error": "amount must be a positive decimal string."}
    except Exception:
        return {"error": f"amount '{amount}' is not a valid decimal string."}

    # validate scheduled_date if provided
    if scheduled_date:
        try:
            date.fromisoformat(scheduled_date)
        except ValueError:
            return {"error": "scheduled_date must be YYYY-MM-DD."}

    body_request = {
        "amount": amount,
        "currency": currency,
        "reference": reference,
        "debit_iban": debit_iban,
    }
    if beneficiary_id:
        body_request["beneficiary_id"] = beneficiary_id
    if credit_iban:
        body_request["credit_iban"] = credit_iban
    if credit_account_name:
        body_request["credit_account_name"] = credit_account_name
    if note:
        body_request["note"] = note
    if scheduled_date:
        body_request["scheduled_date"] = scheduled_date
    if attachment_ids:
        body_request["attachment_ids"] = attachment_ids

    url = f"{qonto_mcp.thirdparty_host}/v2/requests/transfers"
    headers = {**qonto_mcp.headers, "Content-Type": "application/json"}

    try:
        response = requests.post(url, headers=headers, json={"request": body_request})
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        # Surface response body if available — Qonto returns useful 422 hints.
        msg = str(e)
        try:
            msg += f" :: {e.response.text}"  # type: ignore[attr-defined]
        except Exception:
            pass
        return {"error": f"Failed to create transfer request: {msg}"}
