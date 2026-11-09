#!/usr/bin/env python3
"""Export the latest candidate evidence from the BSM append-only journal. Never edits inputs."""
import argparse
import csv
from decimal import Decimal
from pathlib import Path

FIELDS='recorder_version sequence event key server_time symbol timeframe signal_bar_time detection_time direction red_dot_price blue_dot_price dot_buffer_mode dot_count horizontal_price breakout_open breakout_high breakout_low breakout_close breakout_valid rejection_reason theoretical_entry_time theoretical_entry_bid theoretical_expiry_time theoretical_expiry_bid theoretical_result indicator_read_status red_group_price red_group_count red_group_first red_group_last red_group_consumed blue_group_price blue_group_count blue_group_first blue_group_last blue_group_consumed cursor configuration source entry_quote_time expiry_quote_time observed_time result_status red_read_status blue_read_status red_raw blue_raw digits end'.split()

def load(path):
    signals={}
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if reader.fieldnames!=FIELDS:raise ValueError('Expected BSM v1 50-column ledger')
        for sequence,row in enumerate(reader,1):
            if (None in row or any(v is None for v in row.values()) or row['sequence']!=str(sequence) or
                row['recorder_version']!='1.00' or row['end']!='COMMIT' or row['timeframe']!='M1' or
                row['key']!=f"{row['symbol']}|M1|{row['signal_bar_time']}"):
                raise ValueError(f'Invalid ledger record {sequence+1}')
            if row['event'] in ('BAR','RESET','CONFIG'):
                if row['breakout_valid']=='true':
                    if row['event']!='BAR' or row['key'] in signals or row['direction'] not in ('HIGH','LOW') or row['result_status']!='PENDING' or row['theoretical_result']!='UNKNOWN':raise ValueError('Duplicate/invalid candidate')
                    if int(row['theoretical_entry_time'])!=int(row['signal_bar_time'])+60 or int(row['theoretical_expiry_time'])!=int(row['theoretical_entry_time'])+180:raise ValueError('Invalid candidate clock')
                    signals[row['key']]=row
                elif row['breakout_valid']!='false' or row['direction']!='NONE':raise ValueError('Invalid state row')
            elif row['event']=='THEORY':
                original=signals.get(row['key'])
                if original is None or original['result_status']!='PENDING':raise ValueError('Orphan/duplicate theoretical result')
                for field in ('symbol','direction','signal_bar_time','theoretical_entry_time','theoretical_expiry_time','theoretical_entry_bid','entry_quote_time'):
                    if original[field]!=row[field]:raise ValueError('Candidate anchor changed')
                if int(row['observed_time'])<=int(row['theoretical_expiry_time']):raise ValueError('Premature settlement')
                entry=row['theoretical_entry_bid'];exit=row['theoretical_expiry_bid'];expected='UNKNOWN'
                if row['entry_quote_time']!=('0' if not entry else row['theoretical_entry_time']):raise ValueError('Invalid entry quote time')
                if row['expiry_quote_time']!=('0' if not exit else row['theoretical_expiry_time']):raise ValueError('Invalid expiry quote time')
                if entry and exit:
                    a,b=Decimal(entry),Decimal(exit)
                    if not a.is_finite() or not b.is_finite() or a<=0 or b<=0:raise ValueError('Invalid Bid')
                    expected='DRAW' if a==b else 'WIN' if (b>a)==(row['direction']=='HIGH') else 'LOSS'
                if row['theoretical_result']!=expected or row['result_status']!=('FINAL_UNMEASURED' if expected=='UNKNOWN' else 'FINAL_MEASURED'):raise ValueError('Result contradicts price evidence')
                merged=dict(original)
                for field in ('theoretical_expiry_bid','theoretical_result','expiry_quote_time','observed_time','result_status'):merged[field]=row[field]
                signals[row['key']]=merged
            else:raise ValueError('Unknown journal event')
    return list(signals.values())

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ledger',type=Path,required=True)
    parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args()
    if args.out.resolve()==args.ledger.resolve() or args.out.exists():parser.error('Choose a NEW output file; never overwrite journals or reports')
    rows=load(args.ledger)
    with args.out.open('x',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=FIELDS);writer.writeheader();writer.writerows(rows)
    print(f'{len(rows)} candidates; MT4 Bid theory only, not actual TheOption settlement')

if __name__=='__main__':main()
