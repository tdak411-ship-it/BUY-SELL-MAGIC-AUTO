# CSV仕様

CSVはカンマ区切り、MT4ではFILE_ANSI+CP_UTF8。時刻はサーバーのdatetime数値（epoch）です。ブローカーのタイムゾーンを推測してJSTへ変換しません。日付として見る場合はMT4のTimeToStringと照合してください。

## 候補・状態台帳（50列）

| 列 | 名前 | 内容 |
| --- | --- | --- |
| 1 | recorder_version | レコーダー版1.00（スキーマv1） |
| 2 | sequence | 台帳内で1から連続。ヘッダー除外 |
| 3 | event | BAR / RESET / CONFIG / THEORY |
| 4 | key | 銘柄|M1|ブレイク足epoch。RESET等は状態足epoch |
| 5 | server_time | 行を書いた時点のTimeCurrent epoch |
| 6 | symbol | 実際のチャート銘柄名（サフィックスを含む） |
| 7 | timeframe | M1固定 |
| 8 | signal_bar_time | 確定したブレイク/状態足の開始epoch |
| 9 | detection_time | この行の検出/記録TimeCurrent epoch（THEORYは結果行時点） |
| 10 | direction | HIGH / LOW / NONE |
| 11 | red_dot_price | 当該確定足の正規化した赤ドット。なし/異常は空 |
| 12 | blue_dot_price | 当該確定足の正規化した青ドット。なし/異常は空 |
| 13 | dot_buffer_mode | 候補に使ったmode。非候補は空 |
| 14 | dot_count | ブレイク前までの水平連続数。非候補は空 |
| 15 | horizontal_price | 使用した過去群の正規化価格 |
| 16 | breakout_open | 確定足始値、固定16桁 |
| 17 | breakout_high | 確定足高値 |
| 18 | breakout_low | 確定足安値 |
| 19 | breakout_close | 確定足終値 |
| 20 | breakout_valid | true=候補 / false=監査行 |
| 21 | rejection_reason | HIGH/LOW別のPASSや除外理由、RESET理由 |
| 22 | theoretical_entry_time | ブレイク足開始+60秒 |
| 23 | theoretical_entry_bid | 予定入口秒に観測したBid。未取得は空 |
| 24 | theoretical_expiry_time | 予定入口+180秒 |
| 25 | theoretical_expiry_bid | 予定出口秒の観測Bid。未取得は空 |
| 26 | theoretical_result | WIN / LOSS / DRAW / UNKNOWN |
| 27 | indicator_read_status | 赤status/青status |
| 28 | red_group_price | red 更新後の群価格 |
| 29 | red_group_count | red 更新後の連続数 |
| 30 | red_group_first | red 群開始足epoch |
| 31 | red_group_last | red 群最終足epoch |
| 32 | red_group_consumed | red 使用済みフラグ |
| 33 | blue_group_price | blue 更新後の群価格 |
| 34 | blue_group_count | blue 更新後の連続数 |
| 35 | blue_group_first | blue 群開始足epoch |
| 36 | blue_group_last | blue 群最終足epoch |
| 37 | blue_group_consumed | blue 使用済みフラグ |
| 38 | cursor | 状態として処理済みの最終足epoch |
| 39 | configuration | 入力値・明示渡し方式・照合申告フラグ。5入力を名前付きで保持 |
| 40 | source | ICUSTOM_EXPLICIT5_CLOSED_M1_NO_ORDERS（新規行）。旧DEFAULTS行も復元対応 |
| 41 | entry_quote_time | 入口Bidの正しい秒。未取得0 |
| 42 | expiry_quote_time | 出口Bidの正しい秒。未取得0 |
| 43 | observed_time | 結果を確定記録したTimeCurrent。未確定0 |
| 44 | result_status | PENDING / FINAL_MEASURED / FINAL_UNMEASURED / NOT_A_CANDIDATE |
| 45 | red_read_status | 赤選択modeの値分類 |
| 46 | blue_read_status | 青選択modeの値分類 |
| 47 | red_raw | 赤選択modeの生値（-1、EMPTY_VALUE等を維持） |
| 48 | blue_raw | 青選択modeの生値 |
| 49 | digits | 銘柄のDigits |
| 50 | end | COMMIT（完結行） |

THEORY行では元のブレイクOHLC等を重複保存しません。export_signals.pyが元の候補BARと結合します。群の列は各行を書いた時点の状態で、THEORYでも現在の群を保持します。RESETは未処理期間・起動、CONFIGは設定変更の記録です。

## 全バッファ生値（12列）

| 列 | 名前 | 内容 |
| --- | --- | --- |
| 1 | recorder_version | 1.00 |
| 2 | server_time | 取得TimeCurrent epoch |
| 3 | symbol | 実銘柄名 |
| 4 | timeframe | M1 |
| 5 | sample_bar_time | 参照した確定足epoch |
| 6 | mode | 0～ProbeMaxMode |
| 7 | value | 固定16桁 / EMPTY_VALUE / NONFINITE / NOT_READ |
| 8 | value_status | 値の分類 |
| 9 | read_error | iCustom直後のGetLastError（非対応modeは呼出しなし） |
| 10 | configuration | 入力・照合状態 |
| 11 | source | ICUSTOM_EXPLICIT5_CHART_MATCH_UNVERIFIED（新規行）。旧DEFAULT_INPUTS行も保持 |
| 12 | end | COMMIT |

値分類：PRICE、EMPTY_VALUE、ABSENT_MINUS_ONE、READ_ERROR、NONFINITE、INVALID_ZERO、INVALID_NEGATIVE、IMPLAUSIBLE_PRICE、NO_REFERENCE_PRICE、INVALID_NORMALIZED_PRICE、UNSUPPORTED_MT4_MODE、DIAGNOSTIC_BAR_UNAVAILABLE、SERIES_CHANGED_DURING_READ。UNCONFIGUREDは選択mode未設定時の台帳状態です。空欄表示を勝手に-1や価格へ補完しません。

## v1.02の入力記録

列数・ファイル名・recorder_version=1.00は維持します。configuration列にSignalPeriod、ArrowPeriod、SL_pips、AlertON、Emailを明記し、inputs=EXPLICIT_FIVE_USER_SUPPLIED_ORDERとinput_types=int:int:int:bool:boolを記録します。旧DEFAULTS行を上書きしません。現在の入力が旧状態と異なる場合、既存のCONFIGイベントでドット群をリセットします。
