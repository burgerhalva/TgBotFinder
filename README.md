# TgBotFinder
TgBotFinder is a Telegram OSINT tool for pentest.
It searches for Telegram bots, channels, and groups that look related to a target keyword.


## How It Works
- Telegram native search can be unreliable. When you search for a keyword, Telegram does not always show all relevant bots, channels, or groups.
- Online catalogs and aggregators of Telegram bots and channels also have incomplete databases. Many existing bots, channels, and groups are not listed there.

TgBotFinder helps solve this problem by generating many possible username variations for a target keyword and checking them directly.

For a target word like `admin_panel`, TgBotFinder builds mutations such as:

```text
admin_panelbot
admin_panel_bot
admin_panel_a ... admin_panel_z
a_admin_panel ... z_admin_panel
admin_panel_a_bot ... admin_panel_z_bot
admin_panel_abot ... admin_panel_zbot
```

Example result:
```text
============================================================
FINAL RESULTS
============================================================
Total unique entities: 255
Bots: 234
Channels/groups: 21

BOTS
====
- admin panal | @APi_admin_panelbot | https://t.me/APi_admin_panelbot
- Admin Licencias | @Accesos_paneles_bot | https://t.me/Accesos_paneles_bot
- Admin_panel-Jarvis_RAN | @AdmRANbot | https://t.me/AdmRANbot
- @Auth_Bot_For_Admin_Panel | @Auth_For_Admin_Panel_bot | https://t.me/Auth_For_Admin_Panel_bot
- BET2WIN ADMIN PANEL | @BET2WIN_TBOT | https://t.me/BET2WIN_TBOT
- ADMIN PANEL | @Battery_va_admin_bot | https://t.me/Battery_va_admin_bot
- Admin Paneli [BeatBox] | @Beatbox_feedback_admin_bot | https://t.me/Beatbox_feedback_admin_bot
- Admin panel xui | @ChatGpt4_for_uni_bot | https://t.me/ChatGpt4_for_uni_bot
- Admin Panel | @CoderByBuxBot_Abot | https://t.me/CoderByBuxBot_Abot
- 3x-UI Admin panel | @DbJXaAHvcWj2QUU375Y3id4dVd3_bot | https://t.me/DbJXaAHvcWj2QUU375Y3id4dVd3_bot
- Admin Panel | @Dhdejejrhrbejis_bot | https://t.me/Dhdejejrhrbejis_bot
...
...
...
```

## Installation
```bash
pip3 install tgbotfinder
```
or
```bash
python -m pip install tgbotfinder
```

## Authentication

On the first run, log in with your telegram account using your **phone number**

## Usage

Basic:
```bash
tgbotfinder --word admin_panel
```

Override default API credentials:
```bash
tgbotfinder --word admin_panel --api-id 123456 --api-hash 9c38092828a62e...
```
Change the output file:

```bash
tgbotfinder --word admin_panel --output ./admin_panel_results.json
```

Adjust the delay between Telegram queries:
```bash
tgbotfinder --word admin_panel --delay 2
```

Remove the local session:
```bash
tgbotfinder --logout
```


## Notes

- Default `api_id` and `api_hash` are taken from https://plusmessenger.org
