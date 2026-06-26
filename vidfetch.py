"""
VidFetch — 批量视频下载器
输入多个视频网址，按预设画质自动获取格式并下载合并。
依赖: pip install customtkinter yt-dlp pywinstyles
"""

import os
import re
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path

import customtkinter as ctk
import yt_dlp

from ui_utils import (
    ThemeColors, CTkPopupMenu,
    apply_window_effect, apply_treeview_theme,
    create_card, create_label, create_separator,
    create_entry, center_window,
)

# ═══════════════════════════════════════════════════════════
# 画质预设 → yt-dlp 格式选择器
# ═══════════════════════════════════════════════════════════

PRESETS = {
    "🎯 最高画质+音质":     "bestvideo+bestaudio/best",
    "📺 1080p + 最佳音质":  "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
    "📺 720p + 最佳音质":   "bestvideo[height<=720]+bestaudio/best[height<=720]",
    "🎵 仅最高音频":         "bestaudio/best",
}

STATUS_ICONS = {
    "waiting":     "⏳",
    "fetching":    "🔍",
    "downloading": "⬇",
    "merging":     "🔗",
    "done":        "✅",
    "error":       "❌",
    "skipped":     "⏭",
}

STATUS_COLORS = {
    "done":  "#3fb950",
    "error": "#f85149",
    "active": "#58a6ff",
}

MAX_CONCURRENT = 3  # 同时下载的最大数量


# ═══════════════════════════════════════════════════════════
# 主应用
# ═══════════════════════════════════════════════════════════

class VidFetchApp:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("VidFetch — 批量视频下载器")
        self.root.geometry("1150x720")
        self.root.minsize(950, 550)

        # 图标
        icon_path = Path(__file__).parent / "vidfetch.ico"
        if icon_path.exists():
            self.root.iconbitmap(default=str(icon_path))

        # 主题
        self.dark = False
        self.c = ThemeColors.palette(dark=self.dark)
        self.f = "微软雅黑"
        self.s = 13

        # ── 应用状态 ──
        self.queue = []               # 下载队列 list[dict]
        self.batch_running = False
        self.batch_cancelled = False
        self.cookies_path = ""
        self.output_dir = ""

        # 格式预览状态（为选中队列项展示）
        self.formats = []
        self.video_formats = []
        self.audio_formats = []
        self.format_id_to_item = {}
        self.best_video_id = None
        self.best_audio_id = None
        self.preview_queue_index = -1  # 当前预览的队列项索引
        self._url_placeholder_shown = False

        self._build_ui()
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        # 全局左键监听：有右键菜单时，点击任意位置关闭菜单
        self._current_popup = None
        self.root.bind_all('<Button-1>', self._on_global_click, add='+')
        self.root.bind_all('<Button-3>', self._on_global_click, add='+')

        apply_window_effect(self.root, dark=self.dark, bg_color=self.c['bg'])
        center_window(self.root)
        self.root.mainloop()

    # ═══════════════════════════════════════════════════════
    # UI 构建
    # ═══════════════════════════════════════════════════════

    def _build_ui(self):
        c = self.c
        self.root.configure(fg_color=c['bg'])
        self.root.grid_columnconfigure(0, weight=1)
        self.root.grid_rowconfigure(0, weight=1)

        # ── 主容器 ──
        main = ctk.CTkFrame(self.root, fg_color="transparent")
        main.grid(row=0, column=0, sticky='nsew', padx=14, pady=(10, 6))
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self._build_sidebar(main)
        self._build_right_panel(main)

    def _build_sidebar(self, parent):
        """左侧栏：预设 + URL 列表 + 按钮 + Cookies"""
        c = self.c
        f = self.f
        s = self.s

        sidebar = ctk.CTkFrame(parent, width=290, fg_color=c['surface'], corner_radius=10)
        sidebar.grid(row=0, column=0, sticky='nsw', padx=(0, 10))
        sidebar.grid_propagate(False)
        sidebar.grid_rowconfigure(3, weight=1)  # URL text area stretches
        sidebar.grid_rowconfigure(6, weight=1)  # Cookies text area stretches

        # ── 画质预设 ──
        create_label(sidebar, "🎯 画质预设", c, role="fg", font_family=f,
                    font_size=s, bold=True) \
            .pack(fill=tk.X, padx=14, pady=(14, 4))

        preset_keys = list(PRESETS.keys())
        self.preset_var = tk.StringVar(value=preset_keys[0])
        self.combo_preset = ctk.CTkComboBox(
            sidebar, variable=self.preset_var, values=preset_keys,
            state="readonly", font=(f, s - 1), corner_radius=8,
            fg_color=c['input_bg'], text_color=c['fg'],
            border_width=1, border_color=c['border'],
            button_color=c['accent'], button_hover_color=c['accent_hover'],
            dropdown_fg_color=c['card'], dropdown_text_color=c['fg'],
            dropdown_hover_color=c['row_hover'])
        self.combo_preset.pack(fill=tk.X, padx=14, pady=(0, 2))

        # 同时下载数量选择 — 用分段按钮替代下拉框，更直观
        create_label(sidebar, "⚡ 同时下载", c, role="fg", font_family=f,
                    font_size=s, bold=True) \
            .pack(fill=tk.X, padx=14, pady=(8, 4))

        self.max_concurrent = MAX_CONCURRENT
        self.concurrent_var = tk.IntVar(value=MAX_CONCURRENT)
        self._conc_btns = []

        seg_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        seg_frame.pack(fill=tk.X, padx=14, pady=(0, 4))

        for n in (1, 2, 3, 4, 5, 6):
            def make_cmd(val):
                return lambda: self._set_concurrent(val)
            btn = ctk.CTkButton(
                seg_frame, text=str(n), width=36, height=30,
                font=(f, s - 1),
                fg_color=c['accent'] if n == MAX_CONCURRENT else c['button_bg'],
                hover_color=c['accent_hover'] if n == MAX_CONCURRENT else c['button_hover'],
                text_color=c['accent_text'] if n == MAX_CONCURRENT else c['fg'],
                corner_radius=6,
                command=make_cmd(n))
            btn.pack(side=tk.LEFT, padx=(0, 2))
            self._conc_btns.append((n, btn))

        create_separator(sidebar, c).pack(fill=tk.X, padx=14)

        # ── 批量网址 ──
        create_label(sidebar, "📋 批量网址", c, role="fg", font_family=f,
                    font_size=s, bold=True) \
            .pack(fill=tk.X, padx=14, pady=(12, 4))

        self.url_text = ctk.CTkTextbox(
            sidebar, wrap="word", fg_color=c['input_bg'], text_color=c['fg'],
            font=(f, s), corner_radius=8, border_width=1, border_color=c['border'])
        self.url_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 6))
        self.url_text.bind('<FocusIn>', self._clear_url_placeholder)
        self.url_text.bind('<Button-1>', self._clear_url_placeholder)
        # 占位提示
        self.url_text.insert('1.0', "")
        self._show_url_placeholder()

        # ── 按钮组 ──
        btn_row1 = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_row1.pack(fill=tk.X, padx=14, pady=(4, 4))
        btn_row1.grid_columnconfigure(0, weight=1)
        btn_row1.grid_columnconfigure(1, weight=1)

        ctk.CTkButton(btn_row1, text="📋 粘贴网址", width=120, height=34,
                      fg_color="#d4a017", hover_color="#b8860b",
                      text_color="#ffffff", font=(f, s - 1), corner_radius=8,
                      command=self._paste_urls) \
            .grid(row=0, column=0, padx=(0, 4), sticky='ew')
        self.btn_add = ctk.CTkButton(
            btn_row1, text="➕ 添加到队列", width=120, height=34,
            fg_color=c['accent'], hover_color=c['accent_hover'],
            text_color=c['accent_text'], font=(f, s - 1), corner_radius=8,
            command=self._add_to_queue)
        self.btn_add.grid(row=0, column=1, padx=(4, 0), sticky='ew')

        btn_row2 = ctk.CTkFrame(sidebar, fg_color="transparent")
        btn_row2.pack(fill=tk.X, padx=14, pady=(4, 0))
        btn_row2.grid_columnconfigure(0, weight=1)
        btn_row2.grid_columnconfigure(1, weight=1)

        self.btn_start = ctk.CTkButton(
            btn_row2, text="▶ 开始下载", width=120, height=34,
            fg_color=c['success'], hover_color="#2d8a46",
            text_color="#ffffff", font=(f, s - 1, 'bold'), corner_radius=8,
            command=self._start_batch)
        self.btn_start.grid(row=0, column=0, padx=(0, 4), sticky='ew')

        self.btn_clear = ctk.CTkButton(
            btn_row2, text="🗑 清空队列", width=120, height=34,
            fg_color=c['danger'], hover_color=c['danger_hover'],
            text_color="#ffffff", font=(f, s - 1), corner_radius=8,
            command=self._clear_queue)
        self.btn_clear.grid(row=0, column=1, padx=(4, 0), sticky='ew')

        create_separator(sidebar, c).pack(fill=tk.X, padx=14, pady=(10, 0))

        # ── Cookies ──
        cookie_header = ctk.CTkFrame(sidebar, fg_color="transparent")
        cookie_header.pack(fill=tk.X, padx=14, pady=(10, 4))
        create_label(cookie_header, "🍪 Cookies（可选）", c, role="fg2", font_family=f,
                    font_size=s - 1) \
            .pack(side=tk.LEFT)
        ctk.CTkButton(cookie_header, text="📋", width=32, height=26,
                      fg_color=c['button_bg'], hover_color=c['button_hover'],
                      text_color=c['fg'], corner_radius=6,
                      command=self._paste_cookies) \
            .pack(side=tk.RIGHT)

        self.cookies_text = ctk.CTkTextbox(
            sidebar, wrap="word", fg_color=c['input_bg'], text_color=c['fg'],
            font=(f, s - 1), corner_radius=8, border_width=1, border_color=c['border'])
        self.cookies_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(0, 14))

    def _build_right_panel(self, parent):
        """右侧：队列 + 格式预览 + 日志"""
        c = self.c
        f = self.f
        s = self.s

        self.right = ctk.CTkFrame(parent, fg_color="transparent")
        self.right.grid(row=0, column=1, sticky='nsew')
        self.right.grid_columnconfigure(0, weight=1)
        self.right.grid_rowconfigure(1, weight=1)   # 队列表格可拉伸
        self.right.grid_rowconfigure(2, weight=1)   # 格式预览（始终展开）
        self.right.grid_rowconfigure(3, weight=0)   # 日志

        # ── 队列区域 ──
        queue_card = create_card(self.right, c)
        queue_card.grid(row=0, column=0, sticky='ew', pady=(0, 8))
        queue_card.grid_columnconfigure(0, weight=1)

        # 标题栏
        qheader = ctk.CTkFrame(queue_card, fg_color="transparent")
        qheader.pack(fill=tk.X, padx=14, pady=(10, 6))

        create_label(qheader, "📦 下载队列", c, role="fg", font_family=f,
                    font_size=s, bold=True).pack(side=tk.LEFT)

        self.lbl_queue_count = create_label(qheader, "(空)", c, role="fg2",
                                            font_family=f, font_size=s - 1)
        self.lbl_queue_count.pack(side=tk.LEFT, padx=(8, 0))

        # 总进度
        self.overall_bar = ctk.CTkProgressBar(
            queue_card, mode='determinate', height=6, corner_radius=3)
        self.overall_bar.pack(fill=tk.X, padx=14, pady=(0, 4))
        self.overall_bar.set(0)

        self.lbl_overall = create_label(
            queue_card, "就绪 — 请添加网址到队列", c, role="fg2",
            font_family=f, font_size=s - 2)
        self.lbl_overall.pack(fill=tk.X, padx=14, pady=(0, 8))

        # ── 队列表格 ──
        table_frame = ctk.CTkFrame(self.right, fg_color="transparent")
        table_frame.grid(row=1, column=0, sticky='nsew', pady=(0, 8))
        table_frame.grid_rowconfigure(0, weight=1)
        table_frame.grid_columnconfigure(0, weight=1)

        columns = ("status_icon", "index", "title", "progress", "size")
        self.queue_tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode='browse')
        self.queue_tree.heading("status_icon", text="")
        self.queue_tree.heading("index", text="#")
        self.queue_tree.heading("title", text="标题")
        self.queue_tree.heading("progress", text="进度")
        self.queue_tree.heading("size", text="大小")

        self.queue_tree.column("status_icon", width=36, anchor='center', stretch=False)
        self.queue_tree.column("index", width=36, anchor='center', stretch=False)
        self.queue_tree.column("title", width=360, anchor='w')
        self.queue_tree.column("progress", width=100, anchor='center')
        self.queue_tree.column("size", width=80, anchor='center')

        apply_treeview_theme(self.queue_tree, c, font_family=f, font_size=s - 1, row_height=34)

        # 状态标签颜色
        self.queue_tree.tag_configure('done', foreground=STATUS_COLORS['done'])
        self.queue_tree.tag_configure('error', foreground=STATUS_COLORS['error'])
        self.queue_tree.tag_configure('active', foreground=STATUS_COLORS['active'])
        self.queue_tree.tag_configure('waiting', foreground=c['fg2'])

        scrollbar = ctk.CTkScrollbar(table_frame, orientation="vertical",
                                     command=self.queue_tree.yview)
        self.queue_tree.configure(yscrollcommand=scrollbar.set)
        self.queue_tree.grid(row=0, column=0, sticky='nsew')
        scrollbar.grid(row=0, column=1, sticky='ns', padx=(2, 0))

        # 右键菜单
        self.queue_tree.bind('<ButtonRelease-1>', self._on_queue_select)
        self._bind_queue_context_menu()

        # ── 格式预览（可折叠）──
        self._build_format_preview(self.right)

        # ── 日志 ──
        log_card = create_card(self.right, c)
        log_card.grid(row=3, column=0, sticky='ew')
        self.log_text = ctk.CTkTextbox(
            log_card, wrap="word", height=65,
            fg_color=c['input_bg'], text_color=c['fg'],
            font=(f, s - 1), corner_radius=8, border_width=0)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=14, pady=(8, 8))
        self.log_text.configure(state="disabled")

    def _build_format_preview(self, parent):
        """可折叠的格式预览卡片"""
        c = self.c
        f = self.f
        s = self.s

        # 外层容器
        self.preview_container = ctk.CTkFrame(parent, fg_color="transparent")
        self.preview_container.grid(row=2, column=0, sticky='nsew', pady=(0, 8))
        self.preview_container.grid_columnconfigure(0, weight=1)
        self.preview_container.grid_rowconfigure(1, weight=1)

        # 预览卡片 — 始终展开
        self.preview_card = create_card(self.preview_container, c)
        self.preview_card.pack(fill=tk.BOTH, expand=True)

        # 标题行
        title_row = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        title_row.pack(fill=tk.X, padx=12, pady=(10, 4))

        self.lbl_title = create_label(title_row, "", c, role="fg",
                                      font_family=f, font_size=s, bold=True)
        self.lbl_title.pack(side=tk.LEFT)

        self.lbl_preview_title = create_label(title_row, "", c, role="fg2",
                                              font_family=f, font_size=s - 2)
        self.lbl_preview_title.pack(side=tk.LEFT, padx=(8, 0))

        # 格式选择行（仅展示最佳视频/音频）
        combo_row = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        combo_row.pack(fill=tk.X, padx=12, pady=(0, 4))

        create_label(combo_row, "🎬 视频", c, role="fg2", font_family=f,
                    font_size=s - 2).pack(side=tk.LEFT, padx=(0, 4))
        self.video_fmt_var = tk.StringVar(value="—")
        self.combo_video = ctk.CTkComboBox(
            combo_row, variable=self.video_fmt_var, values=["—"], state="readonly",
            font=(f, s - 2), corner_radius=6, width=160)
        self.combo_video.pack(side=tk.LEFT, padx=(0, 14))
        self.combo_video.bind('<KeyPress>', lambda e: 'break')

        create_label(combo_row, "🎵 音频", c, role="fg2", font_family=f,
                    font_size=s - 2).pack(side=tk.LEFT, padx=(0, 4))
        self.audio_fmt_var = tk.StringVar(value="—")
        self.combo_audio = ctk.CTkComboBox(
            combo_row, variable=self.audio_fmt_var, values=["—"], state="readonly",
            font=(f, s - 2), corner_radius=6, width=160)
        self.combo_audio.pack(side=tk.LEFT)
        self.combo_audio.bind('<KeyPress>', lambda e: 'break')

        # 格式表格
        fmt_table_frame = ctk.CTkFrame(self.preview_card, fg_color="transparent")
        fmt_table_frame.pack(fill=tk.BOTH, expand=True, padx=12, pady=(4, 8))
        fmt_table_frame.grid_rowconfigure(0, weight=1)
        fmt_table_frame.grid_columnconfigure(0, weight=1)

        columns = ("mark", "id", "type", "resolution", "codec", "bitrate", "size", "note")
        self.fmt_tree = ttk.Treeview(
            fmt_table_frame, columns=columns, show="headings", selectmode='browse',
            height=8)
        self.fmt_tree.heading("mark", text="")
        self.fmt_tree.heading("id", text="ID")
        self.fmt_tree.heading("type", text="类型")
        self.fmt_tree.heading("resolution", text="分辨率")
        self.fmt_tree.heading("codec", text="编码")
        self.fmt_tree.heading("bitrate", text="码率")
        self.fmt_tree.heading("size", text="大小")
        self.fmt_tree.heading("note", text="备注")

        self.fmt_tree.column("mark", width=30, anchor='center', stretch=False)
        self.fmt_tree.column("id", width=50, anchor='center')
        self.fmt_tree.column("type", width=55, anchor='center')
        self.fmt_tree.column("resolution", width=90, anchor='center')
        self.fmt_tree.column("codec", width=100, anchor='center')
        self.fmt_tree.column("bitrate", width=75, anchor='center')
        self.fmt_tree.column("size", width=75, anchor='center')
        self.fmt_tree.column("note", width=100, anchor='w')

        apply_treeview_theme(self.fmt_tree, c, font_family=f, font_size=s - 2, row_height=30)
        self.fmt_tree.tag_configure('best', foreground='#e6a817')
        self.fmt_tree.tag_configure('selected', foreground='#2563eb')
        self.fmt_tree.tag_configure('best_sel', foreground='#e6a817')

        # 滚动条
        fmt_scroll = ctk.CTkScrollbar(fmt_table_frame, orientation="vertical",
                                      command=self.fmt_tree.yview)
        self.fmt_tree.configure(yscrollcommand=fmt_scroll.set)
        self.fmt_tree.grid(row=0, column=0, sticky='nsew')
        fmt_scroll.grid(row=0, column=1, sticky='ns', padx=(2, 0))

        self.fmt_tree.bind('<ButtonRelease-1>', self._on_fmt_tree_select)
        self.fmt_tree.bind('<Double-1>', self._on_fmt_tree_select)

    # ═══════════════════════════════════════════════════════
    # URL 输入辅助
    # ═══════════════════════════════════════════════════════

    def _show_url_placeholder(self):
        """在 URL 文本区显示占位提示"""
        current = self.url_text.get('1.0', 'end-1c').strip()
        if not current:
            self.url_text.insert('1.0', "粘贴视频网址，自动识别…\n换行/空格/紧挨着都可以\n支持 YouTube / B站等 yt-dlp 兼容站点")
            self.url_text.configure(text_color=self.c['fg2'])
            self._url_placeholder_shown = True
        else:
            self._url_placeholder_shown = False

    def _clear_url_placeholder(self, event=None):
        """用户点击时清除占位文字"""
        if getattr(self, '_url_placeholder_shown', False):
            self.url_text.delete('1.0', tk.END)
            self.url_text.configure(text_color=self.c['fg'])
            self._url_placeholder_shown = False

    def _get_urls_from_input(self):
        """从 URL 文本框提取 URL 列表（按 http 边界智能分割，去空、去重）"""
        raw = self.url_text.get('1.0', 'end-1c').strip()
        if getattr(self, '_url_placeholder_shown', False):
            return []
        # 按 http(s):// 边界分割，处理紧挨、空格、换行等各种情况
        segments = re.split(r'(?=https?://)', raw)
        seen = set()
        urls = []
        for seg in segments:
            u = seg.strip()
            if u and u.startswith('http') and u not in seen:
                urls.append(u)
                seen.add(u)
        return urls

    def _set_concurrent(self, val):
        """切换同时下载数量，更新按钮高亮"""
        self.max_concurrent = val
        self.concurrent_var.set(val)
        c = self.c
        for n, btn in self._conc_btns:
            if n == val:
                btn.configure(fg_color=c['accent'], hover_color=c['accent_hover'],
                            text_color=c['accent_text'])
            else:
                btn.configure(fg_color=c['button_bg'], hover_color=c['button_hover'],
                            text_color=c['fg'])

    def _paste_urls(self):
        """从剪贴板粘贴网址"""
        try:
            text = self.root.clipboard_get().strip()
            if text:
                self._clear_url_placeholder()
                current = self.url_text.get('1.0', 'end-1c').strip()
                if current:
                    self.url_text.insert(tk.END, '\n' + text)
                else:
                    self.url_text.insert('1.0', text)
        except Exception:
            pass

    def _paste_cookies(self):
        """从剪贴板粘贴 Cookies"""
        try:
            text = self.root.clipboard_get().strip()
            if text:
                self.cookies_text.delete('1.0', tk.END)
                self.cookies_text.insert('1.0', text)
        except Exception:
            pass

    # ═══════════════════════════════════════════════════════
    # 队列管理
    # ═══════════════════════════════════════════════════════

    def _add_to_queue(self):
        """从 URL 文本框解析网址并添加到队列"""
        if self.batch_running:
            messagebox.showwarning("提示", "批量下载进行中，无法添加")
            return

        urls = self._get_urls_from_input()
        if not urls:
            messagebox.showwarning("提示", "请先输入至少一个有效的视频网址（以 http 开头）")
            return

        # 过滤已在队列中的 URL
        existing_urls = {item['url'] for item in self.queue}
        new_urls = [u for u in urls if u not in existing_urls]

        if not new_urls:
            messagebox.showinfo("提示", "所有网址已在队列中")
            return

        for url in new_urls:
            self.queue.append({
                'url': url,
                'title': '',
                'status': 'waiting',
                'progress': 0.0,
                'speed': '',
                'filesize': '',
                'error': '',
                'formats': [],
                'best_video_id': None,
                'best_audio_id': None,
            })

        skipped = len(urls) - len(new_urls)
        msg = f"已添加 {len(new_urls)} 个网址到队列"
        if skipped > 0:
            msg += f"（跳过 {skipped} 个重复）"
        self._log(msg)
        self._update_queue_ui()

        # 清空 URL 输入区以便继续添加
        self.url_text.delete('1.0', tk.END)
        self._show_url_placeholder()

        # 自动获取格式（标题 + 格式列表）
        cookies_content = self.cookies_text.get('1.0', 'end-1c')
        start_idx = len(self.queue) - len(new_urls)
        for i in range(start_idx, len(self.queue)):
            threading.Thread(target=self._auto_fetch_info,
                           args=(i, cookies_content), daemon=True).start()

        # 首次添加时自动选中第一项
        if self.queue and self.preview_queue_index < 0:
            self._preview_queue_item(0)

    def _update_queue_ui(self):
        """刷新队列表格"""
        self.queue_tree.delete(*self.queue_tree.get_children())

        for i, item in enumerate(self.queue):
            status = item['status']
            icon = STATUS_ICONS.get(status, '⏳')
            idx_str = f"#{i + 1}"

            # 标题（优先标题，未获取时显示简短 URL）
            if item['title']:
                title = item['title']
            else:
                # 截取 URL 最后一段作为标识
                short_url = item['url']
                if len(short_url) > 50:
                    short_url = short_url[:47] + '...'
                title = short_url
            if len(title) > 55:
                title = title[:52] + '...'

            # 进度
            if status == 'done':
                prog_str = "✅ 完成"
            elif status == 'error':
                prog_str = f"❌ {item['error'][:20]}" if item['error'] else "❌ 失败"
            elif status == 'downloading':
                pct = item['progress'] * 100
                spd = item['speed'] or ''
                prog_str = f"{pct:.0f}% {spd}"
            elif status == 'fetching':
                prog_str = "获取中…"
            elif status == 'merging':
                prog_str = "合并中…"
            elif status == 'skipped':
                prog_str = "已跳过"
            else:
                prog_str = "等待中"

            # 大小
            size_str = item['filesize'] if item.get('filesize') else "—"

            # 行颜色
            base_tag = 'alt' if i % 2 == 0 else 'row'
            if status == 'done':
                status_tag = 'done'
            elif status == 'error':
                status_tag = 'error'
            elif status in ('fetching', 'downloading', 'merging'):
                status_tag = 'active'
            else:
                status_tag = 'waiting'

            tree_iid = self.queue_tree.insert(
                "", tk.END,
                values=(icon, idx_str, title, prog_str, size_str),
                tags=(base_tag, status_tag))
            item['_tree_iid'] = tree_iid

        # 更新计数
        total = len(self.queue)
        done = sum(1 for q in self.queue if q['status'] == 'done')
        errs = sum(1 for q in self.queue if q['status'] == 'error')
        self.lbl_queue_count.configure(text=f"({total} 个, 完成 {done}, 失败 {errs})")

        self._update_overall_progress()

    def _on_queue_select(self, event):
        """单击队列行 → 自动切换格式预览"""
        sel = self.queue_tree.selection()
        if not sel:
            return
        for i, item in enumerate(self.queue):
            if item.get('_tree_iid') == sel[0]:
                self.preview_queue_index = i
                self.lbl_preview_title.configure(text=f"(#{i + 1})")

                if item.get('formats'):
                    # 已有缓存，直接显示
                    self._populate_fmt_table(item['formats'], item.get('title', ''))
                    self.lbl_title.configure(text=f"📺 {item['title'][:60]}" if item['title'] else "📺 (获取中…)")
                else:
                    # 尚未获取
                    self.lbl_title.configure(text="📺 (获取中…)" if item['status'] == 'fetching' else "📺 (等待获取)")
                    self.fmt_tree.delete(*self.fmt_tree.get_children())
                    self.video_fmt_var.set("—")
                    self.audio_fmt_var.set("—")
                break

    def _on_global_click(self, event):
        """全局点击监听：有弹出菜单时，点击菜单外任意位置自动关闭"""
        if self._current_popup is None:
            return
        if self._current_popup._win is None:
            self._current_popup = None
            return
        try:
            wx = self._current_popup._win.winfo_rootx()
            wy = self._current_popup._win.winfo_rooty()
            ww = self._current_popup._win.winfo_width()
            wh = self._current_popup._win.winfo_height()
            if wx <= event.x_root <= wx + ww and wy <= event.y_root <= wy + wh:
                return  # 点击在菜单内，正常处理
        except Exception:
            pass
        # 点击在菜单外 → 关闭
        try:
            self._current_popup._destroy()
        except Exception:
            pass
        self._current_popup = None

    def _bind_queue_context_menu(self):
        """绑定队列右键菜单"""
        self._current_popup = None

        def on_right_click(event):
            # 先关闭上一个弹出菜单
            if self._current_popup:
                try:
                    self._current_popup._destroy()
                except Exception:
                    pass
                self._current_popup = None

            # 悬停即选中：根据鼠标位置定位行
            row_iid = self.queue_tree.identify_row(event.y)
            if not row_iid:
                return
            self.queue_tree.selection_set(row_iid)

            # 找到队列项
            idx = -1
            for i, item in enumerate(self.queue):
                if item.get('_tree_iid') == row_iid:
                    idx = i
                    break
            if idx < 0:
                return

            def _dismiss_and_do(action):
                """先关闭菜单，再执行操作"""
                if self._current_popup:
                    try:
                        self._current_popup._destroy()
                    except Exception:
                        pass
                    self._current_popup = None
                action()

            menu = CTkPopupMenu(self.root, self.c, font_family=self.f,
                               font_size=self.s - 1)
            self._current_popup = menu
            menu.add_command(
                label="🗑 从队列移除", icon="",
                command=lambda: _dismiss_and_do(lambda: self._remove_item(idx)),
                danger=True)
            menu.add_command(
                label="🔄 重试下载", icon="",
                command=lambda: _dismiss_and_do(lambda: self._retry_item(idx)))
            menu.add_separator()
            menu.add_command(
                label="📋 复制网址", icon="",
                command=lambda: _dismiss_and_do(lambda: self._copy_queue_url(idx)))
            menu.popup(event.x_root, event.y_root)

        self.queue_tree.bind('<Button-3>', on_right_click)
        # Windows 上也支持 Shift-F10 / Menu key
        self.queue_tree.bind('<Button-2>', on_right_click)

    def _preview_queue_item(self, idx):
        """右键菜单：预览指定队列项的格式"""
        if idx < 0 or idx >= len(self.queue):
            return
        # 选中并高亮队列行，触发 _on_queue_select 自动切换预览
        tree_iid = self.queue[idx].get('_tree_iid')
        if tree_iid and self.queue_tree.exists(tree_iid):
            self.queue_tree.selection_set(tree_iid)
            self.queue_tree.see(tree_iid)
        self.preview_queue_index = idx
        self._on_queue_select(None)  # 手动触发格式加载

    def _remove_item(self, idx):
        """移除指定队列项"""
        if self.batch_running:
            return
        if idx < 0 or idx >= len(self.queue):
            return
        url = self.queue[idx]['url'][:60]
        del self.queue[idx]
        self._log(f"已从队列移除: {url}")
        self._update_queue_ui()

    def _retry_item(self, idx):
        """重试失败的队列项"""
        if self.batch_running:
            return
        if idx < 0 or idx >= len(self.queue):
            return
        item = self.queue[idx]
        if item['status'] in ('error', 'skipped'):
            item['status'] = 'waiting'
            item['progress'] = 0.0
            item['speed'] = ''
            item['error'] = ''
            self._log(f"已重置: {item['url'][:60]}")
            self._update_queue_ui()

    def _copy_queue_url(self, idx):
        """复制队列项网址到剪贴板"""
        if idx < 0 or idx >= len(self.queue):
            return
        self.root.clipboard_clear()
        self.root.clipboard_append(self.queue[idx]['url'])
        self._log("网址已复制到剪贴板")

    def _clear_queue(self):
        """清空队列（保留正在处理的任务）"""
        if self.batch_running:
            messagebox.showwarning("提示", "批量下载进行中，无法清空队列")
            return
        if not self.queue:
            return
        if messagebox.askyesno("确认", f"确定清空全部 {len(self.queue)} 个队列项吗？"):
            self.queue.clear()
            self._update_queue_ui()
            self._log("队列已清空")

    # ═══════════════════════════════════════════════════════
    # 批量下载
    # ═══════════════════════════════════════════════════════

    def _start_batch(self):
        """开始批量下载"""
        if self.batch_running:
            return

        # 如果队列为空，先尝试从 URL 文本框添加
        if not self.queue:
            urls = self._get_urls_from_input()
            if urls:
                for url in urls:
                    self.queue.append({
                        'url': url, 'title': '', 'status': 'waiting',
                        'progress': 0.0, 'speed': '', 'filesize': '',
                        'error': '', 'formats': [], 'best_video_id': None,
                        'best_audio_id': None,
                    })
                self._update_queue_ui()

        if not self.queue:
            messagebox.showwarning("提示", "队列为空，请先添加下载网址")
            return

        # 过滤已完成项，只处理 waiting / error
        pending = [q for q in self.queue if q['status'] not in ('done',)]
        if not pending:
            if messagebox.askyesno("提示", "所有项目已完成。要重新下载全部吗？"):
                for q in self.queue:
                    q['status'] = 'waiting'
                    q['progress'] = 0.0
                    q['speed'] = ''
                    q['error'] = ''
                    q['filesize'] = ''
                self._update_queue_ui()
            else:
                return

        # 选择输出目录
        self.output_dir = filedialog.askdirectory(title="选择批量下载保存目录")
        if not self.output_dir:
            return

        # 在主线程读取 cookies（tkinter 控件不能跨线程访问）
        cookies_content = self.cookies_text.get('1.0', 'end-1c')
        preset_key = self.preset_var.get()
        fmt_selector = PRESETS.get(preset_key, "bestvideo+bestaudio/best")

        self.batch_running = True
        self.batch_cancelled = False
        self._set_ui_enabled(False)
        self._log(f"🚀 开始批量下载 ({len([q for q in self.queue if q['status'] != 'done'])} 个) → {self.output_dir}")
        self._update_queue_ui()

        threading.Thread(target=self._batch_worker,
                        args=(fmt_selector, cookies_content),
                        daemon=True).start()

    def _batch_worker(self, fmt_selector, cookies_content):
        """后台批量处理主循环 —— 并行下载，由用户选择同时数量"""
        cookie_file = self._save_cookies_to_temp(cookies_content)
        semaphore = threading.Semaphore(self.max_concurrent)
        threads = []

        for i, item in enumerate(self.queue):
            if self.batch_cancelled:
                item['status'] = 'skipped'
                self.root.after(0, self._update_queue_ui)
                break

            if item['status'] == 'done':
                continue

            t = threading.Thread(
                target=self._download_one,
                args=(i, item, fmt_selector, cookie_file, semaphore),
                daemon=True)
            threads.append(t)
            t.start()

        # 等待所有线程完成
        for t in threads:
            t.join()

        # ── 收尾 ──
        done = sum(1 for q in self.queue if q['status'] == 'done')
        errs = sum(1 for q in self.queue if q['status'] == 'error')
        skipped = sum(1 for q in self.queue if q['status'] == 'skipped')
        self.root.after(0, lambda: self._on_batch_complete(done, errs, skipped))

    def _download_one(self, idx, item, fmt_selector, cookie_file, semaphore):
        """下载单个队列项（在独立线程中运行，受 semaphore 并发控制）"""
        with semaphore:
            if self.batch_cancelled:
                item['status'] = 'skipped'
                self.root.after(0, self._update_queue_ui)
                return

            url = item['url']

            # ── Phase 1: 获取格式 ──
            item['status'] = 'fetching'
            self.root.after(0, self._update_queue_ui)
            self.root.after(0, self._update_overall_progress)

            try:
                ydl_opts = {
                    'quiet': True, 'no_warnings': True,
                    'skip_download': True, 'extract_flat': False,
                }
                if cookie_file:
                    ydl_opts['cookiefile'] = cookie_file
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
            except Exception as e:
                item['status'] = 'error'
                item['error'] = str(e)[:80]
                self.root.after(0, self._update_queue_ui)
                self.root.after(0, self._update_overall_progress)
                self.root.after(0, lambda msg=str(e)[:100], u=url[:50]:
                               self._log(f"❌ 获取失败 [{u}]: {msg}"))
                return

            title = info.get('title', '未知标题')
            item['title'] = title
            item['formats'] = info.get('formats', [])

            # 自动检测最佳格式
            best_vid_tbr = -1
            best_aud_tbr = -1
            for fmt_ in item['formats']:
                vcodec = fmt_.get('vcodec', 'none')
                acodec = fmt_.get('acodec', 'none')
                has_v = vcodec and vcodec != 'none'
                has_a = acodec and acodec != 'none'
                tbr = fmt_.get('tbr') or 0
                if has_v and tbr > best_vid_tbr:
                    best_vid_tbr = tbr
                    item['best_video_id'] = fmt_.get('format_id')
                if has_a and not has_v and tbr > best_aud_tbr:
                    best_aud_tbr = tbr
                    item['best_audio_id'] = fmt_.get('format_id')

            self.root.after(0, self._update_queue_ui)

            if self.batch_cancelled:
                item['status'] = 'skipped'
                self.root.after(0, self._update_queue_ui)
                return

            # ── Phase 2: 下载 ──
            item['status'] = 'downloading'
            self.root.after(0, self._update_queue_ui)

            try:
                safe_title = re.sub(r'[\\/*?:"<>|]', '', title)[:80]
                ydl_opts = {
                    'format': fmt_selector,
                    'merge_output_format': 'mp4',
                    'outtmpl': os.path.join(self.output_dir, f'{safe_title}.%(ext)s'),
                    'quiet': True,
                    'no_warnings': True,
                    'progress_hooks': [self._make_progress_hook(idx)],
                }
                if cookie_file:
                    ydl_opts['cookiefile'] = cookie_file

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    ydl.download([url])

                item['status'] = 'done'
                item['progress'] = 1.0

                try:
                    out_path = os.path.join(self.output_dir, f'{safe_title}.mp4')
                    if os.path.exists(out_path):
                        size = os.path.getsize(out_path)
                        if size > 1024**3:
                            item['filesize'] = f"{size/1024**3:.1f} GB"
                        else:
                            item['filesize'] = f"{size/1024**2:.0f} MB"
                except Exception:
                    pass

                self.root.after(0, self._update_queue_ui)
                self.root.after(0, self._update_overall_progress)
                self.root.after(0, lambda t=title[:50]: self._log(f"✅ 完成: {t}"))

            except Exception as e:
                item['status'] = 'error'
                item['error'] = str(e)[:80]
                self.root.after(0, self._update_queue_ui)
                self.root.after(0, self._update_overall_progress)
                self.root.after(0, lambda msg=str(e)[:100], u=url[:50]:
                               self._log(f"❌ 下载失败 [{u}]: {msg}"))

    def _make_progress_hook(self, item_index):
        """创建指定队列项的进度回调"""
        def hook(d):
            if self.batch_cancelled:
                return
            item = self.queue[item_index]
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate', 0)
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed', 0)
                eta = d.get('eta', 0)
                if total > 0:
                    item['progress'] = downloaded / total
                if speed:
                    if speed > 1024**2:
                        item['speed'] = f"{speed/1024**2:.1f} MB/s"
                    else:
                        item['speed'] = f"{speed/1024:.0f} KB/s"
                if eta:
                    item['speed'] += f" ETA:{eta}s"
                self.root.after(0, self._update_queue_ui)
                self.root.after(0, self._update_overall_progress)
            elif d['status'] == 'finished':
                item['progress'] = 1.0
                item['status'] = 'merging'
                item['speed'] = '合并中…'
                self.root.after(0, self._update_queue_ui)
        return hook

    def _update_overall_progress(self):
        """更新总进度条和状态文字"""
        if not self.queue:
            self.overall_bar.set(0)
            self.lbl_overall.configure(text="就绪 — 请添加网址到队列")
            return

        total = len(self.queue)
        aggregate = 0.0
        done_count = 0
        err_count = 0

        for q in self.queue:
            if q['status'] == 'done':
                aggregate += 1.0
                done_count += 1
            elif q['status'] == 'error':
                aggregate += 1.0  # 也算进度
                err_count += 1
            elif q['status'] in ('fetching', 'downloading', 'merging'):
                aggregate += q.get('progress', 0.0)

        fraction = aggregate / total if total > 0 else 0
        self.overall_bar.set(fraction)

        if self.batch_running:
            active = sum(1 for q in self.queue
                        if q['status'] in ('fetching', 'downloading', 'merging'))
            parts = [f"{aggregate:.0f}/{total}"]
            if active > 0:
                parts.append(f"并行: {active}/{self.max_concurrent}")
            if err_count > 0:
                parts.append(f"失败: {err_count}")
            self.lbl_overall.configure(text="  |  ".join(parts))
        else:
            self.lbl_overall.configure(
                text=f"完成 {done_count}/{total}" +
                     (f"  |  失败 {err_count}" if err_count > 0 else ""))

    def _highlight_current(self, idx):
        """高亮当前处理项"""
        item = self.queue[idx]
        tree_iid = item.get('_tree_iid')
        if tree_iid and self.queue_tree.exists(tree_iid):
            self.queue_tree.selection_set(tree_iid)
            self.queue_tree.see(tree_iid)

    def _on_batch_complete(self, done, errors, skipped):
        """批量下载完成"""
        self.batch_running = False
        self.batch_cancelled = False
        self._set_ui_enabled(True)
        self.overall_bar.set(1.0)

        msg = f"批量下载完成！\n✅ 成功: {done}\n❌ 失败: {errors}"
        if skipped > 0:
            msg += f"\n⏭ 跳过: {skipped}"
        self._log(msg.replace('\n', ' | '))
        messagebox.showinfo("批量下载完成", msg)

    def _set_ui_enabled(self, enabled):
        """启用/禁用 UI 控件"""
        state = "normal" if enabled else "disabled"
        self.combo_preset.configure(state="readonly" if enabled else "disabled")
        for _, btn in self._conc_btns:
            btn.configure(state="normal" if enabled else "disabled")
        self.url_text.configure(state="normal" if enabled else "disabled")
        self.cookies_text.configure(state="normal" if enabled else "disabled")
        self.btn_add.configure(state=state)
        self.btn_clear.configure(state=state)

        if enabled:
            self.btn_start.configure(text="▶ 开始下载", fg_color=self.c['success'],
                                     state="normal", command=self._start_batch)
        else:
            self.btn_start.configure(text="⏸ 取消下载", fg_color=self.c['danger'],
                                     state="normal", command=self._cancel_batch)

    def _cancel_batch(self):
        """取消批量下载"""
        if not self.batch_running:
            return
        if messagebox.askyesno("确认取消", "确定取消后续下载吗？\n当前正在下载的项会完成。"):
            self.batch_cancelled = True
            self._log("⏸ 用户取消批量下载（当前项完成后停止）")
            # 按钮状态恢复
            self.btn_start.configure(text="▶ 开始下载", fg_color=self.c['success'],
                                     command=self._start_batch, state="disabled")

    # ═══════════════════════════════════════════════════════
    # 格式预览（可折叠面板）
    # ═══════════════════════════════════════════════════════

    def _auto_fetch_info(self, idx, cookies_content):
        """后台自动获取队列项的标题和格式信息"""
        item = self.queue[idx]
        url = item['url']
        item['status'] = 'fetching'
        self.root.after(0, self._update_queue_ui)

        try:
            cookie_file = self._save_cookies_to_temp(cookies_content)
            ydl_opts = {
                'quiet': True, 'no_warnings': True,
                'skip_download': True, 'extract_flat': False,
            }
            if cookie_file:
                ydl_opts['cookiefile'] = cookie_file

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)

            item['title'] = info.get('title', '未知标题')
            item['formats'] = info.get('formats', [])

            # 自动检测最佳格式
            best_vid_tbr = -1
            best_aud_tbr = -1
            for fmt in item['formats']:
                vcodec = fmt.get('vcodec', 'none')
                acodec = fmt.get('acodec', 'none')
                has_v = vcodec and vcodec != 'none'
                has_a = acodec and acodec != 'none'
                tbr = fmt.get('tbr') or 0
                if has_v and tbr > best_vid_tbr:
                    best_vid_tbr = tbr
                    item['best_video_id'] = fmt.get('format_id')
                if has_a and not has_v and tbr > best_aud_tbr:
                    best_aud_tbr = tbr
                    item['best_audio_id'] = fmt.get('format_id')

            item['status'] = 'waiting'
            self.root.after(0, self._update_queue_ui)
            self.root.after(0, lambda t=item['title'][:50]: self._log(f"✅ 已获取: {t}"))

            # 如果是当前选中的预览项，刷新预览面板
            if idx == self.preview_queue_index:
                self.root.after(0, lambda: self._populate_fmt_table(
                    item['formats'], item['title']))
                self.root.after(0, lambda: self.lbl_title.configure(
                    text=f"📺 {item['title'][:60]}"))

        except Exception as e:
            item['status'] = 'waiting'
            item['error'] = str(e)[:80]
            self.root.after(0, self._update_queue_ui)
            self.root.after(0, lambda msg=str(e)[:80]: self._log(f"⚠ 获取失败: {msg}"))

    def _populate_fmt_table(self, all_formats, title=""):
        """填充格式预览表格"""
        self.fmt_tree.delete(*self.fmt_tree.get_children())
        self.format_id_to_item.clear()
        self.video_formats.clear()
        self.audio_formats.clear()
        self.best_video_id = None
        self.best_audio_id = None

        best_vid_tbr = -1
        best_aud_tbr = -1

        for fmt in all_formats:
            fid = fmt.get('format_id', '?')
            ext = fmt.get('ext', '')
            vcodec = fmt.get('vcodec', 'none')
            acodec = fmt.get('acodec', 'none')
            resolution = fmt.get('resolution') or fmt.get('format_note') or ''
            has_video = vcodec and vcodec != 'none'
            has_audio = acodec and acodec != 'none'

            if has_video and not has_audio:
                ftype = "🎬 视频"
                self.video_formats.append(fmt)
            elif has_audio and not has_video:
                ftype = "🎵 音频"
                self.audio_formats.append(fmt)
            elif has_video and has_audio:
                ftype = "📦 合并"
                self.video_formats.append(fmt)
            else:
                ftype = "❓ 其他"

            codec = vcodec if has_video else acodec
            if len(codec) > 20:
                codec = codec[:18] + '..'

            tbr = fmt.get('tbr')
            bitrate = f"{tbr:.0f} kbps" if tbr else ""

            filesize = fmt.get('filesize') or fmt.get('filesize_approx')
            if filesize:
                if filesize > 1024**3:
                    size = f"{filesize/1024**3:.1f} GB"
                elif filesize > 1024**2:
                    size = f"{filesize/1024**2:.0f} MB"
                else:
                    size = f"{filesize/1024:.0f} KB"
            else:
                size = ""

            note = fmt.get('format_note', '')

            tbr_val = tbr or 0
            if has_video and tbr_val > best_vid_tbr:
                best_vid_tbr = tbr_val
                self.best_video_id = fid
            if has_audio and not has_video and tbr_val > best_aud_tbr:
                best_aud_tbr = tbr_val
                self.best_audio_id = fid

            base_tag = 'alt' if len(self.fmt_tree.get_children()) % 2 == 0 else 'row'
            item_id = self.fmt_tree.insert(
                "", tk.END,
                values=("", fid, ftype, resolution, codec, bitrate, size, note),
                tags=(base_tag,))
            self.format_id_to_item[fid] = item_id

        # 更新下拉框
        vid_choices = [
            f"{f['format_id']} | {f.get('resolution') or f.get('format_note','?')} | {f.get('ext','')}"
            for f in self.video_formats
        ]
        aud_choices = [
            f"{f['format_id']} | {f.get('tbr','?')}kbps | {f.get('ext','')}"
            for f in self.audio_formats
        ]

        self.combo_video.configure(values=vid_choices or ["—"])
        self.combo_audio.configure(values=aud_choices or ["—"])

        if self.best_video_id:
            for c in vid_choices:
                if c.startswith(f"{self.best_video_id} |"):
                    self.video_fmt_var.set(c)
                    break
            else:
                self.video_fmt_var.set(vid_choices[0] if vid_choices else "—")
        else:
            self.video_fmt_var.set(vid_choices[0] if vid_choices else "—")

        if self.best_audio_id:
            for c in aud_choices:
                if c.startswith(f"{self.best_audio_id} |"):
                    self.audio_fmt_var.set(c)
                    break
            else:
                self.audio_fmt_var.set(aud_choices[0] if aud_choices else "—")
        else:
            self.audio_fmt_var.set(aud_choices[0] if aud_choices else "—")

        self._log(f"预览完成: {len(self.video_formats)} 视频 + {len(self.audio_formats)} 音频格式")
        self._refresh_fmt_highlights()

    def _on_fmt_tree_select(self, event):
        """点击格式表格行 → 选中对应格式"""
        sel = self.fmt_tree.selection()
        if not sel:
            return
        values = self.fmt_tree.item(sel[0], 'values')
        if not values:
            return
        fid = values[1]
        ftype = values[2]

        if '视频' in ftype or '合并' in ftype:
            for choice in self.combo_video.cget('values'):
                if choice.startswith(f"{fid} |"):
                    self.video_fmt_var.set(choice)
                    break
        if '音频' in ftype:
            for choice in self.combo_audio.cget('values'):
                if choice.startswith(f"{fid} |"):
                    self.audio_fmt_var.set(choice)
                    break
        self._refresh_fmt_highlights()

    def _refresh_fmt_highlights(self):
        """刷新格式表格高亮"""
        if not self.format_id_to_item:
            return
        vid_sel = self.video_fmt_var.get()
        aud_sel = self.audio_fmt_var.get()
        vid_id = vid_sel.split(' | ')[0] if ' | ' in vid_sel else None
        aud_id = aud_sel.split(' | ')[0] if ' | ' in aud_sel else None

        keys = list(self.format_id_to_item.keys())
        for idx, fid in enumerate(keys):
            item_id = self.format_id_to_item.get(fid)
            if not item_id or not self.fmt_tree.exists(item_id):
                continue
            is_best = (fid == self.best_video_id or fid == self.best_audio_id)
            is_sel = (fid == vid_id or fid == aud_id)
            mark = ""
            if is_best and is_sel:
                mark = "★✓"
            elif is_best:
                mark = "★"
            elif is_sel:
                mark = "✓"

            base_tag = 'alt' if idx % 2 == 0 else 'row'
            if is_best and is_sel:
                tag = 'best_sel'
            elif is_best:
                tag = 'best'
            elif is_sel:
                tag = 'selected'
            else:
                tag = base_tag

            current = list(self.fmt_tree.item(item_id, 'values'))
            if current:
                current[0] = mark
                self.fmt_tree.item(item_id, values=tuple(current), tags=(base_tag, tag))

    # ═══════════════════════════════════════════════════════
    # 通用工具
    # ═══════════════════════════════════════════════════════

    def _log(self, msg):
        """输出日志"""
        self.log_text.configure(state="normal")
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.configure(state="disabled")

    def _save_cookies_to_temp(self, content):
        """将 Cookie 内容写入临时文件"""
        content = (content or '').strip()
        if not content:
            return None
        if not self.cookies_path:
            import tempfile
            fd, self.cookies_path = tempfile.mkstemp(
                suffix='.txt', prefix='ytdlp_cookies_', text=True)
            os.close(fd)
        with open(self.cookies_path, 'w', encoding='utf-8') as fh:
            fh.write(content)
        return self.cookies_path

    def _on_close(self):
        """窗口关闭"""
        if self.batch_running:
            if not messagebox.askyesno("确认退出", "批量下载正在进行中，确定要退出吗？"):
                return
            self.batch_cancelled = True
        # 清理临时 cookies 文件
        if self.cookies_path and os.path.exists(self.cookies_path):
            try:
                os.remove(self.cookies_path)
            except Exception:
                pass
        self.root.destroy()


# ═══════════════════════════════════════════════════════════
# 入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    VidFetchApp()
