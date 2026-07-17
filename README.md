### README

## 開発管理統合アプリケーション（PoC）

<br>

## アプリケーションURL
http://13.192.197.156/

<br>

## テストアカウント一覧
役割一覧
- 申請者
- タスク担当者
- 部門管理者
- 本部管理者

<br>

開発部
| ID | Pass | Role |
| --- | --- | --- |
| applicant_dev | jptintern | 申請者 |
| member_dev | jptintern | タスク担当者 |
| manager_dev | jptintern | 部門管理者 |

<br>

インフラ部
| ID | Pass | Role |
| --- | --- | --- |
| applicant_infra | jptintern | 申請者 |
| member_infra | jptintern | 部門管理者 |

<br>

本部
| ID | Pass | Role |
| --- | --- | --- |
| hq | a | 本部管理者 |

<br>

## アプリケーションのイメージ

<br>

## 機能一覧
【申請者の機能】
- 新規案件の申請
- 自身の申請案件の進捗入力・更新
- 予算実績の入力
- 自身の案件一覧・ステータス確認

【部門管理者の機能】
- 申請の一次承認
- 自部門の案件一覧・進捗確認

【本部管理者の機能】
- 関連部門全案件の一覧・進捗確認
- 関連部門予算消費状況の確認

<br>

## ER図
![ER図](https://i.imgur.com/5sD6laq.png)

<br>

## 画面遷移図

<br>

## 使用技術
| Category  | Technology Stack |
| ------------- | ------------- |
| Frontend  | HTML, CSS, JavaScript |
| Backend  | Python3.12.3, Django6.0.2 |
| Database | PostgreSQL18.3 |
| Infrastructure	| Amazon Web Services |
| etc. | Git, Github |

<br>

## インフラ構成図

<br>

## 工夫点

<br>

## 今後の展望
