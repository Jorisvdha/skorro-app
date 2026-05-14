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
from kivy.utils import get_color_from_hex

from config import APP_ICON, APP_INFO_TEXT, GAMES, RULES, THEME

# ── Resolve theme colours once at startup ─────────────────────────────────────
C = {
    k: get_color_from_hex(v) if isinstance(v, str) and v.startswith("#") else v
    for k, v in THEME.items()
}
Window.clearcolor = C["bg_dark"]

SAVE_FILE        = "skorro_save.json"
LEADERBOARD_FILE = "skorro_leaderboard.json"
YANIV_HALVE_AT   = {50, 100, 150, 200}


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
      50  → 25,  100 → 50,  150 → 75,  200 → 100
    25/50/75/100 reached via halving are NOT halved again.
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


def record_game_result(player_names, ranked_names):
    """
    Update the leaderboard after a game.

    ranked_names — names ordered best → worst (index 0 = gold).

    Rules
    -----
    - Every player:  played += 1
    - Rank 0:        gold   += 1  (always)
    - Rank 1:        silver += 1  (only when 3+ players so 2nd is not last)
    - Rank 2:        bronze += 1  (only when 4+ players so 3rd is not last)
    - Last place:    losses += 1
    - All others:    nothing extra
    """
    n  = len(ranked_names)
    lb = load_leaderboard()

    for name in player_names:
        if name not in lb:
            lb[name] = {"played": 0, "gold": 0, "silver": 0, "bronze": 0, "losses": 0}
        # Migrate old saves that used "wins" instead of "gold"
        if "wins" in lb[name]:
            lb[name]["gold"] = lb[name].pop("wins")
        lb[name]["played"] += 1

    if n >= 1:
        lb[ranked_names[0]]["gold"] += 1
    if n >= 3:
        lb[ranked_names[1]]["silver"] += 1
    if n >= 4:
        lb[ranked_names[2]]["bronze"] += 1
    lb[ranked_names[-1]]["losses"] += 1

    save_leaderboard(lb)


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
#  All visible surfaces (cards, buttons, header bars) use canvas-drawn
#  RoundedRectangles so every platform renders rounded corners identically.
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
    Button whose background is a canvas-drawn RoundedRectangle.
    Kivy's default button skin is bypassed entirely so the button looks
    identical on desktop and Android.
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
            background_color=(0, 0, 0, 0),   # transparent — we paint manually
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
        """Update button colours at runtime (used by ToggleBtn)."""
        self._bg    = bg
        self._fg    = fg
        self.color  = fg
        self._redraw()


class ToggleBtn(RoundedBtn):
    """Two-state rounded button: selected = accent, unselected = card colour."""

    def __init__(self, text, selected=False, cb=None, **kw):
        kw.setdefault("height", dp(48))
        super().__init__(
            text=text,
            bg=c("accent")   if selected else c("bg_card"),
            fg=c("text_on_accent") if selected else c("text_muted"),
            cb=cb,
            bold=selected,
            **kw,
        )

    def set_selected(self, val):
        self.bold = val
        self.set_colors(
            c("accent") if val else c("bg_card"),
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
    kw.setdefault("size_hint", (None, None))
    kw.setdefault("size",      (dp(112), dp(32)))
    kw.setdefault("font_size", dp(THEME["font_size_small"]))
    return RoundedBtn(text, bg=c("bg_card"), fg=c("text_muted"),
                      radius=dp(10), cb=cb, bold=False, **kw)


def header_bar(title, right_widget=None):
    """Dark header bar with title on the left and an optional widget on the right."""
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
        bar.add_widget(right_widget)
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
    """
    A Label that sizes its own height to fit wrapped text.
    Useful for long blocks of text inside scrollable layouts.
    """
    kw.setdefault("font_size",  dp(THEME["font_size_body"]))
    kw.setdefault("color",      c("text_primary"))
    kw.setdefault("halign",     "left")
    kw.setdefault("valign",     "top")
    kw.setdefault("size_hint_y", None)
    widget = Label(text=str(text), **kw)

    def _resize(w, *_):
        w.text_size = (w.width, None)
        w.texture_update()
        w.height = w.texture_size[1] + dp(4)

    widget.bind(width=_resize, text=_resize)
    return widget


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

        # Centre the icon in a horizontal row using flex spacers
        img_row = BoxLayout(orientation="horizontal", size_hint_y=None, height=dp(72))
        img_row.add_widget(Widget())   # left flex spacer
        if os.path.exists(APP_ICON):
            img_row.add_widget(Image(
                source=APP_ICON,
                size_hint=(None, None),
                size=(dp(72), dp(72)),
                allow_stretch=True,
                keep_ratio=True,
                mipmap=True,
            ))
        img_row.add_widget(Widget())   # right flex spacer
        logo_col.add_widget(img_row)

        logo_col.add_widget(make_label(
            "Skorro", size=36, bold=True, halign="center",
            size_hint_y=None, height=dp(42),
        ))
        root.add_widget(logo_col)

        # Subtitle with fixed height so descenders are never clipped
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
        root.add_widget(SecondaryBtn("Leaderboard",   cb=lambda: navigate("leaderboard")))
        root.add_widget(v_spacer(4))
        root.add_widget(SecondaryBtn("Card Game Rules", cb=lambda: navigate("rules")))
        root.add_widget(v_spacer(4))
        root.add_widget(SecondaryBtn("Information",   cb=lambda: navigate("info")))
        root.add_widget(Widget())   # push content up

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

        # Build one button per rules entry.
        # Use a default-argument capture (idx=i) to avoid the late-binding
        # closure bug that would make every button open the last entry.
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


# ── Rules detail (per game) ───────────────────────────────────────────────────

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

            # Column header
            hdr = BoxLayout(size_hint_y=None, height=dp(26),
                            padding=[dp(10), 0], spacing=dp(4))
            hdr.add_widget(make_label("",     size=11, size_hint=(None, 1), width=dp(38)))
            hdr.add_widget(make_label("Name", size=11, color=c("text_muted"), halign="left"))
            for txt, col in [("GP", c("text_muted")), ("G", c("gold")),
                             ("S",  c("silver")),     ("B", c("bronze")),
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
                                          color=c("gold") if pos == 0 else c("text_primary")))
                for val, col in [(played, c("text_muted")), (gold,   c("gold")),
                                 (silver, c("silver")),     (bronze, c("bronze")),
                                 (losses, c("eliminated") if losses else c("text_muted"))]:
                    row.add_widget(make_label(str(val), size=13, color=col,
                                              bold=bool(val and col != c("text_muted")),
                                              size_hint=(None, 1), width=dp(28),
                                              halign="center"))
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

        # Default-argument capture prevents late-binding closure bug
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
            # Set the default
            app.selected_game["low_score_wins"] = True

        inner.add_widget(v_spacer(10))
        inner.add_widget(PrimaryBtn("Let's go!", cb=self._start))
        inner.add_widget(v_spacer(4))
        inner.add_widget(SecondaryBtn("Back", cb=lambda: navigate("which_game", "right")))

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

        # Danger = highest score when low wins, lowest score when high wins
        danger_score = max(scores) if low_wins else min(scores)

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar(
            f"{game['name']}  —  Round {app.round_num}",
            right_widget=SmallBtn("Main Menu", cb=self._go_home),
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
            f"Tap +/−  (step: {step})  or tap the number to type directly.",
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
                "−", bg=c("bg_card"), fg=c("accent"),
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
            # Select-all on focus so typing immediately replaces the value
            ti.bind(focus=lambda inst, focused: inst.select_all() if focused else None)

            plus = RoundedBtn(
                "+", bg=c("bg_card"), fg=c("accent"),
                size_hint=(None, 1), width=dp(44), bold=True,
            )

            # Default-argument capture avoids the late-binding closure bug
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

class FinalScoreScreen(Screen):
    def __init__(self, **kw):
        super().__init__(name="final_score", **kw)

    def on_pre_enter(self):
        self._build()

    def _build(self):
        self.clear_widgets()
        app       = App.get_running_app()
        game      = app.selected_game
        scores    = app.total_scores
        names     = app.player_names
        limit     = game["max_score"]
        low_wins  = game["low_score_wins"]

        # Sort best → worst
        ranking = sorted(zip(scores, names),
                         key=lambda x: x[0], reverse=not low_wins)

        # Winner = first non-eliminated entry
        winner_rank = next(
            (i for i, (s, _) in enumerate(ranking)
             if limit is None or s < limit),
            0,
        )

        rank_txt   = ["1st", "2nd", "3rd"]
        rank_color = [c("gold"), c("silver"), c("bronze")]

        root = BoxLayout(orientation="vertical")
        root.add_widget(header_bar("Final Scores"))

        inner = make_inner(spacing=4)
        inner.add_widget(make_label(game["name"],
                                    size=THEME["font_size_small"],
                                    color=c("text_muted"),
                                    size_hint_y=None, height=dp(22)))
        inner.add_widget(v_spacer(6))

        for rank, (score, name) in enumerate(ranking):
            over    = limit is not None and score >= limit
            is_win  = rank == winner_rank
            is_last = rank == len(ranking) - 1

            # All rows are the same compact height — no more variable heights
            row = RoundedBox(
                bg_key="bg_card",
                orientation="horizontal",
                size_hint_y=None, height=dp(46),
                padding=[dp(10), 0], spacing=dp(6),
            )

            # Left indicator: OUT / 1st / 2nd / 3rd / 4. 5. …
            if over:
                ind, ind_col = "OUT", c("eliminated")
            elif rank < 3:
                ind, ind_col = rank_txt[rank], rank_color[rank]
            else:
                ind, ind_col = f"{rank + 1}.", c("text_muted")

            row.add_widget(make_label(ind, size=11, color=ind_col,
                                      size_hint=(None, 1), width=dp(36),
                                      bold=rank < 3))

            # Player name (left-aligned, expands)
            name_color = c("eliminated") if over else c("text_primary")
            row.add_widget(make_label(name, halign="left", bold=True,
                                      size=THEME["font_size_body"],
                                      color=name_color))

            # Tag text sits to the RIGHT of the name, before the score
            if over:
                tag_txt = random.choice(["maybe next time", "nice try lol", "weird flex", "oof", "dove play", "bacon & beans", "tough times"])
                tag_col = c("eliminated")
            elif is_win:
                tag_txt = random.choice(["no sweat!","le champion","easy money","good stuff","hawk play","masterclass", "tryhard..", "luck no skill", "the GOAT", "maillot jaune", "ez W"])
                tag_col = c("gold")
            elif is_last and not over:
                tag_txt = random.choice(["maybe next time", "nice try lol", "weird flex", "oof", "dove play", "bacon & beans", "tough times"])
                tag_col = c("text_muted")
            else:
                tag_txt = ""
                tag_col = c("text_muted")

            row.add_widget(make_label(tag_txt, size=10, color=tag_col,
                                      halign="right", italic=True,
                                      size_hint=(None, 1), width=dp(80)))

            # Score (fixed width, right-aligned)
            sc_col = (c("eliminated") if over
                      else c("gold")   if rank == 0
                      else c("silver") if rank == 1
                      else c("bronze") if rank == 2
                      else c("text_primary"))

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
        Write leaderboard entry for the finished game then delete the save file.
        Call this immediately before navigating to FinalScoreScreen.
        Skip if all scores are still zero (no real play happened).
        """
        if not self.player_names or all(s == 0 for s in self.total_scores):
            self.delete_save()
            return

        low_wins = self.selected_game["low_score_wins"]
        ranking  = sorted(
            zip(self.total_scores, self.player_names),
            key=lambda x: x[0],
            reverse=not low_wins,
        )
        ranked_names = [name for _, name in ranking]
        record_game_result(self.player_names, ranked_names)
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
