"""Run actual MQL core and EA in C++ MT4/file mocks. Not a MetaEditor compilation."""
import csv
import sys
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import unquote
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

void exportMockFiles(string folder){for(auto& entry:disk){std::ofstream f(folder+"/"+entry.first);for(auto& row:entry.second){for(size_t i=0;i<row.size();i++){if(i)f<<',';f<<row[i];}f<<'\n';}}}
void v103Case(string test,string folder){
 if(test=="v103-restore"){
  string names[]={"BSMRecorder_USDJPY_M1_v1.csv","BSMRaw_USDJPY_M1_v1.csv","BSMDiagnostics_USDJPY_M1_v1.csv","BSMObjects_USDJPY_M1_v1.csv"};
  for(string name:names){std::ifstream f(folder+"/"+name);string line;while(std::getline(f,line)){std::vector<string> row;StringSplit(line,',',row);disk[name].push_back(row);}}
  auto primary=disk[names[0]],raw=disk[names[1]],diagnostics=disk[names[2]],objects=disk[names[3]];
  currentBar=StringToInteger(primary.back()[37])+60;now=currentBar;tick={now,158};
  assert(OnInit()==0 && candidates()==0 && disk[names[0]]==primary && disk[names[1]]==raw);
  assert(disk[names[2]].size()==diagnostics.size()+1 && disk[names[3]].size()==objects.size()+1);
  for(size_t i=0;i<diagnostics.size();i++)assert(disk[names[2]][i]==diagnostics[i]);
  for(size_t i=0;i<objects.size();i++)assert(disk[names[3]][i]==objects[i]);return;
 }
 BuffersConfirmed=false;DiagnosticBarTime=currentBar-120;
 bool objectFixture=test=="v103-objects" || test=="v103-invalid-object" || test=="v103-property-error" || test=="v103-limit" || test=="v103-export";
 if(objectFixture){
  ChartObject first;first.name="=red,dot%\"\n";first.text="note,\"quoted\"\n%2C";first.time1=DiagnosticBarTime;first.width=6;chartObjects.push_back(first);
  ChartObject second;second.name="other-indicator-trend";second.type=OBJ_TREND;second.price1=157.924;second.price2=157.924;chartObjects.push_back(second);
  ChartObject label;label.name="screen-label";label.type=OBJ_LABEL;chartObjects.push_back(label);
 }
 if(test=="v103-lines"){
  ChartObject h;h.type=OBJ_HLINE;h.name="hline";h.time1=0;chartObjects.push_back(h);
  ChartObject v;v.type=OBJ_VLINE;v.name="vline";v.price1=0;chartObjects.push_back(v);
 }
 if(test=="v103-object-change")spawnObjectOnProbe=true;
 if(test=="v103-invalid-object"){chartObjects[0].price1=std::nan("");chartObjects[0].time1=-1;chartObjects[0].color=-1;chartObjects[0].width=0;chartObjects[1].time2=0;chartObjects[1].price2=EMPTY_VALUE;}
 if(test=="v103-property-error"){chartObjects[0].errors[{OBJPROP_TIME,0}]=4202;chartObjects[0].errors[{OBJPROP_PRICE,0}]=4202;chartObjects[0].errors[{OBJPROP_TEXT,0}]=4203;}
 if(test=="v103-enumeration-error")objectsTotalError=4200;
 if(test=="v103-limit")ObjectSnapshotLimit=1;
 if(test=="v103-disabled")CollectChartObjects=false;
 if(test=="v103-mismatch")lookupShiftBias=1;
 if(test=="v103-history-missing")missingDiagnostic=true;
 if(test=="v103-bars-missing")availableBars=0;
 if(test=="v103-dll-query-error")dllQueryError=4000;
 if(test=="v103-dll-true")dllFlag=true;
 if(test=="v103-diagnostic-write" || test=="v103-object-write" || test=="v103-diagnostic-flush")DiagnosticBarTime=0;
 if(test=="v103-dll-reported" || test=="v103-export"){
  DiagnosticBarTime=1794217380;DiagnosticBarTime2=1794233460;currentBar=DiagnosticBarTime2+60;now=currentBar;tick={now,158};
  if(!chartObjects.empty()){chartObjects[0].time1=DiagnosticBarTime;chartObjects[1].time1=DiagnosticBarTime2;chartObjects[1].time2=DiagnosticBarTime2+60;}
  for(datetime bar:{DiagnosticBarTime,DiagnosticBarTime2})for(int mode=0;mode<8;mode++)buffers[{mode,(int)((currentBar-bar)/60)}]={mode<6?EMPTY_VALUE:0,0};
 }
 if(test=="v103-values"){
  buffers[{0,2}]={EMPTY_VALUE,0};buffers[{1,2}]={-1,0};buffers[{2,2}]={0,0};buffers[{3,2}]={158.098,4802};buffers[{4,2}]={158.098,0};
 }
 if(test=="v103-mode15")ProbeMaxMode=15;
 bool originalDll=dllFlag;assert(OnInit()==0);assert(dllFlag==originalDll && candidates()==0);
 auto &detail=disk[diagnosticsName];auto &objects=disk[objectsName];assert(detail[0].size()==41 && objects[0].size()==30);
 assert(detail[1][3]=="SESSION" && detail[1][26]=="UNVERIFIED_REVIEW_EXPERTS_LOG");
 assert(detail[1][35]==(dllQueryError?"UNAVAILABLE":Flag(originalDll)));
 for(size_t i=1;i<detail.size();i++){assert(detail[i].size()==41 && detail[i][1]==std::to_string(i) && detail[i][40]=="COMMIT");}
 if(test=="v103-disabled"){assert(objects.size()==1 && detail[1][37]=="false");return;}
 if(test=="v103-enumeration-error"){assert(objects[1][21].find("OBJECT_ENUMERATION_ERROR")==0 && objects[1][22].find("total_error=4200")!=string::npos);return;}
 if(test=="v103-mismatch" || test=="v103-history-missing" || test=="v103-bars-missing"){
  assert(indicatorCalls.empty());auto &row=detail[2];assert(row[20]=="false" && row[21]=="NOT_READ");
  if(test=="v103-mismatch")assert(row[15]!=row[18] && row[34]=="BAR_TIME_MISMATCH");
  if(test=="v103-history-missing")assert(row[27]=="4066" && row[23]=="NOT_CALLED" && row[34]=="LOOKUP_ERROR");
  if(test=="v103-bars-missing")assert(row[24]=="0" && row[34]=="HISTORY_UNAVAILABLE");return;
 }
 if(test=="v103-objects" || test=="v103-limit"){
  auto &row=objects[1];assert(row[13]==std::to_string(DiagnosticBarTime) && row[14]==RawValue(158.098) && row[15]=="NA" && row[16]=="NA" && row[19]=="6");
  assert(row[11].find("%2C")!=string::npos && row[20].find("%0A")!=string::npos);
  if(test=="v103-limit")assert(objects[2][21]=="OBJECT_LIMIT_REACHED_PARTIAL");
  else{assert(objects[2][15]==std::to_string(chartObjects[1].time2) && objects[2][16]==RawValue(157.924));assert(objects[3][13]=="NA" && objects[3][14]=="NA");}return;
 }
 if(test=="v103-lines"){
  ChartObject h;h.type=OBJ_HLINE;h.name="hline";h.time1=0;chartObjects.push_back(h);
  ChartObject v;v.type=OBJ_VLINE;v.name="vline";v.price1=0;chartObjects.push_back(v);
 }
 if(test=="v103-object-change")spawnObjectOnProbe=true;
 if(test=="v103-invalid-object"){
  assert(objects[1][13]=="NA" && objects[1][14]=="NA" && objects[1][23]=="-1" && objects[1][24]=="NONFINITE" && objects[1][21].find("INVALID_VALUE")!=string::npos);
  assert(objects[2][15]=="NA" && objects[2][16]=="NA" && objects[2][26]=="EMPTY_VALUE");return;
 }
 if(test=="v103-lines"){
  assert(objects[1][13]=="NA" && objects[1][14]==RawValue(158.098) && objects[1][23]=="NOT_READ");
  assert(objects[2][12]=="0" && objects[2][13]==std::to_string(chartObjects[1].time1) && objects[2][14]=="NA" && objects[2][24]=="NOT_READ");return;
 }
 if(test=="v103-object-change"){
  assert(objects[1][21]=="NO_OBJECTS" && objects[2][11]=="created%2Dby%2Dmock%2Dhidden%2Dinstance" && objects[3][21]=="SNAPSHOT_COMPLETE_SOURCE_UNVERIFIED");
  assert(objects[2][3].find(detail[2][4]+"|O|")==0 && candidates()==0);return;
 }
 if(test=="v103-property-error"){assert(objects[1][13]=="NA" && objects[1][20]=="NA" && objects[1][22].find("time1=4202")!=string::npos);return;}
 if(test=="v103-values"){
  assert(detail[2][22]=="EMPTY_VALUE" && detail[3][22]=="ABSENT_MINUS_ONE" && detail[4][22]=="INVALID_ZERO");
  assert(detail[5][21]==RawValue(158.098) && detail[5][23]=="4802" && detail[5][25]=="ICUSTOM_API_ERROR_INIT_UNVERIFIED");
  assert(detail[6][22]=="PRICE" && detail[6][25]=="PRICE_RETURNED_CHART_MATCH_UNVERIFIED");return;
 }
 if(test=="v103-mode15"){assert(indicatorCalls.size()==8);for(size_t i=10;i<detail.size();i++)assert(detail[i][20]=="false" && detail[i][22]=="UNSUPPORTED_MT4_MODE");return;}
 if(test=="v103-dll-reported" || test=="v103-export"){
  assert(detail.size()==18 && indicatorCalls.size()==16);
  for(size_t i=2;i<detail.size();i++){
   assert(detail[i][15]==detail[i][18] && detail[i][23]=="0" && detail[i][35]=="false" && detail[i][26]=="UNVERIFIED_REVIEW_EXPERTS_LOG");
   int mode=std::stoi(detail[i][19]);assert(detail[i][22]==(mode<6?"EMPTY_VALUE":"INVALID_ZERO"));
  }
  if(test=="v103-export")exportMockFiles(folder);return;
 }
 if(test=="v103-diagnostic-write" || test=="v103-object-write" || test=="v103-diagnostic-flush"){
  auto before=disk[ledgerName];failWrite=test=="v103-diagnostic-flush"?2:1;failName=test=="v103-object-write"?objectsName:diagnosticsName;
  step();assert(halted && candidates()==0 && disk[ledgerName]==before);return;
 }
 if(test=="v103-corrupt-diagnostic"){
  OnDeinit(0);disk[diagnosticsName].back().pop_back();auto before=disk[diagnosticsName];auto primary=disk[ledgerName];
  assert(OnInit()==INIT_FAILED && disk[diagnosticsName]==before && disk[ledgerName]==primary);return;
 }
 if(test=="v103-restart"){
  auto before=disk[diagnosticsName];auto objectBefore=disk[objectsName];auto primary=disk[ledgerName];string session=diagnosticsSession;
  restart();assert(diagnosticsSession!=session && disk[ledgerName]==primary && candidates()==0);
  for(size_t i=0;i<before.size();i++)assert(disk[diagnosticsName][i]==before[i]);
  for(size_t i=0;i<objectBefore.size();i++)assert(disk[objectsName][i]==objectBefore[i]);
  for(size_t i=1;i<disk[diagnosticsName].size();i++)assert(disk[diagnosticsName][i][1]==std::to_string(i));return;
 }
 if(test=="v103-zero"){
  assert(objects.size()==3 && objects[1][21]=="NO_OBJECTS" && objects[2][21]=="NO_OBJECTS");
  bool found=false;for(string log:logs)if(log.find("BSM_OBJECTS_ZERO")!=string::npos)found=true;assert(found);return;
 }
 if(test=="v103-dll-query-error"){assert(detail[1][36]=="4000" && indicatorCalls.empty() && detail[2][22]=="DLL_CONTEXT_BLOCKED");}
 if(test=="v103-dll-true"){assert(indicatorCalls.empty() && dllFlag && detail[2][20]=="false" && detail[2][25]=="DLL_CONTEXT_NOT_FALSE_NOT_CALLED");}
}
int main(int argc,char** argv){
 assert(argc>=2);string test=argv[1];assert(!BuffersConfirmed && RedDotMode==-1 && BlueDotMode==-1);if(test.find("v103-")==0){v103Case(test,argc>2?argv[2]:"");return 0;}BuffersConfirmed=true;RedDotMode=0;BlueDotMode=1;
 if(test=="input-custom"){SignalPeriod=20;ArrowPeriod=4;SL_pips=75;AlertON=false;Email=false;}
 if(test=="invalid-signal-period"){SignalPeriod=0;assert(OnInit()==INIT_PARAMETERS_INCORRECT && disk.empty());return 0;}
 if(test=="invalid-arrow-period"){ArrowPeriod=0;assert(OnInit()==INIT_PARAMETERS_INCORRECT && disk.empty());return 0;}
 if(test=="invalid-sl-pips"){SL_pips=-1;assert(OnInit()==INIT_PARAMETERS_INCORRECT && disk.empty());return 0;}
 if(test=="diagnostic-target" || test=="diagnostic-unavailable" || test=="diagnostic-read-error" || test=="diagnostic-series-change"){
  DiagnosticBarTime=1794217380;currentBar=DiagnosticBarTime+600;now=currentBar;tick={now,100};
  advanceDuringIndicator=test=="diagnostic-series-change";missingDiagnostic=test=="diagnostic-unavailable";buffers[{3,10}]={test=="diagnostic-read-error"?EMPTY_VALUE:158.098,test=="diagnostic-read-error"?4802:0};
 }
 if(test=="diagnostic-forming")DiagnosticBarTime=currentBar;
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
 if(test=="diagnostic-forming"){assert(candidates()==0 && indicatorCalls.empty() && disk[rawName][1][6]=="NOT_READ" && disk[rawName][1][7]=="DIAGNOSTIC_BAR_UNAVAILABLE");return 0;}
 if(test=="diagnostic-target" || test=="diagnostic-unavailable" || test=="diagnostic-read-error" || test=="diagnostic-series-change"){
  assert(candidates()==0 && disk[rawName].size()==9);
  for(int mode=0;mode<8;mode++){
   auto &row=disk[rawName][mode+1];assert(row[4]==std::to_string(DiagnosticBarTime));
   if(test=="diagnostic-unavailable"){assert(row[6]=="NOT_READ" && row[7]=="DIAGNOSTIC_BAR_UNAVAILABLE" && row[8]=="4066");}
  }
  if(test=="diagnostic-target")assert(disk[rawName][4][7]=="PRICE");
  if(test=="diagnostic-read-error")assert(disk[rawName][4][6]=="EMPTY_VALUE" && disk[rawName][4][7]=="READ_ERROR" && disk[rawName][4][8]=="4802");
  if(test=="diagnostic-series-change")assert(disk[rawName][1][7]=="SERIES_CHANGED_DURING_READ" && disk[rawName][2][6]=="NOT_READ");
  assert(indicatorCalls.size()==(test=="diagnostic-unavailable"?0:test=="diagnostic-series-change"?1:8));return 0;
 }
 if(test=="input-defaults" || test=="input-custom"){
  step();assert(indicatorCalls.size()==8);
  for(auto call:indicatorCalls){assert(std::get<0>(call)==SignalPeriod && std::get<1>(call)==ArrowPeriod && std::get<2>(call)==SL_pips && std::get<3>(call)==AlertON && std::get<4>(call)==Email && std::get<6>(call)==1);}
  string expected="SignalPeriod="+std::to_string(SignalPeriod)+";ArrowPeriod="+std::to_string(ArrowPeriod)+";SL_pips="+std::to_string(SL_pips)+";AlertON="+Flag(AlertON)+";Email="+Flag(Email);
  assert(config.find(expected)!=string::npos && disk[ledgerName].back()[38]==config);
  for(size_t i=1;i<disk[rawName].size();i++)assert(disk[rawName][i][9]==config && disk[rawName][i][10]=="ICUSTOM_EXPLICIT5_CHART_MATCH_UNVERIFIED");return 0;
 }
 if(test=="legacy-input-transition"){
  for(int i=0;i<5;i++)step();breakout();OnDeinit(0);
  for(auto &row:disk[ledgerName])if(row[0]=="1.00"){row[38]="indicator=buy-sell-magic1;inputs=DEFAULTS_UNCONFIRMED;confirmed=true;red=0;blue=1;min=5;ratio=10";row[39]="ICUSTOM_DEFAULTS_CLOSED_M1_NO_ORDERS";}
  auto before=disk[ledgerName];assert(OnInit()==0 && pending.size()==1 && !pending[0].isSettled);
  assert(disk[ledgerName].size()==before.size()+1 && disk[ledgerName].back()[2]=="CONFIG");
  for(size_t i=0;i<before.size();i++)assert(disk[ledgerName][i]==before[i]);assert(red.count==0);return 0;
 }
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
cases=['high','low','four','point-change','missing','normalize','wick','doji','read-error','invalid-values','duplicate','restart-group','restart-pending','restart-gap','gap','disconnect','timer-only','unconfirmed','config-change','modes-15','late-entry','unknown-expiry','loss','draw','corrupt','header-mismatch','writer-lock','ledger-write-failure','raw-write-failure','flush-failure','open-above','changed-break-dot','corrupt-consumed','low-theory','config-pending','invalid-mode','invalid-min','digits-five','low-wick','group-six','diagnostic-time','stale-timer','input-defaults','input-custom','invalid-signal-period','invalid-arrow-period','invalid-sl-pips','diagnostic-target','diagnostic-unavailable','diagnostic-read-error','legacy-input-transition','diagnostic-series-change','diagnostic-forming','v103-zero','v103-objects','v103-invalid-object','v103-property-error','v103-enumeration-error','v103-limit','v103-disabled','v103-mismatch','v103-history-missing','v103-bars-missing','v103-values','v103-mode15','v103-dll-reported','v103-dll-query-error','v103-dll-true','v103-diagnostic-write','v103-object-write','v103-diagnostic-flush','v103-corrupt-diagnostic','v103-restart','v103-lines','v103-object-change']
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
    diagFolder=p/'diagnostic_export';diagFolder.mkdir()
    subprocess.run([str(p/'tests'),'v103-export',str(diagFolder)],check=True)
    with (diagFolder/'BSMDiagnostics_USDJPY_M1_v1.csv').open() as f: diagnostics=list(csv.DictReader(f))
    assert len(diagnostics)==17 and all(len(r)==41 and r['end']=='COMMIT' for r in diagnostics)
    buffers=[r for r in diagnostics if r['event']=='BUFFER']
    assert len(buffers)==16 and {r['requested_bar_time'] for r in buffers}=={'1794217380','1794233460'}
    assert all(r['requested_bar_time']==r['actual_bar_time'] and r['GetLastError']=='0' and r['ea_dll_allowed']=='false' and r['indicator_init_status']=='UNVERIFIED_REVIEW_EXPERTS_LOG' for r in buffers)
    assert all([r[k] for k in ('SignalPeriod','ArrowPeriod','SL_pips','AlertON','Email')]==['12','2','100','true','true'] for r in buffers)
    with (diagFolder/'BSMObjects_USDJPY_M1_v1.csv').open() as f: objects=list(csv.DictReader(f))
    assert len(objects)==16 and all(len(r)==30 and r['end']=='COMMIT' for r in objects)
    assert unquote(objects[0]['object_name'])=='=red,dot%"\n'
    assert unquote(objects[0]['object_description'])=='note,"quoted"\n%2C'
    assert all(r['source']=='CURRENT_CHART_OBJECTS_NO_SIGNAL_INFERENCE' for r in objects)
    subprocess.run([str(p/'tests'),'v103-restore',str(diagFolder)],check=True)
for term in ('OrderSend','OrderClose','WebRequest','#import','ShellExecute','http://','https://','ObjectCreate(', 'ObjectDelete(', 'ObjectSet', 'ChartSet', 'ShellExecute', 'WinExec'):
    assert term not in ea+core
print(f'{len(cases)} actual-code host scenarios plus CSV integration passed; MetaEditor/MT4 not tested.')
