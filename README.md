# Skorro – Card Game Score Tracker

## Run in PyCharm (no Linux, no Buildozer needed for development)

1. Open the `skorro` folder in PyCharm.
2. Open the built-in terminal (bottom of the screen).
3. Run:
   ```
   pip install kivy
   python main.py
   ```
That's it — the app opens in a window on your desktop.

---

## Files

| File | What to edit |
|---|---|
| `config.py` | **Everything you'll ever want to change**: game rules, game settings, colours, fonts, app icon, info text. |
| `main.py` | App logic and screens. Only touch this for structural changes. |
| `buildozer.spec` | Android packaging config (only needed for Google Play publishing). |
| `icon.png` | Drop your PNG icon here. |
| `skorro_save.json` | Auto-created. Stores the in-progress game. |
| `skorro_leaderboard.json` | Auto-created. Stores player stats across all games. |

---

## How to customise (all in config.py)

### Change the app icon
Drop a PNG in the folder and set:
```python
APP_ICON = "your_icon.png"
```

### Edit the Information page
Change the `APP_INFO_TEXT` string.

### Edit or add game rules (Rules page)
Find the `RULES` list. Each entry has a `"title"` and a `"text"`. Edit freely.
To add rules for a new game, copy the template block at the bottom of the list.

### Add a new playable game
Copy the template block at the bottom of the `GAMES` list:
```python
{
    "id":             "my_game",      # unique lowercase id
    "name":           "My Game",      # shown in UI
    "max_score":      50,             # game ends here; None = no limit
    "low_score_wins": True,           # True for most card games
    "score_step":     1,              # +/- button step size
},
```
No changes to `main.py` needed.

### Change colours / fonts / layout
Edit the `THEME` dict. Every colour, font size, padding, and corner radius is there.

---

## Feature overview

| Feature | Notes |
|---|---|
| Up to 8 players | Names entered before each game |
| Multiple games | Toepen, Yaniv, Freestyle (+ easy to add more) |
| Freestyle win mode | Choose "lowest" or "highest" score wins before starting |
| Freestyle End Game | End button on the Current Score page |
| Score entry | Tap +/– buttons (configurable step) or tap the number and type directly |
| Negative scores | Supported (e.g. Yaniv checkpoints) |
| Current Score view | 🏮 red lantern on the player in danger |
| Final Score view | 🥇🥈🥉 medals, 💀 for eliminated players, special labels for winner and loser |
| Leaderboard | Persistent across all sessions; tracks games played, wins, losses per player |
| Continue Game | Saves automatically; resume from the home screen |
| No data piling | Only one save file; leaderboard is the only persistent data |

---

## Screen flow

```
Home
├── Leaderboard
├── Card Game Rules
├── Information
└── Start a Game
      └── Which Game?
            └── Add Players (+ win-mode for Freestyle)
                  └── Current Score  ←──────────────┐
                        ├── Update Scores ───────────┘
                        ├── End Game (Freestyle only) → Final Score
                        └── [auto → Final Score when limit hit]
                                    ├── Play Again → Current Score
                                    └── Main Menu
```
