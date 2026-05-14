# =============================================================================
#  SKORRO – Configuration File
#  Edit this file to customise everything. You never need to touch main.py.
# =============================================================================

# ── App icon ──────────────────────────────────────────────────────────────────
APP_ICON = "icon.png"   # place your PNG next to main.py and set the name here


# =============================================================================
#  INFORMATION PAGE
# =============================================================================

APP_INFO_TEXT = (
    "ABOUT SKORRO\n\n"
    "This app was built to keep score during card games with friends and "
    "family — no more scraps of paper or lost tallies.\n\n"
    "FEATURES\n"
    "- Track scores across multiple rounds for up to 8 players\n"
    "- Supports Toepen, Yaniv, and any freestyle game\n"
    "- Leaderboard that tracks wins and losses across all sessions\n"
    "- Auto-saves your game so you can pick up where you left off\n\n"
    "HOW TO USE\n"
    "1. Tap 'Start a Game' and choose which game to play.\n"
    "2. Enter the names of all players (2 to 8).\n"
    "3. After each round tap 'Update Scores' and fill in each player's score.\n"
    "4. Tap 'Next' — scores are added up automatically.\n"
    "5. The game ends when a player hits the score limit, or tap 'End Game' "
    "in freestyle mode.\n"
    "6. The Final Scores page shows the full ranking with medals.\n\n"
    "LEADERBOARD\n"
    "Tracks gold, silver, and bronze wins plus losses across all finished "
    "games. Only the last-place player gets a loss point.\n\n"
    "Version: 1.0\n\n"
    "PRIVACY POLICY:\n\n"
    "Effective date: 14-5-2026\n"
    "This application is designed to function primarily offline.\n\n1. Data collection\n\nThis app does not collect, transmit, or store any personal data on external servers."
    "\n\nUser-provided names are stored locally on the device solely to support the in-app leaderboard feature. This data remains on the device and is not shared or uploaded."
    "\n\n2. Internet usage\n\nThe app does not require an internet connection and does not communicate with external servers."
    "\n\n3. Third-party services\n\n"
    "This app does not use analytics, advertising, or tracking services.\n\n"
    "4. Data control\n\nAll stored data remains on the user’s device. Users can delete all stored data at any time by clearing the app data or uninstalling the app.\n\n"
    "5. Contact\n\nFor questions or support:\nskorrocard@gmail.com\n\n"
    "Online Privacy Policy can be found on: https://skorrocard.github.io/PrivacyPolicy/"

)


# =============================================================================
#  CARD GAME RULES
#  ──────────────────────────────────────────────────────────────────────────
#  Each entry shows as a button on the Rules screen.
#  Tapping it opens a full-screen page with the rules text.
#
#  "title" → button label and page heading
#  "text"  → full rules shown on the detail page
#
#  To ADD rules: copy a block to the bottom of the list and fill it in.
#  To REMOVE: delete the block. No changes to main.py needed.
# =============================================================================

RULES = [
    {
        "title": "Toepen",
        "text": (
            "Toepen is a Dutch trick-taking card game for 2-8 players.\n\n"
            "GOAL\n"
            "Keep your score below 10. The first player to reach 10 or more "
            "points loses.\n\n"
            "THE DECK\n"
            "Use a 32-card deck (7 through Ace in four suits). Remove cards 2-6.\n\n"
            "CARD VALUES\n"
            "10 > 9 > 8 > 7 > Ace > King > Queen > Jack\n\n"
            "DEAL\n"
            "Deal 4 cards to each player. If one has only one 7 and three jack-ace they can call 'dirty laundry', this can be bluffed so be aware. Getting caught costs 1 point as well as a false accusation. \n\n"
            "PLAY\n"
            "The player left of the dealer leads. Players must follow suit if "
            "possible; otherwise play any card. Highest card of the led suit "
            "wins.\n\n"
            "TOEPEN (raising the stakes)\n"
            "Before playing a card on your turn you may 'toep' (knock on the "
            "table) to raise the round value by 1 point. Others may fold "
            "(take current points) or continue. Multiple toeps can stack in "
            "one round.\n\n"
            "SCORING\n"
            "The loser of the last trick takes all the points for that round "
            "(normally 1, plus 1 per accepted toep). Scores accumulate. "
            "First to 10 or more loses."
        ),
    },
    {
        "title": "Yaniv",
        "text": (
            "Yaniv is a hand-reduction card game for 2-8 players.\n\n"
            "GOAL\n"
            "Have the lowest cumulative score. First to 200 or more is out.\n\n"
            "THE DECK\n"
            "Standard 52-card deck + 2 Jokers (54 cards total).\n\n"
            "CARD VALUES\n"
            "Ace = 1  |  2-10 = face value  |  J/Q/K = 10  |  Joker = 0\n\n"
            "DEAL\n"
            "Deal 7 cards to each player. Remaining cards go face-down as the "
            "draw pile; flip one card to start the discard pile.\n\n"
            "YOUR TURN\n"
            "1. DISCARD — play 1 or more cards face-up. Valid discards: a "
            "single card, a pair, three/four of a kind, or a run of 3+ "
            "consecutive same-suit cards.\n"
            "2. DRAW — take the top card of the draw pile OR the top card of "
            "the discard pile.\n\n"
            "CALLING YANIV\n"
            "If your hand totals 7 or less, call 'Yaniv!' instead of taking "
            "a normal turn. Everyone reveals their hand.\n"
            "- If yours is lowest (or joint lowest): you score 0.\n"
            "- If someone else is lower: they shout Yawee! — score your hand "
            "value + 35.\n"
            "All other players score the total value of their remaining cards.\n\n"
            "CHECKPOINTS (halving)\n"
            "After scoring, if your total is exactly 50, 100, 150, or 200, "
            "your score is halved immediately:\n"
            "  50 → 25  |  100 → 50  |  150 → 75  |  200 → 100\n"
            "The result is NOT halved again.\n\n"
            "ELIMINATION\n"
            "First to 201 or more points is eliminated. The player with the "
            "lowest score wins."
        ),
    },
    {
        "title": "Other Game: Freestyling it",
        "text": (
            "Use this mode for any game not listed above.\n\n"
            "HOW IT WORKS\n"
            "- Add 2 to 8 players with custom names.\n"
            "- Choose whether the lowest or highest total score wins.\n"
            "- Enter scores each round; they accumulate.\n"
            "- There is no automatic game-over — tap 'End Game' on the "
            "Current Score screen when you are done.\n\n"
            "The game is saved automatically so you can close the app and "
            "continue later."
        ),
    },

    # ── Template ──────────────────────────────────────────────────────────────
    # {
    #     "title": "My New Game",
    #     "text": (
    #         "GOAL\n"
    #         "...\n\n"
    #         "RULES\n"
    #         "..."
    #     ),
    # },
]


# =============================================================================
#  GAMES
#  ──────────────────────────────────────────────────────────────────────────
#  Each entry is a button on the 'Which Game?' screen.
#
#  id             — unique snake_case key (used in save file)
#  name           — display name in the UI
#  max_score      — game ends when a player reaches/exceeds this; None = no end
#  low_score_wins — True = lowest score is best
#  score_step     — +/- button increment on the score entry screen
#  yaniv_halving  — True = apply 50/100/150 halving after each round
#
#  To ADD: copy a block, fill in values. No main.py changes needed.
#  To REMOVE: delete the block.
# =============================================================================

GAMES = [
    {
        "id":             "toepen",
        "name":           "Toepen",
        "max_score":      10,
        "low_score_wins": True,
        "score_step":     1,
        "yaniv_halving":  False,
    },
    {
        "id":             "yaniv",
        "name":           "Yaniv",
        "max_score":      201,
        "low_score_wins": True,
        "score_step":     1,
        "yaniv_halving":  True,
    },
    {
        "id":             "freestyle",
        "name":           "Other Game: Freestyling it",
        "max_score":      None,
        "low_score_wins": True,   # overridden at runtime by player choice
        "score_step":     1,
        "yaniv_halving":  False,
    },

    # ── Template ──────────────────────────────────────────────────────────────
    # {
    #     "id":             "my_game",
    #     "name":           "My Game",
    #     "max_score":      50,
    #     "low_score_wins": True,
    #     "score_step":     1,
    #     "yaniv_halving":  False,
    # },
]


# =============================================================================
#  VISUAL THEME
#  ──────────────────────────────────────────────────────────────────────────
#  Change any value here to restyle the entire app.
#  All colours are hex strings (#RRGGBB or #RRGGBBAA).
# =============================================================================

THEME = {
    # Backgrounds
    "bg_dark":        "#1C1C2E",
    "bg_card":        "#2A2A42",
    "bg_header":      "#14142A",

    # Brand
    "accent":         "#E94560",
    "accent_dark":    "#B5304A",

    # Text
    "text_primary":   "#EEEEF4",
    "text_muted":     "#8888AA",
    "text_on_accent": "#FFFFFF",

    # Semantic
    "gold":       "#FFD700",
    "silver":     "#C0C0C0",
    "bronze":     "#CD7F32",
    "lantern":    "#E94560",
    "eliminated": "#FF6B6B",

    # Structure
    "border":     "#3A3A5C",

    # Font sizes in dp
    "font_size_title": 28,
    "font_size_h2":    20,
    "font_size_body":  16,
    "font_size_small": 13,

    # Layout in dp
    "padding": 16,
    "spacing": 10,
    "radius":  16,   # rounded corners — increase for rounder, decrease for sharper
}
