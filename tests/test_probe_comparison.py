import csv
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
import check_probe as probe

class ProbeComparisonTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory();self.addCleanup(self.folder.cleanup)
        self.path=Path(self.folder.name)/'raw.csv'
        self.rows=[]
        for mode,value,status,error in [(0,'EMPTY_VALUE','EMPTY_VALUE',0),(1,'-1.0000000000000000','ABSENT_MINUS_ONE',0),(2,'158.098','READ_ERROR',4802),(3,'158.0980000000000132','PRICE',0),(4,'158.099','PRICE',0),(5,'NONFINITE','NONFINITE',0),(6,'158.0984','PRICE',0),(7,'0','INVALID_ZERO',0)]:
            self.rows.append(dict(zip(probe.FIELDS,['1.00','1794218000','USDJPY','M1','1794217380',str(mode),value,status,str(error),
                'inputs=EXPLICIT_FIVE_USER_SUPPLIED_ORDER;SignalPeriod=12;ArrowPeriod=2;SL_pips=100;AlertON=true;Email=true',
                'ICUSTOM_EXPLICIT5_CHART_MATCH_UNVERIFIED','COMMIT'])))
        self.write()
    def write(self):
        with self.path.open('w',newline='') as stream:
            writer=csv.DictWriter(stream,fieldnames=probe.FIELDS);writer.writeheader();writer.writerows(self.rows)
    def report(self):return probe.inspect(self.path,'USDJPY',1794217380)
    def test_display_matches_are_not_buffer_role_proof(self):
        result=self.report();self.assertEqual(result['matching_modes'],[3,6]);self.assertFalse(result['buffer_identity_verified']);self.assertFalse(result['chart_settings_verified'])
        self.assertEqual(result['observations'][3]['indicator_inputs'],dict(SignalPeriod='12',ArrowPeriod='2',SL_pips='100',AlertON='true',Email='true'))
    def test_read_error_cannot_match_even_if_raw_value_matches(self):
        row=self.report()['observations'][2];self.assertEqual(row['read_error'],4802);self.assertFalse(row['display_price_match'])
    def test_missing_time_and_symbol_not_substituted(self):
        self.assertEqual(probe.inspect(self.path,'USDJPY',1794217440)['status'],'REQUESTED_SAMPLE_NOT_FOUND')
        self.assertEqual(probe.inspect(self.path,'USDJPY.a',1794217380)['observations'],[])
    def test_read_only(self):
        before=self.path.read_bytes();self.report();self.assertEqual(self.path.read_bytes(),before)
    def test_partial_and_header_rejected(self):
        self.path.write_text('bad,header\n')
        with self.assertRaises(ValueError):self.report()
        self.write();self.path.write_text(self.path.read_text()+'partial\n')
        with self.assertRaises(ValueError):self.report()
    def test_legacy_samples_keep_default_input_provenance(self):
        self.rows[3]['configuration']='inputs=DEFAULTS_UNCONFIRMED';self.rows[3]['source']='ICUSTOM_DEFAULT_INPUTS_CHART_MATCH_UNVERIFIED';self.write()
        row=self.report()['observations'][3];self.assertEqual(row['input_method'],'DEFAULTS_UNCONFIRMED');self.assertIsNone(row['indicator_inputs']['SignalPeriod'])
    def test_cli_defaults_target_requested_server_bar(self):
        output=subprocess.check_output([sys.executable,str(ROOT/'analysis/check_probe.py'),'--raw',str(self.path)],text=True)
        report=json.loads(output);self.assertEqual(report['sample_bar_epoch'],1794217380);self.assertEqual(report['expected_display_price'],'158.098')
    def test_invalid_reference_rejected(self):
        for value in ('NaN','-1','0'):
            with self.assertRaises(ValueError):probe.inspect(self.path,'USDJPY',1794217380,Decimal(value))

if __name__=='__main__':unittest.main()
