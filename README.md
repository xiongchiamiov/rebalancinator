# Rebalancinator

Automatic rebalancing of your Schwab investment portfolios.

Background
----------

A basic principle of long-term investing, from a [Boglehead] perspective, is to
maintain a fixed _asset allocation_.  That is, you make decisions about things
like the percentage of stocks vs bonds based on your situation, and hold steady
in that no matter what the market is doing.

As the values of your various investments change, they will naturally drift
away from your desired allocation.  Thus, periodically you'll need to
_rebalance_ assets.  Depending on taxable status and personal preference, this
might involve selling overweight positions or simply adjusting where new
contributions get invested.  Regardless, this can be a somewhat tedious and
error-prone operation, especially if you find yourself with many accounts (eg
switching employers often and not rolling over each one's 401(k) plan) and/or a
more [slice-and-dice] portfolio than a simple [three-fund portfolio].

Additionally, Schwab makes this a bit more difficult to handle automatically
because they only support automatic investments via mutual funds.  That means
that if you want to set up a [pay yourself first] automatic transfer into
Schwab, your only investment option is mutual funds.  That can often be
limiting, and doesn't even address rebalancing!  The other option is Schwab's
robo-advisor, Intelligent Portfolios, which although free doesn't provide quite
as much control as I would like.

Rebalancinator is intended to provide a hands-off approach to rebalancing
portfolios, inspired by [infrastructure-as-code] concepts and powered by
Schwab's API.  It's also just a fun project.

[Boglehead]: https://www.bogleheads.org/wiki/Getting_started
[slice-and-dice]: https://www.bogleheads.org/wiki/Slice_and_dice
[three-fund portfolio]: https://www.bogleheads.org/wiki/Three-fund_portfolio
[pay yourself first]: https://www.investopedia.com/terms/p/payyourselffirst.asp
[infrastructure-as-code]: https://www.hashicorp.com/resources/what-is-infrastructure-as-code
