#include <string>
#include <vector>
#include <map>
#include <tuple>
#include <sstream>
#include <iomanip>
#include <iostream>
#include <fstream>
#include <cassert>
#include <cmath>
#include <cstdlib>
#include <algorithm>
#undef SEEK_END
using string=std::string;using datetime=long long;using uint=unsigned int;
const int INVALID_HANDLE=-1,PERIOD_M1=1,FILE_READ=1,FILE_WRITE=2,FILE_CSV=4,FILE_ANSI=8,FILE_SHARE_READ=16,CP_UTF8=65001,SEEK_END=2;
const int INIT_SUCCEEDED=0,INIT_FAILED=-1,INIT_PARAMETERS_INCORRECT=2;
const double EMPTY_VALUE=2147483647.;int Digits=3,lastError=0;
int availableBars=5000,barsApiError=0,lookupShiftBias=0,timeErrorShift=-1;
datetime now=6000,currentBar=6000;bool missingDiagnostic=false,advanceDuringIndicator=false,spawnObjectOnProbe=false;bool connected=true;int failWrite=0;string failName="";
std::vector<string> logs;
struct MqlTick{datetime time;double bid;};MqlTick tick={6000,100};
struct Candle{double o=99,h=101,l=98,c=100;};Candle candle;
std::map<std::tuple<int,int>,std::pair<double,int>> buffers;
struct Handle{string name;size_t row=0,col=0;bool eol=false,open=true;};
std::map<string,std::vector<std::vector<string>>> disk;std::map<int,Handle> handles;int nextHandle=0;
string Symbol(){return "USDJPY";}int Period(){return PERIOD_M1;}
datetime TimeCurrent(){return now;}
int StringLen(string s){return s.size();}int StringFind(string s,string sub){size_t p=s.find(sub);return p==string::npos?-1:p;}
int StringGetCharacter(string s,int at){return (unsigned char)s[at];}
string IntegerToString(long n){return std::to_string(n);}long StringToInteger(string s){return std::strtol(s.c_str(),nullptr,10);}
double StringToDouble(string s){return std::strtod(s.c_str(),nullptr);}bool MathIsValidNumber(double x){return std::isfinite(x);}
string DoubleToString(double x,int n){std::ostringstream s;s<<std::fixed<<std::setprecision(n)<<x;return s.str();}
double NormalizeDouble(double x,int n){double m=std::pow(10.,n);return std::round(x*m)/m;}
int StringSplit(string s,char delimiter,std::vector<string>& out){out.clear();std::istringstream in(s);string part;while(std::getline(in,part,delimiter))out.push_back(part);return out.size();}
template<typename T>int ArraySize(const std::vector<T>& a){return a.size();}
template<typename T>int ArrayResize(std::vector<T>& a,int n){a.resize(n);return n;}
void ResetLastError(){lastError=0;}int GetLastError(){int e=lastError;lastError=0;return e;}
template<typename T>string cell(T v){std::ostringstream s;s<<v;return s.str();}string cell(string s){return s;}
void printParts(std::ostringstream&){}template<typename T,typename... A>void printParts(std::ostringstream& s,T v,A... a){s<<v;printParts(s,a...);}
template<typename... A>void Print(A... a){std::ostringstream s;printParts(s,a...);logs.push_back(s.str());}
bool IsConnected(){return connected;}bool SymbolInfoTick(string,MqlTick& result){result=tick;return true;}
int iBars(string,int){lastError=barsApiError;return availableBars;}
datetime iTime(string,int,int shift){if(shift==timeErrorShift){lastError=4073;return 0;}return currentBar-shift*60;}
int iBarShift(string,int,datetime time,bool){if(missingDiagnostic){lastError=4066;return -1;}if(time>currentBar)return -1;return (currentBar-time)/60+lookupShiftBias;}
double iOpen(string,int,int){return candle.o;}double iHigh(string,int,int){return candle.h;}double iLow(string,int,int){return candle.l;}double iClose(string,int,int){return candle.c;}
std::vector<std::tuple<int,int,int,bool,bool,int,int>> indicatorCalls;
void MaybeAddProbeObject();

double iCustom(string,int,string,int signalPeriod,int arrowPeriod,int stopPips,bool alertOn,bool email,int mode,int shift){
 if(spawnObjectOnProbe)MaybeAddProbeObject();
 if(advanceDuringIndicator){currentBar+=60;advanceDuringIndicator=false;}
 indicatorCalls.push_back({signalPeriod,arrowPeriod,stopPips,alertOn,email,mode,shift});assert(mode>=0 && mode<=7 && shift>=1);auto it=buffers.find({mode,shift});if(it==buffers.end())return -1;lastError=it->second.second;return it->second.first;}
bool EventSetTimer(int){return true;}void EventKillTimer(){}
int FileOpen(string name,int,char,int){for(auto& h:handles)if(h.second.open && h.second.name==name){lastError=5004;return -1;}if(!disk.count(name))disk[name]={};int id=++nextHandle;handles[id].name=name;return id;}
void FileClose(int id){handles[id].open=false;}
long FileSize(int id){return disk[handles[id].name].size();}
bool FileIsEnding(int id){return handles[id].row>=disk[handles[id].name].size();}
bool FileIsLineEnding(int id){return handles[id].eol;}
string FileReadString(int id){auto& h=handles[id];auto& row=disk[h.name][h.row];string result=row[h.col++];h.eol=h.col>=row.size();if(h.eol){h.row++;h.col=0;}return result;}
bool FileSeek(int id,long,int){auto& h=handles[id];h.row=disk[h.name].size();h.col=0;h.eol=false;return true;}
void FileFlush(int id){if(failWrite==2 && handles[id].name==failName)lastError=5004;}
template<typename... A>uint FileWrite(int id,A... args){auto& h=handles[id];if(failWrite==1 && h.name==failName){lastError=5004;return 0;}std::vector<string> row={cell(args)...};disk[h.name].push_back(row);h.row=disk[h.name].size();return row.size();}
// Read-only chart/series/DLL-context APIs used by v1.03 diagnostics.
const int OBJ_VLINE=0,OBJ_HLINE=1,OBJ_TREND=2,OBJ_TEXT=21,OBJ_ARROW=22,OBJ_LABEL=23,OBJ_BUTTON=24,OBJ_BITMAP_LABEL=25,OBJ_EDIT=26,OBJ_RECTANGLE_LABEL=27;
const int OBJPROP_TYPE=1,OBJPROP_TIME=2,OBJPROP_PRICE=3,OBJPROP_COLOR=4,OBJPROP_STYLE=5,OBJPROP_WIDTH=6,OBJPROP_TEXT=7;
struct ChartObject {
 string name,text;long type=OBJ_ARROW,color=255,style=0,width=2;datetime time1=5900,time2=5960;double price1=158.098,price2=157.924;
 std::map<std::pair<int,int>,int> errors;
};
std::vector<ChartObject> chartObjects;bool dllFlag=false;int dllQueryError=0,objectsTotalError=0;
long ChartID(){return 123456;}uint GetTickCount(){return (uint)(now*1000);}
bool IsDllsAllowed(){lastError=dllQueryError;return dllFlag;}
int StringReplace(string &value,string from,string to){int count=0;size_t pos=0;while((pos=value.find(from,pos))!=string::npos){value.replace(pos,from.size(),to);pos+=to.size();count++;}return count;}
int ObjectsTotal(long chart,int subwindow,int type){assert(chart==ChartID() && subwindow==-1 && type==-1);lastError=objectsTotalError;return objectsTotalError?-1:chartObjects.size();}
string ObjectName(long chart,int index,int subwindow,int type){assert(chart==ChartID() && subwindow==-1 && type==-1);if(index<0 || index>=(int)chartObjects.size()){lastError=4202;return "";}return chartObjects[index].name;}
ChartObject* findChartObject(string name){for(auto &object:chartObjects)if(object.name==name)return &object;lastError=4202;return nullptr;}
long ObjectGetInteger(long chart,string name,int prop,int modifier){
 assert(chart==ChartID());auto *o=findChartObject(name);if(!o)return 0;
 auto error=o->errors.find({prop,modifier});if(error!=o->errors.end()){lastError=error->second;return 0;}
 if(prop==OBJPROP_TYPE)return o->type;if(prop==OBJPROP_TIME)return modifier==0?o->time1:o->time2;
 if(prop==OBJPROP_COLOR)return o->color;if(prop==OBJPROP_STYLE)return o->style;if(prop==OBJPROP_WIDTH)return o->width;
 lastError=4203;return 0;
}
double ObjectGetDouble(long chart,string name,int prop,int modifier){
 assert(chart==ChartID());auto *o=findChartObject(name);if(!o)return 0;
 auto error=o->errors.find({prop,modifier});if(error!=o->errors.end()){lastError=error->second;return 0;}
 if(prop==OBJPROP_PRICE)return modifier==0?o->price1:o->price2;lastError=4203;return 0;
}
string ObjectGetString(long chart,string name,int prop,int modifier){
 assert(chart==ChartID());auto *o=findChartObject(name);if(!o)return "";
 auto error=o->errors.find({prop,modifier});if(error!=o->errors.end()){lastError=error->second;return "";}
 if(prop==OBJPROP_TEXT)return o->text;lastError=4203;return "";
}

void MaybeAddProbeObject(){spawnObjectOnProbe=false;ChartObject object;object.name="created-by-mock-hidden-instance";chartObjects.push_back(object);}
