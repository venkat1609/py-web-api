from typing import List, Optional, Literal, Dict
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from datetime import date
from dateutil.relativedelta import relativedelta

router = APIRouter()


# ─────── Pydantic Models ───────
class Repayment(BaseModel):
    month: int = Field(..., gt=0)
    amount: float = Field(..., gt=0)
    recurring: bool = False


class InterestRevision(BaseModel):
    month: int = Field(..., gt=0)
    interest: float = Field(..., gt=0)


class AdjustedEMIEntry(BaseModel):
    month: int = Field(..., gt=0)
    emi: float = Field(..., gt=0)


class LoanRequest(BaseModel):
    amount: float
    interest: float
    tenure_in_months: Optional[int] = None
    tenure_in_years: Optional[int] = None
    adjust: Literal["tenure", "emi"]
    repayments: Optional[List[Repayment]] = []
    interest_revision: Optional[List[InterestRevision]] = []
    adjusted_emi_schedule: Optional[List[AdjustedEMIEntry]] = []
    start_date: Optional[date] = Field(default_factory=date.today)


class AmortizationEntry(BaseModel):
    month: int
    date: date
    emi: float
    interest_rate: float
    principal_component: float
    interest_component: float
    prepayment: float
    remaining_principal: float


class AmortizationSchedule(BaseModel):
    loan_amount: float
    initial_interest_rate: float
    original_tenure_months: int
    final_tenure_months: int
    total_amount_paid: float
    total_interest_paid: float
    schedule: List[AmortizationEntry]


# ─────── Utility ───────
def _emi(principal: float, rate: float, months: int) -> float:
    if months <= 0 or principal <= 0:
        return 0
    factor = (1 + rate) ** months
    return principal * rate * factor / (factor - 1)


# ─────── Core Logic ───────
def calculate_schedule(data: LoanRequest) -> AmortizationSchedule:
    tenure_months = data.tenure_in_months or (data.tenure_in_years * 12)
    monthly_rate = data.interest / (12 * 100)
    remaining = data.amount
    start_date = data.start_date or date.today()

    rate_changes: Dict[int, float] = {
        r.month: r.interest for r in data.interest_revision or []
    }

    emi_changes: Dict[int, float] = {
        e.month: e.emi for e in sorted(data.adjusted_emi_schedule or [], key=lambda x: x.month)
    }

    emi = emi_changes.get(1, _emi(remaining, monthly_rate, tenure_months))

    total_interest_paid = 0.0
    total_amount_paid = 0.0
    schedule: List[AmortizationEntry] = []
    current_rate = data.interest
    month = 1
    max_months = max(tenure_months * 3, 1500)

    while remaining > 0 and month <= max_months:
        # Interest revision
        if month in rate_changes:
            current_rate = rate_changes[month]
            monthly_rate = current_rate / (12 * 100)
            if data.adjust == "emi":
                rem_term = tenure_months - month + 1
                emi = _emi(remaining, monthly_rate, rem_term)

        # EMI change
        if month in emi_changes:
            emi = emi_changes[month]

        # Calculate interest/principal
        interest = remaining * monthly_rate
        principal = emi - interest
        if principal < 0:
            raise HTTPException(400, f"EMI {emi:.2f} too low to cover interest {interest:.2f} at month {month}")

        # Calculate prepayment
        prepayment = 0.0
        for r in data.repayments or []:
            if r.recurring and month >= r.month:
                prepayment += r.amount
            elif not r.recurring and month == r.month:
                prepayment += r.amount

        # Prevent overpay
        if principal + prepayment > remaining:
            prepayment = max(remaining - principal, 0)

        # Calculate after payment
        remaining -= (principal + prepayment)
        total_interest_paid += interest
        total_amount_paid += emi + prepayment
        emi_date = start_date + relativedelta(months=month - 1)

        # Final month — stop early
        if remaining <= 0:
            # schedule.append(AmortizationEntry(
            #     month=month,
            #     date=emi_date,
            #     emi=round(emi, 2),
            #     interest_rate=round(current_rate, 4),
            #     principal_component=round(principal, 2),
            #     interest_component=round(interest, 2),
            #     prepayment=round(prepayment, 2),
            #     remaining_principal=0.0,
            # ))
            break

        # Normal case
        schedule.append(AmortizationEntry(
            month=month,
            date=emi_date,
            emi=round(emi, 2),
            interest_rate=round(current_rate, 4),
            principal_component=round(principal, 2),
            interest_component=round(interest, 2),
            prepayment=round(prepayment, 2),
            remaining_principal=round(remaining, 2),
        ))

        # Recalculate EMI after prepayment if needed
        if data.adjust == "emi" and prepayment > 0 and remaining > 0:
            rem_term = max(tenure_months - month, 1)
            emi = _emi(remaining, monthly_rate, rem_term)

        month += 1

    return AmortizationSchedule(
        loan_amount=data.amount,
        initial_interest_rate=data.interest,
        original_tenure_months=tenure_months,
        final_tenure_months=len(schedule),
        total_amount_paid=round(total_amount_paid, 2),
        total_interest_paid=round(total_interest_paid, 2),
        schedule=schedule,
    )


# ─────── API Endpoint ───────
@router.post("/amortization", response_model=AmortizationSchedule)
async def amortization(data: LoanRequest):
    return calculate_schedule(data)
