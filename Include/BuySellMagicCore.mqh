#ifndef BUY_SELL_MAGIC_CORE
#define BUY_SELL_MAGIC_CORE
struct DotGroup { string price;int count;datetime first,last;bool consumed; };
bool SameGroup(DotGroup &a,DotGroup &b){return a.price==b.price && a.count==b.count && a.first==b.first && a.last==b.last && a.consumed==b.consumed;}
void ClearGroup(DotGroup &g){g.price="";g.count=0;g.first=0;g.last=0;g.consumed=false;}
bool Positive(double x){return MathIsValidNumber(x) && x>0 && x!=EMPTY_VALUE;}
string RawValue(double x){if(!MathIsValidNumber(x))return "NONFINITE";if(x==EMPTY_VALUE)return "EMPTY_VALUE";return DoubleToString(x,16);}
string DotStatus(double x,int error,double reference,double ratio){
 if(error!=0)return "READ_ERROR";
 if(!MathIsValidNumber(x))return "NONFINITE";
 if(x==EMPTY_VALUE)return "EMPTY_VALUE";
 if(x==-1)return "ABSENT_MINUS_ONE";
 if(x==0)return "INVALID_ZERO";
 if(x<0)return "INVALID_NEGATIVE";
 if(!Positive(reference))return "NO_REFERENCE_PRICE";
 if(x<reference/ratio || x>reference*ratio)return "IMPLAUSIBLE_PRICE";
 return "PRICE";
}
bool AbsentDot(string status){return status=="EMPTY_VALUE" || status=="ABSENT_MINUS_ONE";}
bool UsableRead(string status){return status=="PRICE" || AbsentDot(status);}
void AdvanceGroup(DotGroup &g,string price,string status,datetime bar){
 if(status!="PRICE"){ClearGroup(g);return;}
 if(g.count>0 && g.price==price && g.last+60==bar){g.count++;g.last=bar;return;}
 g.price=price;g.count=1;g.first=bar;g.last=bar;g.consumed=false;
}
string BreakReason(DotGroup &g,datetime bar,double open,double high,double low,double close,bool isHigh,int minimum){
 if(g.count<minimum)return "INSUFFICIENT_DOTS";
 if(g.last+60!=bar)return "NONCONTIGUOUS_GROUP";
 if(g.consumed)return "GROUP_ALREADY_CONSUMED";
 double level=StringToDouble(g.price);
 if(isHigh){
  if(close<=open)return "NOT_BULLISH";
  if(open>level)return "OPEN_ABOVE_LEVEL";
  if(close<=level)return high>level ? "WICK_ONLY" : "NO_CLOSE_BREAK";
 }else{
  if(close>=open)return "NOT_BEARISH";
  if(open<level)return "OPEN_BELOW_LEVEL";
  if(close>=level)return low<level ? "WICK_ONLY" : "NO_CLOSE_BREAK";
 }
 return "PASS";
}
string TextVerdict(string direction,string entry,string exit){
 int a=StringFind(entry,"."),b=StringFind(exit,".");int c=0;
 if(a!=b)c=a>b ? 1 : -1;
 else for(int i=0;i<StringLen(entry);i++){int x=StringGetCharacter(entry,i),y=StringGetCharacter(exit,i);if(x!=y){c=x>y?1:-1;break;}}
 if(c==0)return "DRAW";
 return (direction=="HIGH" ? c<0 : c>0) ? "WIN" : "LOSS";
}
bool FixedPrice(string s){
 int dot=StringFind(s,".");if(dot<1 || StringLen(s)!=dot+17 || (dot>1 && StringGetCharacter(s,0)=='0'))return false;
 for(int i=0;i<StringLen(s);i++)if(i!=dot && (StringGetCharacter(s,i)<'0' || StringGetCharacter(s,i)>'9'))return false;
 return Positive(StringToDouble(s));
}
#endif
