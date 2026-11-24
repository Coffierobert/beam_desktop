"""Beam Designer: a local Tkinter beam analysis desktop application."""
import math
import tkinter as tk
from tkinter import ttk, messagebox

BG, CARD, INK, MUTED, PURPLE, ORANGE = "#f4efff", "#fffefa", "#29243b", "#6c6680", "#6856b5", "#ff8757"

STEEL = {
    "W12x26": (26.0, 14.0, 204.0),
    "W12x30": (30.0, 16.7, 238.0),
    "W10x22": (22.0, 11.1, 118.0),
    "W14x30": (30.0, 21.0, 291.0),
}
LUMBER = {"2x4": (1.5, 3.5), "2x6": (1.5, 5.5), "2x8": (1.5, 7.25), "2x10": (1.5, 9.25), "2x12": (1.5, 11.25)}


def analyze(span, support, loads, sx, ix, modulus, allowable, limit):
    """Numerically integrate load response and Euler-Bernoulli curvature."""
    n = max(800, int(span * 80))
    dx = span / n
    xs = [i * dx for i in range(n + 1)]
    total, moment_load = 0.0, 0.0
    for load in loads:
        if load["kind"] == "point":
            total += load["magnitude"]
            moment_load += load["magnitude"] * load["position"]
        else:
            amount = load["magnitude"] * (load["end"] - load["start"])
            total += amount
            moment_load += amount * (load["start"] + load["end"]) / 2
    if support == "Simply supported":
        rb = moment_load / span
        ra = total - rb
        reactions = [("Left support", ra), ("Right support", rb)]
    else:
        ra = total
        reactions = [("Fixed support", ra), ("Fixed moment", moment_load)]

    shear, moment = [], []
    for x in xs:
        v, m = ra, ra * x
        for load in loads:
            if load["kind"] == "point":
                if x >= load["position"]:
                    v -= load["magnitude"]
                    m -= load["magnitude"] * (x - load["position"])
            else:
                a, b, w = load["start"], load["end"], load["magnitude"]
                length = max(0.0, min(x, b) - a)
                if length:
                    v -= w * length
                    m -= w * length * (x - (a + min(x, b)) / 2)
        if support == "Cantilever":
            m -= moment_load
        shear.append(v)
        moment.append(m)

    # Curvature uses inches and kip-in. Integrate twice; enforce support boundary conditions.
    curvature = [m * 12 / (modulus * ix) if modulus and ix else 0.0 for m in moment]
    slope = [0.0]
    for i in range(n):
        slope.append(slope[-1] + (curvature[i] + curvature[i + 1]) * 0.5 * dx * 12)
    raw = [0.0]
    for i in range(n):
        raw.append(raw[-1] + (slope[i] + slope[i + 1]) * 0.5 * dx * 12)
    if support == "Simply supported":
        correction = raw[-1] / (span * 12)
        deflection = [y - correction * x * 12 for x, y in zip(xs, raw)]
    else:
        deflection = raw
    peaks = lambda values: max(range(len(values)), key=lambda i: abs(values[i]))
    mi, vi, di = peaks(moment), peaks(shear), peaks(deflection)
    max_m = abs(moment[mi])
    return {"xs": xs, "shear": shear, "moment": moment, "deflection": deflection,
            "reactions": reactions, "vpeak": (abs(shear[vi]), xs[vi]),
            "mpeak": (max_m, xs[mi]), "dpeak": (abs(deflection[di]), xs[di]),
            "stress": max_m * 12 / sx if sx else 0.0, "loads": loads}


class BeamDesigner(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Beam Designer")
        self.geometry("1360x900")
        self.minsize(1050, 720)
        self.configure(bg=BG)
        self.point_rows, self.uniform_rows = [], []
        self.vars = {}
        self._build()
        self.validation_example()

    def field(self, parent, label, default, unit=""):
        box = ttk.Frame(parent)
        ttk.Label(box, text=label).pack(anchor="w")
        var = tk.StringVar(value=str(default))
        ent = ttk.Entry(box, textvariable=var, width=14)
        ent.pack(side="left", fill="x", expand=True, pady=(3, 0))
        if unit:
            ttk.Label(box, text=unit, foreground=MUTED).pack(side="left", padx=5)
        self.vars[label] = var
        return box

    def _build(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=CARD)
        style.configure("TLabel", background=BG, foreground=INK, font=("Segoe UI", 9))
        style.configure("Card.TLabel", background=CARD, foreground=INK)
        style.configure("Title.TLabel", background="#423278", foreground="white", font=("Segoe UI", 23, "bold"))
        style.configure("TButton", font=("Segoe UI", 10), padding=7)
        header = tk.Frame(self, bg="#423278", padx=26, pady=18)
        header.pack(fill="x")
        tk.Label(header, text="BEAM DESIGNER", fg="#f8e98e", bg="#423278", font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(header, text="Beam analysis, made clear.", fg="white", bg="#423278", font=("Segoe UI", 22, "bold")).pack(anchor="w")
        tk.Label(header, text="Static vertical loading · Euler–Bernoulli beam model", fg="#eee8ff", bg="#423278").pack(anchor="w")
        main = ttk.Panedwindow(self, orient="horizontal")
        main.pack(fill="both", expand=True, padx=16, pady=14)
        left = ttk.Frame(main, style="Card.TFrame", padding=14)
        main.add(left, weight=0)
        right = ttk.Frame(main, style="Card.TFrame", padding=12)
        main.add(right, weight=1)
        controls = ttk.Frame(left, style="Card.TFrame")
        controls.pack(fill="both", expand=True)
        self._controls(controls)
        self.notebook = ttk.Notebook(right)
        self.notebook.pack(fill="both", expand=True)
        self.canvases = {}
        for key, title in (("beam", "Beam & loads"), ("shear", "Shear force"), ("moment", "Bending moment"), ("deflection", "Deflection")):
            page = ttk.Frame(self.notebook, padding=8)
            self.notebook.add(page, text=title)
            c = tk.Canvas(page, bg=CARD, highlightthickness=0, height=330)
            c.pack(fill="both", expand=True)
            self.canvases[key] = c
        self.summary = ttk.Frame(right, padding=(4, 10))
        self.summary.pack(fill="x")
        self.status = tk.StringVar(value="Load the example or enter beam properties, then run analysis.")
        ttk.Label(right, textvariable=self.status, wraplength=850).pack(anchor="w", pady=(6, 0))

    def _controls(self, p):
        ttk.Label(p, text="Analysis inputs", font=("Segoe UI", 15, "bold"), style="Card.TLabel").pack(anchor="w")
        ttk.Label(p, text="Use consistent units shown beside each input.", style="Card.TLabel").pack(anchor="w", pady=(0, 10))
        self.vars["Support"] = tk.StringVar(value="Simply supported")
        ttk.Label(p, text="Support condition", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(p, textvariable=self.vars["Support"], values=("Simply supported", "Cantilever"), state="readonly", width=24).pack(anchor="w", pady=3)
        self.field(p, "Span", 20, "ft").pack(anchor="w", pady=4)
        self.vars["Material"] = tk.StringVar(value="Steel")
        ttk.Label(p, text="Material", style="Card.TLabel").pack(anchor="w")
        ttk.Combobox(p, textvariable=self.vars["Material"], values=("Steel", "Sawn lumber"), state="readonly", width=24).pack(anchor="w", pady=3)
        self.vars["Section"] = tk.StringVar(value="W12x26")
        ttk.Label(p, text="Section", style="Card.TLabel").pack(anchor="w")
        self.section_combo = ttk.Combobox(p, textvariable=self.vars["Section"], values=list(STEEL), state="readonly", width=24)
        self.section_combo.pack(anchor="w", pady=3)
        self.section_combo.bind("<<ComboboxSelected>>", self.section_changed)
        self.field(p, "E", 29000, "ksi").pack(anchor="w", pady=4)
        self.field(p, "Allowable bending stress", "", "ksi").pack(anchor="w", pady=4)
        self.field(p, "Deflection limit", 0.666667, "in").pack(anchor="w", pady=4)
        self.self_weight = tk.BooleanVar(value=False)
        ttk.Checkbutton(p, text="Include beam self-weight", variable=self.self_weight).pack(anchor="w", pady=5)
        ttk.Label(p, text="Point loads (downward +)", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(10, 2))
        self.point_area = ttk.Frame(p, style="Card.TFrame"); self.point_area.pack(fill="x")
        ttk.Button(p, text="＋ Add point load", command=lambda: self.add_load("point")).pack(anchor="w", pady=3)
        ttk.Label(p, text="Uniform loads (downward +)", style="Card.TLabel", font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(8, 2))
        self.uniform_area = ttk.Frame(p, style="Card.TFrame"); self.uniform_area.pack(fill="x")
        ttk.Button(p, text="＋ Add uniform load", command=lambda: self.add_load("uniform")).pack(anchor="w", pady=3)
        buttons = ttk.Frame(p, style="Card.TFrame"); buttons.pack(fill="x", pady=(12, 2))
        ttk.Button(buttons, text="Validation example", command=self.validation_example).pack(fill="x", pady=2)
        ttk.Button(buttons, text="Run analysis", command=self.run).pack(fill="x", pady=2)
        ttk.Label(p, text="Engineering aid only; verify properties and assumptions before use.", wraplength=260, style="Card.TLabel").pack(anchor="w", pady=8)

    def add_load(self, kind, initial=None):
        area = self.point_area if kind == "point" else self.uniform_area
        row = ttk.Frame(area, style="Card.TFrame"); row.pack(fill="x", pady=2)
        items = []
        values = initial or ((1, 10) if kind == "point" else (1, 0, 20))
        for val in values:
            var = tk.StringVar(value=str(val)); ttk.Entry(row, textvariable=var, width=6).pack(side="left", padx=(0, 3)); items.append(var)
        ttk.Label(row, text="kip @ ft" if kind == "point" else "kip/ft · from to ft", style="Card.TLabel").pack(side="left")
        ttk.Button(row, text="×", width=2, command=lambda: (row.destroy(), self._remove_row(kind, items))).pack(side="right")
        (self.point_rows if kind == "point" else self.uniform_rows).append(items)

    def _remove_row(self, kind, items):
        rows = self.point_rows if kind == "point" else self.uniform_rows
        if items in rows: rows.remove(items)

    def validation_example(self):
        self.vars["Support"].set("Simply supported"); self.vars["Span"].set("20")
        self.vars["Material"].set("Steel"); self.vars["Section"].set("W12x26")
        self.section_combo.configure(values=list(STEEL)); self.vars["E"].set("29000")
        self.vars["Allowable bending stress"].set(""); self.vars["Deflection limit"].set(f"{20*12/360:.6f}")
        for rows in (self.point_rows, self.uniform_rows):
            rows.clear()
        for child in self.point_area.winfo_children(): child.destroy()
        for child in self.uniform_area.winfo_children(): child.destroy()
        self.add_load("uniform", (1, 0, 20))
        self.run()

    def section_changed(self, _event=None):
        sec = self.vars["Section"].get()
        if sec in STEEL:
            self.status.set(f"{sec}: W-shape values in this built-in starter list; catalog release must be verified.")

    def run(self):
        try:
            span = float(self.vars["Span"].get())
            if span <= 0: raise ValueError("Span must be greater than zero.")
            if self.vars["Material"].get() == "Steel":
                w, sx, ix = STEEL[self.vars["Section"].get()]
                density_load = w / 1000 * 1.0  # kip/ft from lb/ft
            else:
                b, h = LUMBER[self.vars["Section"].get()]
                sx, ix = b*h*h/6, b*h**3/12
                density_load = 0.0
            modulus = float(self.vars["E"].get())
            allowable_text = self.vars["Allowable bending stress"].get().strip()
            allowable = float(allowable_text) if allowable_text else None
            limit = float(self.vars["Deflection limit"].get())
            loads = []
            for row in self.point_rows:
                magnitude, x = map(lambda v: float(v.get()), row)
                if not 0 <= x <= span: raise ValueError("Point load positions must be within the span.")
                loads.append({"kind":"point", "magnitude":magnitude, "position":x})
            for row in self.uniform_rows:
                magnitude, a, b = map(lambda v: float(v.get()), row)
                if not 0 <= a < b <= span: raise ValueError("Uniform load limits must satisfy 0 ≤ start < end ≤ span.")
                loads.append({"kind":"uniform", "magnitude":magnitude, "start":a, "end":b})
            if self.self_weight.get() and density_load:
                loads.append({"kind":"uniform", "magnitude":density_load, "start":0, "end":span, "label":"Beam self-weight"})
            if not loads: raise ValueError("Add at least one load.")
            self.result = analyze(span, self.vars["Support"].get(), loads, sx, ix, modulus, allowable, limit)
            self.result.update(span=span, support=self.vars["Support"].get(), section=self.vars["Section"].get(), sx=sx, ix=ix, allowable=allowable, limit=limit)
            self._summary(); self.draw_all()
            self.status.set("Analysis complete. Results are approximate numerical output for preliminary review; verify material data and design assumptions.")
        except (ValueError, KeyError) as exc:
            messagebox.showerror("Check inputs", str(exc))

    def _summary(self):
        for child in self.summary.winfo_children(): child.destroy()
        r=self.result
        ttk.Label(self.summary, text="Key results", font=("Segoe UI", 12, "bold")).pack(anchor="w")
        row=ttk.Frame(self.summary); row.pack(fill="x", pady=4)
        summaries=[("Maximum |V|",f"{r['vpeak'][0]:.3f} kip · x={r['vpeak'][1]:.2f} ft"),("Maximum |M|",f"{r['mpeak'][0]:.3f} kip-ft · x={r['mpeak'][1]:.2f} ft"),("Maximum |δ|",f"{r['dpeak'][0]:.3f} in · x={r['dpeak'][1]:.2f} ft"),("Maximum bending stress",f"{r['stress']:.3f} ksi")]
        for title,value in summaries:
            card=ttk.Frame(row, padding=8, style="Card.TFrame"); card.pack(side="left", fill="x", expand=True, padx=3)
            ttk.Label(card,text=title,style="Card.TLabel").pack(anchor="w"); ttk.Label(card,text=value,style="Card.TLabel",font=("Segoe UI",10,"bold")).pack(anchor="w")
        reactions="Support reactions:  " + "   ·   ".join(f"{name}: {value:.3f} kip" if name != "Fixed moment" else f"{name}: {value:.3f} kip-ft" for name,value in r["reactions"])
        ttk.Label(self.summary,text=reactions).pack(anchor="w",pady=3)
        bending="Not evaluated (allowable required)" if r["allowable"] is None else ("PASS" if r["stress"]<=r["allowable"] else "FAIL")+f" · {r['stress']:.3f} / {r['allowable']:.3f} ksi"
        deflection=("PASS" if r["dpeak"][0]<=r["limit"] else "FAIL")+f" · {r['dpeak'][0]:.3f} / {r['limit']:.3f} in"
        ttk.Label(self.summary,text=f"Bending-stress check: {bending}     Deflection check: {deflection}").pack(anchor="w")

    def draw_all(self):
        if not hasattr(self,"result"): return
        self.draw_beam(); self.draw_plot("shear", self.result["shear"], "V (kip)"); self.draw_plot("moment", self.result["moment"], "M (kip-ft)"); self.draw_plot("deflection", self.result["deflection"], "δ (in)")

    def draw_beam(self):
        c=self.canvases["beam"]; c.delete("all"); c.update_idletasks()
        w=max(c.winfo_width(),500); h=max(c.winfo_height(),280); x0,x1=70,w-55; y=h*.48; scale=(x1-x0)/self.result["span"]
        c.create_text(18,18,text="BEAM / LOAD SCHEMATIC",anchor="nw",fill=PURPLE,font=("Segoe UI",10,"bold"))
        c.create_line(x0,y,x1,y,width=8,fill="#37304e")
        if self.result["support"]=="Simply supported":
            for x in (x0,x1): c.create_polygon(x,y+6,x-17,y+32,x+17,y+32,fill="#d9cfee",outline=PURPLE); c.create_line(x-24,y+33,x+24,y+33,fill=PURPLE,width=2)
        else:
            c.create_rectangle(x0-9,y-24,x0+1,y+25,fill="#c9c1dc",outline=PURPLE)
            for yy in range(int(y-24),int(y+26),8): c.create_line(x0-17,yy,x0-8,yy+8,fill=PURPLE)
        for ld in self.result["loads"]:
            yy=y-65
            if ld["kind"]=="point":
                x=x0+ld["position"]*scale; self.arrow(c,x,yy,x,y-5,"#c34f43")
            else:
                a=x0+ld["start"]*scale; b=x0+ld["end"]*scale
                c.create_line(a,yy,b,yy,fill="#c34f43")
                for i in range(9): self.arrow(c,a+(b-a)*i/8,yy,x0+(a+(b-a)*i/8-x0),y-5,"#c34f43")
        c.create_line(x0,h-40,x1,h-40,fill="#8797aa"); c.create_text((x0+x1)/2,h-24,text=f"{self.result['span']:.2f} ft",fill=INK)
        c.create_text(x0,y+52,text=self.result["section"],anchor="w",fill=PURPLE)

    def arrow(self,c,x1,y1,x2,y2,color):
        c.create_line(x1,y1,x2,y2,fill=color,width=2,arrow=tk.LAST)

    def draw_plot(self,key,values,label):
        c=self.canvases[key]; c.delete("all"); c.update_idletasks()
        w=max(c.winfo_width(),500); h=max(c.winfo_height(),280); left,right,top,bottom=65,w-25,28,h-45
        peak=max((abs(v) for v in values),default=1) or 1; mid=(top+bottom)/2
        c.create_text(12,10,text=label,anchor="nw",fill=PURPLE,font=("Segoe UI",10,"bold"))
        c.create_line(left,mid,right,mid,fill="#aeb7c3"); c.create_line(left,top,left,bottom,fill="#aeb7c3")
        coords=[]
        for i,val in enumerate(values): coords.extend((left+(right-left)*i/(len(values)-1), mid-val/peak*(bottom-top)*.42))
        c.create_line(*coords,fill=PURPLE if key=="deflection" else "#327a72",width=2,smooth=False)
        c.create_text(left, bottom+20,text="0 ft",anchor="w",fill=MUTED); c.create_text(right,bottom+20,text=f"{self.result['span']:.2f} ft",anchor="e",fill=MUTED)
        vals={"shear":self.result["vpeak"],"moment":self.result["mpeak"],"deflection":self.result["dpeak"]}[key]
        c.create_text(right-4,top+6,text=f"Max |{label.split()[0]}| = {vals[0]:.3f} at x = {vals[1]:.2f} ft",anchor="ne",fill=INK)


if __name__ == "__main__":
    BeamDesigner().mainloop()
