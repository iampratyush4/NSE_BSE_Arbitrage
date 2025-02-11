# arbitrage_cy.pyx
# cython: language_level=3

cdef public double compute_profit(double ask_price, double bid_price):
    if ask_price <= 0:
        return 0.0
    return ((bid_price - ask_price) / ask_price) * 100.0
