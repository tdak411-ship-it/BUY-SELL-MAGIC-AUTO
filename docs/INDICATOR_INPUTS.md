# v1.02：明示入力と09:43のバッファ照合

## 呼出し仕様

利用者がチャート上で確認した5項目を、EAのinputへ追加しました。渡す順序とEAでの型は次のとおりです。

| 順序 | 名前 | 型 | 初期値 |
| --- | --- | --- | --- |
| 1 | SignalPeriod | int | 12 |
| 2 | ArrowPeriod | int | 2 |
| 3 | SL_pips | int | 100 |
| 4 | AlertON | bool | true |
| 5 | Email | bool | true |

```cpp
iCustom(Symbol(), PERIOD_M1, IndicatorName,
        SignalPeriod, ArrowPeriod, SL_pips, AlertON, Email,
        mode, shift);
```

この後にmodeとshiftを渡し、他の入力や空文字のパラメーターは挿入しません。通常の新足診断も指定日時診断も、同じProbe関数を使います。mode 0～7は全取得し、8以上のMQL4非対応扱いは維持します。

順序は利用者提示の順序、型は3整数・2boolとして実装しています。EX4ソースや宣言一覧がないため、追加のextern項目がないこと、元のSL_pipsがint型であること等を独立には確認できません。ここで「正しい宣言順・型を実機確認済み」とは報告しません。実際に型や項目順が異なる場合は、.setやパラメーター画面・提供元仕様で照合してから修正します。AlertON/Emailは指定どおり渡しますが、EX4内部の通知挙動は未検証です。EAに注文・メール送信・外部API処理を追加していません。

## CSVと互換性

既存の50列台帳・12列生値は維持します。両方のconfiguration列に次のタグを追加します。

```text
inputs=EXPLICIT_FIVE_USER_SUPPLIED_ORDER;SignalPeriod=12;ArrowPeriod=2;SL_pips=100;AlertON=true;Email=true;input_types=int:int:int:bool:bool
```

新規sourceは台帳がICUSTOM_EXPLICIT5_CLOSED_M1_NO_ORDERS、生値がICUSTOM_EXPLICIT5_CHART_MATCH_UNVERIFIEDです。旧DEFAULTS出典も読込可能で、過去行を変更しません。入力方式/設定が変わるため、復元した群はCONFIGイベントでリセットし、これからの確定足を新設定で蓄積します。既存の理論結果待ちは維持します。

候補を抽出するexport_signals.pyは、元のBAR行のconfiguration/sourceを保持します。後続THEORYの行はその記録時点のEA設定を持つので、過去サインに使った設定を調べる場合は元のBAR/抽出結果を参照してください。

## MT4で指定日時を再診断

1. 稼働中の本EAを停止し、BSMの既存CSVと旧EX4をバックアップします。M3のEAには触れません。
2. 最新BuySellMagicRecorder.mq4をMQL4/Expertsへ配置し、MetaEditorで本体をコンパイルします。Coreは変更なしです。実際のerrors/warningsを確認します。
3. USDJPY・M1チャートで5入力を確認し、DiagnosticBarTimeを **2026.11.09 09:43:00** に設定して起動します。バッファ対応が未確認ならBuffersConfirmed=falseを維持します。
4. Expertsの `BSM_DIAGNOSTIC` に、requested/actual（サーバーdatetimeの数値）、shift、lookup_error、time_error、price_error、5入力を含むconfigurationが出ます。指定足の時刻が厳密に一致し、shift>=1のときだけ読みます。
5. `BSMRaw_USDJPY_M1_v1.csv` のsample_bar_time=1794217380のmode 0～7を確認します。別の時刻へ補正したり、過去の候補を生成したりしません。同じ設定でEAを再初期化すれば診断を再実行でき、生値は追記されます。

ヒストリーがなければ、各modeにvalue=NOT_READ、value_status=DIAGNOSTIC_BAR_UNAVAILABLEとAPIエラーを保存します。iCustomを実行して失敗した場合は、実際の生値、READ_ERROR等の分類、直後のGetLastErrorを保存します。EMPTY_VALUEと-1は区別します。取得中に参照時刻が変わればSERIES_CHANGED_DURING_READとして、値を正常なPRICE扱いしません。

## DownTrend Stop=158.098との比較

EA停止後の生値CSVのコピーを使います。Python3だけで実行できます。

```sh
python3 analysis/check_probe.py \
  --raw /path/to/BSMRaw_USDJPY_M1_v1.csv \
  --symbol USDJPY \
  --bar '2026.11.09 09:43:00' \
  --expected 158.098 \
  --digits 3
```

日時・期待値・桁数の初期値は上の例なので、--rawだけでも実行できます。サフィックス付きなら--symbolへ実銘柄名を指定します。時刻はCSVのMT4サーバー壁時計表現で照合し、ブローカーのUTCオフセットやJSTへの変換を推測しません。

JSONには元のvalue、value_status、read_error、全configuration、5項目のindicator_inputs、表示精度で一致したmodeを出します。取得エラー・無効値は一致候補に含めません。対象日時の記録がなければREQUESTED_SAMPLE_NOT_FOUNDとし、近隣の時刻では代替しません。原本は変更しません。

一致は **小数3桁のデータウィンドウ表示に合う**という意味で、完全精度の一致や赤ドットのバッファ役割を証明しません。Stop/Signal/Lineが同値なら複数modeが一致し得ます。出力のbuffer_identity_verified/chart_settings_verifiedはfalseを維持します。過去のデフォルト入力による観測も含まれ得るため、各観測のinput_method/sourceを確認してください。

## 検証の範囲

ホストでは5引数の順序・値・bool型、設定変更、53シナリオ、CSV列数と既存台帳の復元、照合ツール8テストを確認しました。158.098を返す模擬バッファによる試験であり、実際のインジケーターがその値を返したと主張しません。MetaEditor・MT4実機・実EX4の型/順序・指定日時の価格一致は未検証です。
