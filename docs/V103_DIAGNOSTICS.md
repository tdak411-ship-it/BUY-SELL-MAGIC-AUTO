# v1.03：赤・青ドット未取得の切り分け

## 現時点の事実と原因候補

以下は利用者からの実機報告です。本環境で実EX4を実行した結果ではありません。

- USDJPY M1、2026.11.09 09:43：データウィンドウのDownTrend Stop/Signal/Lineは158.098。
- 同14:11：UpTrend Stop/Lineは157.924、UpTrend Signalは-1。
- 同じ指定時刻のEA側mode 0～5はEMPTY_VALUE、6～7は0、iCustomのGetLastErrorは0。
- Expertsに `Set Allow DLL Imports checkbox while launching the indicator.` が表示された。

上記は「チャート表示の値とEA側のiCustom結果が一致しない」ことを示します。0をドット価格として採用したり、EMPTY_VALUEを価格へ補完したりしません。

最も優先して確認する仮説は、**iCustom用の別インスタンスで、DLL関連の確認・ライセンス・初期化/計算のガードにより、バッファへ値が入っていない**可能性です。iCustom呼出しはインジケーターを初期化・計算する契機となるため、EA起動時にインジケーター由来のログが出ることと整合します。ただし、提供されたメッセージだけで、実際のOnInit戻り値、DLLの必要性、失敗箇所や内部ロジックは断定できません。

他にも、指定足の検索不一致、M1履歴不足、インジケーター独自の計算範囲、入力宣言の型/順序、チャートとのEX4/設定/キャッシュ状態の違い等が候補です。GetLastError=0は、その呼出しでAPIエラーが取得されなかったという意味で、初期化成功やドットの取得成功を保証しません。mode 6/7の0は未使用バッファ等の可能性もあり、内部用途を断定しません。

## A：現在チャートのオブジェクト

`BSMObjects_<銘柄>_M1_v1.csv` を追加します。ChartID()のチャートのみ、全サブウィンドウ・全タイプのオブジェクトを列挙します。MQLのObjectGet系APIだけを使い、オブジェクトを作成・変更・削除しません。

起動時にBEFORE_FIRST_ICUSTOMを保存し、最初の実際のiCustomバッチの後にAFTER_FIRST_ICUSTOMを保存します。2件目以降の指定日時診断では、BEFORE_DIAGNOSTIC_BATCHと、呼出しを実行できた場合のAFTER_DIAGNOSTIC_ICUSTOMを追加します。毎ティックの列挙は行いません。

- 名前、typeの数値コード、第1/第2アンカーの時刻/価格、color/style/width、説明を記録。
- 画面座標のラベル等では時間/価格をNOT_APPLICABLEとし、NAを保存。HLINEの時刻、VLINEの価格、単一アンカーの第2点も同様です。
- 未知の形状では第2点の取得を試みますが、0やエラーを有効なアンカーと決めつけません。未取得・非対応の可能性を状態へ残します。
- 無効な価格や時刻は主要列をNAとし、4つの座標の生返り値を別列に保存。取得エラーはproperty_errorsへ残します。色なし・空の説明・対応しないスタイル等も区別します。
- 名前・説明のカンマ、引用符、改行、%、=、+、-、@は可逆なパーセント形式でエスケープ。text_encoding=PERCENT_DELIMITERS_V1。Pythonのurllib.parse.unquoteで1回だけ復元できます。ファイルを改変する必要はありません。
- 各スナップショットの末尾にobject_index=-1の集計行。0件ならNO_OBJECTSをCSVとExpertsへ記録。列挙失敗はOBJECT_ENUMERATION_ERRORで、0件とは区別します。
- ObjectSnapshotLimit=0は全件。上限を設定して省略した場合はOBJECT_LIMIT_REACHED_PARTIALを記録し、完全成功とは扱いません。

**価格・色・名前が一致しても、そのオブジェクトがbuy-sell-magic1の赤/青ドットとは確定しません。** 他の指標やEAが作ったものも含みます。逆に0件でも、現在のチャート・その瞬間にオブジェクトが見つからないという事実だけで、バッファ方式を否定しません。スナップショットは原子的ではなく、途中変更や消失の検知には限界があります。SNAPSHOT_COMPLETEは列挙の完了であり、オブジェクトの所有者や全プロパティの正常性の保証ではありません。

オブジェクト値はCSVへ記録するだけで、水平群・ブレイク・候補の入力には使用しません。

## B：iCustomとバーの詳細

`BSMDiagnostics_<銘柄>_M1_v1.csv` を追加します。SESSION行とBUFFER行があり、次を独立した列で保存します。

- indicator_nameとSignalPeriod=12、ArrowPeriod=2、SL_pips=100、AlertON=true、Email=true（変更値もそのまま記録）。
- requested_bar_time、iBarShiftのresolved_bar_shift、呼出しに使うreference_shift、iTimeのactual_bar_time。
- buffer_mode、icustom_called、生値raw_value、value_classification、iCustom直後のGetLastError。
- bars_availableとbars_error、lookup_error、bar_time_error、reference_price_error、anchor_bar_time/anchor_error、mapping_status。
- indicator_read_status、indicator_init_status、EA側DLL許可状態とその取得エラー、build。

指定時刻はM1確定足と厳密一致を要求します。隣接足で代替せず、shift=0の価格も使用しません。不一致はBAR_TIME_MISMATCH等として記録し、そのmodeのiCustomは呼びません。呼んでいない場合、GetLastErrorはNOT_CALLED、raw_valueはNOT_READです。検索自体のエラーはlookup_error等に残します。既存の12列生値CSVでは、未呼出しの検索エラーは従来どおりread_errorへ残る場合があるため、詳細CSVと区別して読んでください。

mode 0～7を維持します。8～15を指定してもMQL4で文書化された範囲外なのでUNSUPPORTED_MT4_MODEとして記録し、呼出しやドット採用はしません。

分類の例：

| 返り値/状態 | 記録 | 意味 |
| --- | --- | --- |
| EMPTY_VALUE、エラー0 | NO_PRICE_RETURNED_INIT_UNVERIFIED | 価格なし。初期化成功とはしない |
| -1、エラー0 | ABSENT_MINUS_ONE | EMPTY_VALUE・0と区別 |
| 0、エラー0 | INVALID_ZERO | 正常なドット価格として使わない |
| 正価格、エラー0 | PRICE_RETURNED_CHART_MATCH_UNVERIFIED | 価格は返ったがチャートとの一致は未確認 |
| 返り値あり、エラー非0 | ICUSTOM_API_ERROR_INIT_UNVERIFIED | 生値とエラーの両方を保持 |
| 読取中に時刻が変化 | SERIES_CHANGED_DURING_READ | その価格を正常として採用しない |

## C：DLL許可・初期化・実行ログ

IsDllsAllowed()を**読み取るだけ**で、ea_dll_allowedを記録します。これはEA自身のコンテキストの状態で、チャート上や隠れたインジケーターの実際の許可状態を直接取得した値ではありません。

この診断版は、**EA側のDLL許可をOFFと取得できた場合だけiCustomを呼びます**。ONまたは取得不能ならDLL_CONTEXT_BLOCKED / DLL_CONTEXT_NOT_FALSE_NOT_CALLEDとして記録します。自動ONも自動OFFもしません。外部DLLのダウンロード・導入・直接呼出し、DLL import、Web操作は実装しません。EX4内部の動作自体はソース未提供のため独立には保証できません。

MT4のiCustomはMQL5のインジケーターハンドルのような初期化状態照会手段ではなく、また本EAからExperts/Journal全体を読む標準的な手段は使用できません。そのためindicator_init_statusはUNVERIFIED_REVIEW_EXPERTS_LOGを維持します。初期化成功を推測で記録しません。

`BSM_RUNTIME_CONTEXT`、`BSM_ICUSTOM_BATCH_BEGIN`、`BSM_ICUSTOM_BATCH_END`を出すので、利用者はその前後のExperts/Journalのインジケーター由来ログを保存できます。提供されたDLLメッセージをEA自身が捏造して出すことはしません。明示的な初期化失敗・ライセンス・配列範囲エラー等があれば、その全文と時刻を確認してください。ログがないことも成功の証明にはなりません。

DLL許可なしで確認できるのは、Aの現在オブジェクト、Bの時刻解決/履歴/返り値/分類/APIエラー、CのEA側コンテキストと利用者が見られるログです。安全な切り分けのためにDLLを許可する手順は案内しません。

## 設定・実行手順

新しいinputはCollectChartObjects=true、ObjectSnapshotLimit=0、DiagnosticBarTime2=0です。5つの指標入力・BuffersConfirmed=falseの初期値は維持します。

1. 本EAを停止してBSMの既存CSV/EX4をバックアップします。M3のEA/ファイルに触れません。
2. v1.03のBuySellMagicRecorder.mq4をMQL4/Expertsへ配置し、MetaEditorで本体をコンパイルします。Coreは変更なしです。
3. 既存EAが動作していないUSDJPY・M1チャートで、正規buy-sell-magic1を表示し、入力5項目を確認します。DLL許可はOFFのまま、BuffersConfirmed=falseを維持します。
4. DiagnosticBarTime=2026.11.09 09:43:00、DiagnosticBarTime2=2026.11.09 14:11:00、CollectChartObjects=trueで起動します。
5. MQL4/Filesにある既存2ファイルと新しい2ファイルを確認します。詳細CSVのrequested/actual一致・shift・bars・エラーを見てから返り値を見ます。両時刻に一致する履歴がなければ、その事実を記録します。
6. EA停止後の新CSVのコピーと、該当するBSMバッチ前後のExperts/Journalログを保管します。GetLastError=0だけで対応modeを決定しません。

日時はMT4サーバーのdatetime数値です。09:43は1794217380、14:11は1794233460として照合されます。ブローカーのタイムゾーンを推測してJSTへ補正しません。

元のcheck_probe.pyは既存12列生値CSVに引き続き利用できます。158.098/157.924との一致があっても役割の自動確定はしません。詳細CSVで実際に呼出したか、同じ入力か、正しい時刻かも確認します。

## 保存・重複・障害

既存50列台帳・12列生値、CSVのrecorder_version=1.00は維持し、新しい2ファイルだけschema_version=1の別スキーマです。全ファイルは追記/排他オープン/完結COMMITで、既存データを削除・上書き・修復しません。新ファイルの不正ヘッダー・途中行・連番不良でも停止します。書込・flushエラーはファイル名とエラーをログへ出して停止し、その後の候補を作りません。

各診断ファイルのsequenceは再起動後も連続します。再診断の観測はsession_id/sample_id/snapshot_idで区別して追記するため、同じ対象時刻やオブジェクト名が複数回出ること自体は重複候補ではありません。snapshot_idにsample_idが接頭辞として入る場合はそのバッチとの対応で、起動前スナップショットはsession_idで対応します。元の候補キー・群の使用済み状態・結果待ちの復元と重複防止は維持しています。

オブジェクト名・説明には私的なチャート情報が含まれる可能性があるため、新CSVもgitignore対象です。自動的にGitHubへ送信しません。

## テスト・未解決事項

ホストでは、0件/複数/無効プロパティ/取得エラー/上限/無効化/文字列エスケープ、時刻の一致/不一致/履歴不足、EMPTY_VALUE/-1/0とGetLastError、DLLフラグの読取り専用・呼出し抑止、書込/flush失敗、再起動時の追記、旧判定維持を確認します。

実機CSV・EX4ソース・当該ログ全文は未提供です。MetaEditorコンパイル、ネイティブObjectGet系APIの実動作、チャートとiCustomの一致、DLLメッセージの実際の発生箇所は未検証です。今回の実装だけで赤/青の取得方法を確定したとは報告しません。

DLLなしではバッファが埋まらないことが実機で確認された場合は、販売元へ「DLL不要で利用可能な版/設定」「正確な5入力の宣言順・型」「iCustomの別インスタンスでの利用可否」「履歴計算範囲」「オブジェクトとバッファの役割」「ライセンス制限」を確認するのが次の安全な手段です。EAから販売元へ連絡は行いません。
