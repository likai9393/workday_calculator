import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import datetime
import re
import json
import os
import csv

BASE_APPDATA = os.environ.get("LOCALAPPDATA") or os.path.join(os.path.expanduser("~"), "AppData", "Local")
CONFIG_DIR = os.path.join(BASE_APPDATA, "WorkdayCalculator")
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = os.path.join(CONFIG_DIR, "holidays_config.json")


class WorkdayCalculatorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("有效日期计算")
        self.root.geometry("1240x740")
        self.root.minsize(1080, 560)

        self.default_holidays_text = (
            "# 支持换行、逗号、空格分隔，支持单日或区间（用 ~ 或 to 连接）\n"
            "# 香港 2024–2027 公众假期：\n"
            "2024-01-01, 2024-02-10, 2024-02-12~2024-02-13, 2024-03-29~2024-03-30, 2024-04-01, 2024-04-04, 2024-05-01, 2024-05-15, 2024-06-10, 2024-07-01, 2024-09-18, 2024-10-01, 2024-10-11, 2024-12-25~2024-12-26\n"
            "2025-01-01, 2025-01-29~2025-01-31, 2025-04-04, 2025-04-18~2025-04-19, 2025-04-21, 2025-05-01, 2025-05-05, 2025-05-31, 2025-07-01, 2025-10-01, 2025-10-07, 2025-10-29, 2025-12-25~2025-12-26\n"
            "2026-01-01, 2026-02-17~2026-02-19, 2026-04-03~2026-04-04, 2026-04-06~2026-04-07, 2026-05-01, 2026-05-25, 2026-06-19, 2026-07-01, 2026-09-26, 2026-10-01, 2026-10-19, 2026-12-25~2026-12-26\n"
            "2027-01-01, 2027-02-06, 2027-02-08~2027-02-09, 2027-03-26~2027-03-27, 2027-03-29, 2027-04-05, 2027-05-01, 2027-05-13, 2027-06-09, 2027-07-01, 2027-09-16, 2027-10-01, 2027-10-08, 2027-12-25, 2027-12-27\n"
        )

        # 每条记录存为 {"seq": int, "start": date, "end": date, "res": dict}
        self.items = []
        self._next_seq = 1
        self.sort_col = "seq"
        self.sort_desc = False

        self._highlight_after_id = None
        self._banner_after_id = None
        self._sync_after_id = None

        self._setup_styles()
        self._build_ui()
        self._load_config()
        self._update_heading_arrows()
        self.recalculate_all(show_feedback=False)
        self.root.after(50, self._enforce_min_width)
        self.root.after(60, self._redraw_group_headers)

    def _setup_styles(self):
        self.bg_page = "#F4F6F9"
        self.bg_card = "#FFFFFF"
        self.border_color = "#DCE2EA"
        self.accent_color = "#1B6EC2"
        self.accent_hover = "#15589B"
        self.text_main = "#1E293B"
        self.text_muted = "#64748B"

        self.root.configure(bg=self.bg_page)

        style = ttk.Style(self.root)
        if "clam" in style.theme_names():
            style.theme_use("clam")

        font_ui = ("Microsoft YaHei UI", 9)
        font_ui_bold = ("Microsoft YaHei UI", 9, "bold")
        font_title = ("Microsoft YaHei UI", 10, "bold")

        style.configure(".", font=font_ui, foreground=self.text_main, background=self.bg_page)
        style.configure("TFrame", background=self.bg_card)
        style.configure("Page.TFrame", background=self.bg_page)

        style.configure(
            "Card.TLabelframe",
            background=self.bg_card,
            bordercolor=self.border_color,
            relief="solid",
            borderwidth=1,
            padding=(12, 8, 12, 10)
        )
        style.configure(
            "Card.TLabelframe.Label",
            background=self.bg_card,
            foreground=self.text_main,
            font=font_title
        )

        style.configure("Hint.TLabel", background=self.bg_card, foreground=self.text_muted, font=("Microsoft YaHei UI", 8))
        style.configure("TLabel", background=self.bg_card, foreground=self.text_main, font=font_ui)
        style.configure("TRadiobutton", background=self.bg_card, foreground=self.text_main, font=font_ui, padding=(2, 2))
        style.map("TRadiobutton", background=[("active", self.bg_card)])

        style.configure(
            "TEntry",
            fieldbackground="#FFFFFF",
            foreground=self.text_main,
            bordercolor="#CBD5E1",
            lightcolor="#CBD5E1",
            darkcolor="#CBD5E1",
            padding=(6, 4),
            font=("Consolas", 10)
        )

        style.configure(
            "TButton",
            background="#F8FAFC",
            foreground=self.text_main,
            bordercolor="#CBD5E1",
            lightcolor="#F8FAFC",
            darkcolor="#E2E8F0",
            font=font_ui,
            padding=(10, 5)
        )
        style.map(
            "TButton",
            background=[("active", "#E2E8F0"), ("pressed", "#CBD5E1")],
            bordercolor=[("active", "#94A3B8")]
        )

        style.configure(
            "Primary.TButton",
            background=self.accent_color,
            foreground="#FFFFFF",
            bordercolor=self.accent_color,
            lightcolor=self.accent_color,
            darkcolor=self.accent_hover,
            font=font_ui_bold,
            padding=(12, 5)
        )
        style.map(
            "Primary.TButton",
            background=[("active", self.accent_hover), ("pressed", self.accent_hover)],
            bordercolor=[("active", self.accent_hover)]
        )

        style.configure(
            "TPanedwindow",
            background=self.bg_page,
            sashrelief="flat",
            sashpad=5
        )

        style.configure(
            "Treeview",
            background="#FFFFFF",
            foreground=self.text_main,
            fieldbackground="#FFFFFF",
            bordercolor=self.border_color,
            rowheight=28,
            font=("Consolas", 10)
        )
        style.configure(
            "Treeview.Heading",
            background="#F1F5F9",
            foreground=self.text_main,
            bordercolor="#CBD5E1",
            relief="flat",
            font=font_ui_bold,
            padding=(6, 6)
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#E2E8F0")]
        )
        style.map(
            "Treeview",
            background=[("selected", "#DBEAFE")],
            foreground=[("selected", "#0F172A")]
        )

    def _build_ui(self):
        self.page = ttk.Frame(self.root, style="Page.TFrame")
        self.page.pack(fill="both", expand=True, padx=14, pady=12)

        # 1. 添加时间段工具栏
        self.mid_frame = ttk.LabelFrame(self.page, text="2. 添加时间段", style="Card.TLabelframe")
        self.mid_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(self.mid_frame, text="开始时间：").pack(side="left")
        self.start_entry = ttk.Entry(self.mid_frame, width=13)
        self.start_entry.pack(side="left", padx=(2, 10))

        ttk.Label(self.mid_frame, text="结束时间：").pack(side="left")
        self.end_entry = ttk.Entry(self.mid_frame, width=13)
        self.end_entry.pack(side="left", padx=(2, 12))

        ttk.Button(self.mid_frame, text="添加计算", style="Primary.TButton", command=self.add_single_row).pack(side="left", padx=(0, 6))
        ttk.Button(self.mid_frame, text="批量粘贴", command=self.open_batch_dialog).pack(side="left", padx=(0, 6))
        ttk.Button(self.mid_frame, text="导入 CSV", command=self.import_csv).pack(side="left", padx=(0, 6))

        ttk.Button(self.mid_frame, text="删除选中", command=self.delete_selected).pack(side="right")
        ttk.Button(self.mid_frame, text="清空表格", command=self.clear_all).pack(side="right", padx=(0, 6))
        ttk.Button(self.mid_frame, text="导出 CSV", command=self.export_csv).pack(side="right", padx=(0, 6))

        # 底部状态提示横幅
        self.banner_label = tk.Label(
            self.page,
            text="",
            font=("Microsoft YaHei UI", 9, "bold"),
            anchor="w",
            padx=10,
            pady=4
        )

        # 2. 可上下拉伸区域
        self.paned = ttk.PanedWindow(self.page, orient="vertical")
        self.paned.pack(fill="both", expand=True)

        # 1号区域：节假日 / 个人请假配置
        top_frame = ttk.LabelFrame(self.paned, text="1. 节假日 / 个人请假配置（拖动下方分隔条可调整上下高度）", style="Card.TLabelframe")
        self.paned.add(top_frame, weight=2)

        top_content = ttk.Frame(top_frame)
        top_content.pack(fill="both", expand=True)

        left_top = ttk.Frame(top_content)
        left_top.pack(side="left", fill="both", expand=True)

        ttk.Label(
            left_top,
            text="粘贴节假日或请假日期（支持 YYYY-MM-DD、YYYY/MM/DD、YYYYMMDD 或区间 2026-10-01~2026-10-03）：",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(0, 4))

        text_wrap = ttk.Frame(left_top)
        text_wrap.pack(fill="both", expand=True)

        self.holiday_text = tk.Text(
            text_wrap,
            height=9,
            font=("Consolas", 10),
            wrap="word",
            bg="#FAFBFD",
            fg=self.text_main,
            insertbackground=self.text_main,
            relief="solid",
            bd=1,
            highlightthickness=1,
            highlightcolor=self.accent_color,
            highlightbackground="#CBD5E1",
            padx=8,
            pady=6
        )
        h_scroll = ttk.Scrollbar(text_wrap, orient="vertical", command=self.holiday_text.yview)
        self.holiday_text.configure(yscrollcommand=h_scroll.set)
        self.holiday_text.pack(side="left", fill="both", expand=True)
        h_scroll.pack(side="right", fill="y")

        right_top = ttk.Frame(top_content)
        right_top.pack(side="right", fill="y", padx=(16, 2))

        ttk.Label(right_top, text="周末规则：").pack(anchor="w", pady=(0, 4))
        self.weekend_mode = tk.StringVar(value="double")
        ttk.Radiobutton(right_top, text="双休（周六、周日）", variable=self.weekend_mode, value="double", command=self.recalculate_all).pack(anchor="w")
        ttk.Radiobutton(right_top, text="单休（仅周日）", variable=self.weekend_mode, value="sunday", command=self.recalculate_all).pack(anchor="w")
        ttk.Radiobutton(right_top, text="无休（仅扣节假日/个人请假）", variable=self.weekend_mode, value="none", command=self.recalculate_all).pack(anchor="w")

        ttk.Button(right_top, text="应用并重算全部", style="Primary.TButton", command=self.recalculate_all).pack(fill="x", pady=(10, 0))

        # 3号区域：结果表格区
        table_frame = ttk.LabelFrame(
            self.paned,
            text="3. 计算结果明细（点击列头可切换升序/降序）",
            style="Card.TLabelframe"
        )
        self.paned.add(table_frame, weight=2)

        ttk.Label(
            table_frame,
            text="说明：【总天数】为自然日；【总天数扣周末】扣除区间内周末；【总天数扣假日和请假】扣除周末及节假日/个人请假（重叠日期不重复扣减）。",
            style="Hint.TLabel"
        ).pack(anchor="w", pady=(0, 6))

        # 合并表头画布
        self.group_canvas = tk.Canvas(
            table_frame,
            height=26,
            bg="#FFFFFF",
            highlightthickness=1,
            highlightbackground="#CBD5E1"
        )
        self.group_canvas.pack(fill="x")

        tree_wrap = ttk.Frame(table_frame)
        tree_wrap.pack(fill="both", expand=True)

        self.columns = (
            "seq", "start", "end",
            "total_both", "total_start",
            "no_wk_both", "no_wk_start",
            "valid_both", "valid_start"
        )
        self.tree = ttk.Treeview(tree_wrap, columns=self.columns, show="headings")
        self.tree.tag_configure("even", background="#FFFFFF", foreground=self.text_main)
        self.tree.tag_configure("odd", background="#F8FAFC", foreground=self.text_main)
        self.tree.tag_configure("changed", background="#DBEAFE", foreground="#0F172A")

        self.base_headers = {
            "seq": "序号",
            "start": "开始时间",
            "end": "结束时间",
            "total_both": "算头又算尾",
            "total_start": "算头不算尾",
            "no_wk_both": "算头又算尾",
            "no_wk_start": "算头不算尾",
            "valid_both": "算头又算尾",
            "valid_start": "算头不算尾"
        }

        for col in self.columns:
            self.tree.heading(col, text=self.base_headers[col], command=lambda c=col: self.sort_by_column(c))
            if col == "seq":
                w, min_w = 72, 60
            elif col in ("start", "end"):
                w, min_w = 120, 95
            else:
                w, min_w = 125, 95
            self.tree.column(col, anchor="center", width=w, minwidth=min_w, stretch=True)

        y_scroll = ttk.Scrollbar(tree_wrap, orient="vertical", command=self.tree.yview)
        x_scroll = ttk.Scrollbar(tree_wrap, orient="horizontal", command=self._on_xscroll)
        self.tree.configure(yscrollcommand=y_scroll.set, xscrollcommand=self._on_tree_xview)

        self.tree.grid(row=0, column=0, sticky="nsew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        x_scroll.grid(row=1, column=0, sticky="ew")
        self._x_scroll = x_scroll
        tree_wrap.rowconfigure(0, weight=1)
        tree_wrap.columnconfigure(0, weight=1)

        self.tree.bind("<Delete>", lambda e: self.delete_selected())
        self.tree.bind("<Configure>", lambda e: self._schedule_group_redraw())
        self.tree.bind("<ButtonRelease-1>", lambda e: self._schedule_group_redraw())
        self.group_canvas.bind("<Configure>", lambda e: self._schedule_group_redraw())

    def _enforce_min_width(self):
        self.root.update_idletasks()
        req_toolbar_w = self.mid_frame.winfo_reqwidth() + 56
        min_w = max(1080, req_toolbar_w)
        self.root.minsize(min_w, 560)
        if self.root.winfo_width() < min_w:
            self.root.geometry(f"{min_w}x{max(self.root.winfo_height(), 560)}")

    def _update_heading_arrows(self):
        for col, base_text in self.base_headers.items():
            if col == self.sort_col:
                arrow = " ▼" if self.sort_desc else " ▲"
                self.tree.heading(col, text=base_text + arrow)
            else:
                self.tree.heading(col, text=base_text)

    def sort_by_column(self, col):
        if self.sort_col == col:
            self.sort_desc = not self.sort_desc
        else:
            self.sort_col = col
            self.sort_desc = False

        def sort_key(entry):
            if col == "seq":
                return entry["seq"]
            if col == "start":
                return entry["start"]
            if col == "end":
                return entry["end"]
            return entry["res"][col]

        self.items.sort(key=sort_key, reverse=self.sort_desc)
        self._update_heading_arrows()
        self._refresh_tree_view(changed_set=set())
        self._show_banner(
            f"已按【{self.base_headers[col]}】{'降序' if self.sort_desc else '升序'}排列",
            changed=False
        )

    def _on_xscroll(self, *args):
        self.tree.xview(*args)
        self._schedule_group_redraw()

    def _on_tree_xview(self, first, last):
        self._x_scroll.set(first, last)
        self._schedule_group_redraw()

    def _schedule_group_redraw(self):
        if self._sync_after_id is not None:
            self.root.after_cancel(self._sync_after_id)
        self._sync_after_id = self.root.after(15, self._redraw_group_headers)

    def _redraw_group_headers(self):
        self._sync_after_id = None
        c = self.group_canvas
        c.delete("all")

        canvas_w = max(c.winfo_width(), 1)
        h = max(c.winfo_height(), 26)

        col_widths = [int(self.tree.column(col, "width")) for col in self.columns]
        total_w = sum(col_widths)
        first_frac, _ = self._x_scroll.get()
        scroll_offset = first_frac * total_w

        col_x = []
        acc = -scroll_offset
        for w in col_widths:
            col_x.append((acc, acc + w))
            acc += w

        c.create_rectangle(0, 0, canvas_w, h, fill="#F1F5F9", outline="")

        groups = [
            (0, 0, "#", "#F1F5F9", "#334155"),
            (1, 2, "起止时间", "#F1F5F9", "#334155"),
            (3, 4, "总天数", "#DBEAFE", "#1E3A8A"),
            (5, 6, "总天数扣周末", "#E0F2FE", "#0369A1"),
            (7, 8, "总天数扣假日和请假", "#DCFCE7", "#166534"),
        ]

        for start_idx, end_idx, title, bg_fill, fg_color in groups:
            x0 = col_x[start_idx][0]
            x1 = col_x[end_idx][1]
            if x1 <= 0 or x0 >= canvas_w:
                continue
            c.create_rectangle(x0 + 1, 1, x1 - 1, h - 1, fill=bg_fill, outline="#CBD5E1")
            c.create_text((x0 + x1) / 2, h / 2, text=title, fill=fg_color, font=("Microsoft YaHei UI", 9, "bold"))

    def _show_banner(self, message, changed=True):
        if self._banner_after_id is not None:
            self.root.after_cancel(self._banner_after_id)
            self._banner_after_id = None

        if changed:
            self.banner_label.configure(text=f"✔ {message}", bg="#DCFCE7", fg="#166534")
        else:
            self.banner_label.configure(text=f"ℹ {message}", bg="#E2E8F0", fg="#334155")

        if not self.banner_label.winfo_manager():
            self.paned.pack_forget()
            self.banner_label.pack(fill="x", side="bottom", pady=(6, 0))
            self.paned.pack(fill="both", expand=True)

        self._banner_after_id = self.root.after(2600, self._hide_banner)

    def _hide_banner(self):
        self._banner_after_id = None
        if self.banner_label.winfo_manager():
            self.banner_label.pack_forget()
            self.page.update_idletasks()

    def _schedule_clear_highlight(self):
        if self._highlight_after_id is not None:
            self.root.after_cancel(self._highlight_after_id)
        self._highlight_after_id = self.root.after(1600, self._clear_highlight)

    def _clear_highlight(self):
        self._highlight_after_id = None
        for idx, item in enumerate(self.tree.get_children()):
            base_tag = "even" if idx % 2 == 0 else "odd"
            self.tree.item(item, tags=(base_tag,))

    def _res_tuple(self, res):
        return (
            res["total_both"], res["total_start"],
            res["no_wk_both"], res["no_wk_start"],
            res["valid_both"], res["valid_start"]
        )

    def _row_values(self, entry):
        res = entry["res"]
        return (
            entry["seq"], res["start"], res["end"],
            res["total_both"], res["total_start"],
            res["no_wk_both"], res["no_wk_start"],
            res["valid_both"], res["valid_start"]
        )

    def _refresh_tree_view(self, changed_set):
        for item in self.tree.get_children():
            self.tree.delete(item)
        for idx, entry in enumerate(self.items):
            tag = "changed" if idx in changed_set else ("even" if idx % 2 == 0 else "odd")
            self.tree.insert("", tk.END, values=self._row_values(entry), tags=(tag,))

    def parse_single_date(self, date_str):
        s = date_str.strip().split()[0]
        for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y.%m.%d", "%Y%m%d"):
            try:
                return datetime.datetime.strptime(s, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"无法识别的日期格式: {date_str}")

    def parse_holidays_from_text(self):
        raw_text = self.holiday_text.get("1.0", tk.END)
        holidays = set()

        lines = []
        for line in raw_text.splitlines():
            line = line.split("#")[0].strip()
            if line:
                lines.append(line)
        clean_text = " ".join(lines)

        range_pattern = re.compile(r"(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})\s*(?:~|-|to|至)\s*(\d{4}[-/.]?\d{1,2}[-/.]?\d{1,2})")
        for match in range_pattern.finditer(clean_text):
            try:
                d1 = self.parse_single_date(match.group(1))
                d2 = self.parse_single_date(match.group(2))
                if d1 > d2:
                    d1, d2 = d2, d1
                curr = d1
                while curr <= d2:
                    holidays.add(curr)
                    curr += datetime.timedelta(days=1)
            except ValueError:
                pass

        remaining_text = range_pattern.sub(" ", clean_text)
        single_pattern = re.compile(r"\d{4}[-/.]\d{1,2}[-/.]\d{1,2}|\b\d{8}\b")
        for match in single_pattern.finditer(remaining_text):
            try:
                holidays.add(self.parse_single_date(match.group(0)))
            except ValueError:
                pass

        return holidays

    def is_weekend(self, d):
        mode = self.weekend_mode.get()
        wd = d.weekday()
        if mode == "double":
            return wd in (5, 6)
        elif mode == "sunday":
            return wd == 6
        return False

    def calculate_row(self, start_date, end_date, holidays):
        if start_date > end_date:
            raise ValueError("开始时间不能晚于结束时间")

        total_both = 0
        total_start = 0
        no_wk_both = 0
        no_wk_start = 0
        valid_both = 0
        valid_start = 0

        curr = start_date
        while curr <= end_date:
            is_before_end = curr < end_date
            wk = self.is_weekend(curr)
            hol_or_leave = curr in holidays

            total_both += 1
            if is_before_end:
                total_start += 1

            if not wk:
                no_wk_both += 1
                if is_before_end:
                    no_wk_start += 1

                if not hol_or_leave:
                    valid_both += 1
                    if is_before_end:
                        valid_start += 1

            curr += datetime.timedelta(days=1)

        return {
            "start": start_date.strftime("%Y-%m-%d"),
            "end": end_date.strftime("%Y-%m-%d"),
            "total_both": total_both,
            "total_start": total_start,
            "no_wk_both": no_wk_both,
            "no_wk_start": no_wk_start,
            "valid_both": valid_both,
            "valid_start": valid_start
        }

    def add_single_row(self):
        try:
            s_date = self.parse_single_date(self.start_entry.get())
            e_date = self.parse_single_date(self.end_entry.get())
            holidays = self.parse_holidays_from_text()
            self._save_config()

            res = self.calculate_row(s_date, e_date, holidays)
            self.items.append({"seq": self._next_seq, "start": s_date, "end": e_date, "res": res})
            self._next_seq += 1
            new_idx = len(self.items) - 1
            self._refresh_tree_view(changed_set={new_idx})
            self._schedule_clear_highlight()
            self._show_banner(
                f"已添加 {res['start']} ~ {res['end']}（扣假日和请假：算头又算尾 {res['valid_both']} 天 / 算头不算尾 {res['valid_start']} 天）",
                changed=True
            )
        except ValueError as e:
            messagebox.showerror("输入错误", str(e))

    def recalculate_all(self, show_feedback=True):
        holidays = self.parse_holidays_from_text()
        self._save_config()

        changed_set = set()
        for idx, entry in enumerate(self.items):
            old_tup = self._res_tuple(entry["res"])
            new_res = self.calculate_row(entry["start"], entry["end"], holidays)
            entry["res"] = new_res
            if old_tup != self._res_tuple(new_res):
                changed_set.add(idx)

        self._refresh_tree_view(changed_set=changed_set)

        if changed_set:
            self._schedule_clear_highlight()

        if show_feedback and self.items:
            if changed_set:
                self._show_banner(f"已重算 {len(self.items)} 条记录：{len(changed_set)} 条天数发生变化（已高亮标蓝）", changed=True)
            else:
                self._show_banner(f"已重算 {len(self.items)} 条记录：各项天数无变化", changed=False)

    def _append_date_pairs(self, pairs, holidays):
        added_indices = set()
        errors = []
        for idx, (raw_s, raw_e) in enumerate(pairs, 1):
            try:
                s_date = self.parse_single_date(raw_s)
                e_date = self.parse_single_date(raw_e)
                res = self.calculate_row(s_date, e_date, holidays)
                self.items.append({"seq": self._next_seq, "start": s_date, "end": e_date, "res": res})
                self._next_seq += 1
                added_indices.add(len(self.items) - 1)
            except ValueError as err:
                errors.append(f"第 {idx} 条 ({raw_s},{raw_e}): {err}")
        return added_indices, errors

    def open_batch_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("批量粘贴时间段")
        dialog.geometry("500x360")
        dialog.configure(bg=self.bg_page)
        dialog.transient(self.root)
        dialog.grab_set()

        frame = ttk.LabelFrame(dialog, text="每行一对日期，中间用英文逗号 , 隔开", style="Card.TLabelframe")
        frame.pack(fill="both", expand=True, padx=12, pady=12)

        text_box = tk.Text(
            frame,
            height=12,
            font=("Consolas", 10),
            bg="#FAFBFD",
            fg=self.text_main,
            relief="solid",
            bd=1,
            padx=8,
            pady=6
        )
        text_box.pack(fill="both", expand=True)
        text_box.insert("1.0", "2026-07-26,2026-09-16\n2026-09-16,2026-10-04\n2026-06-14,2026-07-05")

        def process_batch():
            raw = text_box.get("1.0", tk.END).strip()
            if not raw:
                dialog.destroy()
                return

            holidays = self.parse_holidays_from_text()
            self._save_config()

            pairs = []
            errors = []
            for idx, line in enumerate(raw.splitlines(), 1):
                line = line.strip()
                if not line:
                    continue
                if "," in line:
                    parts = [p.strip() for p in line.split(",")]
                else:
                    parts = [p.strip() for p in re.split(r"[\t;]+", line)]
                if len(parts) < 2 or not parts[0] or not parts[1]:
                    errors.append(f"第 {idx} 行缺少开始或结束时间: {line}")
                    continue
                pairs.append((parts[0], parts[1]))

            added_indices, calc_errors = self._append_date_pairs(pairs, holidays)
            errors.extend(calc_errors)

            dialog.destroy()
            if added_indices:
                self._refresh_tree_view(changed_set=added_indices)
                self._schedule_clear_highlight()
                self._show_banner(f"批量导入成功：新增 {len(added_indices)} 条记录（已高亮标蓝）", changed=True)
            if errors:
                messagebox.showwarning("部分行未导入", f"成功导入 {len(added_indices)} 条。\n以下行存在问题：\n" + "\n".join(errors[:10]))

        ttk.Button(frame, text="确认导入并计算", style="Primary.TButton", command=process_batch).pack(pady=(10, 0))

    def import_csv(self):
        file_path = filedialog.askopenfilename(
            title="选择 CSV 文件",
            filetypes=[("CSV 文件", "*.csv"), ("所有文件", "*.*")]
        )
        if not file_path:
            return

        holidays = self.parse_holidays_from_text()
        self._save_config()

        pairs = []
        errors = []
        start_col_idx = 0
        end_col_idx = 1

        try:
            with open(file_path, "r", newline="", encoding="utf-8-sig") as f:
                reader = csv.reader(f)
                rows = [r for r in reader if any(cell.strip() for cell in r)]
        except UnicodeDecodeError:
            with open(file_path, "r", newline="", encoding="gbk", errors="replace") as f:
                reader = csv.reader(f)
                rows = [r for r in reader if any(cell.strip() for cell in r)]
        except Exception as err:
            messagebox.showerror("读取失败", f"无法读取 CSV 文件：\n{err}")
            return

        if not rows:
            messagebox.showinfo("提示", "所选 CSV 文件为空。")
            return

        first_row_clean = [c.strip() for c in rows[0]]
        data_rows = rows
        if "开始时间" in first_row_clean and "结束时间" in first_row_clean:
            start_col_idx = first_row_clean.index("开始时间")
            end_col_idx = first_row_clean.index("结束时间")
            data_rows = rows[1:]

        for idx, r in enumerate(data_rows, 1):
            max_idx = max(start_col_idx, end_col_idx)
            if len(r) <= max_idx:
                errors.append(f"第 {idx} 行列数不足: {','.join(r)}")
                continue
            raw_s = r[start_col_idx].strip()
            raw_e = r[end_col_idx].strip()
            if not raw_s and not raw_e:
                continue
            pairs.append((raw_s, raw_e))

        added_indices, calc_errors = self._append_date_pairs(pairs, holidays)
        errors.extend(calc_errors)

        if added_indices:
            self._refresh_tree_view(changed_set=added_indices)
            self._schedule_clear_highlight()
            self._show_banner(f"CSV 导入成功：新增 {len(added_indices)} 条记录（已高亮标蓝）", changed=True)
        if errors:
            messagebox.showwarning("部分行未导入", f"成功导入 {len(added_indices)} 条。\n以下行存在问题：\n" + "\n".join(errors[:10]))
        elif not added_indices:
            messagebox.showinfo("提示", "未导入任何有效时间段。")

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        indices = sorted([self.tree.index(item) for item in selected], reverse=True)
        for idx in indices:
            del self.items[idx]
        self._refresh_tree_view(changed_set=set())
        self._show_banner(f"已删除 {len(indices)} 条选中记录", changed=False)

    def clear_all(self):
        self.items.clear()
        self._next_seq = 1
        self._refresh_tree_view(changed_set=set())
        self._show_banner("已清空表格", changed=False)

    def export_csv(self):
        if not self.items:
            messagebox.showinfo("提示", "当前表格没有数据可导出。")
            return
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV 文件", "*.csv")],
            initialfile=f"有效天数统计_{datetime.date.today()}.csv"
        )
        if not file_path:
            return

        with open(file_path, "w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "序号", "开始时间", "结束时间",
                "总天数-算头又算尾", "总天数-算头不算尾",
                "总天数扣周末-算头又算尾", "总天数扣周末-算头不算尾",
                "总天数扣假日和请假-算头又算尾", "总天数扣假日和请假-算头不算尾"
            ])
            for entry in self.items:
                writer.writerow(self._row_values(entry))
        messagebox.showinfo("导出成功", f"已保存至：\n{file_path}")

    def _save_config(self):
        data = {
            "holidays_text": self.holiday_text.get("1.0", tk.END).strip(),
            "weekend_mode": self.weekend_mode.get()
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.holiday_text.delete("1.0", tk.END)
                self.holiday_text.insert("1.0", data.get("holidays_text", self.default_holidays_text))
                self.weekend_mode.set(data.get("weekend_mode", "double"))
                return
            except Exception:
                pass
        self.holiday_text.insert("1.0", self.default_holidays_text)


if __name__ == "__main__":
    root = tk.Tk()
    app = WorkdayCalculatorApp(root)
    root.mainloop()