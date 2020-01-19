import blpapi
import numpy
import pandas
from .bbg_connect import *
from .tools import progress


def get_hist_data(symbols, fieldname, start_date, end_date, currency='USD', adjust_prices=True):

    data_dict = {}

    session, identity = connect_user()
    if not session.openService('//blp/refdata'):
        raise Exception('Failed to open //blp/refdata')
    else:
        ref_data_service = session.getService('//blp/refdata')

    request = ref_data_service.createRequest('HistoricalDataRequest')
    request.set('periodicityAdjustment', 'ACTUAL')
    request.set('periodicitySelection', 'DAILY')
    request.set('adjustmentFollowDPDF', False)

    if adjust_prices:
        request.set('adjustmentNormal', True)
        request.set('adjustmentAbnormal', True)
        request.set('adjustmentSplit', True)
    else:
        request.set('adjustmentNormal', False)
        request.set('adjustmentAbnormal', False)
        request.set('adjustmentSplit', False)

    tickers_list = list(set(list(symbols)))
    for ticker in tickers_list:
        request.getElement('securities').appendValue(ticker)
    request.getElement('fields').appendValue(fieldname)
    request.set('startDate', start_date)
    request.set('endDate', end_date)
    if currency is not None:
        request.set('currency', currency)

    session.sendRequest(request)

    while True:
        ev = session.nextEvent(500)
        if ev.eventType() in [blpapi.Event.PARTIAL_RESPONSE, blpapi.Event.RESPONSE]:
            for msg in ev:
                security_data = msg.getElement('securityData')
                field_data = security_data.getElement('fieldData')
                num_values = field_data.numValues()
                ticker = str(security_data.getElementAsString('security'))

                if security_data.hasElement('securityError'):
                    error_message = str(security_data.getElement('securityError').getElement('message').getValueAsString())

                if num_values > 0:
                    for k in range(num_values):
                        field = field_data.getValue(k)
                        if field.hasElement('date'):
                            date = pandas.to_datetime(str(field.getElement('date').getValue()), format='%Y-%m-%d', errors='coerce')
                        else:
                            continue
                        if field.hasElement(fieldname):
                            value = field.getElement(fieldname).getValue()
                            if ticker in data_dict.keys():
                                data_dict[ticker].update({date: value})
                            else:
                                data_dict[ticker] = {date: value}
                progress(count=len(data_dict.keys()), total=len(tickers_list), status='Download historical {} values...'.format(fieldname))

        if ev.eventType() == blpapi.Event.RESPONSE:
            break
    session.stop()

    for ticker in tickers_list:
        if ticker not in data_dict.keys():
            data_dict[ticker] = {}

    data = pandas.DataFrame.from_dict(data_dict, orient='columns').sort_index(axis=0)
    return data


def get_prices_hedged(symbols, hedge_symbol, start_date, end_date, hedge_dict={}, fieldname='PX_LAST', currency='USD', adjust_prices=True):

    for ticker in set(symbols):
        if ticker not in hedge_dict.keys():
            hedge_dict[ticker] = hedge_symbol

    tickers_list = list(set(symbols))
    hedges_list = list(set([hedge_dict[ticker] for ticker in symbols]))

    data = get_hist_data(symbols=list(set(tickers_list + hedges_list)),
                         fieldname=fieldname,
                         start_date=start_date,
                         end_date=end_date,
                         currency=currency,
                         adjust_prices=adjust_prices)

    stock_prices = data.loc[:, tickers_list]
    hedge_prices = data.loc[:, hedges_list]
    stock_hedges = stock_prices.apply(lambda x: hedge_prices.loc[:, hedge_dict[x.name]], axis=0)

    prices = stock_prices.where(numpy.isfinite(stock_prices) & numpy.isfinite(stock_hedges), numpy.nan)
    hedges = stock_hedges.where(numpy.isfinite(stock_prices) & numpy.isfinite(stock_hedges), numpy.nan)

    return prices, hedges