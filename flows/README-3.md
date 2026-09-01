```mermaid
flowchart TD
    S([保護PDFを開く]) --> O1[PDFから/Custom_OTP_Dataを取得]
    O1 --> O2{保護メタデータが存在する?}

    O2 -->|いいえ| NOTPROTECTED[未保護PDFとして処理<br/>またはポリシーに従い拒否]
    O2 -->|はい| O3[メタデータを厳格に解析]

    O3 --> O4{スキーマ・フィールド長・<br/>暗号方式・policyは妥当?}
    O4 -->|いいえ| FAIL
    O4 -->|はい| O5[document_idとkey_idを取得]

    O5 --> C1[共有Credentialを検索<br/>shared/key_id]
    C1 --> C2{共有Credentialが存在する?}

    C2 -->|いいえ| C3[旧形式の文書単位Credentialを検索]
    C2 -->|はい| C4[Credentialを読み込む]
    C3 --> C5{Credentialが存在する?}
    C5 -->|いいえ| FAIL
    C5 -->|はい| C4

    C4 --> C6[DPAPIでVaultを復号]
    C6 --> C7{Vaultの認証・解析に成功?}
    C7 -->|いいえ| FAIL
    C7 -->|はい| MODE{passphrase_mode}

    MODE -->|user| RAM{有効な秘密鍵が<br/>RAMキャッシュにある?}
    RAM -->|はい| KEYREADY[RAM上のX25519秘密鍵を使用]
    RAM -->|いいえ| PASS[パスフレーズを入力]
    PASS --> KDF[PBKDF2-HMAC-SHA256で<br/>K_pinを導出]
    KDF --> UNWRAP[Vault内の秘密鍵を<br/>AES-256-GCMで復号]
    UNWRAP --> UPASS{復号・タグ検証に成功?}
    UPASS -->|いいえ| RETRY{再試行可能?}
    RETRY -->|はい| PASS
    RETRY -->|いいえ| FAIL
    UPASS -->|はい| REMEMBER{RAMで記憶する期間}
    REMEMBER --> KEYREADY

    MODE -->|none| POLICY{現在のローカルポリシーで<br/>空パスフレーズを許可?}
    POLICY -->|いいえ| FAIL
    POLICY -->|はい| KEYREADY

    KEYREADY --> TIME1[validity_policyを読み込む]
    TIME1 --> TIME2[ntp_profile_idから<br/>ntp/profile.ntpを解決]
    TIME2 --> TIME3{NTPプロファイルが<br/>正常かつ空でない?}

    TIME3 -->|はい| NTP[NTPサーバーを順番に照会]
    TIME3 -->|いいえ| LOCALCHECK

    NTP --> NTPOK{NTP時刻を取得できた?}
    NTPOK -->|はい| VALIDATE[取得時刻を信頼時刻として使用]
    NTPOK -->|いいえ| LOCALCHECK{allow_local_time=1?}

    LOCALCHECK -->|いいえ| TIMEFAIL[時刻を確認できないため拒否]
    TIMEFAIL --> FAIL
    LOCALCHECK -->|はい| LOCAL[ローカルシステム時刻を使用]
    LOCAL --> VALIDATE

    VALIDATE --> BEFORE{現在時刻が<br/>valid_from_utc以上?}
    BEFORE -->|いいえ| FAIL
    BEFORE -->|はい| AFTER{現在時刻が<br/>valid_until_utc以下?}
    AFTER -->|いいえ| FAIL
    AFTER -->|はい| WRAP1[X25519で共有秘密を導出]

    WRAP1 --> WRAP2[HKDF-SHA256でK_wrapを導出]
    WRAP2 --> BUNDLE[鍵バンドルをAES-256-GCMで復号]
    BUNDLE --> BOK{タグ検証に成功?}
    BOK -->|いいえ| FAIL
    BOK -->|はい| DOCID{鍵バンドル内document_idと<br/>メタデータが一致?}
    DOCID -->|いいえ| FAIL

    DOCID -->|はい| OTPREQ{OTPが必要?<br/>RequireOtpEveryOpen=1<br/>またはRAM鍵未使用}
    OTPREQ -->|いいえ| PAYLOAD
    OTPREQ -->|はい| OTP1[AuthenticatorのOTPを入力]
    OTP1 --> OTP2[T-1・T・T+1の候補を計算]
    OTP2 --> OTP3{OTPが一致する?}
    OTP3 -->|いいえ| OTPRETRY{再試行可能?}
    OTPRETRY -->|はい| OTP1
    OTPRETRY -->|いいえ| FAIL
    OTP3 -->|はい| REPLAY{ローカル再利用チェックに<br/>抵触しない?}
    REPLAY -->|いいえ| FAIL
    REPLAY -->|はい| PAYLOAD

    PAYLOAD[K_encでPDFペイロードを<br/>AES-256-GCM復号] --> POK{タグ検証に成功?}
    POK -->|いいえ| FAIL
    POK -->|はい| RENDER[復号PDFをメモリから<br/>PDFiumへ渡す]
    RENDER --> VIEW[PDFを表示]
    VIEW --> CLOSE{文書を閉じる?}
    CLOSE -->|いいえ| VIEW
    CLOSE -->|はい| WIPE[PDF平文・K_enc・K_totp・K_wrap・<br/>OTP等をゼロ化]
    WIPE --> SUCCESS([閲覧終了])

    FAIL[一般化された解除失敗メッセージを表示] --> LOG[秘密情報を含まない<br/>診断ログを記録]
    LOG --> WIPEFAIL[取得済み秘密情報をゼロ化]
    WIPEFAIL --> END([オープン失敗])

        ##  判定ロジックの要約
```
