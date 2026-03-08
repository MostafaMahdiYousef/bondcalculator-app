import streamlit as st
from datetime import date
from calendar import monthrange


def add_months(dt: date, months: int) -> date:
    y = dt.year + (dt.month - 1 + months) // 12
    m = (dt.month - 1 + months) % 12 + 1
    d = min(dt.day, monthrange(y, m)[1])
    return date(y, m, d)


def previous_coupon_date(settlement: date, maturity: date, freq: int = 2) -> date:
    months = 12 // freq
    d = maturity
    while d > settlement:
        d = add_months(d, -months)
    return d


def next_coupon_date(settlement: date, maturity: date, freq: int = 2) -> date:
    prev_c = previous_coupon_date(settlement, maturity, freq)
    return add_months(prev_c, 12 // freq)


def coupon_dates_after_settlement(settlement: date, maturity: date, freq: int = 2):
    dates = []
    nxt = next_coupon_date(settlement, maturity, freq)
    while nxt <= maturity:
        dates.append(nxt)
        nxt = add_months(nxt, 12 // freq)
    return dates


def accrued_interest(clean_settlement: date, maturity: date, coupon_rate_pct: float, face: float, freq: int = 2):
    prev_c = previous_coupon_date(clean_settlement, maturity, freq)
    next_c = add_months(prev_c, 12 // freq)

    coupon_per_period = face * (coupon_rate_pct / 100.0) / freq
    days_accrued = (clean_settlement - prev_c).days
    days_period = (next_c - prev_c).days

    ai = coupon_per_period * days_accrued / days_period
    return ai, prev_c, next_c, days_accrued, days_period


def dirty_price_from_yield(
    ytm_pct: float,
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    face: float,
    freq: int = 2,
):
    y = ytm_pct / 100.0
    coupon_per_period = face * (coupon_rate_pct / 100.0) / freq

    prev_c = previous_coupon_date(settlement, maturity, freq)
    next_c = add_months(prev_c, 12 // freq)

    days_to_next = (next_c - settlement).days
    days_period = (next_c - prev_c).days
    fraction = days_to_next / days_period

    cashflow_dates = coupon_dates_after_settlement(settlement, maturity, freq)

    pv = 0.0
    for i, cf_date in enumerate(cashflow_dates):
        exponent = fraction + i
        cf = coupon_per_period
        if cf_date == maturity:
            cf += face
        pv += cf / ((1 + y / freq) ** exponent)

    return pv


def solve_ytm_from_dirty_price(
    dirty_price: float,
    settlement: date,
    maturity: date,
    coupon_rate_pct: float,
    face: float,
    freq: int = 2,
):
    low = -99.0
    high = 100.0

    for _ in range(200):
        mid = (low + high) / 2
        model_price = dirty_price_from_yield(mid, settlement, maturity, coupon_rate_pct, face, freq)
        if model_price > dirty_price:
            low = mid
        else:
            high = mid

    return (low + high) / 2


st.set_page_config(page_title="Bond Yield Calculator", page_icon="📈")
st.title("Bond Annual Yield Calculator")
st.write("Plain non-callable semiannual bond using clean price and accrued interest.")

coupon_rate = st.number_input("Coupon rate (%)", min_value=0.0, value=2.000, step=0.001, format="%.3f")
price = st.number_input("Clean price", min_value=0.0001, value=100.000, step=0.001, format="%.3f")
face_value = st.number_input("Face value", min_value=0.0001, value=100.00, step=0.01, format="%.2f")
maturity_date = st.date_input("Maturity date", value=date(2027, 1, 1))
settlement_date = st.date_input("Settlement date", value=date.today())
freq = st.selectbox("Coupon frequency", options=[2], index=0)

if maturity_date <= settlement_date:
    st.error("Maturity date must be after settlement date.")
else:
    ai, prev_c, next_c, days_accrued, days_period = accrued_interest(settlement_date, maturity_date, coupon_rate, face_value, freq)
    dirty_price = price + ai

    ytm = solve_ytm_from_dirty_price(dirty_price, settlement_date, maturity_date, coupon_rate, face_value, freq)

    st.write(f"Previous coupon date: {prev_c}")
    st.write(f"Next coupon date: {next_c}")
    st.write(f"Accrued interest: {ai:.3f}")
    st.write(f"Dirty price: {dirty_price:.3f}")

    st.subheader("Annual yield")
    st.write(f"{ytm:.3f}%")
