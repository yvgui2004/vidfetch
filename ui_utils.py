"""
Desktop GUI styling utilities / 桌面 GUI 美化工具模块
====================================================
Includes: color palettes, window Mica effect, Treeview themes, popup menus, etc.

pip dependencies: pip install customtkinter pywinstyles

Usage / 用法:
    from ui_utils import (ThemeColors, CTkPopupMenu,
                          apply_window_effect, apply_treeview_theme,
                          create_card, create_sidebar_button, create_accent_button)
"""

import tkinter as tk
from tkinter import ttk
from typing import Optional, Callable

import customtkinter as ctk

try:
    import pywinstyles
    HAS_PYWINSTYLES = True
except ImportError:
    HAS_PYWINSTYLES = False


# ═══════════════════════════════════════════════════════
# 1. Color Palette / 配色方案
# ═══════════════════════════════════════════════════════

class ThemeColors:
    """Complete light/dark dual-theme color palette. / 明/暗双主题完整色板。

    Usage / 用法:
        c = ThemeColors.palette(dark=True)   # dark / 暗色
        c = ThemeColors.palette(dark=False)  # light / 亮色
    """
    @staticmethod
    def palette(dark: bool = False) -> dict:
        if dark:
            return {
                "bg": "#0d1117",
                "surface": "#161b22",
                "card": "#1c2333",
                "border": "#30363d",
                "fg": "#e6edf3",
                "fg2": "#8b949e",
                "accent": "#58a6ff",
                "accent_hover": "#4090e0",
                "accent_text": "#ffffff",
                "danger": "#f85149",
                "danger_hover": "#da3633",
                "success": "#3fb950",
                "header_bg": "#161b22",
                "header_fg": "#e6edf3",
                "row_alt": "#0d1117",
                "row": "#0d1117",
                "select_bg": "#1f6feb",
                "select_fg": "#ffffff",
                "input_bg": "#0d1117",
                "input_fg": "#e6edf3",
                "button_bg": "#21262d",
                "button_hover": "#30363d",
                "button_active": "#30363d",
                "separator": "#30363d",
                "row_hover": "#1a2332",
            }
        else:
            return {
                "bg": "#fafbfc",
                "surface": "#f0f2f5",
                "card": "#ffffff",
                "border": "#d0d7de",
                "fg": "#1c1e29",
                "fg2": "#656d76",
                "accent": "#4263eb",
                "accent_hover": "#3451d1",
                "accent_text": "#ffffff",
                "danger": "#cf222e",
                "danger_hover": "#a40e26",
                "success": "#1a7f37",
                "header_bg": "#f0f2f5",
                "header_fg": "#3d4153",
                "row_alt": "#f6f8fa",
                "row": "#ffffff",
                "select_bg": "#4263eb",
                "select_fg": "#ffffff",
                "input_bg": "#ffffff",
                "input_fg": "#1c1e29",
                "button_bg": "#f0f2f5",
                "button_hover": "#d0d7de",
                "button_active": "#c4cad3",
                "separator": "#d0d7de",
                "row_hover": "#eef1f7",
            }


# ═══════════════════════════════════════════════════════
# 2. Window Mica / Acrylic Effect / 窗口 Mica 效果
# ═══════════════════════════════════════════════════════

def apply_window_effect(window: tk.Toplevel, dark: bool = False, bg_color: str = "#0d1117"):
    """Apply Windows 11 title bar effect to any window. / 对任意窗口应用 Windows 11 标题栏效果。

    Args:
        window:   Target tk.Toplevel or ctk.CTk
        dark:     True = dark title bar, False = light
        bg_color: Title bar background color (match window background)
    """
    if not HAS_PYWINSTYLES:
        return
    try:
        if dark:
            pywinstyles.apply_style(window, "dark")
        else:
            pywinstyles.apply_style(window, "normal")
        pywinstyles.change_header_color(window, bg_color)
    except Exception:
        pass


def apply_mica(window: tk.Toplevel, dark: bool = False, bg_color: str = "#0d1117"):
    """apply_window_effect 的别名, 语义更明确。"""
    apply_window_effect(window, dark, bg_color)


# ═══════════════════════════════════════════════════════
# 3. Treeview Theme (ttk) / Treeview 主题
# ═══════════════════════════════════════════════════════

def apply_treeview_theme(tree: ttk.Treeview, c: dict, font_family: str = "微软雅黑",
                         font_size: int = 14, row_height: int = 40):
    """美化 ttk.Treeview: 行高、表头、选中态、交替行色。

    参数:
        tree:        目标 ttk.Treeview
        c:           ThemeColors.palette() 返回的色板
        font_family: 字体名
        font_size:   字号
        row_height:  行高 (px)
    """
    style = ttk.Style()
    style.theme_use('clam')

    style.configure('.',
                    background=c['bg'],
                    foreground=c['fg'],
                    fieldbackground=c['input_bg'],
                    font=(font_family, font_size))

    style.configure('TFrame', background=c['bg'], borderwidth=0, relief='flat')

    style.configure('Treeview',
                    background=c['row'],
                    foreground=c['fg'],
                    fieldbackground=c['row'],
                    rowheight=row_height,
                    borderwidth=0,
                    relief='flat')

    style.configure('Treeview.Heading',
                    background=c['header_bg'],
                    foreground=c['header_fg'],
                    relief='flat',
                    borderwidth=0,
                    padding=(12, 10),
                    font=(font_family, font_size, 'bold'))

    style.map('Treeview.Heading',
              background=[('active', c['button_hover'])],
              bordercolor=[('!focus', c['header_bg'])])

    style.map('Treeview',
              background=[('selected', c['select_bg'])],
              foreground=[('selected', c['select_fg'])],
              bordercolor=[('!focus', c['row']), ('focus', c['row'])])

    style.layout('Treeview', [('Treeview.treearea', {'sticky': 'nswe', 'border': '0'})])

    # Tag configuration for alternating rows
    tree.tag_configure('row', background=c['row'])
    tree.tag_configure('alt', background=c['row_alt'])
    tree.tag_configure('hover', background=c['row_hover'])

    # Disable keyboard navigation (optional)
    try:
        tree.tk.eval('bind Treeview <KeyPress> {}')
    except Exception:
        pass

    # Set ctk appearance mode to match
    ctk.set_appearance_mode("dark" if c['bg'] == "#0d1117" else "light")


# ═══════════════════════════════════════════════════════
# 4. Custom CTk Popup Menu / 自定义右键菜单
# ═══════════════════════════════════════════════════════

class CTkPopupMenu:
    """Modern rounded popup menu, replaces tk.Menu. / 现代圆角弹出菜单，替代 tk.Menu。

    Usage / 用法:
        menu = CTkPopupMenu(parent_window, ThemeColors.palette(dark=True),
                            font_family="微软雅黑", font_size=14)
        menu.add_command(label="Open File", icon="📄", command=open_file)
        menu.add_separator()
        menu.add_command(label="Delete", icon="🗑", command=delete, danger=True)
        menu.popup(x, y)
    """

    def __init__(self, parent: tk.Widget, c: dict = None,
                 font_family: str = "微软雅黑", font_size: int = 14):
        if c is None:
            c = ThemeColors.palette(dark=False)
        self.parent = parent
        self.c = c
        self.font_family = font_family
        self.font_size = font_size
        self._win: Optional[tk.Toplevel] = None
        self._items: list = []
        self._bind_id: Optional[str] = None

    def add_command(self, label: str, command: Callable, icon: str = "",
                    danger: bool = False, disabled: bool = False):
        """添加菜单项。"""
        self._items.append({
            'type': 'command',
            'label': label,
            'command': command,
            'icon': icon,
            'danger': danger,
            'disabled': disabled,
        })

    def add_separator(self):
        """添加分割线。"""
        self._items.append({'type': 'separator'})

    def popup(self, x: int, y: int):
        """在屏幕坐标 (x, y) 弹出菜单。"""
        self._show(x, y)

    # ── 内部实现 ──

    def _show(self, x, y):
        c = self.c

        self._win = tk.Toplevel(self.parent)
        self._win.overrideredirect(True)
        self._win.attributes('-topmost', True)
        self._win.withdraw()

        outer = ctk.CTkFrame(self._win, fg_color=c['border'], corner_radius=10)
        outer.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        inner = ctk.CTkFrame(outer, fg_color=c['card'], corner_radius=9)
        inner.pack(fill=tk.BOTH, expand=True, padx=1, pady=1)

        for item in self._items:
            if item['type'] == 'separator':
                sep = ctk.CTkFrame(inner, height=1, fg_color=c['border'], corner_radius=0)
                sep.pack(fill=tk.X, padx=10, pady=4)
            else:
                self._create_menu_item(inner, item)

        self._win.bind('<FocusOut>', lambda e: self._dismiss())
        self._win.bind('<Escape>', lambda e: self._dismiss())

        self._win.update_idletasks()
        w = self._win.winfo_reqwidth()
        h = self._win.winfo_reqheight()

        screen_w = self.parent.winfo_screenwidth()
        screen_h = self.parent.winfo_screenheight()
        if x + w > screen_w:
            x = screen_w - w - 4
        if y + h > screen_h:
            y = screen_h - h - 4
        x = max(4, x)
        y = max(4, y)

        self._win.geometry(f"+{x}+{y}")
        self._win.deiconify()

        self._bind_id = self.parent.bind('<Button-1>', lambda e: self._dismiss_global(e), add='+')

    def _create_menu_item(self, parent, item):
        c = self.c
        fg = c['danger'] if item['danger'] else c['fg']
        hover_bg = c['danger_hover'] if item['danger'] else c['accent']
        state = "disabled" if item['disabled'] else "normal"
        label = f"  {item['icon']}  {item['label']}" if item['icon'] else f"  {item['label']}"

        btn = ctk.CTkButton(
            parent,
            text=label,
            font=(self.font_family, self.font_size),
            fg_color="transparent",
            hover_color=hover_bg,
            text_color=fg,
            text_color_disabled=c['fg2'],
            corner_radius=6,
            height=34,
            anchor="w",
            state=state,
            command=item['command'] if not item['disabled'] else None,
        )
        btn.pack(fill=tk.X, padx=6, pady=2)

    def _dismiss(self, event=None):
        self._destroy()

    def _dismiss_global(self, event=None):
        if self._win and event:
            wx = self._win.winfo_rootx()
            wy = self._win.winfo_rooty()
            ww = self._win.winfo_width()
            wh = self._win.winfo_height()
            if wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh:
                return
        self._destroy()

    def _destroy(self):
        if self._bind_id:
            try:
                self.parent.unbind('<Button-1>', self._bind_id)
            except Exception:
                pass
            self._bind_id = None
        if self._win:
            try:
                self._win.destroy()
            except Exception:
                pass
            self._win = None


# ═══════════════════════════════════════════════════════
# 5. Component Factory / 快捷组件工厂
# ═══════════════════════════════════════════════════════

def create_card(parent, c: dict, corner_radius: int = 10, **pack_kw) -> ctk.CTkFrame:
    """创建带边框的卡片容器。"""
    card = ctk.CTkFrame(parent, fg_color=c['card'], corner_radius=corner_radius,
                        border_width=1, border_color=c['border'])
    if pack_kw:
        card.pack(**pack_kw)
    return card


def create_separator(parent, c: dict, horizontal: bool = True, **pack_kw) -> ctk.CTkFrame:
    """创建分割线。"""
    if horizontal:
        sep = ctk.CTkFrame(parent, height=1, corner_radius=0, fg_color=c['border'])
    else:
        sep = ctk.CTkFrame(parent, width=1, corner_radius=0, fg_color=c['border'])
    if pack_kw:
        sep.pack(**pack_kw)
    return sep


def create_sidebar_button(parent, text: str, c: dict, command: Callable,
                          font_family: str = "微软雅黑", font_size: int = 14,
                          accent: bool = False, bold: bool = False, **pack_kw) -> ctk.CTkButton:
    """创建侧边栏风格按钮 (自动配色)。"""
    if accent:
        btn = ctk.CTkButton(parent, text=text, command=command,
                            font=(font_family, font_size, 'bold' if bold else 'normal'),
                            fg_color=c['accent'], hover_color=c['accent_hover'],
                            text_color=c['accent_text'],
                            corner_radius=8, height=38)
    else:
        btn = ctk.CTkButton(parent, text=text, command=command,
                            font=(font_family, font_size, 'bold' if bold else 'normal'),
                            fg_color=c['button_bg'], hover_color=c['button_hover'],
                            text_color=c['fg'],
                            corner_radius=8, height=36)
    if pack_kw:
        btn.pack(**pack_kw)
    return btn


def create_label(parent, text: str, c: dict, role: str = "fg",
                 font_family: str = "微软雅黑", font_size: int = 14,
                 bold: bool = False, offset: int = 0, **pack_kw) -> ctk.CTkLabel:
    """创建标签 (自动配色)。"""
    lbl = ctk.CTkLabel(parent, text=text,
                       text_color=c[role],
                       font=(font_family, font_size + offset, 'bold' if bold else 'normal'),
                       anchor="w")
    if pack_kw:
        lbl.pack(**pack_kw)
    return lbl


def create_entry(parent, variable, c: dict,
                 font_family: str = "微软雅黑", font_size: int = 14,
                 width: int = 200, **pack_kw) -> ctk.CTkEntry:
    """创建输入框 (自动配色 + 边框)。"""
    entry = ctk.CTkEntry(parent, textvariable=variable,
                         fg_color=c['input_bg'], text_color=c['fg'],
                         font=(font_family, font_size),
                         corner_radius=8, border_width=1,
                         border_color=c['border'], width=width)
    if pack_kw:
        entry.pack(**pack_kw)
    return entry


# ═══════════════════════════════════════════════════════
# 6. General Helpers / 通用辅助
# ═══════════════════════════════════════════════════════

def _lighten(hex_color: str, factor: float = 0.1) -> str:
    """将 hex 颜色变亮。"""
    if not hex_color or not hex_color.startswith('#'):
        return hex_color or '#000000'
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f"#{r:02x}{g:02x}{b:02x}"


def _darken(hex_color: str, factor: float = 0.1) -> str:
    """将 hex 颜色变暗。"""
    if not hex_color or not hex_color.startswith('#'):
        return hex_color or '#000000'
    hex_color = hex_color.lstrip('#')
    r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return f"#{r:02x}{g:02x}{b:02x}"


def center_window(window: tk.Toplevel):
    """将窗口居中显示。"""
    window.update_idletasks()
    w = window.winfo_width()
    h = window.winfo_height()
    sw = window.winfo_screenwidth()
    sh = window.winfo_screenheight()
    x = (sw - w) // 2
    y = (sh - h) // 2
    window.geometry(f"+{x}+{y}")
