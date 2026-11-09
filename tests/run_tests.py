"""Run actual MQL core and EA in C++ MT4/file mocks. Not a MetaEditor compilation."""
import csv
import sys
from pathlib import Path
import re
import subprocess
import tempfile
from check_mql_identifiers import check_mql_identifiers, regression_checks
ROOT=Path(__file__).resolve().parents[1]
regression_checks()
for path in (ROOT/'Include/BuySellMagicCore.mqh',ROOT/'Experts/BuySellMagicRecorder.mq4'):
    check_mql_identifiers(path.read_text(),str(path))
core=(ROOT/'Include/BuySellMagicCore.mqh').read_text()
ea=(ROOT/'Experts/BuySellMagicRecorder.mq4').read_text()
ea=re.sub(r'^#property.*$|^#include.*$','',ea,flags=re.M)
ea=re.sub(r'\binput\s+','',ea)
source=(ROOT/'tests/mt4_stubs.cpp').read_text()+core+ea
source=re.sub(r'\b(string|PendingTheory)\s+&(\w+)\[\]',r'std::vector<\1>& \2',source)
source=re.sub(r'\b(string|PendingTheory)\s+(\w+)\[\]',r'std::vector<\1> \2',source)
main=r'''
void restart(){OnDeinit(0);assert(OnInit()==0);}
void step(double redPrice=100,double bluePrice=-1,int error=0){
 currentBar+=60;now=currentBar;tick={now,100};candle={};buffers[{0,1}]={redPrice,error};buffers[{1,1}]={bluePrice,0};OnTick();
}
int candidates(){int n=0;for(auto& row:disk[ledgerName])if(row[2]=="BAR" && row[19]=="true")n++;return n;}
void breakout(bool high=true,double dot=-1){
 currentBar+=60;now=currentBar;tick={now,high?101.:99.};candle.o=100;candle.h=102;candle.l=98;candle.c=high?101:99;
 buffers[{0,1}]={high?dot:-1,0};buffers[{1,1}]={high?-1:dot,0};OnTick();
}
int main(int argc,char** argv){
 assert(argc>=2);string test=argv[1];assert(!BuffersConfirmed && RedDotMode==-1 && BlueDotMode==-1);BuffersConfirmed=true;RedDotMode=0;BlueDotMode=1;
 if(test=="unconfirmed")BuffersConfirmed=false;
 if(test=="modes-15")ProbeMaxMode=15;
 if(test=="invalid-mode"){RedDotMode=8;assert(OnInit()==INIT_PARAMETERS_INCORRECT && disk.empty());return 0;}
 if(test=="invalid-min"){MinimumHorizontalDots=4;assert(OnInit()==INIT_PARAMETERS_INCORRECT && disk.empty());return 0;}
 if(test=="digits-five")Digits=5;
 if(test=="diagnostic-time")DiagnosticBarTime=currentBar-120;
 if(test=="restore-files"){
  assert(argc==3);string names[]={"BSMRecorder_USDJPY_M1_v1.csv","BSMRaw_USDJPY_M1_v1.csv"};
  for(string name:names){std::ifstream f(string(argv[2])+"/"+name);string line;while(std::getline(f,line)){std::vector<string> row;StringSplit(line,',',row);disk[name].push_back(row);}}
  auto saved=disk[names[0]];currentBar=StringToInteger(saved.back()[37])+60;now=currentBar;tick={now,100};
  assert(OnInit()==0 && candidates()==1 && pending[0].isSettled && disk[names[0]]==saved);return 0;
 }
 assert(OnInit()==0);assert(sequence==1);
 if(test=="diagnostic-time"){assert(candidates()==0 && disk[rawName].size()==9);assert(disk[rawName][1][4]==std::to_string(DiagnosticBarTime));return 0;}
 if(test=="digits-five"){for(int i=0;i<5;i++)step(100.000001);assert(red.count==5);step(100.00001);assert(red.count==1);breakout();assert(candidates()==0);return 0;}
 if(test=="group-six"){for(int i=0;i<6;i++)step();breakout();assert(candidates()==1 && disk[ledgerName].back()[13]=="6");return 0;}
 if(test=="low-wick"){
  for(int i=0;i<5;i++)step(-1,100);currentBar+=60;now=currentBar;tick={now,100};candle.o=101;candle.c=100;candle.h=102;candle.l=98;OnTick();assert(candidates()==0 && disk[ledgerName].back()[20].find("LOW:WICK_ONLY")!=string::npos);return 0;
 }
 if(test=="invalid-values"){
  assert(DotStatus(-1,0,100,10)=="ABSENT_MINUS_ONE");assert(DotStatus(EMPTY_VALUE,0,100,10)=="EMPTY_VALUE");
  for(double value:{0.,-2.,1e99,std::nan("")})assert(!UsableRead(DotStatus(value,0,100,10)));
  assert(DotStatus(100,4066,100,10)=="READ_ERROR");assert(DotStatus(100,0,0,10)=="NO_REFERENCE_PRICE");return 0;
 }
 if(test=="low-theory"){for(int i=0;i<5;i++)step(-1,100);breakout(false);datetime end=pending[0].expiry;now=end;tick={now,98};OnTick();now=end+1;tick={now,999};OnTimer();assert(disk[ledgerName].back()[25]=="WIN");restart();assert(pending[0].isSettled);return 0;}
 if(test=="low"){for(int i=0;i<5;i++)step(-1,100);breakout(false);assert(candidates()==1 && pending[0].direction=="LOW");return 0;}
 if(test=="four"){for(int i=0;i<4;i++)step();breakout();assert(candidates()==0);return 0;}
 if(test=="point-change"){for(int i=0;i<4;i++)step();step(100.001);breakout();assert(candidates()==0);return 0;}
 if(test=="missing"){for(int i=0;i<4;i++)step();step(-1);step();breakout();assert(candidates()==0);return 0;}
 if(test=="normalize"){for(int i=0;i<5;i++)step(100.00001);assert(red.count==5 && red.price=="100.000");return 0;}
 for(int i=0;i<5;i++)step();
 if(test=="restart-group")restart();
 if(test=="config-change"){RedDotMode=2;restart();assert(red.count==0);breakout();assert(candidates()==0);return 0;}
 if(test=="open-above"){
  currentBar+=60;now=currentBar;tick={now,101};candle.o=100.1;candle.c=101;candle.h=102;candle.l=98;OnTick();assert(candidates()==0);return 0;
 }
 if(test=="changed-break-dot"){breakout(true,101);assert(candidates()==1 && red.count==1 && red.price=="101.000");return 0;}
 if(test=="corrupt-consumed"){
  breakout(true,100);OnDeinit(0);disk[ledgerName].back()[31]="false";auto before=disk[ledgerName];assert(OnInit()==INIT_FAILED && disk[ledgerName]==before);return 0;
 }
 if(test=="wick"){
  currentBar+=60;now=currentBar;tick={now,100};candle.o=99;candle.c=100;candle.h=102;candle.l=98;OnTick();assert(candidates()==0);return 0;
 }
 if(test=="doji"){
  currentBar+=60;now=currentBar;tick={now,100};candle.o=100;candle.c=100;candle.h=102;candle.l=98;OnTick();assert(candidates()==0);return 0;
 }
 if(test=="read-error"){step(100,-1,4066);breakout();assert(candidates()==0);return 0;}
 if(test=="gap" || test=="restart-gap"){
  currentBar+=300;now=currentBar;tick={now,101};if(test=="restart-gap")restart();else OnTick();assert(red.count==0 && candidates()==0);return 0;
 }
 if(test=="disconnect"){connected=false;OnTick();connected=true;currentBar+=300;now=currentBar;OnTick();assert(candidates()==0 && red.count==0);return 0;}
 if(test=="timer-only"){currentBar+=60;now=currentBar;OnTimer();assert(red.count==5);OnTick();assert(red.count==6);return 0;}
 if(test=="ledger-write-failure" || test=="raw-write-failure" || test=="flush-failure"){
  failWrite=test=="flush-failure"?2:1;failName=test=="raw-write-failure"?rawName:ledgerName;auto before=disk[ledgerName];breakout();assert(halted && candidates()<=1);
  if(test!="flush-failure")assert(disk[ledgerName]==before);return 0;
 }
 if(test=="corrupt" || test=="header-mismatch" || test=="writer-lock"){
  if(test=="writer-lock"){int h=FileOpen(ledgerName,0,',',0);assert(h==INVALID_HANDLE);return 0;}
  OnDeinit(0);if(test=="corrupt")disk[ledgerName].back().pop_back();else disk[ledgerName][0][0]="WRONG";
  auto before=disk[ledgerName];assert(OnInit()==INIT_FAILED);assert(disk[ledgerName]==before);return 0;
 }
 if(test=="late-entry"){
  currentBar+=60;now=currentBar+2;tick={now,101};candle.o=100;candle.h=102;candle.l=98;candle.c=101;buffers[{0,1}]={-1,0};OnTick();assert(candidates()==1 && pending[0].entryBid=="");
 }else breakout(true,test=="duplicate"?100:-1);
 if(test=="unconfirmed"){assert(candidates()==0);return 0;}
 assert(candidates()==1);assert(pending[0].entry==currentBar && pending[0].expiry==currentBar+180);
 auto saved=disk[ledgerName];OnTick();assert(disk[ledgerName]==saved);
 if(test=="duplicate"){breakout(true,100);assert(candidates()==1);restart();breakout(true,100);assert(candidates()==1);return 0;}
 if(test=="restart-pending" || test=="unknown-expiry")restart();
 if(test=="config-pending"){RedDotMode=2;restart();assert(red.count==0 && pending.size()==1);}
 datetime expiry=pending[0].expiry;
 if(test!="unknown-expiry"){
  now=expiry;tick={now,test=="loss"?100.:test=="draw"?101.:102.};if(test=="stale-timer")OnTimer();else OnTick();
 }
 now=expiry+1;tick={now,999};OnTimer();assert(pending[0].isSettled);
 auto& last=disk[ledgerName].back();assert(last[2]=="THEORY");
 string result=test=="unknown-expiry" || test=="late-entry" || test=="stale-timer"?"UNKNOWN":test=="loss"?"LOSS":test=="draw"?"DRAW":"WIN";
 assert(last[25]==result);restart();assert(pending[0].isSettled && candidates()==1);
 if(test=="modes-15"){bool found=false;for(auto &row:disk[rawName])if(row[5]=="15"){assert(row[6]=="NOT_READ" && row[7]=="UNSUPPORTED_MT4_MODE");found=true;}assert(found);}
 if(test=="export"){
  assert(argc==3);for(auto& entry:disk){std::ofstream f(string(argv[2])+"/"+entry.first);for(auto& row:entry.second){for(size_t i=0;i<row.size();i++){if(i)f<<',';f<<row[i];}f<<'\n';}}
 }
 std::cout<<"passed "<<test<<"\n";
}
'''
cases=['high','low','four','point-change','missing','normalize','wick','doji','read-error','invalid-values','duplicate','restart-group','restart-pending','restart-gap','gap','disconnect','timer-only','unconfirmed','config-change','modes-15','late-entry','unknown-expiry','loss','draw','corrupt','header-mismatch','writer-lock','ledger-write-failure','raw-write-failure','flush-failure','open-above','changed-break-dot','corrupt-consumed','low-theory','config-pending','invalid-mode','invalid-min','digits-five','low-wick','group-six','diagnostic-time','stale-timer']
with tempfile.TemporaryDirectory(prefix='bsm-tests-') as folder:
    p=Path(folder);(p/'tests.cpp').write_text(source+main)
    subprocess.run(['g++','-std=c++11','-Wall','-Wextra','-Werror','-Wno-misleading-indentation','-fsanitize=address,undefined','-g',str(p/'tests.cpp'),'-o',str(p/'tests')],check=True)
    for case in cases:subprocess.run([str(p/'tests'),case],check=True)
    subprocess.run([str(p/'tests'),'export',folder],check=True)
    with (p/'BSMRecorder_USDJPY_M1_v1.csv').open() as f:
        rows=list(csv.reader(f));assert len(rows[0])==50 and all(len(r)==50 for r in rows)
        assert sum(r[2]=='BAR' and r[19]=='true' for r in rows[1:])==1
        assert rows[-1][25]=='WIN'
    subprocess.run([str(p/'tests'),'restore-files',folder],check=True)
    ledger=p/'BSMRecorder_USDJPY_M1_v1.csv';before=ledger.read_bytes()
    subprocess.run([sys.executable,str(ROOT/'analysis/export_signals.py'),'--ledger',str(ledger),'--out',str(p/'signals.csv')],check=True)
    with (p/'signals.csv').open(encoding='utf-8-sig') as f:
        signals=list(csv.DictReader(f));assert len(signals)==1 and signals[0]['theoretical_result']=='WIN' and signals[0]['breakout_open']!=''
    assert ledger.read_bytes()==before
    blocked=subprocess.run([sys.executable,str(ROOT/'analysis/export_signals.py'),'--ledger',str(ledger),'--out',str(ledger)],capture_output=True)
    assert blocked.returncode!=0 and ledger.read_bytes()==before
    with (p/'BSMRaw_USDJPY_M1_v1.csv').open() as f:
        rows=list(csv.reader(f));assert all(len(r)==12 for r in rows)
        assert {r[5] for r in rows[1:]}==set(map(str,range(8)))
for term in ('OrderSend','OrderClose','WebRequest','#import','ShellExecute','http://','https://'):
    assert term not in ea+core
print(f'{len(cases)} actual-code host scenarios plus CSV integration passed; MetaEditor/MT4 not tested.')
