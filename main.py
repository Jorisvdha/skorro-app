"""
Skorro – Card Game Score Tracker
main.py  •  All screen logic and app entry point.

Customise content, colours, and games in config.py — you rarely need to
edit this file.

To run in PyCharm:
  1.  File > Open  →  select the skorro/ folder (not a file inside it)
  2.  Terminal (bottom bar):  pip install kivy
  3.  python main.py
"""

import json
import os
import random

from kivy.app import App
from kivy.core.text import LabelBase
from kivy.core.window import Window
from kivy.graphics import Color, RoundedRectangle, Rectangle
from kivy.metrics import dp
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.image import Image
from kivy.uix.label import Label
from kivy.uix.popup import Popup
from kivy.uix.screenmanager import ScreenManager, Screen, SlideTransition
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.uix.widget import Widget
from kivy.utils import get_color_from_hex, platform

from config import APP_ICON, APP_INFO_TEXT, GAMES, RULES, THEME

# ── Resolve theme colours once at startup ─────────────────────────────────────
C = {
    k: get_color_from_hex(v) if isinstance(v, str) and v.startswith("#") else v
    for k, v in THEME.items()
}
Window.clearcolor = C["bg_dark"]
Window.set_icon("icon.png")
SAVE_FILE        = "skorro_save.json"
LEADERBOARD_FILE = "skorro_leaderboard.json"
YANIV_HALVE_AT   = {50, 100, 150, 200}

# ── Emoji font setup ──────────────────────────────────────────────────────────
# On Android, Kivy can use the system Noto Color Emoji font for emoji rendering.
# We register it under the alias "emoji" and use it wherever emoji appear.
# On desktop the alias falls back to the default font gracefully.
EMOJI_FONT = "Roboto"   # safe default (always available in Kivy)
if platform == "android":
    # Android ships NotoColorEmoji; tell Kivy where to find it.
    _emoji_candidates = [
        "/system/fonts/NotoColorEmoji.ttf",
        "/system/fonts/NotoEmoji-Regular.ttf",
    ]
    for _path in _emoji_candidates:
        if os.path.exists(_path):
            try:
                LabelBase.register("emoji", _path)
                EMOJI_FONT = "emoji"
            except Exception:
                pass
            break


def emoji_label(text, size=16, **kw):
    """Label that uses the emoji font on Android, default font on desktop."""
    kw.setdefault("halign",  "center")
    kw.setdefault("valign",  "middle")
    kw.setdefault("color",   C["text_primary"])
    kw.setdefault("size_hint_y", None)
    w = Label(
        text=str(text),
        font_size=dp(size),
        font_name=EMOJI_FONT,
        **kw,
    )
    w.bind(size=w.setter("text_size"))
    return w


# =============================================================================
#  Colour helper
# =============================================================================

def c(key):
    """Return the resolved RGBA tuple for a theme colour key."""
    return C[key]


# =============================================================================
#  Yaniv halving rule
# =============================================================================

def apply_yaniv_halving(score):
    """
    Halve score if it is exactly 50, 100, 150, or 200.
    The result is never halved a second time:
      50 -> 25  |  100 -> 50  |  150 -> 75  |  200 -> 100
    """
    return score // 2 if score in YANIV_HALVE_AT else score


# =============================================================================
#  Leaderboard persistence
# =============================================================================

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_FILE):
        return {}
    try:
        with open(LEADERBOARD_FILE) as f:
            return json.load(f)
    except Exception:
        return {}


def save_leaderboard(data):
    try:
        with open(LEADERBOARD_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"[Skorro] leaderboard save error: {e}")


def record_game_result(player_names, scores, low_wins):
    """
    Update the leaderboard after a game, respecting Olympic-style ties.

    player_names — all participant names
    scores       — their corresponding final scores (same order)
    low_wins     — True when lowest score is best

    Medal rules (matching what is shown on the Final Score screen):
    - Rank 0 group  → everyone gets gold
    - Rank 1 group  → everyone gets silver  (only if rank-1 is not the last rank)
    - Rank 2 group  → everyone gets bronze  (only if rank-2 is not the last rank)
    - Last rank     → everyone gets a loss
    - Middle ranks  → nothing extra
    - All players   → played += 1
    """
    lb = load_leaderboard()
    for name in player_names:
        if name not in lb:
            lb[name] = {"played": 0, "gold": 0, "silver": 0, "bronze": 0, "losses": 0}
        if "wins" in lb[name]:          # migrate old key
            lb[name]["gold"] = lb[name].pop("wins")
        lb[name]["played"] += 1

    ranking   = compute_ranking(scores, player_names, low_wins)
    last_rank = ranking[-1]["rank"] if ranking else None

    for entry in ranking:
        rank = entry["rank"]
        name = entry["name"]
        # Gold
        if rank == 0:
            lb[name]["gold"] += 1
        # Silver — only if this rank is not the last rank
        elif rank == 1 and rank != last_rank:
            lb[name]["silver"] += 1
        # Bronze — only if this rank is not the last rank
        elif rank == 2 and rank != last_rank:
            lb[name]["bronze"] += 1
        # Loss — everyone who shares the last rank
        if rank == last_rank:
            lb[name]["losses"] += 1

    save_leaderboard(lb)


# =============================================================================
#  Ranking helper — handles ties (Olympic style)
# =============================================================================

def compute_ranking(scores, names, low_wins):
    """
    Return a list of dicts, sorted best -> worst, with Olympic-style ranks.

    Each dict: {"score": int, "name": str, "rank": int, "tied": bool}

    rank is 0-based. Tied players share the same rank; the next rank after
    a tie group skips accordingly (like the Olympics: two golds -> no silver).

    Example (low wins): scores [10, 20, 20, 30]
      rank 0 -> 10 (gold)
      rank 1 -> 20 (silver, tied)
      rank 1 -> 20 (silver, tied)
      rank 3 -> 30 (4th, no medal — rank 2 is skipped)
    """
    paired = sorted(zip(scores, names), key=lambda x: x[0], reverse=not low_wins)

    result = []
    rank = 0
    i    = 0
    while i < len(paired):
        score, name = paired[i]
        # Count how many share this exact score
        j = i
        while j < len(paired) and paired[j][0] == score:
            j += 1
        group_size = j - i
        tied = group_size > 1
        for k in range(group_size):
            result.append({"score": score, "name": paired[i + k][1],
                           "rank": rank, "tied": tied})
        rank += group_size   # skip ranks for tied group (Olympic rule)
        i     = j

    return result


# =============================================================================
#  Low-level UI primitives
# =============================================================================

def make_label(text, size=None, color=None, bold=False,
               halign="center", italic=False, **kw):
    """
    Create a Label whose text_size tracks its own size so text wraps
    and alignment works correctly on all screen sizes.
    """
    size = size or THEME["font_size_body"]
    widget = Label(
        text=str(text),
        font_size=dp(size),
        color=color or c("text_primary"),
        bold=bold,
        italic=italic,
        halign=halign,
        valign="middle",
        **kw,
    )
    widget.bind(size=widget.setter("text_size"))
    return widget


def v_spacer(h=8):
    """Vertical spacer for use in vertical BoxLayouts."""
    return Widget(size_hint=(1, None), height=dp(h))


def h_spacer(w=8):
    """Horizontal spacer for use in horizontal BoxLayouts."""
    return Widget(size_hint=(None, 1), width=dp(w))


def thin_divider():
    """One-pixel horizontal rule."""
    d = Widget(size_hint=(1, None), height=dp(1))
    with d.canvas:
        Color(*c("border"))
        Rectangle(pos=d.pos, size=d.size)
    d.bind(
        pos =lambda w, *_: setattr(w.canvas.children[-1], "pos",  w.pos),
        size=lambda w, *_: setattr(w.canvas.children[-1], "size", w.size),
    )
    return d


def navigate(screen_name, direction="left"):
    App.get_running_app().sm.transition = SlideTransition(direction=direction)
    App.get_running_app().sm.current    = screen_name


# =============================================================================
#  Rounded surfaces
# =============================================================================

class RoundedBox(BoxLayout):
    """BoxLayout with a solid rounded-rectangle background drawn on canvas."""

    def __init__(self, bg_key="bg_card", radius=None, **kw):
        super().__init__(**kw)
        self._bg_key = bg_key
        self._r      = radius if radius is not None else dp(THEME["radius"])
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*c(self._bg_key))
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._r])


class RoundedBtn(Button):
    """
    Button with a canvas-drawn RoundedRectangle background.
    Looks identical on desktop and Android.
    """

    def __init__(self, text, bg=None, fg=None, radius=None,
                 cb=None, bold=True, **kw):
        kw.setdefault("size_hint_y", None)
        kw.setdefault("height",      dp(50))
        kw.setdefault("font_size",   dp(THEME["font_size_body"]))
        self._bg = bg     if bg     is not None else c("accent")
        self._fg = fg     if fg     is not None else c("text_on_accent")
        self._r  = radius if radius is not None else dp(THEME["radius"])
        super().__init__(
            text=str(text),
            background_normal="",
            background_color=(0, 0, 0, 0),
            color=self._fg,
            bold=bold,
            **kw,
        )
        self.bind(pos=self._redraw, size=self._redraw)
        if cb:
            self.bind(on_release=lambda *_: cb())

    def _redraw(self, *_):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(*self._bg)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[self._r])

    def set_colors(self, bg, fg):
        self._bg   = bg
        self._fg   = fg
        self.color = fg
        self._redraw()


class ToggleBtn(RoundedBtn):
    """Two-state rounded button."""

    def __init__(self, text, selected=False, cb=None, **kw):
        kw.setdefault("height", dp(48))
        super().__init__(
            text=text,
            bg=c("accent")         if selected else c("bg_card"),
            fg=c("text_on_accent") if selected else c("text_muted"),
            cb=cb,
            bold=selected,
            **kw,
        )

    def set_selected(self, val):
        self.bold = val
        self.set_colors(
            c("accent")         if val else c("bg_card"),
            c("text_on_accent") if val else c("text_muted"),
        )


# ── Convenience constructors ──────────────────────────────────────────────────

def PrimaryBtn(text, cb=None, **kw):
    kw.setdefault("height", dp(52))
    return RoundedBtn(text, bg=c("accent"), fg=c("text_on_accent"), cb=cb, **kw)


def SecondaryBtn(text, cb=None, **kw):
    kw.setdefault("height", dp(48))
    return RoundedBtn(text, bg=c("bg_card"), fg=c("text_primary"),
                      cb=cb, bold=False, **kw)


def SmallBtn(text, cb=None, **kw):
    """Small button for header corners — vertically centred inside a wrapper."""
    kw.setdefault("size_hint", (None, None))
    kw.setdefault("size",      (dp(112), dp(30)))
    kw.setdefault("font_size", dp(THEME["font_size_small"]))
    return RoundedBtn(text, bg=c("bg_card"), fg=c("text_muted"),
                      radius=dp(10), cb=cb, bold=False, **kw)


def header_bar(title, right_widget=None):
    """
    Dark header bar.  If right_widget is provided it is wrapped in a small
    vertical BoxLayout that centres it so it does not touch the top/bottom
    edges of the bar.
    """
    bar = RoundedBox(
        bg_key="bg_header",
        radius=dp(0),
        orientation="horizontal",
        size_hint_y=None,
        height=dp(58),
        padding=[dp(THEME["padding"]), 0],
        spacing=dp(8),
    )
    bar.add_widget(make_label(title, size=THEME["font_size_h2"],
                              bold=True, halign="left"))
    if right_widget:
        # Wrap in a vertical container so the button floats vertically centred.
        # Kivy BoxLayout padding=[left, bottom, right, top].
        # We calculate margin so the button sits exactly in the middle.
        btn_h  = getattr(right_widget, "height", dp(30))
        bar_h  = dp(58)
        margin = max((bar_h - btn_h) / 2, dp(6))
        wrapper = BoxLayout(
            orientation="vertical",
            size_hint=(None, 1),
            width=getattr(right_widget, "width", dp(112)),
            padding=[0, margin, 0, margin],
        )
        wrapper.add_widget(right_widget)
        bar.add_widget(wrapper)
    return bar


def wrap_scroll(inner):
    """Put inner (a size_hint_y=None BoxLayout) inside a ScrollView."""
    sv = ScrollView(size_hint=(1, 1))
    sv.add_widget(inner)
    return sv


def make_inner(spacing=None, **kw):
    """Scrollable inner column: vertical BoxLayout that sizes itself to content."""
    bx = BoxLayout(
        orientation="vertical",
        size_hint_y=None,
        padding=[dp(THEME["padding"]), dp(8), dp(THEME["padding"]), dp(16)],
        spacing=dp(spacing if spacing is not None else THEME["spacing"]),
        **kw,
    )
    bx.bind(minimum_height=bx.setter("height"))
    return bx


def auto_label(text, **kw):
    """A Label that sizes its own height to fit wrapped text."""
    kw.setdefault("font_size",   dp(THEME["font_size_body"]))
    kw.setdefault("color",       c("text_primary"))
    kw.setdefault("halign",      "left")
    kw.setdefault("valign",      "top")
    kw.setdefault("size_hint_y", None)
    widget = Label(text=str(text), **kw)

    def _resize(w, *_):
        w.text_size = (w.width, None)
        w.texture_update()
        w.height = w.texture_size[1] + dp(4)

    widget.bind(width=_resize, text=_resize)
    return widget


# =============================================================================
#  Android back-button support
# =============================================================================
# Map screen names to where the back button should go.
# Screens not listed here will close the app (default behaviour).

BACK_NAV = {
    "info":         ("home",         "right"),
    "rules":        ("home",         "right"),
    "rules_detail": ("rules",        "right"),
    "leaderboard":  ("home",         "right"),
    "which_game":   ("home",         "right"),
    "add_players":  ("which_game",   "right"),
    "current_score":("home",         "right"),   # triggers go-home popup
    "update_scores":("current_score","right"),
    "final_score":  ("home",         "right"),
}


def _handle_back(window, key, *args):
    """
    Called on every key press.  key 27 = Escape on desktop = Back on Android.
    Returns True to consume the event (prevents app exit), False to pass through.
    """
    if key != 27:
        return False

    app = App.get_running_app()
    current = app.sm.current

    if current == "home":
        return False   # let Android close the app normally from home

    if current == "current_score":
        # Reuse the existing go-home popup logic
        screen = app.sm.get_screen("current_score")
        screen._go_home()
        return True

    if current in BACK_NAV:
        dest, direction = BACK_NAV[current]
        navigate(dest, direction)
        return True

    return False


# =============================================================================
#  Screens
# =============================================================================

# ── Home ──────────────────────────────────────────────────────────────────────

class HomeScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="home", **kw)

        root = BoxLayout(
            orientation="vertical",
            padding=dp(THEME["padding"]),
            spacing=dp(THEME["spacing"]),
        )

        root.add_widget(v_spacer(24))

        # ── Logo: image centred above title ───────────────────────────────────
        logo_col = BoxLayout(
            orientation="vertical",
            size_hint_y=None,
            height=dp(120),
            spacing=dp(6),
        )
        img_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(72))
        img_row.add_widget(Widget())
        if os.path.exists(APP_ICON):
            img_row.add_widget(Image(
                source=APP_ICON,
                size_hint=(None, None),
                size=(dp(72), dp(72)),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True,
            ))
        img_row.add_widget(Widget())
        logo_col.add_widget(img_row)
        logo_col.add_widget(make_label(
            "Skorro", size=36, bold=True, halign="center",
            size_hint_y=None, height=dp(42),
        ))
        root.add_widget(logo_col)

        root.add_widget(make_label(
            "Your card game score keeper",
            size=THEME["font_size_small"],
            color=c("text_muted"),
            halign="center",
            size_hint_y=None,
            height=dp(24),
        ))

        root.add_widget(v_spacer(16))
        root.add_widget(PrimaryBtn("Start a Game",    cb=self._start))
        root.add_widget(v_spacer(4))
        self._cont_btn = SecondaryBtn("Continue Game", cb=self._continue)
        root.add_widget(self._cont_btn)
        root.add_widget(v_spacer(4))
        root.add_widget(SecondaryBtn("Leaderboard",    cb=lambda: navigate("leaderboard")))
        root.add_widget(v_spacer(4))
        root.add_widget(SecondaryBtn("Card Game Rules", cb=lambda: navigate("rules")))
        root.add_widget(v_spacer(4))
        root.add_widget(SecondaryBtn("Information",    cb=lambda: navigate("info")))
        root.add_widget(Widget())

        self.add_widget(root)

    def on_pre_enter(self):
        has = os.path.exists(SAVE_FILE)
        self._cont_btn.disabled = not has
        self._cont_btn.color    = c("text_primary") if has else c("text_muted")

    def _start(self):
        navigate("which_game")

    def _continue(self):
        if App.get_running_app().load_game():
            navigate("current_score")


# ── Information ───────────────────────────────────────────────────────────────

class InfoScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="info", **kw)
        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Information"))
        inner = make_inner()
        inner.add_widget(auto_label(APP_INFO_TEXT))
        inner.add_widget(v_spacer(12))
        inner.add_widget(PrimaryBtn("Back", cb=lambda: navigate("home", "right")))
        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)


# ── Rules index ───────────────────────────────────────────────────────────────

class RulesScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="rules", **kw)
        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Card Game Rules"))
        inner = make_inner()
        inner.add_widget(make_label(
            "Select a game to read its rules:",
            color=c("text_muted"), size_hint_y=None, height=dp(28),
        ))
        inner.add_widget(v_spacer(4))

        for i, entry in enumerate(RULES):
            def _open(idx=i):
                App.get_running_app().rules_index = idx
                navigate("rules_detail")
            inner.add_widget(PrimaryBtn(entry["title"], cb=_open))
            inner.add_widget(v_spacer(4))

        inner.add_widget(v_spacer(8))
        inner.add_widget(SecondaryBtn("Back", cb=lambda: navigate("home", "right")))
        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)


# ── Rules detail ──────────────────────────────────────────────────────────────

class RulesDetailScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="rules_detail", **kw)

    def on_pre_enter(self):
        self.clear_widgets()
        app   = App.get_running_app()
        idx   = getattr(app, "rules_index", 0)
        entry = RULES[max(0, min(idx, len(RULES) - 1))]

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar(entry["title"]))
        inner = make_inner()
        inner.add_widget(auto_label(entry["text"]))
        inner.add_widget(v_spacer(12))
        inner.add_widget(PrimaryBtn("Back", cb=lambda: navigate("rules", "right")))
        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)


# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="leaderboard", **kw)

    def on_pre_enter(self):
        self._build()

    def _build(self):
        self.clear_widgets()
        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Leaderboard"))

        inner = make_inner(spacing=6)
        lb    = load_leaderboard()

        if not lb:
            inner.add_widget(v_spacer(32))
            inner.add_widget(make_label(
                "No games recorded yet.\nFinish a game to appear here!",
                color=c("text_muted"),
            ))
            inner.add_widget(v_spacer(32))
        else:
            ranked = sorted(
                lb.items(),
                key=lambda x: (
                    -x[1].get("gold",   0),
                    -x[1].get("silver", 0),
                    -x[1].get("bronze", 0),
                     x[1].get("losses", 0),
                ),
            )

            hdr = BoxLayout(size_hint_y=None, height=dp(26),
                            padding=[dp(10), 0], spacing=dp(4))
            hdr.add_widget(make_label("",     size=11,
                                      size_hint=(None, 1), width=dp(38)))
            hdr.add_widget(make_label("Name", size=11,
                                      color=c("text_muted"), halign="left"))
            for txt, col in [("GP", c("text_muted")), ("G",  c("gold")),
                              ("S",  c("silver")),     ("B",  c("bronze")),
                              ("L",  c("eliminated"))]:
                hdr.add_widget(make_label(txt, size=11, color=col,
                                          size_hint=(None, 1), width=dp(28),
                                          halign="center"))
            inner.add_widget(hdr)
            inner.add_widget(thin_divider())
            inner.add_widget(v_spacer(4))

            rank_labels  = ["1st", "2nd", "3rd"]
            rank_colours = [c("gold"), c("silver"), c("bronze")]

            for pos, (name, stats) in enumerate(ranked):
                gold   = stats.get("gold",   0)
                silver = stats.get("silver", 0)
                bronze = stats.get("bronze", 0)
                losses = stats.get("losses", 0)
                played = stats.get("played", 0)

                row = RoundedBox(
                    bg_key="bg_card",
                    orientation="horizontal",
                    size_hint_y=None, height=dp(44),
                    padding=[dp(10), 0], spacing=dp(4),
                )
                if pos < 3:
                    ind_txt = rank_labels[pos]
                    ind_col = rank_colours[pos]
                else:
                    ind_txt = f"{pos + 1}."
                    ind_col = c("text_muted")

                row.add_widget(make_label(ind_txt, size=11, color=ind_col,
                                          size_hint=(None, 1), width=dp(38)))
                row.add_widget(make_label(name, halign="left",
                                          bold=(pos == 0),
                                          color=c("gold") if pos == 0
                                          else c("text_primary")))
                for val, col in [
                    (played, c("text_muted")),
                    (gold,   c("gold")),
                    (silver, c("silver")),
                    (bronze, c("bronze")),
                    (losses, c("eliminated") if losses else c("text_muted")),
                ]:
                    row.add_widget(make_label(
                        str(val), size=13, color=col,
                        bold=bool(val and col != c("text_muted")),
                        size_hint=(None, 1), width=dp(28), halign="center",
                    ))
                inner.add_widget(row)
                inner.add_widget(v_spacer(4))

        inner.add_widget(v_spacer(12))
        if lb:
            inner.add_widget(SecondaryBtn("Clear Leaderboard",
                                          cb=self._confirm_clear))
            inner.add_widget(v_spacer(4))
        inner.add_widget(PrimaryBtn("Back to Main Menu",
                                    cb=lambda: navigate("home", "right")))
        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)

    def _confirm_clear(self):
        def _do_clear():
            popup.dismiss()
            if os.path.exists(LEADERBOARD_FILE):
                os.remove(LEADERBOARD_FILE)
            self._build()

        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(make_label(
            "Clear all leaderboard data?\nThis cannot be undone.", size=14))
        btn_row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        yes = SecondaryBtn("Yes, clear", cb=_do_clear, height=dp(44))
        yes.color = c("eliminated")
        btn_row.add_widget(yes)
        btn_row.add_widget(PrimaryBtn("Cancel",
                                      cb=lambda: popup.dismiss(), height=dp(44)))
        content.add_widget(btn_row)
        popup = Popup(title="Clear Leaderboard", content=content,
                      size_hint=(0.85, 0.30))
        popup.open()


# ── Which Game? ───────────────────────────────────────────────────────────────

class WhichGameScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="which_game", **kw)
        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Which Game?"))
        inner = make_inner()
        inner.add_widget(make_label("Choose a game to play:",
                                    color=c("text_muted"),
                                    size_hint_y=None, height=dp(28)))
        inner.add_widget(v_spacer(4))

        for game in GAMES:
            def _pick(g=game):
                App.get_running_app().selected_game = dict(g)
                navigate("add_players")
            inner.add_widget(PrimaryBtn(game["name"], cb=_pick))
            inner.add_widget(v_spacer(4))

        inner.add_widget(v_spacer(8))
        inner.add_widget(SecondaryBtn("Back", cb=lambda: navigate("home", "right")))
        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)


# ── Add Players ───────────────────────────────────────────────────────────────

class AddPlayersScreen(Screen):
    MAX = 8

    def __init__(self, **kw):
        super().__init__(name="add_players", **kw)

    def on_pre_enter(self):
        self.clear_widgets()
        self._inputs   = []
        self._low_btn  = None
        self._high_btn = None

        app          = App.get_running_app()
        game         = app.selected_game
        is_freestyle = game["max_score"] is None

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar(f"Players  —  {game['name']}"))

        inner = make_inner(spacing=8)
        inner.add_widget(make_label("Add 2 to 8 players:",
                                    color=c("text_muted"),
                                    size_hint_y=None, height=dp(24)))
        inner.add_widget(v_spacer(4))

        for i in range(self.MAX):
            ti = TextInput(
                hint_text=f"Player {i + 1}" + (" (optional)" if i >= 2 else ""),
                multiline=False,
                font_size=dp(THEME["font_size_body"]),
                background_color=c("bg_card"),
                foreground_color=c("text_primary"),
                hint_text_color=c("text_muted"),
                cursor_color=c("accent"),
                size_hint_y=None,
                height=dp(44),
                padding=[dp(12), dp(11)],
            )
            self._inputs.append(ti)
            inner.add_widget(ti)

        if is_freestyle:
            inner.add_widget(v_spacer(10))
            inner.add_widget(make_label("Who wins this game?",
                                        color=c("text_muted"),
                                        size=THEME["font_size_small"],
                                        size_hint_y=None, height=dp(22)))
            inner.add_widget(v_spacer(4))
            toggle_row = BoxLayout(size_hint_y=None, height=dp(48), spacing=dp(8))
            self._low_btn  = ToggleBtn("Lowest score wins",  selected=True,
                                       cb=lambda: self._set_mode(True))
            self._high_btn = ToggleBtn("Highest score wins", selected=False,
                                       cb=lambda: self._set_mode(False))
            toggle_row.add_widget(self._low_btn)
            toggle_row.add_widget(self._high_btn)
            inner.add_widget(toggle_row)
            app.selected_game["low_score_wins"] = True

        inner.add_widget(v_spacer(10))
        inner.add_widget(PrimaryBtn("Let's go!", cb=self._start))
        inner.add_widget(v_spacer(4))
        inner.add_widget(SecondaryBtn("Back",
                                      cb=lambda: navigate("which_game", "right")))
        # Extra bottom padding so players can scroll past the on-screen keyboard
        inner.add_widget(v_spacer(220))

        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)

    def _set_mode(self, low_wins):
        App.get_running_app().selected_game["low_score_wins"] = low_wins
        if self._low_btn:
            self._low_btn.set_selected(low_wins)
        if self._high_btn:
            self._high_btn.set_selected(not low_wins)

    def _start(self):
        names = [ti.text.strip() for ti in self._inputs if ti.text.strip()]
        if len(names) < 2:
            Popup(
                title="More players needed",
                content=make_label("Please enter at least 2 player names.", size=14),
                size_hint=(0.8, 0.22),
            ).open()
            return
        App.get_running_app().init_new_game(names)
        navigate("current_score")


# ── Current Score ─────────────────────────────────────────────────────────────

class CurrentScoreScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="current_score", **kw)

    def on_pre_enter(self):
        self._build()

    def _build(self):
        self.clear_widgets()
        app          = App.get_running_app()
        game         = app.selected_game
        is_freestyle = game["max_score"] is None
        scores       = app.total_scores
        low_wins     = game["low_score_wins"]
        all_same     = len(set(scores)) <= 1
        danger_score = max(scores) if low_wins else min(scores)

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar(
            f"{game['name']}  —  Round {app.round_num}",
            right_widget=SmallBtn("Main Menu", cb=self._go_home,height=dp(40)),
        ))

        inner = make_inner(spacing=4)

        for i, name in enumerate(app.player_names):
            is_danger = (not all_same) and scores[i] == danger_score
            row = RoundedBox(
                bg_key="bg_card",
                orientation="horizontal",
                size_hint_y=None, height=dp(46),
                padding=[dp(12), 0], spacing=dp(6),
            )
            row.add_widget(make_label(
                ">>" if is_danger else "  ",
                size=13,
                color=c("lantern") if is_danger else c("bg_card"),
                size_hint=(None, 1), width=dp(26),
            ))
            row.add_widget(make_label(name, halign="left", bold=is_danger,
                                      size=THEME["font_size_body"]))
            row.add_widget(make_label(
                str(scores[i]), size=20, bold=True,
                color=c("lantern") if is_danger else c("text_primary"),
                size_hint=(None, 1), width=dp(58), halign="right",
            ))
            inner.add_widget(row)
            inner.add_widget(v_spacer(4))

        inner.add_widget(v_spacer(10))
        inner.add_widget(PrimaryBtn("Update Scores",
                                    cb=lambda: navigate("update_scores")))
        if is_freestyle:
            inner.add_widget(v_spacer(4))
            inner.add_widget(SecondaryBtn("End Game", cb=self._end_game))

        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)

    def _end_game(self):
        app = App.get_running_app()
        app.record_and_clear()
        navigate("final_score")

    def _go_home(self):
        def _confirm():
            popup.dismiss()
            navigate("home", "right")

        content = BoxLayout(orientation="vertical", padding=dp(16), spacing=dp(12))
        content.add_widget(make_label(
            "Go to main menu?\nYour game progress is saved.", size=14))
        row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(8))
        row.add_widget(PrimaryBtn("Yes, go home", cb=_confirm, height=dp(44)))
        row.add_widget(SecondaryBtn("Cancel",
                                    cb=lambda: popup.dismiss(), height=dp(44)))
        content.add_widget(row)
        popup = Popup(title="Main Menu", content=content, size_hint=(0.85, 0.30))
        popup.open()


# ── Update Scores ─────────────────────────────────────────────────────────────

class UpdateScoresScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="update_scores", **kw)

    def on_pre_enter(self):
        self._build()

    def _build(self):
        self.clear_widgets()
        self._score_inputs = []
        app  = App.get_running_app()
        step = app.selected_game["score_step"]

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar(f"Round {app.round_num}  —  Enter Scores"))

        inner = make_inner(spacing=6)
        inner.add_widget(make_label(
            f"Tap +/-  (step: {step})  or tap the number to type directly.",
            size=THEME["font_size_small"], color=c("text_muted"),
            size_hint_y=None, height=dp(22),
        ))
        inner.add_widget(v_spacer(6))

        for name in app.player_names:
            row = BoxLayout(size_hint_y=None, height=dp(44), spacing=dp(6))
            row.add_widget(make_label(
                name, halign="left",
                size=THEME["font_size_small"], color=c("text_primary"),
                size_hint=(None, 1), width=dp(90),
            ))
            minus = RoundedBtn(
                "-", bg=c("bg_card"), fg=c("accent"),
                size_hint=(None, 1), width=dp(44), bold=True,
            )
            ti = TextInput(
                text="0", multiline=False,
                font_size=dp(THEME["font_size_body"]),
                background_color=c("bg_card"),
                foreground_color=c("text_primary"),
                cursor_color=c("accent"),
                halign="center",
                padding=[dp(4), dp(10)],
            )
            ti.bind(focus=lambda inst, focused: inst.select_all() if focused else None)

            plus = RoundedBtn(
                "+", bg=c("bg_card"), fg=c("accent"),
                size_hint=(None, 1), width=dp(44), bold=True,
            )

            def _make_adj(field, s):
                def _minus(*_):
                    try:
                        field.text = str(int(field.text or "0") - s)
                    except ValueError:
                        field.text = str(-s)
                def _plus(*_):
                    try:
                        field.text = str(int(field.text or "0") + s)
                    except ValueError:
                        field.text = str(s)
                return _minus, _plus

            adj_minus, adj_plus = _make_adj(ti, step)
            minus.bind(on_release=adj_minus)
            plus.bind(on_release=adj_plus)

            row.add_widget(minus)
            row.add_widget(ti)
            row.add_widget(plus)
            self._score_inputs.append(ti)
            inner.add_widget(row)

        inner.add_widget(v_spacer(12))
        inner.add_widget(PrimaryBtn("Next", cb=self._submit))
        inner.add_widget(v_spacer(4))
        inner.add_widget(SecondaryBtn("Back",
                                      cb=lambda: navigate("current_score", "right")))

        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)

    def _submit(self):
        app = App.get_running_app()
        try:
            round_scores = [int(ti.text or "0") for ti in self._score_inputs]
        except ValueError:
            Popup(
                title="Invalid score",
                content=make_label("Please enter whole numbers only.", size=14),
                size_hint=(0.8, 0.22),
            ).open()
            return

        app.apply_round_scores(round_scores)
        app.save_game()

        limit = app.selected_game["max_score"]
        if limit is not None and max(app.total_scores) >= limit:
            app.record_and_clear()
            navigate("final_score")
        else:
            navigate("current_score")


# ── Final Score ───────────────────────────────────────────────────────────────

# Random tag pools
_WIN_TAGS  = ["no sweat!", "le champion", "easy money", "good stuff",
              "the hawk", "masterclass", "tryhard..", "luck no skill",
              "the GOAT", "maillot jaune", "ez W", "damn daniel"]
_LOSE_TAGS = ["maybe next time", "nice try lol", "weird flex", "oof",
              "the dove", "bacon & beans", "tough times", "that was grim"]


class FinalScoreScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="final_score", **kw)

    def on_pre_enter(self):
        self._build()

    def _build(self):
        self.clear_widgets()
        app      = App.get_running_app()
        game     = app.selected_game
        scores   = app.total_scores
        names    = app.player_names
        limit    = game["max_score"]
        low_wins = game["low_score_wins"]

        # ── Olympic-style ranking (ties share a rank, next rank is skipped) ──
        ranking = compute_ranking(scores, names, low_wins)
        n       = len(ranking)

        # Find the rank of the last (worst) non-eliminated player for the
        # "last place" tag. If everyone is eliminated, use the last entry.
        last_rank = None
        for entry in reversed(ranking):
            if limit is None or entry["score"] < limit:
                last_rank = entry["rank"]
                break
        if last_rank is None and ranking:
            last_rank = ranking[-1]["rank"]

        # Find winner rank (first non-eliminated)
        winner_rank = None
        for entry in ranking:
            if limit is None or entry["score"] < limit:
                winner_rank = entry["rank"]
                break
        if winner_rank is None and ranking:
            winner_rank = ranking[0]["rank"]

        rank_txt   = {0: "1st", 1: "2nd", 2: "3rd"}
        rank_color = {0: c("gold"), 1: c("silver"), 2: c("bronze")}

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Final Scores"))

        inner = make_inner(spacing=4)
        inner.add_widget(make_label(game["name"],
                                    size=THEME["font_size_small"],
                                    color=c("text_muted"),
                                    size_hint_y=None, height=dp(22)))
        inner.add_widget(v_spacer(6))

        # Pick a single random tag per winner/loser group so tied players
        # that share a tag pool get the same quip (fairer and looks cleaner).
        win_tag  = random.choice(_WIN_TAGS)
        lose_tag = random.choice(_LOSE_TAGS)

        for entry in ranking:
            rank  = entry["rank"]
            score = entry["score"]
            name  = entry["name"]
            tied  = entry["tied"]
            over  = limit is not None and score >= limit
            is_win  = rank == winner_rank
            is_last = rank == last_rank and not over

            row = RoundedBox(
                bg_key="bg_card",
                orientation="horizontal",
                size_hint_y=None, height=dp(46),
                padding=[dp(10), 0], spacing=dp(6),
            )

            # Left indicator
            if over:
                ind, ind_col = "OUT", c("eliminated")
            elif rank in rank_txt:
                ind_suffix = "=" if tied else ""
                ind        = rank_txt[rank] + ind_suffix
                ind_col    = rank_color[rank]
            else:
                ind        = f"{rank + 1}."
                ind_col    = c("text_muted")

            row.add_widget(make_label(ind, size=11, color=ind_col,
                                      size_hint=(None, 1), width=dp(36),
                                      bold=(rank in rank_txt and not over)))

            name_color = c("eliminated") if over else c("text_primary")
            row.add_widget(make_label(name, halign="left", bold=True,
                                      size=THEME["font_size_body"],
                                      color=name_color))

            # Tag (right of name, before score)
            if over:
                tag_txt = lose_tag
                tag_col = c("eliminated")
            elif is_win:
                tag_txt = win_tag
                tag_col = c("gold")
            else:
                tag_txt = ""
                tag_col = c("text_muted")

            row.add_widget(make_label(tag_txt, size=10, color=tag_col,
                                      halign="right", italic=True,
                                      size_hint=(None, 1), width=dp(88)))

            sc_col = (c("eliminated") if over
                      else rank_color.get(rank, c("text_primary")))

            row.add_widget(make_label(str(score), size=18, bold=True,
                                      color=sc_col,
                                      size_hint=(None, 1), width=dp(50),
                                      halign="right"))
            inner.add_widget(row)
            inner.add_widget(v_spacer(4))

        inner.add_widget(v_spacer(14))
        inner.add_widget(PrimaryBtn("Play Again (same players)",
                                    cb=self._play_again))
        inner.add_widget(v_spacer(4))
        inner.add_widget(SecondaryBtn("Main Menu", cb=self._home))

        root.add_widget(wrap_scroll(inner))
        self.add_widget(root)

    def _play_again(self):
        app = App.get_running_app()
        app.init_new_game(app.player_names)
        navigate("current_score")

    def _home(self):
        App.get_running_app().delete_save()
        navigate("home", "right")


# =============================================================================
#  App
# =============================================================================

class SkorroApp(App):

    def build(self):
        self.selected_game = None
        self.player_names  = []
        self.total_scores  = []
        self.round_num     = 1
        self.rules_index   = 0

        # Bind Android back button / Escape key
        Window.bind(on_keyboard=_handle_back)

        self.sm = ScreenManager()
        for s in [
            HomeScreen(),
            InfoScreen(),
            RulesScreen(),
            RulesDetailScreen(),
            LeaderboardScreen(),
            WhichGameScreen(),
            AddPlayersScreen(),
            CurrentScoreScreen(),
            UpdateScoresScreen(),
            FinalScoreScreen(),
        ]:
            self.sm.add_widget(s)

        return self.sm

    # ── Game state ────────────────────────────────────────────────────────────

    def init_new_game(self, names):
        self.player_names  = names
        self.total_scores  = [0] * len(names)
        self.round_num     = 1
        self.save_game()

    def apply_round_scores(self, round_scores):
        """Add round scores and apply Yaniv halving if the game uses it."""
        use_halving = self.selected_game.get("yaniv_halving", False)
        for i, s in enumerate(round_scores):
            self.total_scores[i] += s
            if use_halving:
                self.total_scores[i] = apply_yaniv_halving(self.total_scores[i])
        self.round_num += 1

    def record_and_clear(self):
        """
        Write leaderboard entry then delete the save file.
        Skips if all scores are zero (no real play happened).
        """
        if not self.player_names or all(s == 0 for s in self.total_scores):
            self.delete_save()
            return

        low_wins = self.selected_game["low_score_wins"]
        record_game_result(self.player_names, self.total_scores, low_wins)
        self.delete_save()

    # ── Persistence ───────────────────────────────────────────────────────────

    def save_game(self):
        data = {
            "game_id":        self.selected_game["id"] if self.selected_game else None,
            "low_score_wins": self.selected_game.get("low_score_wins", True)
                              if self.selected_game else True,
            "player_names":   self.player_names,
            "total_scores":   self.total_scores,
            "round_num":      self.round_num,
        }
        try:
            with open(SAVE_FILE, "w") as f:
                json.dump(data, f)
        except Exception as e:
            print(f"[Skorro] save error: {e}")

    def load_game(self):
        if not os.path.exists(SAVE_FILE):
            return False
        try:
            with open(SAVE_FILE) as f:
                data = json.load(f)
            game_id = data.get("game_id")
            base = next((g for g in GAMES if g["id"] == game_id), GAMES[0])
            self.selected_game = dict(base)
            self.selected_game["low_score_wins"] = data.get(
                "low_score_wins", base["low_score_wins"])
            self.player_names = data["player_names"]
            self.total_scores = data["total_scores"]
            self.round_num    = data["round_num"]
            return True
        except Exception as e:
            print(f"[Skorro] load error: {e}")
            return False

    def delete_save(self):
        if os.path.exists(SAVE_FILE):
            try:
                os.remove(SAVE_FILE)
            except Exception:
                pass


if __name__ == "__main__":
    SkorroApp().run()