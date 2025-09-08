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


class SchwabAccount:
    def __init__(self, client, account_number):
        self._client = client
        self.account_number = account_number

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
        allocations = {}

        response = self._client.get_account(self._account_hash,
                                            fields=Client.Account.Fields.POSITIONS)
        assert response.status_code == httpx.codes.OK, response.raise_for_status()

        total = response.json()['aggregatedBalance']['liquidationValue']
        for position in response.json()['securitiesAccount']['positions']:
            ticker = position['instrument']['symbol']
            value = position['marketValue']
            allocations[ticker] = value / total * 100
        allocations['Cash'] = response.json()['securitiesAccount']['currentBalances']['cashAvailableForTrading'] / total * 100

        return allocations


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
            current_allocation = account.calculate_allocations()
            print('For account {}, the current asset allocation is:'
                  .format(account_number))
            for ticker, percentage in current_allocation.items():
                print('    {}: {}'.format(ticker, percentage))
            print()
