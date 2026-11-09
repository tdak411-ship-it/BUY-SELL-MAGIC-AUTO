#!/usr/bin/env python3
"""Compare raw closed-M1 probe values to a user-observed Data Window price; no buffer-role inference."""
import argparse
import calendar
import csv
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import json
from pathlib import Path

FIELDS='recorder_version server_time symbol timeframe sample_bar_time mode value value_status read_error configuration source end'.split()
INPUTS=('SignalPeriod','ArrowPeriod','SL_pips','AlertON','Email')

def inspect(path,symbol,bar,expected=Decimal('158.098'),digits=3):
    expected=Decimal(expected)
    if not expected.is_finite() or expected<=0 or not 0<=digits<=8:raise ValueError('Invalid reference price/digits')
    quantum=Decimal(1).scaleb(-digits);observations=[]
    with Path(path).open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=FIELDS:raise ValueError('Expected BSM raw 12-column header')
        for row in reader:
            if None in row or any(v is None for v in row.values()) or row['end']!='COMMIT':raise ValueError('Incomplete raw record')
            if row['symbol']!=symbol or row['timeframe']!='M1' or row['sample_bar_time']!=str(bar):continue
            mode=int(row['mode']);error=int(row['read_error']);match=False;display=None
            if 0<=mode<=7 and error==0 and row['value_status']=='PRICE':
                try:
                    value=Decimal(row['value'])
                    if value.is_finite() and value>0:
                        rounded=value.quantize(quantum,rounding=ROUND_HALF_UP);display=str(rounded)
                        match=rounded==expected.quantize(quantum,rounding=ROUND_HALF_UP)
                except InvalidOperation:pass
            config=dict(part.split('=',1) for part in row['configuration'].split(';') if '=' in part)
            observations.append(dict(mode=mode,value=row['value'],value_status=row['value_status'],read_error=error,
                display_value=display,display_price_match=match,observed_server_epoch=row['server_time'],
                input_method=config.get('inputs','UNKNOWN'),indicator_inputs={key:config.get(key) for key in INPUTS},
                configuration=row['configuration'],source=row['source']))
    return dict(symbol=symbol,sample_bar_epoch=bar,expected_display_price=str(expected),digits=digits,
        status='SAMPLES_FOUND' if observations else 'REQUESTED_SAMPLE_NOT_FOUND',
        matching_modes=sorted({r['mode'] for r in observations if r['display_price_match']}),
        comparison_scope='DISPLAY_PRECISION_ONLY_USER_EXPECTED_VALUE',buffer_identity_verified=False,
        chart_settings_verified=False,observations=observations)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--raw',type=Path,required=True)
    parser.add_argument('--symbol',default='USDJPY')
    parser.add_argument('--bar',default='2026.11.09 09:43:00',help='MT4 server wall time; no timezone conversion')
    parser.add_argument('--expected',default='158.098')
    parser.add_argument('--digits',type=int,default=3)
    args=parser.parse_args()
    try:
        # MQL server datetime is compared in its recorded wall-time representation,
        # without guessing the broker UTC offset or converting to the user's timezone.
        bar=calendar.timegm(datetime.strptime(args.bar,'%Y.%m.%d %H:%M:%S').timetuple())
        report=inspect(args.raw,args.symbol,bar,Decimal(args.expected),args.digits)
    except (ValueError,InvalidOperation) as error:parser.error(str(error))
    print(json.dumps(report,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
