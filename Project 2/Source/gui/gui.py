from __future__ import annotations
import sys, time, threading, tracemalloc
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from queue import Queue, Empty
from collections import defaultdict

_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from Source.utils.parser import parse_futoshiki_file, FutoshikiInstance

def _unpack(result_data):
    """Unpack solver result: supports (grid,), (grid,steps), (grid,steps,logs), or just grid."""
    if not isinstance(result_data, tuple):
        return result_data, 0, []
    if len(result_data) >= 3:
        return result_data[0], result_data[1], result_data[2]
    if len(result_data) == 2:
        return result_data[0], result_data[1], []
    return result_data[0], 0, []

# ═══════════════ SOLVERS ═══════════════
SOLVERS: dict[str, callable] = {}

def _register():
    for mod, nm, fn in [
        ("Source.solvers.backtracking",      "Backtracking",      "solve_bt"),
        ("Source.solvers.bruteforce",        "Brute Force",       "solve_bf"),
        ("Source.solvers.forward_chaining",  "Forward Chaining",  "solve_fc"),
        ("Source.solvers.backward_chaining", "Backward Chaining", "solve_bc"),
        ("Source.solvers.astar",             "A* Search",         "solve_astar"),
    ]:
        try:
            m = __import__(mod, fromlist=[fn]); SOLVERS[nm] = getattr(m, fn)
        except (ImportError, AttributeError):
            pass
    if not SOLVERS:
        SOLVERS["Built-in BT"] = _fallback

def _fallback(inst):
    n=inst.n; g=[r[:] for r in inst.grid]; h=inst.h_constraints; v=inst.v_constraints
    emp=[(i,j) for i in range(n) for j in range(n) if g[i][j]==0]
    def ok(r,c,vl):
        for k in range(n):
            if k!=c and g[r][k]==vl: return False
            if k!=r and g[k][c]==vl: return False
        if c>0 and g[r][c-1]!=0:
            if h[r][c-1]==1 and not g[r][c-1]<vl: return False
            if h[r][c-1]==-1 and not g[r][c-1]>vl: return False
        if c<n-1 and g[r][c+1]!=0:
            if h[r][c]==1 and not vl<g[r][c+1]: return False
            if h[r][c]==-1 and not vl>g[r][c+1]: return False
        if r>0 and g[r-1][c]!=0:
            if v[r-1][c]==1 and not g[r-1][c]<vl: return False
            if v[r-1][c]==-1 and not g[r-1][c]>vl: return False
        if r<n-1 and g[r+1][c]!=0:
            if v[r][c]==1 and not vl<g[r+1][c]: return False
            if v[r][c]==-1 and not vl>g[r+1][c]: return False
        return True
    def bt(idx):
        if idx==len(emp): return True
        r,c=emp[idx]
        for vl in range(1,n+1):
            if ok(r,c,vl):
                g[r][c]=vl
                if bt(idx+1): return True
                g[r][c]=0
        return False
    return [r[:] for r in g] if bt(0) else None

def _animated_bt(inst, q, stop):
    n=inst.n; g=[r[:] for r in inst.grid]; h=inst.h_constraints; v=inst.v_constraints
    emp=[(i,j) for i in range(n) for j in range(n) if g[i][j]==0]
    eff=defaultdict(int)
    def ok(r,c,vl):
        for k in range(n):
            if k!=c and g[r][k]==vl: return False
            if k!=r and g[k][c]==vl: return False
        if c>0 and g[r][c-1]!=0:
            if h[r][c-1]==1 and not g[r][c-1]<vl: return False
            if h[r][c-1]==-1 and not g[r][c-1]>vl: return False
        if c<n-1 and g[r][c+1]!=0:
            if h[r][c]==1 and not vl<g[r][c+1]: return False
            if h[r][c]==-1 and not vl>g[r][c+1]: return False
        if r>0 and g[r-1][c]!=0:
            if v[r-1][c]==1 and not g[r-1][c]<vl: return False
            if v[r-1][c]==-1 and not g[r-1][c]>vl: return False
        if r<n-1 and g[r+1][c]!=0:
            if v[r][c]==1 and not vl<g[r+1][c]: return False
            if v[r][c]==-1 and not vl>g[r+1][c]: return False
        return True
    def bt(idx):
        if stop[0]: return False
        if idx==len(emp):
            q.put(("done",[r[:] for r in g],dict(eff))); return True
        r,c=emp[idx]
        for vl in range(1,n+1):
            if stop[0]: return False
            eff[(r,c)]+=1
            q.put(("try",r,c,vl,dict(eff)))
            if ok(r,c,vl):
                g[r][c]=vl; q.put(("set",r,c,vl))
                if bt(idx+1): return True
                g[r][c]=0; q.put(("undo",r,c))
            else:
                q.put(("fail",r,c,vl))
        return False
    if not bt(0) and not stop[0]: q.put(("nosoln",))

# ═══════════════ PALETTE ═══════════════
P = dict(
    bg="#080b14", bg2="#0e1220", panel="#111730", panel2="#161e3a",
    cell="#1c2448", given="#301e68", solved="#0e3828",
    trying="#4a3808", fail="#481018",
    brd="#283060", brd_hi="#4050a0",
    num="#d4d0f0", gnum="#c0a0ff", snum="#50ff90", tnum="#ffd050",
    fnum="#ff5060", domain="#484878", sign="#ff4848",
    lbl="#606088", title="#f0f0ff", sub="#9090b8",
    accent="#5030b0", accent_h="#7050e0",
    green="#18884a", green_h="#20bb60",
    orange="#b86018", orange_h="#e08030",
    red="#b02030", red_h="#e03848",
    cyan="#1888a0", cyan_h="#20b8d0",
    heat=["#1c2448","#2a3018","#484008","#785800","#a84000","#d82000"],
    chart_bg="#0c1028",
    tab_on="#2040a0", tab_off="#182040",
    scol={"Backtracking":"#50ff90","Brute Force":"#ff5060",
          "Forward Chaining":"#ffd050","Backward Chaining":"#c0a0ff",
          "A* Search":"#20d0e0","Built-in BT":"#50ff90"},
)

# ═══════════════ APP ═══════════════
class App:
    F = "Cascadia Code"

    def __init__(self, root):
        self.root = root
        self.root.title("Futoshiki Solver")
        self.root.configure(bg=P["bg"])
        try: self.root.state("zoomed")
        except: pass

        self.inst = None; self.sol = None
        self.agrid = None; self.ahl = {}
        self.anim_on = False; self.anim_stop = [False]
        self.q = None; self.steps = 0
        self.effort = {}; self.show_heat = False
        self.cmp = {}
        self.chart_metric = "time"  # "time" | "mem" | "steps"
        self.log_data = []
        self.last_logs = []
        self.all_results = {}  # {input_name: {algo: {time, mem, steps, n}}}


        self._build()
        _register()
        self.root.after(80, self._rebuild_radios)

    def _build(self):
        # ── Top bar ──
        top = tk.Frame(self.root, bg=P["bg2"], height=50)
        top.pack(fill="x"); top.pack_propagate(False)
        tk.Label(top, text=" FUTOSHIKI", font=(self.F,20,"bold"),
                 fg=P["title"], bg=P["bg2"]).pack(side="left", padx=(20,0))
        tk.Label(top, text="SOLVER", font=(self.F,20),
                 fg=P["accent_h"], bg=P["bg2"]).pack(side="left", padx=(6,0))

        rf = tk.Frame(top, bg=P["bg2"])
        rf.pack(side="right", padx=20)
        self.heat_var = tk.BooleanVar()
        tk.Checkbutton(rf, text="Heatmap", variable=self.heat_var,
                       command=self._toggle_heat, font=(self.F,9),
                       fg=P["orange_h"], bg=P["bg2"], selectcolor=P["panel"],
                       activebackground=P["bg2"], activeforeground=P["orange_h"]
                       ).pack(side="right", padx=8)
        self.status = tk.StringVar(value="Load a puzzle to begin")
        tk.Label(rf, textvariable=self.status, font=(self.F,9),
                 fg=P["sub"], bg=P["bg2"]).pack(side="right", padx=(0,16))

        # ── Body: 3 columns with weight ──
        body = tk.Frame(self.root, bg=P["bg"])
        body.pack(fill="both", expand=True, padx=14, pady=(6,10))

        # Left sidebar — fixed width
        left = tk.Frame(body, bg=P["panel"], width=220)
        left.pack(side="left", fill="y", padx=(0,6))
        left.pack_propagate(False)
        self._build_sidebar(left)

        # Right panel — wider, contains stats + chart + output
        right = tk.Frame(body, bg=P["panel"], width=420)
        right.pack(side="right", fill="y", padx=(6,0))
        right.pack_propagate(False)
        self._build_right(right)

        # Center — grid only, adapts to remaining space
        self.canvas = tk.Canvas(body, bg=P["bg"], highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)
        self.canvas.bind("<Configure>", lambda _: self._draw())

    def _build_sidebar(self, p):
        self._sec(p, "FILE")
        self.fvar = tk.StringVar(value="No file loaded")
        tk.Label(p, textvariable=self.fvar, font=(self.F,8),
                 fg=P["accent_h"], bg=P["panel"], anchor="w", wraplength=190
                 ).pack(fill="x", padx=12, pady=(0,3))
        self._btn(p, "Open File", self._browse, P["accent"])
        self._sep(p)

        self._sec(p, "ALGORITHM")
        self.algo = tk.StringVar()
        self._rf = tk.Frame(p, bg=P["panel"])
        self._rf.pack(fill="x", padx=12)
        self._sep(p)

        self._sec(p, "ACTIONS")
        self._btn(p, "▶   Solve", self._solve, P["green"])
        self._btn(p, "⏩  Animate", self._animate, P["orange"])
        self._btn(p, "⚔   Compare All", self._compare, P["cyan"])
        self._btn(p, "⏹   Stop", self._stop, P["red"])
        self._sep(p)

        sf = tk.Frame(p, bg=P["panel"]); sf.pack(fill="x", padx=12)
        tk.Label(sf, text="SPEED", font=(self.F,7,"bold"),
                 fg=P["lbl"], bg=P["panel"]).pack(side="left")
        self.speed = tk.IntVar(value=80)
        tk.Scale(sf, from_=0, to=100, orient="horizontal", variable=self.speed,
                 showvalue=False, bg=P["panel"], fg=P["num"],
                 troughcolor=P["cell"], highlightthickness=0
                 ).pack(side="left", fill="x", expand=True, padx=(6,0))
        self._sep(p)
        self._btn(p, "⟲  Reset", self._reset, P["accent"])
        self._btn(p, "💾  Save Output", self._save, P["accent"])
        self._btn(p, "📊  Export Log", self._export_log, P["cyan"])
        self._btn(p, "📈  Export Charts", self._export_charts, P["accent"])


    def _build_right(self, p):
        # ── Stats section (compact, horizontal pairs) ──
        self._sec(p, "STATISTICS")
        self._st = {}
        stats_frame = tk.Frame(p, bg=P["panel"])
        stats_frame.pack(fill="x", padx=14, pady=(0,4))

        # 2-column grid for stats
        for idx, (k, lb) in enumerate([("status","Status"),("algo","Algorithm"),
                                        ("size","Grid"),("time","Time"),
                                        ("mem","Memory"),("steps","Steps")]):
            row = idx
            tk.Label(stats_frame, text=lb, font=(self.F,8), fg=P["lbl"],
                     bg=P["panel"], anchor="w").grid(row=row, column=0, sticky="w", padx=(0,8))
            l = tk.Label(stats_frame, text="-", font=(self.F,10,"bold"),
                         fg=P["num"], bg=P["panel"], anchor="w")
            l.grid(row=row, column=1, sticky="w")
            self._st[k] = l

        self._sep(p)

        # ── Chart section with metric tabs ──
        self._sec(p, "PERFORMANCE CHART")

        # Tab buttons
        tab_frame = tk.Frame(p, bg=P["panel"])
        tab_frame.pack(fill="x", padx=14, pady=(0,4))

        self.chart_metric = "time"
        self.tab_btns = {}
        for metric, label in [("time","Time (s)"), ("mem","Memory (KB)"), ("steps","Steps")]:
            b = tk.Label(tab_frame, text=label, font=(self.F,8,"bold"),
                         fg=P["title"], bg=P["tab_off"], cursor="hand2",
                         padx=10, pady=3)
            b.bind("<Button-1>", lambda _e, m=metric: self._set_metric(m))
            b.pack(side="left", padx=(0,3), pady=0)
            self.tab_btns[metric] = b
        self._update_tabs()

        # Chart canvas — tall enough to be useful
        self.chart = tk.Canvas(p, bg=P["chart_bg"], highlightthickness=0, height=200)
        self.chart.pack(fill="x", padx=14, pady=(0,4))

        self._sep(p)

        # ── Output section ──
        self._sec(p, "OUTPUT PREVIEW")
        self.out = tk.Text(p, font=(self.F,8), fg=P["num"], bg=P["cell"],
                           relief="flat", wrap="none", state="disabled")
        self.out.pack(fill="both", expand=True, padx=14, pady=(0,10))

    # ─── UI atoms ────────────────────────────
    def _sec(self, p, t):
        tk.Label(p, text=t, font=(self.F,8,"bold"), fg=P["lbl"],
                 bg=P["panel"], anchor="w").pack(fill="x", padx=14, pady=(8,2))
    def _sep(self, p):
        tk.Frame(p, bg=P["brd"], height=1).pack(fill="x", padx=14, pady=6)

    def _label_btn(self, p, t, cmd, bg, fg, hover_bg=None, *, font=None, padx=12, pady=2, ipady=5):
        # tk.Button background can be ignored on some platforms/themes (commonly macOS aqua),
        # making buttons look "transparent". Label respects bg reliably.
        if hover_bg is None:
            hover_bg = bg
        if font is None:
            font = (self.F, 9, "bold")
        b = tk.Label(p, text=t, font=font, fg=fg, bg=bg, cursor="hand2", pady=ipady)
        b.pack(fill="x", padx=padx, pady=pady)
        b.bind("<Button-1>", lambda _e: cmd())
        b.bind("<Enter>", lambda _e: b.config(bg=hover_bg))
        b.bind("<Leave>", lambda _e: b.config(bg=bg))
        return b

    def _btn(self, p, t, cmd, col):
        h={P["accent"]:P["accent_h"],P["green"]:P["green_h"],
           P["orange"]:P["orange_h"],P["red"]:P["red_h"],
           P["cyan"]:P["cyan_h"]}.get(col,col)
        self._label_btn(p, t, cmd, col, "#fff", h)

    def _rebuild_radios(self):
        for w in self._rf.winfo_children(): w.destroy()
        nms=list(SOLVERS.keys()) or ["(none)"]
        self.algo.set(nms[0])
        for nm in nms:
            tk.Radiobutton(self._rf, text=nm, variable=self.algo, value=nm,
                           font=(self.F,9), fg=P["num"], bg=P["panel"],
                           selectcolor=P["cell"], activebackground=P["panel"],
                           activeforeground=P["num"], anchor="w").pack(fill="x")

    def _ss(self,k,v,c=None):
        l=self._st.get(k)
        if l: l.config(text=str(v))
        if l and c: l.config(fg=c)
    def _cs(self):
        for l in self._st.values(): l.config(text="-",fg=P["num"])
        self.out.config(state="normal"); self.out.delete("1.0","end"); self.out.config(state="disabled")

    # ─── Chart metric tabs ───────────────────
    def _set_metric(self, m):
        self.chart_metric = m
        self._update_tabs()
        self._draw_chart()

    def _update_tabs(self):
        for mk, b in self.tab_btns.items():
            if mk == self.chart_metric:
                b.config(bg=P["tab_on"], fg=P["title"])
            else:
                b.config(bg=P["tab_off"], fg=P["lbl"])

    # ─── Grid ────────────────────────────────
    def _draw(self):
        c=self.canvas; c.delete("all")
        if not self.inst:
            cw,ch=c.winfo_width(),c.winfo_height()
            c.create_text(cw//2,ch//2-12,text="FUTOSHIKI",
                          font=(self.F,30,"bold"),fill=P["brd"])
            c.create_text(cw//2,ch//2+24,text="Open a puzzle file to begin",
                          font=(self.F,11),fill=P["lbl"])
            return
        n=self.inst.n
        show=self.agrid or self.sol or self.inst.grid
        cw,ch=c.winfo_width(),c.winfo_height()
        gap=28; sz=min((cw-50-(n-1)*gap)/n,(ch-50-(n-1)*gap)/n,80); sz=max(sz,30)
        gw=n*sz+(n-1)*gap; ox=(cw-gw)/2; oy=(ch-gw)/2
        mx_e=max(self.effort.values()) if self.effort else 1

        for i in range(n):
            for j in range(n):
                x,y=ox+j*(sz+gap),oy+i*(sz+gap)
                val=show[i][j]; given=self.inst.grid[i][j]!=0
                is_sol=self.sol and not given and val!=0
                is_anim=self.agrid and not given and val!=0

                if self.show_heat and (i,j) in self.effort:
                    bg=P["heat"][min(int((self.effort[(i,j)]/mx_e)*5),5)]
                elif (i,j) in self.ahl: bg=self.ahl[(i,j)]
                elif given: bg=P["given"]
                elif is_sol or is_anim: bg=P["solved"]
                else: bg=P["cell"]

                r=6
                pts=[x+r,y,x+sz-r,y,x+sz,y,x+sz,y+r,x+sz,y+sz-r,
                     x+sz,y+sz,x+sz-r,y+sz,x+r,y+sz,x,y+sz,x,y+sz-r,x,y+r,x,y]
                brd=P["brd_hi"] if (i,j) in self.ahl else P["brd"]
                c.create_polygon(pts,fill=bg,outline=brd,width=2,smooth=True)

                if val!=0:
                    if (i,j) in self.ahl and self.ahl[(i,j)]==P["fail"]: fg=P["fnum"]
                    elif (i,j) in self.ahl: fg=P["tnum"]
                    elif given: fg=P["gnum"]
                    elif is_sol or is_anim: fg=P["snum"]
                    else: fg=P["num"]
                    c.create_text(x+sz/2,y+sz/2,text=str(val),
                                  font=(self.F,max(int(sz*.46),14),"bold"),fill=fg)
                elif not self.agrid and not self.sol:
                    dom=self._domain(i,j,show)
                    if dom and len(dom)<n:
                        c.create_text(x+sz/2,y+sz/2,
                                      text=" ".join(str(d) for d in sorted(dom)),
                                      font=(self.F,max(int(sz*.16),7)),fill=P["domain"])

                if j<n-1:
                    s=_hs(self.inst.h_constraints[i][j])
                    if s: c.create_text(x+sz+gap/2,y+sz/2,text=s,
                              font=(self.F,max(int(gap*.6),14),"bold"),fill=P["sign"])
                if i<n-1:
                    s=_vs(self.inst.v_constraints[i][j])
                    if s: c.create_text(x+sz/2,y+sz+gap/2,text=s,
                              font=(self.F,max(int(gap*.6),14),"bold"),fill=P["sign"])

    def _domain(self,r,c,g):
        n=self.inst.n; h=self.inst.h_constraints; v=self.inst.v_constraints
        used=set()
        for k in range(n):
            if g[r][k]: used.add(g[r][k])
            if g[k][c]: used.add(g[k][c])
        out=set()
        for vl in range(1,n+1):
            if vl in used: continue
            ok=True
            if c>0 and g[r][c-1]:
                if h[r][c-1]==1 and not g[r][c-1]<vl: ok=False
                if h[r][c-1]==-1 and not g[r][c-1]>vl: ok=False
            if c<n-1 and g[r][c+1]:
                if h[r][c]==1 and not vl<g[r][c+1]: ok=False
                if h[r][c]==-1 and not vl>g[r][c+1]: ok=False
            if r>0 and g[r-1][c]:
                if v[r-1][c]==1 and not g[r-1][c]<vl: ok=False
                if v[r-1][c]==-1 and not g[r-1][c]>vl: ok=False
            if r<n-1 and g[r+1][c]:
                if v[r][c]==1 and not vl<g[r+1][c]: ok=False
                if v[r][c]==-1 and not vl>g[r+1][c]: ok=False
            if ok: out.add(vl)
        return out

    # ─── Browse ──────────────────────────────
    def _browse(self):
        if self.anim_on: messagebox.showwarning("","Stop animation first."); return
        d=_ROOT/"Inputs"
        fp=filedialog.askopenfilename(initialdir=str(d) if d.exists() else str(_ROOT),
                                      filetypes=[("Text","*.txt"),("All","*.*")])
        if not fp: return
        try:
            self.inst=parse_futoshiki_file(Path(fp))
            self.sol=None; self.agrid=None; self.ahl={}
            self.effort={}; self.show_heat=False; self.heat_var.set(False)
            self.cmp={}; self.chart.delete("all")
            self.fvar.set(Path(fp).name); self._cs()
            self._ss("size",f"{self.inst.n} x {self.inst.n}"); self._ss("status","Ready",P["snum"])
            self._draw(); self.status.set(f"Loaded {Path(fp).name}")
        except Exception as e: messagebox.showerror("",str(e))

    # ─── Solve ───────────────────────────────
    def _solve(self):
        if not self.inst: messagebox.showwarning("","Open a file first."); return
        if self.anim_on: messagebox.showwarning("","Stop animation first."); return
        nm=self.algo.get(); fn=SOLVERS.get(nm)
        if not fn: messagebox.showerror("",f"'{nm}' not found."); return
        self.agrid=None; self.ahl={}
        self._ss("status","Solving...",P["orange_h"]); self._ss("algo",nm)
        self.status.set(f"Solving with {nm}..."); self.root.update()
        def run():
            try:
                tracemalloc.start()
                t0 = time.perf_counter()
                result_data = fn(self.inst)
                g, step_count, solver_logs = _unpack(result_data)
                t = time.perf_counter() - t0
                _, pk = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                s = {"time": round(t, 4), "mem": round(pk/1024, 2), "steps": step_count}
                if g is None:
                    self.root.after(0, self._no_sol)
                else:
                    self.root.after(0, lambda: self._ok(g, s, nm, solver_logs))
            except NotImplementedError as e:
                self.root.after(0, lambda: self._ni(str(e)))
            except Exception as e:
                self.root.after(0, lambda: self._er(str(e)))
            
        threading.Thread(target=run,daemon=True).start()

    def _ok(self,g,s,nm,solver_logs=None):
        self.last_logs = solver_logs or []
        self.sol=g
        self._ss("status","Solved",P["snum"]); self._ss("time",f"{s['time']}s")
        self._ss("mem",f"{s['mem']} KB"); self._draw(); self._out_text(g)
        self._ss("steps", s['steps'])
        self.status.set(f"Solved by {nm} in {s['time']}s")
        self.cmp[nm] = {"time": s["time"], "mem": s["mem"], "steps": s["steps"], "ok": True}
        self.log_data.append({
            "input": self.fvar.get(),
            "grid_size": f"{self.inst.n}x{self.inst.n}",
            "algo": nm,
            "time": s["time"],
            "mem": s["mem"],
            "steps": s["steps"],
        })
        inp = self.fvar.get()
        if inp not in self.all_results:
            self.all_results[inp] = {}
        self.all_results[inp][nm] = {
            "time": s["time"], "mem": s["mem"],
            "steps": s["steps"], "n": self.inst.n,
        }
        self._draw_chart()

    def _no_sol(self):
        self._ss("status","No solution",P["red_h"]); self.status.set("No solution.")
    def _ni(self,m):
        self._ss("status","N/A",P["orange_h"]); self.status.set(m); messagebox.showinfo("",m)
    def _er(self,m):
        self._ss("status","Error",P["red_h"]); self.status.set(m); messagebox.showerror("",m)

    # ─── Animate ─────────────────────────────
    def _animate(self):
        if not self.inst: messagebox.showwarning("","Open a file first."); return
        if self.anim_on: return
        self.anim_on=True; self.anim_stop=[False]; self.sol=None
        self.agrid=[r[:] for r in self.inst.grid]; self.ahl={}
        self.steps=0; self.effort={}; self.show_heat=False; self.heat_var.set(False)
        self.q=Queue(); self._cs()
        self._ss("status","Animating...",P["orange_h"]); self._ss("algo","Backtracking")
        self._ss("size",f"{self.inst.n} x {self.inst.n}")
        self.status.set("Animation running...")
        threading.Thread(target=_animated_bt,args=(self.inst,self.q,self.anim_stop),daemon=True).start()
        self._poll()

    def _poll(self):
        if not self.anim_on: return
        spd=self.speed.get(); delay=max(1,int(350*(1-spd/100)**2)); batch=max(1,spd//12)
        for _ in range(batch):
            try: step=self.q.get_nowait()
            except Empty: break
            k=step[0]
            if k=="try":
                _,r,c,vl,ef=step; self.steps+=1; self.effort=ef
                self.agrid[r][c]=vl; self.ahl={(r,c):P["trying"]}; self._ss("steps",str(self.steps))
            elif k=="set": _,r,c,vl=step; self.agrid[r][c]=vl; self.ahl={(r,c):P["solved"]}
            elif k=="fail": _,r,c,vl=step; self.agrid[r][c]=0; self.ahl={(r,c):P["fail"]}
            elif k=="undo": _,r,c=step; self.agrid[r][c]=0; self.ahl={(r,c):P["fail"]}
            elif k=="done":
                g,ef=step[1],step[2]; self.sol=g; self.effort=ef
                self.agrid=None; self.ahl={}; self.anim_on=False
                self._ss("status","Solved",P["snum"]); self._draw(); self._out_text(g)
                self.status.set(f"Done - {self.steps} steps"); return
            elif k=="nosoln":
                self.anim_on=False; self.agrid=None; self.ahl={}
                self._ss("status","No solution",P["red_h"]); self._draw(); return
        self._draw(); self.root.after(delay,self._poll)

    def _stop(self):
        if self.anim_on:
            self.anim_stop[0]=True; self.anim_on=False; self.agrid=None; self.ahl={}
            self._ss("status","Stopped",P["orange_h"]); self._draw(); self.status.set("Stopped.")

    # ─── Compare ─────────────────────────────
    def _compare(self):
        if not self.inst: messagebox.showwarning("","Open a file first."); return
        if self.anim_on: messagebox.showwarning("","Stop animation first."); return
        self._ss("status","Comparing...",P["orange_h"])
        self.status.set("Running all algorithms..."); self.root.update()
        def run():
            res={}; timeout=10
            for nm,fn in SOLVERS.items():
                self.root.after(0,lambda n=nm: self.status.set(f"Running {n}..."))
                try:
                    box = [None, 0, 0, 0]
                    def worker(f=fn):
                        try:
                            tracemalloc.start()
                            t0 = time.perf_counter()
                            res_val = f(self.inst)
                            grid_res, steps_res, _ = _unpack(res_val)
                            t = time.perf_counter() - t0
                            _, pk = tracemalloc.get_traced_memory()
                            tracemalloc.stop()
                            box[0] = grid_res
                            box[1] = round(t, 4)
                            box[2] = round(pk/1024, 2)
                            box[3] = steps_res
                        except NotImplementedError:
                            box[0] = "NI"
                        except Exception:
                            box[0] = "ERR"
                    th=threading.Thread(target=worker,daemon=True)
                    th.start(); th.join(timeout=timeout)
                    if th.is_alive(): res[nm] = {"time": timeout, "mem": 0, "steps": 0, "ok": False, "note": "timeout"}
                    elif box[0] in ("NI", "ERR"): res[nm] = {"time": 0, "mem": 0, "steps": 0, "ok": None}
                    else: res[nm] = {"time": box[1], "mem": box[2], "steps": box[3], "ok": True}
                except: res[nm] = {"time": 0, "mem": 0, "steps": 0, "ok": None}
            self.root.after(0,lambda:self._cmp_done(res))
        threading.Thread(target=run,daemon=True).start()

    def _cmp_done(self, res):
        self.cmp=res; self._draw_chart()
        inp = self.fvar.get()
        if inp not in self.all_results:
            self.all_results[inp] = {}
        for nm, info in res.items():
            if info.get("ok"):
                self.all_results[inp][nm] = {
                    "time": info["time"], "mem": info["mem"],
                    "steps": info["steps"], "n": self.inst.n,
                }
        for nm, info in res.items():
            if info.get("ok"):
                self.log_data.append({
                    "input": self.fvar.get(),
                    "grid_size": f"{self.inst.n}x{self.inst.n}",
                    "algo": nm,
                    "time": info["time"],
                    "mem": info["mem"],
                    "steps": info["steps"],
                })
        solved=[k for k,v in res.items() if v.get("ok")]
        if solved:
            fastest=min(solved,key=lambda k:res[k]["time"])
            self._ss("status",f"Winner: {fastest}",P["snum"])
            self._ss("algo",fastest); self._ss("time",f"{res[fastest]['time']}s")
            self._ss("mem",f"{res[fastest]['mem']} KB")
            self.status.set(f"Fastest: {fastest} ({res[fastest]['time']}s)")
        else:
            self._ss("status","No solver OK",P["red_h"])

    # ─── Chart drawing ───────────────────────
    def _draw_chart(self):
        c=self.chart; c.delete("all")
        cw=c.winfo_width() or 380; ch=c.winfo_height() or 200

        if not self.cmp:
            c.create_text(cw//2,ch//2,text="Run Solve or Compare All\nto see results",
                          font=(self.F,9),fill=P["lbl"],justify="center"); return

        metric=self.chart_metric
        unit={"time":"s","mem":"KB","steps":""}[metric]
        all_nms=list(self.cmp.keys())
        n=len(all_nms)
        if n==0: return

        pad_l,pad_r,pad_t,pad_b=55,15,12,30
        area_w=cw-pad_l-pad_r; area_h=ch-pad_t-pad_b
        group_w=area_w/n; bar_w=max(group_w*0.5,14)

        # Get values
        vals=[]
        for nm in all_nms:
            info=self.cmp[nm]
            if info.get("ok"):
                vals.append(info.get(metric,0))
            else:
                vals.append(None)

        ok_vals=[v for v in vals if v is not None]
        mx=max(ok_vals) if ok_vals else 1
        if mx==0: mx=0.001

        # Grid lines + Y axis
        for i in range(5):
            yy=pad_t+int(area_h*i/4)
            c.create_line(pad_l,yy,cw-pad_r,yy,fill=P["brd"],dash=(2,4))
            lv=mx*(1-i/4)
            if metric=="time":
                txt=f"{lv:.4f}"
            elif metric=="mem":
                txt=f"{lv:.1f}"
            else:
                txt=f"{int(lv)}"
            c.create_text(pad_l-6,yy,text=txt,font=(self.F,6),fill=P["lbl"],anchor="e")

        # Bars
        for idx,nm in enumerate(all_nms):
            x_center=pad_l+idx*group_w+group_w/2
            info=self.cmp[nm]
            col=P["scol"].get(nm,"#888888")
            v=vals[idx]

            if v is not None and info.get("ok"):
                bh=max((v/mx)*area_h,4)
                x=x_center-bar_w/2; y=pad_t+area_h-bh
                c.create_rectangle(x,y,x+bar_w,pad_t+area_h,fill=col,outline="")
                # Highlight top edge
                c.create_rectangle(x,y,x+bar_w,y+2,fill="#ffffff",outline="",stipple="gray25")
                # Value label
                if metric=="time":
                    vt=f"{v:.4f}{unit}"
                elif metric=="mem":
                    vt=f"{v:.1f}{unit}"
                else:
                    vt=f"{int(v)}"
                c.create_text(x_center,y-9,text=vt,font=(self.F,7,"bold"),fill=col)
            elif info.get("note")=="timeout":
                c.create_text(x_center,pad_t+area_h-16,text="TIMEOUT",
                              font=(self.F,7,"bold"),fill=P["orange_h"])
            else:
                c.create_text(x_center,pad_t+area_h-16,text="N/A",
                              font=(self.F,8),fill=P["lbl"])

            # Name
            c.create_text(x_center,pad_t+area_h+14,text=nm[:14],
                          font=(self.F,7),fill=P["sub"])

    # ─── Heatmap ─────────────────────────────
    def _toggle_heat(self):
        self.show_heat=self.heat_var.get(); self._draw()

    # ─── Output / Reset / Save ───────────────
    def _out_text(self,g):
        n=self.inst.n; lines=[]
        for i in range(n):
            parts=[]
            for j in range(n):
                parts.append(str(g[i][j]))
                if j<n-1:
                    s=_hs(self.inst.h_constraints[i][j]); parts.append(s if s else " ")
            lines.append(" ".join(parts))
            if i<n-1:
                vp=[]
                for j in range(n):
                    s=_vs(self.inst.v_constraints[i][j]); vp.append(s if s else " ")
                lines.append("   ".join(vp))
        self.out.config(state="normal"); self.out.delete("1.0","end")
        self.out.insert("1.0","\n".join(lines)); self.out.config(state="disabled")

    def _export_log(self):
        if not self.log_data and not self.last_logs:
            messagebox.showwarning("", "No data. Run Solve or Compare first.")
            return
        d = _ROOT / "Outputs"
        fp = filedialog.asksaveasfilename(
            initialdir=str(d), defaultextension=".csv",
            filetypes=[("CSV (statistics)", "*.csv"), ("TXT (step detail)", "*.txt")])
        if not fp:
            return

        import csv

        if fp.endswith(".csv"):
            with open(fp, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=["input","grid_size","algo","time","mem","steps"])
                writer.writeheader()
                for row in self.log_data:
                    writer.writerow(row)
            self.status.set(f"CSV exported: {Path(fp).name}")

        else:
            with open(fp, "w", encoding="utf-8") as f:
                f.write(f"=== Futoshiki Solver Log ===\n")
                f.write(f"Input: {self.fvar.get()}\n")
                if self.inst:
                    f.write(f"Grid: {self.inst.n}x{self.inst.n}\n")
                f.write(f"Total steps: {len(self.last_logs)}\n")
                f.write(f"{'='*40}\n\n")
                for line in self.last_logs:
                    f.write(line + "\n")
            self.status.set(f"Log exported: {Path(fp).name}")

    def _export_charts(self):
        """Export performance charts as PNG images."""
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
        except ImportError:
            messagebox.showerror("", "Cần cài matplotlib:\npip install matplotlib")
            return
 
        if not self.cmp and not self.all_results:
            messagebox.showwarning("", "No data. Run Solve or Compare first.")
            return
 
        d = _ROOT / "Outputs"
        folder = filedialog.askdirectory(title="Choose folder to save charts", initialdir=str(d))
        if not folder:
            return
        folder = Path(folder)
 
        colors = {
            "Backtracking": "#50ff90", "Brute Force": "#ff5060",
            "Forward Chaining": "#ffd050", "Backward Chaining": "#c0a0ff",
            "A* Search": "#20d0e0", "Built-in BT": "#50ff90",
        }
        dark_bg = "#0c1028"
        grid_color = "#283060"
        text_color = "#d4d0f0"
        label_color = "#9090b8"
 
        plt.rcParams.update({
            "figure.facecolor": dark_bg,
            "axes.facecolor": dark_bg,
            "axes.edgecolor": grid_color,
            "axes.labelcolor": text_color,
            "xtick.color": label_color,
            "ytick.color": label_color,
            "text.color": text_color,
            "grid.color": grid_color,
            "grid.alpha": 0.3,
            "font.family": "monospace",
            "font.size": 10,
        })
 
        saved = []
 
        # ── Chart 1: Current comparison (per algorithm) ──
        if self.cmp:
            ok = {k: v for k, v in self.cmp.items() if v.get("ok")}
            if ok:
                for metric, unit, title in [
                    ("time", "s", "Time"), ("mem", "KB", "Memory"), ("steps", "", "Steps")
                ]:
                    fig, ax = plt.subplots(figsize=(8, 5))
                    names = list(ok.keys())
                    vals = [ok[n][metric] for n in names]
                    cols = [colors.get(n, "#888") for n in names]
                    bars = ax.bar(names, vals, color=cols, edgecolor="none", width=0.6)
                    for bar, val in zip(bars, vals):
                        fmt = f"{val:.4f}{unit}" if metric == "time" else (f"{val:.1f}{unit}" if metric == "mem" else f"{int(val)}")
                        ax.text(bar.get_x() + bar.get_width()/2, bar.get_height(),
                                fmt, ha="center", va="bottom", fontsize=9, color=text_color)
                    ax.set_title(f"{title} Comparison — {self.fvar.get()}", fontsize=13, pad=12)
                    ax.set_ylabel(f"{title} ({unit})" if unit else title)
                    ax.grid(axis="y", linestyle="--")
                    plt.xticks(rotation=15, ha="right")
                    plt.tight_layout()
                    path = folder / f"compare_{metric}.png"
                    fig.savefig(path, dpi=150, facecolor=dark_bg)
                    plt.close(fig)
                    saved.append(path.name)
 
        # ── Chart 2: Scalability (N vs Time/Steps) ──
        if self.all_results and len(self.all_results) >= 2:
            # Collect data: {algo: [(n, time, steps), ...]}
            algo_data = {}
            for inp, algos in self.all_results.items():
                for algo, info in algos.items():
                    if algo not in algo_data:
                        algo_data[algo] = []
                    algo_data[algo].append((info["n"], info["time"], info["steps"]))
 
            # Sort by n
            for algo in algo_data:
                algo_data[algo].sort(key=lambda x: x[0])
 
            for metric_idx, (ylabel, title, fname) in enumerate([
                ("Time (s)", "Scalability: Grid Size vs Time", "scalability_time"),
                ("Steps", "Scalability: Grid Size vs Steps", "scalability_steps"),
            ]):
                fig, ax = plt.subplots(figsize=(9, 5.5))
                for algo, data in algo_data.items():
                    ns = [d[0] for d in data]
                    vs = [d[1] if metric_idx == 0 else d[2] for d in data]
                    col = colors.get(algo, "#888")
                    ax.plot(ns, vs, "o-", color=col, label=algo, linewidth=2, markersize=7)
                ax.set_xlabel("Grid Size (N)")
                ax.set_ylabel(ylabel)
                ax.set_title(title, fontsize=13, pad=12)
                ax.legend(facecolor=dark_bg, edgecolor=grid_color, fontsize=9)
                ax.grid(True, linestyle="--")
                if metric_idx == 1 and max(d[2] for data in algo_data.values() for d in data) > 100:
                    ax.set_yscale("log")
                    ax.set_ylabel(f"{ylabel} (log scale)")
                plt.tight_layout()
                path = folder / f"{fname}.png"
                fig.savefig(path, dpi=150, facecolor=dark_bg)
                plt.close(fig)
                saved.append(path.name)
 
        # ── Chart 3: Per-algorithm detail ──
        if self.cmp:
            ok = {k: v for k, v in self.cmp.items() if v.get("ok")}
            for algo, info in ok.items():
                fig, axes = plt.subplots(1, 3, figsize=(12, 4))
                metrics = [
                    ("time", "Time (s)", f"{info['time']:.4f}s"),
                    ("mem", "Memory (KB)", f"{info['mem']:.1f}KB"),
                    ("steps", "Steps", f"{int(info['steps'])}"),
                ]
                col = colors.get(algo, "#888")
                for ax, (key, label, val_str) in zip(axes, metrics):
                    val = info[key]
                    ax.bar([label], [val], color=col, width=0.5)
                    ax.text(0, val, val_str, ha="center", va="bottom", fontsize=11, color=text_color)
                    ax.set_title(label, fontsize=10)
                    ax.grid(axis="y", linestyle="--")
                fig.suptitle(f"{algo} — {self.fvar.get()}", fontsize=13)
                plt.tight_layout()
                safe_name = algo.replace(" ", "_").replace("*", "star")
                path = folder / f"detail_{safe_name}.png"
                fig.savefig(path, dpi=150, facecolor=dark_bg)
                plt.close(fig)
                saved.append(path.name)
 
        if saved:
            self.status.set(f"Exported {len(saved)} charts to {folder.name}/")
            messagebox.showinfo("Export Complete",
                f"Saved {len(saved)} charts:\n\n" + "\n".join(saved))
        else:
            messagebox.showwarning("", "No charts generated. Need more data.")

    def _reset(self):
        if self.anim_on: self._stop()
        self.sol=None; self.agrid=None; self.ahl={}
        self.effort={}; self.show_heat=False; self.heat_var.set(False)
        self.cmp={}; self.chart.delete("all")
        self.log_data = []
        self.last_logs = []
        self._cs()
        if self.inst:
            self._ss("size",f"{self.inst.n} x {self.inst.n}"); self._ss("status","Ready",P["snum"])
        self._draw(); self.status.set("Reset.")

    def _save(self):
        if not self.sol: messagebox.showwarning("","No solution."); return
        d=_ROOT/"Outputs"
        fp=filedialog.asksaveasfilename(initialdir=str(d),defaultextension=".txt",
                                        filetypes=[("Text","*.txt")])
        if not fp: return
        with open(fp,"w") as f:
            for r in self.sol: f.write(" ".join(str(v) for v in r)+"\n")
        self.status.set(f"Saved: {Path(fp).name}")


def _hs(v):
    v=int(v) if not isinstance(v,int) else v
    return "<" if v==1 else (">" if v==-1 else None)
def _vs(v):
    v=int(v) if not isinstance(v,int) else v
    return "\u2228" if v==-1 else ("\u2227" if v==1 else None)

def main():
    root=tk.Tk(); root.geometry("1300x800")
    try: root.state("zoomed")
    except: pass
    App(root); root.mainloop()

if __name__=="__main__": main()
