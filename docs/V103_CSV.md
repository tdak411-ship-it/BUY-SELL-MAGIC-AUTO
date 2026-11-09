# v1.03追加CSV仕様

既存50列台帳と12列生値は変更しません。保存先はMQL4/Filesです。新規CSVも追記専用で、原本の削除・上書き・自動修復はしません。

## BSMDiagnostics_<銘柄>_M1_v1.csv（41列）

| 列 | 名前 | 内容 |
| --- | --- | --- |
| 1 | schema_version | 1（新しい独立スキーマ） |
| 2 | sequence | ファイル内の連続番号。再起動でも復元 |
| 3 | session_id | 再初期化を区別する観測セッション |
| 4 | event | SESSION / BUFFER |
| 5 | sample_id | 1バッチの識別子 |
| 6 | server_time | 記録時のTimeCurrent数値 |
| 7 | chart_id | EAが稼働する現在チャートのChartID |
| 8 | symbol | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 9 | timeframe | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 10 | indicator_name | 実際に渡したIndicatorName |
| 11 | SignalPeriod | 明示渡しint |
| 12 | ArrowPeriod | 明示渡しint |
| 13 | SL_pips | 明示渡しint |
| 14 | AlertON | 明示渡しbool |
| 15 | Email | 明示渡しbool |
| 16 | requested_bar_time | 指定した足のサーバーdatetime数値 |
| 17 | resolved_bar_shift | iBarShiftの返り値 |
| 18 | reference_shift | 呼出しに使用しようとしたshift |
| 19 | actual_bar_time | 参照shiftのiTime（読取り後も確認）。不一致はmapping_statusへ |
| 20 | buffer_mode | 対象mode。SESSIONは-1 |
| 21 | icustom_called | 実際に当該modeを呼んだか |
| 22 | raw_value | iCustomの生値、EMPTY_VALUE、NONFINITE、未呼出しNOT_READ |
| 23 | value_classification | EMPTY_VALUE/-1/0/エラー/未呼出し等を区別 |
| 24 | GetLastError | iCustom直後のコード。呼出しなしはNOT_CALLED。検索等のエラーは別列 |
| 25 | bars_available | iBarsの実測返り値（bars_errorも参照） |
| 26 | indicator_read_status | 値・呼出し有無・初期化未確認を分離した取得状態 |
| 27 | indicator_init_status | UNVERIFIED_REVIEW_EXPERTS_LOG固定。成功を推測しない |
| 28 | lookup_error | iBarShiftのエラー |
| 29 | bar_time_error | iTimeのエラー |
| 30 | bars_error | iBarsのエラー |
| 31 | reference_price_error | 参照iCloseのエラー |
| 32 | price_reference | 値分類に使える終値参照。未取得NA |
| 33 | anchor_bar_time | 時刻の安定性確認用の現在M1足開始。価格は使用しない |
| 34 | anchor_error | 現在バーiTimeのエラー |
| 35 | mapping_status | EXACT_CLOSED_BARまたは時刻検索/履歴/変化の不一致理由 |
| 36 | ea_dll_allowed | IsDllsAllowedによるEA側のtrue/false/UNAVAILABLE。指標側の状態ではない |
| 37 | dll_flag_error | IsDllsAllowedの取得エラー |
| 38 | object_diagnostics_enabled | CollectChartObjectsの値 |
| 39 | build | 1.03 |
| 40 | source | 観測方法。オブジェクトはCURRENT_CHART_OBJECTS_NO_SIGNAL_INFERENCE |
| 41 | end | COMMIT |

## BSMObjects_<銘柄>_M1_v1.csv（30列）

| 列 | 名前 | 内容 |
| --- | --- | --- |
| 1 | schema_version | 1（新しい独立スキーマ） |
| 2 | sequence | ファイル内の連続番号。再起動でも復元 |
| 3 | session_id | 再初期化を区別する観測セッション |
| 4 | snapshot_id | スナップショット識別子。バッチとの対応は接頭辞 |
| 5 | phase | BEFORE_FIRST_ICUSTOM / AFTER_FIRST_ICUSTOM / BEFORE_DIAGNOSTIC_BATCH / AFTER_DIAGNOSTIC_ICUSTOM |
| 6 | server_time | 記録時のTimeCurrent数値 |
| 7 | chart_id | EAが稼働する現在チャートのChartID |
| 8 | symbol | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 9 | timeframe | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 10 | object_index | 0始まり。-1はスナップショット集計行 |
| 11 | objects_total | スナップショット開始時のObjectsTotal。失敗は負数/エラー |
| 12 | object_name | 可逆パーセントエスケープ済み。所有者は未確定 |
| 13 | object_type | OBJ_*に対応するMT4の数値コード。未取得NA |
| 14 | object_time1 | 第1アンカーepoch。未取得/非対応はNA |
| 15 | object_price1 | 第1アンカー価格。未取得/無効はNA |
| 16 | object_time2 | 第2アンカーepoch。未取得/非対応はNA |
| 17 | object_price2 | 第2アンカー価格。未取得/無効はNA |
| 18 | object_color | MT4のcolor数値。未取得/色なしはNA（生値はproperty_errors） |
| 19 | object_style | MT4のstyle数値。未取得はNA |
| 20 | object_width | 正の幅。5を超える矢印幅も記録。未取得はNA |
| 21 | object_description | OBJPROP_TEXT。可逆エスケープ。未取得NA、実際の空文字は空 |
| 22 | read_status | 全体/各プロパティの状態。SOURCE_UNVERIFIEDはドット役割を保証しない |
| 23 | property_errors | 各プロパティのGetLastErrorと、色/style/widthの生値 |
| 24 | time1_raw | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 25 | price1_raw | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 26 | time2_raw | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 27 | price2_raw | 該当座標APIの生返り値。未呼出しNOT_READ、エラー時も主要列と区別して保持 |
| 28 | text_encoding | PERCENT_DELIMITERS_V1。urllib.parse.unquoteで1回復元 |
| 29 | source | 観測方法。オブジェクトはCURRENT_CHART_OBJECTS_NO_SIGNAL_INFERENCE |
| 30 | end | COMMIT |

NA/NOT_READ/NOT_CALLEDはゼロや正常値の代用ではありません。GetLastError=0だけでは価格取得・初期化成功としません。再起動/再診断は新しいsession_idで追記し、既存の候補を再生成しません。詳細な解釈・DLL制約・手順は [V103_DIAGNOSTICS.md](V103_DIAGNOSTICS.md) を参照してください。
