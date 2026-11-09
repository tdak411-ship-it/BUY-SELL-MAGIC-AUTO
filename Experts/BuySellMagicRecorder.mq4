#property strict
#property version "1.01"
#property description "Independent Buy Sell Magic buffer probe and closed-M1 breakout evidence recorder. No orders."
#include <BuySellMagicCore.mqh>
input string IndicatorName="buy-sell-magic1";
input bool BuffersConfirmed=false;
input int RedDotMode=-1;
input int BlueDotMode=-1;
input int ProbeMaxMode=7; // MQL4 documented mode range is 0..7; higher modes logged unsupported
input int MinimumHorizontalDots=5;
input double DotPriceRatioLimit=10.0;
input datetime DiagnosticBarTime=0; // optional exact closed M1 bar, raw probe only
const int COLS=50;
string VERSION="1.00";
int ledger=INVALID_HANDLE,rawFile=INVALID_HANDLE,sequence=0;
string ledgerName,rawName,config,restoredConfig;
datetime cursor=0,seenOpen=0;
DotGroup red,blue;
bool halted=false,busy=false,disconnectLogged=false,historyLogged=false;
datetime quoteTimes[600];double quoteBids[600];
struct PendingTheory { string key,direction,entryBid;datetime bar,entry,expiry;bool isSettled; };
PendingTheory pending[];
string Header(){return "recorder_version|sequence|event|key|server_time|symbol|timeframe|signal_bar_time|detection_time|direction|red_dot_price|blue_dot_price|dot_buffer_mode|dot_count|horizontal_price|breakout_open|breakout_high|breakout_low|breakout_close|breakout_valid|rejection_reason|theoretical_entry_time|theoretical_entry_bid|theoretical_expiry_time|theoretical_expiry_bid|theoretical_result|indicator_read_status|red_group_price|red_group_count|red_group_first|red_group_last|red_group_consumed|blue_group_price|blue_group_count|blue_group_first|blue_group_last|blue_group_consumed|cursor|configuration|source|entry_quote_time|expiry_quote_time|observed_time|result_status|red_read_status|blue_read_status|red_raw|blue_raw|digits|end";}
string RawHeader(){return "recorder_version|server_time|symbol|timeframe|sample_bar_time|mode|value|value_status|read_error|configuration|source|end";}
string Num(long v){return IntegerToString(v);}
string Flag(bool b){return b?"true":"false";}
void Stop(string reason){halted=true;Print("BSM_RECORDER_STOPPED ",reason,"; ledger=",ledgerName);}
bool SafeName(string s){return s!="" && StringFind(s,"|")<0 && StringFind(s,",")<0 && StringFind(s,"\n")<0 && StringFind(s,"\r")<0 && StringFind(s,"\"")<0 && StringFind(s,"/")<0 && StringFind(s,"\\")<0 && StringFind(s,":")<0;}
string Configuration(){return "indicator="+IndicatorName+";inputs=DEFAULTS_UNCONFIRMED;confirmed="+Flag(BuffersConfirmed)+";red="+Num(RedDotMode)+";blue="+Num(BlueDotMode)+";min="+Num(MinimumHorizontalDots)+";tolerance_points=0;ratio="+DoubleToString(DotPriceRatioLimit,16)+";probe_max="+Num(ProbeMaxMode);}
bool Flush(int h){ResetLastError();FileFlush(h);return GetLastError()==0;}
bool ReadCells(int h,string &f[],int n){
 ArrayResize(f,n);for(int i=0;i<n;i++){if(FileIsEnding(h))return false;f[i]=FileReadString(h);if(i<n-1 && FileIsLineEnding(h))return false;}
 return FileIsLineEnding(h);
}
bool WriteLedger(string &f[]){
 ResetLastError();uint bytes=FileWrite(ledger,f[0],f[1],f[2],f[3],f[4],f[5],f[6],f[7],f[8],f[9],f[10],f[11],f[12],f[13],f[14],f[15],f[16],f[17],f[18],f[19],f[20],f[21],f[22],f[23],f[24],f[25],f[26],f[27],f[28],f[29],f[30],f[31],f[32],f[33],f[34],f[35],f[36],f[37],f[38],f[39],f[40],f[41],f[42],f[43],f[44],f[45],f[46],f[47],f[48],f[49]);int error=GetLastError();
 if(bytes==0 || error!=0 || !Flush(ledger)){Stop("LEDGER_WRITE_OR_FLUSH_FAILED_PRESERVE_FILE");return false;}return true;
}
void GroupCells(DotGroup &g,string &f[],int at){f[at]=g.price;f[at+1]=Num(g.count);f[at+2]=Num((long)g.first);f[at+3]=Num((long)g.last);f[at+4]=Flag(g.consumed);}
bool LoadGroup(string &f[],int at,datetime atBar,DotGroup &g){
 g.price=f[at];g.count=(int)StringToInteger(f[at+1]);g.first=(datetime)StringToInteger(f[at+2]);g.last=(datetime)StringToInteger(f[at+3]);g.consumed=f[at+4]=="true";
 if(Num(g.count)!=f[at+1] || Num((long)g.first)!=f[at+2] || Num((long)g.last)!=f[at+3] || (f[at+4]!="true" && f[at+4]!="false"))return false;
 if(g.count==0)return g.price=="" && g.first==0 && g.last==0 && !g.consumed;
 return g.count>0 && Positive(StringToDouble(g.price)) && DoubleToString(NormalizeDouble(StringToDouble(g.price),Digits),Digits)==g.price && g.first>0 && g.first%60==0 && g.last==atBar && g.last-g.first==(long)(g.count-1)*60;
}
int FindPending(string key){for(int i=0;i<ArraySize(pending);i++)if(pending[i].key==key)return i;return -1;}
bool AddPending(string &f[]){
 int n=ArraySize(pending);if(FindPending(f[3])>=0 || ArrayResize(pending,n+1)!=n+1)return false;
 pending[n].key=f[3];pending[n].direction=f[9];pending[n].bar=(datetime)StringToInteger(f[7]);pending[n].entry=(datetime)StringToInteger(f[21]);pending[n].expiry=(datetime)StringToInteger(f[23]);pending[n].entryBid=f[22];pending[n].isSettled=false;return true;
}
bool Restore(string &f[]){
 if(f[0]!=VERSION || f[1]!=Num(sequence+1) || f[5]!=Symbol() || f[6]!="M1" || f[49]!="COMMIT" || f[39]!="ICUSTOM_DEFAULTS_CLOSED_M1_NO_ORDERS" || f[48]!=Num(Digits))return false;
 datetime bar=(datetime)StringToInteger(f[7]);if(bar<=0 || bar%60!=0 || f[7]!=Num((long)bar) || (f[19]!="true" && f[19]!="false"))return false;
 if(f[2]=="BAR" || f[2]=="RESET" || f[2]=="CONFIG"){
  if((f[2]=="CONFIG" ? (bar!=cursor || f[38]==restoredConfig) : bar<=cursor) || f[37]!=f[7] || f[3]!=Symbol()+"|M1|"+f[7])return false;
  if(f[2]=="BAR" && bar!=cursor+60)return false;
  DotGroup r,b;if(!LoadGroup(f,27,bar,r) || !LoadGroup(f,32,bar,b))return false;
  if(f[2]!="BAR" && (r.count!=0 || b.count!=0 || f[19]!="false"))return false;
  if(f[19]=="true"){
   if(f[2]!="BAR" || (f[9]!="HIGH" && f[9]!="LOW") || f[21]!=Num((long)(bar+60)) || f[23]!=Num((long)(bar+240)) || f[25]!="UNKNOWN" || f[43]!="PENDING" || f[24]!="" || f[41]!="0" || f[42]!="0" || f[13]=="" || StringToInteger(f[13])<5)return false;
   if(f[22]!="" && !FixedPrice(f[22]))return false;
   if(f[40]!=(f[22]=="" ? "0" : f[21]))return false;
   DotGroup prior;if(f[9]=="HIGH")prior=red;else prior=blue;
   if(f[13]!=Num(prior.count) || f[14]!=prior.price || !UsableRead(f[44]) || !UsableRead(f[45]))return false;
   for(int j=15;j<=18;j++)if(!FixedPrice(f[j]))return false;
   if(BreakReason(prior,bar,StringToDouble(f[15]),StringToDouble(f[16]),StringToDouble(f[17]),StringToDouble(f[18]),f[9]=="HIGH",5)!="PASS")return false;
   if(!AddPending(f))return false;
  }else if(f[9]!="NONE" || f[43]!="NOT_A_CANDIDATE" || f[25]!="UNKNOWN" || f[22]!="" || f[24]!="")return false;
  if(f[2]=="BAR"){
   DotGroup expectedRed=red,expectedBlue=blue;
   if(f[19]=="true"){if(f[9]=="HIGH")expectedRed.consumed=true;else expectedBlue.consumed=true;}
   if(StringFind(f[38],";confirmed=true;")>=0 && UsableRead(f[44]) && UsableRead(f[45])){
    AdvanceGroup(expectedRed,f[10],f[44],bar);AdvanceGroup(expectedBlue,f[11],f[45],bar);
   }else{ClearGroup(expectedRed);ClearGroup(expectedBlue);}
   if(!SameGroup(expectedRed,r) || !SameGroup(expectedBlue,b))return false;
  }
  red=r;blue=b;cursor=bar;restoredConfig=f[38];
 }else if(f[2]=="THEORY"){
  int index=FindPending(f[3]);if(index<0 || pending[index].isSettled)return false;
  PendingTheory p=pending[index];
  if(f[9]!=p.direction || bar!=p.bar || f[21]!=Num((long)p.entry) || f[23]!=Num((long)p.expiry) || f[22]!=p.entryBid || f[19]!="true" || f[40]!=(p.entryBid=="" ? "0" : f[21]) || StringToInteger(f[42])<=p.expiry || f[37]!=Num((long)cursor))return false;
  string expected="UNKNOWN";
  if(f[24]!=""){if(!FixedPrice(f[24]) || f[41]!=f[23])return false;if(p.entryBid!="")expected=TextVerdict(p.direction,p.entryBid,f[24]);}
  else if(f[41]!="0")return false;
  if(f[25]!=expected || f[43]!=(expected=="UNKNOWN" ? "FINAL_UNMEASURED" : "FINAL_MEASURED"))return false;
  string r[];string b[];ArrayResize(r,COLS);ArrayResize(b,COLS);GroupCells(red,r,27);GroupCells(blue,b,32);
  for(int j=27;j<=31;j++)if(f[j]!=r[j])return false;for(int j=32;j<=36;j++)if(f[j]!=b[j])return false;
  pending[index].isSettled=true;
 }else return false;
 sequence++;return true;
}
bool OpenFiles(){
 ledgerName="BSMRecorder_"+Symbol()+"_M1_v1.csv";rawName="BSMRaw_"+Symbol()+"_M1_v1.csv";
 ledger=FileOpen(ledgerName,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',',CP_UTF8);
 if(ledger==INVALID_HANDLE){Stop("LEDGER_OPEN_OR_WRITER_LOCK");return false;}
 string h[];string f[];StringSplit(Header(),'|',h);
 if(FileSize(ledger)==0){if(!WriteLedger(h))return false;}
 else{
  if(!ReadCells(ledger,f,COLS))return false;for(int j=0;j<COLS;j++)if(f[j]!=h[j])return false;
  while(!FileIsEnding(ledger))if(!ReadCells(ledger,f,COLS) || !Restore(f)){Print("BSM_LEDGER_REJECT expected_data_row=",sequence+1);return false;}
 }
 if(!FileSeek(ledger,0,SEEK_END))return false;
 rawFile=FileOpen(rawName,FILE_READ|FILE_WRITE|FILE_CSV|FILE_ANSI|FILE_SHARE_READ,',',CP_UTF8);
 if(rawFile==INVALID_HANDLE)return false;
 StringSplit(RawHeader(),'|',h);
 if(FileSize(rawFile)==0){
  ResetLastError();uint count=FileWrite(rawFile,h[0],h[1],h[2],h[3],h[4],h[5],h[6],h[7],h[8],h[9],h[10],h[11]);int error=GetLastError();if(count==0 || error!=0 || !Flush(rawFile))return false;
 }else{
  if(!ReadCells(rawFile,f,12))return false;for(int j=0;j<12;j++)if(f[j]!=h[j])return false;
  while(!FileIsEnding(rawFile))if(!ReadCells(rawFile,f,12) || f[11]!="COMMIT")return false;
 }
 return FileSeek(rawFile,0,SEEK_END);
}
bool Probe(datetime bar,int shift,double reference,double &redValue,string &redStatus,double &blueValue,string &blueStatus){
 redValue=0;blueValue=0;redStatus="UNCONFIGURED";blueStatus="UNCONFIGURED";int firstError=0,firstMode=-1;
 for(int mode=0;mode<=ProbeMaxMode;mode++){
  double value=0;int error=0;string status="UNSUPPORTED_MT4_MODE";
  if(mode<=7){ResetLastError();value=iCustom(Symbol(),PERIOD_M1,IndicatorName,mode,shift);error=GetLastError();status=DotStatus(value,error,reference,DotPriceRatioLimit);if(status=="PRICE" && !Positive(NormalizeDouble(value,Digits)))status="INVALID_NORMALIZED_PRICE";}
  if(error!=0 && firstMode<0){firstMode=mode;firstError=error;}
  if(mode==RedDotMode){redValue=value;redStatus=status;}if(mode==BlueDotMode){blueValue=value;blueStatus=status;}
  ResetLastError();uint count=FileWrite(rawFile,VERSION,(long)TimeCurrent(),Symbol(),"M1",(long)bar,mode,mode<=7?RawValue(value):"NOT_READ",status,error,config,"ICUSTOM_DEFAULT_INPUTS_CHART_MATCH_UNVERIFIED","COMMIT");int writeError=GetLastError();
  if(count==0 || writeError!=0 || !Flush(rawFile)){Stop("RAW_WRITE_OR_FLUSH_FAILED");return false;}
 }
 if(firstMode>=0)Print("BSM_INDICATOR_READ_ERROR; bar=",(long)bar,"; mode=",firstMode,"; error=",firstError);
 return true;
}
void BaseRow(string &f[],string event,datetime bar){
 ArrayResize(f,COLS);for(int i=0;i<COLS;i++)f[i]="";
 f[0]=VERSION;f[1]=Num(sequence+1);f[2]=event;f[3]=Symbol()+"|M1|"+Num((long)bar);f[4]=Num((long)TimeCurrent());f[5]=Symbol();f[6]="M1";f[7]=Num((long)bar);f[8]=Num((long)TimeCurrent());f[9]="NONE";f[19]="false";f[21]="0";f[23]="0";f[25]="UNKNOWN";f[26]="NOT_READ";f[37]=Num((long)bar);f[38]=config;f[39]="ICUSTOM_DEFAULTS_CLOSED_M1_NO_ORDERS";f[40]="0";f[41]="0";f[42]="0";f[43]="NOT_A_CANDIDATE";f[48]=Num(Digits);f[49]="COMMIT";
 GroupCells(red,f,27);GroupCells(blue,f,32);
}
void CacheQuote(){
 MqlTick tick;if(!IsConnected() || !SymbolInfoTick(Symbol(),tick) || tick.time<=0 || tick.time!=TimeCurrent() || !Positive(tick.bid))return;
 int slot=(int)(tick.time%600);if(quoteTimes[slot]==tick.time)return;quoteTimes[slot]=tick.time;quoteBids[slot]=tick.bid;
}
string ExactBid(datetime time){int slot=(int)(time%600);return time>0 && quoteTimes[slot]==time ? DoubleToString(quoteBids[slot],16) : "";}
void Settle(){
 for(int i=0;i<ArraySize(pending);i++){
  PendingTheory p=pending[i];if(p.isSettled || TimeCurrent()<=p.expiry)continue;
  string f[];BaseRow(f,"THEORY",p.bar);f[3]=p.key;f[9]=p.direction;f[19]="true";f[21]=Num((long)p.entry);f[22]=p.entryBid;f[23]=Num((long)p.expiry);f[24]=ExactBid(p.expiry);f[40]=p.entryBid==""?"0":f[21];f[41]=f[24]==""?"0":f[23];f[42]=Num((long)TimeCurrent());f[37]=Num((long)cursor);
  if(f[22]!="" && f[24]!="")f[25]=TextVerdict(p.direction,f[22],f[24]);
  f[43]=f[25]=="UNKNOWN"?"FINAL_UNMEASURED":"FINAL_MEASURED";
  if(!WriteLedger(f))return;sequence++;pending[i].isSettled=true;
 }
}
void ResetAt(datetime bar,string reason,string event="RESET"){
 DotGroup oldRed=red,oldBlue=blue;ClearGroup(red);ClearGroup(blue);
 string f[];BaseRow(f,event,bar);f[20]=reason;
 if(WriteLedger(f)){sequence++;cursor=bar;restoredConfig=config;Print("BSM_GAP_OR_STARTUP ",reason,"; bar=",(long)bar);}else{red=oldRed;blue=oldBlue;}
}
void ProcessBar(datetime reference,datetime bar){
 if(bar<=cursor)return;
 if(bar!=cursor+60 || reference!=bar+60){ResetAt(bar,"GAP_NO_BACKFILL_GROUPS_RESET");return;}
 ResetLastError();double o=iOpen(Symbol(),PERIOD_M1,1),h=iHigh(Symbol(),PERIOD_M1,1),l=iLow(Symbol(),PERIOD_M1,1),c=iClose(Symbol(),PERIOD_M1,1);int error=GetLastError();
 if(error!=0 || !Positive(o) || !Positive(h) || !Positive(l) || !Positive(c) || h<o || h<c || l>o || l>c || h<l){ResetAt(bar,"OHLC_UNAVAILABLE_GROUPS_RESET");return;}
 double rv,bv;string rs,bs;if(!Probe(bar,1,c,rv,rs,bv,bs))return;
 DotGroup nextRed=red,nextBlue=blue;string highReason="BUFFERS_UNCONFIRMED",lowReason=highReason;
 bool reads=BuffersConfirmed && UsableRead(rs) && UsableRead(bs);
 if(BuffersConfirmed && !reads){highReason="INDICATOR_READ_INVALID";lowReason=highReason;}
 if(reads){highReason=BreakReason(red,bar,o,h,l,c,true,MinimumHorizontalDots);lowReason=BreakReason(blue,bar,o,h,l,c,false,MinimumHorizontalDots);}
 string f[];BaseRow(f,"BAR",bar);f[10]=rs=="PRICE"?DoubleToString(NormalizeDouble(rv,Digits),Digits):"";f[11]=bs=="PRICE"?DoubleToString(NormalizeDouble(bv,Digits),Digits):"";f[15]=RawValue(o);f[16]=RawValue(h);f[17]=RawValue(l);f[18]=RawValue(c);f[26]=rs+"/"+bs;f[44]=rs;f[45]=bs;f[46]=RawValue(rv);f[47]=RawValue(bv);f[20]="HIGH:"+highReason+";LOW:"+lowReason;
 if(highReason=="PASS" || lowReason=="PASS"){
  bool high=highReason=="PASS";DotGroup g;if(high){g=red;nextRed.consumed=true;}else{g=blue;nextBlue.consumed=true;}
  f[9]=high?"HIGH":"LOW";f[12]=Num(high?RedDotMode:BlueDotMode);f[13]=Num(g.count);f[14]=g.price;f[19]="true";f[21]=Num((long)reference);f[22]=ExactBid(reference);f[23]=Num((long)(reference+180));f[40]=f[22]==""?"0":f[21];f[43]="PENDING";
 }
 // Evaluate against the prior confirmed group BEFORE the breakout bar updates it.
 if(reads){AdvanceGroup(nextRed,f[10],rs,bar);AdvanceGroup(nextBlue,f[11],bs,bar);}else{ClearGroup(nextRed);ClearGroup(nextBlue);}
 GroupCells(nextRed,f,27);GroupCells(nextBlue,f,32);
 if(iTime(Symbol(),PERIOD_M1,0)!=reference || iTime(Symbol(),PERIOD_M1,1)!=bar){Stop("SERIES_CHANGED_DURING_READ");return;}
 if(!WriteLedger(f))return;sequence++;cursor=bar;red=nextRed;blue=nextBlue;
 if(f[19]=="true" && !AddPending(f))Stop("MEMORY_FAILED_RESTART_TO_RESTORE");
}
void Poll(bool newBars){
 if(halted || busy)return;busy=true;if(newBars)CacheQuote();
 if(!IsConnected()){if(!disconnectLogged)Print("BSM_DISCONNECTED_NEW_BARS_MAY_BE_MISSED");disconnectLogged=true;busy=false;return;}disconnectLogged=false;
 Settle();if(halted){busy=false;return;}
 datetime reference=iTime(Symbol(),PERIOD_M1,0),bar=iTime(Symbol(),PERIOD_M1,1);
 if(reference<=0 || bar<=0){if(!historyLogged)Print("BSM_M1_HISTORY_UNAVAILABLE");historyLogged=true;busy=false;return;}historyLogged=false;
 if(newBars && reference!=seenOpen){seenOpen=reference;ProcessBar(reference,bar);}busy=false;
}
void OnDeinit(const int reason){Print("BSM_DEINIT reason=",reason);if(ledger!=INVALID_HANDLE){FileClose(ledger);ledger=INVALID_HANDLE;}if(rawFile!=INVALID_HANDLE){FileClose(rawFile);rawFile=INVALID_HANDLE;}EventKillTimer();}
int OnInit(){
 halted=false;busy=false;sequence=0;cursor=0;seenOpen=0;ClearGroup(red);ClearGroup(blue);ArrayResize(pending,0);
 for(int i=0;i<600;i++){quoteTimes[i]=0;quoteBids[i]=0;}
 if(Period()!=PERIOD_M1 || !SafeName(Symbol()) || !SafeName(IndicatorName) || ProbeMaxMode<0 || ProbeMaxMode>15 || MinimumHorizontalDots<5 || MinimumHorizontalDots>10000 || !MathIsValidNumber(DotPriceRatioLimit) || DotPriceRatioLimit<1 || DotPriceRatioLimit>1000 ||
    RedDotMode < -1 || RedDotMode>7 || BlueDotMode < -1 || BlueDotMode>7 || (BuffersConfirmed && (RedDotMode<0 || BlueDotMode<0 || RedDotMode==BlueDotMode || RedDotMode>ProbeMaxMode || BlueDotMode>ProbeMaxMode)))return INIT_PARAMETERS_INCORRECT;
 config=Configuration();restoredConfig="";if(!OpenFiles()){Stop("INVALID_PARTIAL_OR_LOCKED_FILE_NO_REWRITE");OnDeinit(0);return INIT_FAILED;}
 datetime reference=iTime(Symbol(),PERIOD_M1,0),bar=iTime(Symbol(),PERIOD_M1,1);
 if(reference<=0 || bar<=0 || cursor>bar){Stop("HISTORY_NOT_READY_OR_BACKWARDS");OnDeinit(0);return INIT_FAILED;}
 if(cursor<bar)ResetAt(bar,cursor==0?"STARTUP_NO_HISTORICAL_CANDIDATES":"RESTART_GAP_NO_BACKFILL");
 if(restoredConfig!="" && restoredConfig!=config)ResetAt(bar,"CONFIG_CHANGED_GROUPS_RESET","CONFIG");
 seenOpen=reference;if(halted || !EventSetTimer(1)){OnDeinit(0);return INIT_FAILED;}
 if(DiagnosticBarTime>0){int shift=iBarShift(Symbol(),PERIOD_M1,DiagnosticBarTime,true);double r,b;string rs,bs;
  if(shift>=1 && iTime(Symbol(),PERIOD_M1,shift)==DiagnosticBarTime)Probe(DiagnosticBarTime,shift,iClose(Symbol(),PERIOD_M1,shift),r,rs,b,bs);else Print("BSM_DIAGNOSTIC_BAR_UNAVAILABLE");}
 Print("BSM build=1.01; recorder=",VERSION,"; confirmed=",BuffersConfirmed,"; no orders; review indicator runtime logs");return halted?INIT_FAILED:INIT_SUCCEEDED;
}
void OnTick(){Poll(true);}
void OnTimer(){Poll(false);}
