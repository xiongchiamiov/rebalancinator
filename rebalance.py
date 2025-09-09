#!/usr/bin/env python3
"""rebalancinator

Usage:
    rebalancinator [options]

Options:
    -h --help                      Show this screen.
       --dry-run                   Don't execute any trades.
       --no-confirm                Don't confirm any actions.  Designed for
                                   cron operation.
       --percentage-limit=<limit>  Only adjust positions that are off by at
                                   least this percentage.
       --sell                      Sell positions to rebalance.  Recommended
                                   only for tax-advantaged accounts.
"""

# May you recognize your weaknesses and share your strengths.
# May you share freely, never taking more than you give.
# May you find love and love everyone you find.

import httpx
import yaml
from collections import namedtuple
from docopt import docopt
from functools import cached_property
from schwab.client import Client
from schwab.auth import easy_client


class RebalancinatorException(Exception):
    pass


class IncorrectWeightingException(RebalancinatorException):
    def __init__(self, allocations):
        self.allocations = allocations

    def __str__(self):
        return "Weights don't add up to 100: {}".format(self.allocations)


def calculate_allocations(portfolio, multiplier=1):
    """Given a nested portfolio, return the desired allocation for each
    position.

    portfolio:   A list of dicts in a format not specified here.
    multiplier:  Multiply all values by this.  Intended to be used when we're
                 looking already at a subset of the overall portfolio (eg 50%
                 of 10% of the portfolio would be 50*.1=5%).
    """
    allocations = {}
    running_total = 0
    for asset_class in portfolio:
        for percentage, investment in asset_class.items():
            running_total += percentage

            # Is this a single ticker?
            if isinstance(investment, str):
                allocations[investment] = int(percentage * multiplier)
                continue

            # If it's a nested breakdown instead, recurse.
            allocations.update(
                calculate_allocations(investment, percentage/100))

    # Check that the user correctly gave us numbers that add up to 100%.
    if running_total != 100:
        raise IncorrectWeightingException(allocations)

    # Sort the dict with largest first, because that's convenient and if this
    # is a performance issue your portfolio is too complex.
    # https://stackoverflow.com/a/613218/120999
    return dict(sorted(allocations.items(), key=lambda item: item[1], reverse=True))


class Portfolio:
    def __init__(self):
        self.cash = None
        self.positions = {}

    def __str__(self):
        string = []
        for ticker, percentage in self.positions.items():
            string.append('    {}: {}'.format(ticker, percentage))
        string.append('    Cash: {}'.format(self.cash))

        return '\n'.join(string)


Position = namedtuple('Position', ['dollars', 'percent', 'shares'])
Price = namedtuple('Price', ['bid', 'ask'])


class SchwabAccount:
    def __init__(self, client, account_number):
        self._client = client
        self.account_number = account_number
        self.portfolio = Portfolio()
        self.total = None

    @cached_property
    def _account_hash(self):
        response = self._client.get_account_numbers()
        assert response.status_code == httpx.codes.OK, response.raise_for_status()

        for mapping in response.json():
            if mapping['accountNumber'] == self.account_number:
                return mapping['hashValue']

        # TODO: Throw some sort of exception
        return None

    def calculate_allocations(self):
        response = self._client.get_account(self._account_hash,
                                            fields=Client.Account.Fields.POSITIONS)
        assert response.status_code == httpx.codes.OK, response.raise_for_status()

        self.total = response.json()['aggregatedBalance']['liquidationValue']
        for position in response.json()['securitiesAccount']['positions']:
            ticker = position['instrument']['symbol']
            value = position['marketValue']
            percentage = value / self.total * 100
            shares = position['shortQuantity'] + position['longQuantity']
            self.portfolio.positions[ticker] = Position(value, percentage, shares)
        cash = response.json()['securitiesAccount']['currentBalances']['cashAvailableForTrading']
        # We set the number of shares of cash equal to the number of dollars to
        # be akin to a money market fund, and because nothing else makes much
        # sense.
        self.portfolio.cash = Position(cash, cash / self.total * 100, cash)

    def lookup_price(self, symbol):
        response = self._client.get_quote(symbol)
        assert response.status_code == httpx.codes.OK, response.raise_for_status()

        quote = response.json()[symbol]['quote']
        return Price(quote['bidPrice'], quote['askPrice'])


Buy = namedtuple('Buy', ['ticker', 'shares', 'price'])
Sell = namedtuple('Sell', ['ticker', 'shares', 'price'])


class AlwaysRebalance:
    '''Buy and sell anything to get to the target AA.'''
    @staticmethod
    def analyze(account, target_allocation):
        cash = account.portfolio.cash.dollars
        orders = []
        desired_buys = []

        for ticker, position in account.portfolio.positions.items():
            price = account.lookup_price(ticker)

            if ticker not in target_allocation:
                cash += position.shares * price.bid
                orders.append(Sell(ticker, position.shares, price.bid))
                continue
            if position.percent > target_allocation[ticker]:
                desired = account.total * target_allocation[ticker] / 100
                surplus = position.dollars - desired
                # We could take a number of approaches to dealing with
                # over-under (since Schwab doesn't support fractional shares):
                # 1. Sell until the next one would push us under, to reduce the
                #    amount of churn.
                # 2. Sell until we go under, to do more "sell high buy low".
                # 3. Round to the nearest, to be as accurate as possible.
                # Really it shouldn't matter much, unless you have very
                # expensive shares compared to your positions (ie you're buying
                # BRK/A).  We're going with option 1 because... I wanted to.
                num_shares = surplus // price.bid
                cash += num_shares * price.bid
                orders.append(Sell(ticker, num_shares, price.bid))
                continue
            elif position.percent < target_allocation[ticker]:
                desired = account.total * target_allocation[ticker] / 100
                deficiency = desired - position.dollars
                # See above note in the sell section on how to deal with
                # boundary issues.  To match what's there, we're going to buy
                # until the next would put us over.
                num_shares = deficiency // price.ask
                # Because all these bits don't necessarily add together nicely,
                # we're going to just build a list of what we'd like to buy,
                # and then once we know how much cash we'll have, go through
                # and figure out what we can actually do.
                desired_buys.append(Buy(ticker, num_shares, price.ask))
                continue
            else:
                # We have exactly the perfect amount we want!
                continue

        # Sort by the highest share price first, so we can utilize as much of
        # our cash as possible.
        desired_buys.sort(key=lambda x: x.price, reverse=True)

        for desired_buy in desired_buys:
            if desired_buy.shares * desired_buy.price > cash:
                # If we've run out of money to buy as much of this as we want,
                # just get what we can.
                num_shares = cash // desired_buy.price
                # Named tuples are immutable, so we have to make a new one.
                desired_buy = desired_buy._replace(shares=num_shares)
            cash -= desired_buy.shares * desired_buy.price
            orders.append(desired_buy)

        return orders


if __name__ == '__main__':
    arguments = docopt(__doc__)
    print(arguments)

    # TODO: Probably use a different/better method of pulling in these keys.
    # But this works for now.
    import local_settings
    client = easy_client(api_key=local_settings.APP_KEY,
                         app_secret=local_settings.APP_SECRET,
                         callback_url='https://127.0.0.1:8182',
                         token_path='token.json')

    with open('config.yaml', 'r') as f:
        configs = yaml.safe_load(f)

    for config in configs:
        target_allocation = calculate_allocations(config['portfolio'])
        print('For accounts {}, the target asset allocation is:'
              .format(config['accounts']))
        for ticker, percentage in target_allocation.items():
            print('    {}: {}'.format(ticker, percentage))
        print()

        account_numbers = [x.strip() for x in str(config['accounts']).split(',')]
        for account_number in account_numbers:
            account = SchwabAccount(client, account_number)
            account.calculate_allocations()
            print('For account {}, the current asset allocation is:'
                  .format(account_number))
            print(account.portfolio)
            print()

            changes = AlwaysRebalance.analyze(account, target_allocation)
            print(changes)
            #confirm or not
            #account.execute_orders(changes)
            #account.calculate_allocations()
            #print(account.portfolio)
