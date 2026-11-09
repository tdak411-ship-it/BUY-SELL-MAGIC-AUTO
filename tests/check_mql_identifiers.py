"""Project guard for MQL object-modifier words accidentally used as identifiers.

This supplements the C++ mock build; it is NOT a complete MQL parser/compiler.
"""
from pathlib import Path
import re

# These MQL modifiers must not be used as our variable/member names. C++ can
# accept some of them as contextual identifiers, so g++ alone is insufficient.
FORBIDDEN={'final','override','abstract'}
LEXEME=re.compile(r'//[^\n]*|/\*[\s\S]*?\*/|"(?:\\.|[^"\\])*"|\'(?:\\.|[^\'\\])*\'')

def check_mql_identifiers(source,label='source'):
    code=LEXEME.sub(' ',source)
    found=FORBIDDEN.intersection(re.findall(r'\b[A-Za-z_][A-Za-z_0-9]*\b',code))
    if found:raise ValueError(f'{label}: reserved MQL identifiers: {", ".join(sorted(found))}')

def regression_checks():
    for source in ('bool final;', 'pending[0].final=true;', 'void F(int final){}', 'bool override;', 'int abstract;'):
        try:check_mql_identifiers(source)
        except ValueError:pass
        else:raise AssertionError('Reserved identifier was missed')
    check_mql_identifiers('bool isSettled; string s="final"; // final\n/* override */')

if __name__=='__main__':
    regression_checks()
    root=Path(__file__).resolve().parents[1]
    for path in (root/'Experts/BuySellMagicRecorder.mq4',root/'Include/BuySellMagicCore.mqh'):
        check_mql_identifiers(path.read_text(),str(path))
    print('MQL reserved-identifier regression checks passed; NOT MetaEditor compilation.')
