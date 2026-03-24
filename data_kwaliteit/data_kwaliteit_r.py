"""
Data Quality Check — Wijkprofiel Rotterdam 2014-2024
=====================================================
Checks: Compleetheid, Validiteit, Consistentie, Duplicatie

Werkt met de Excel-structuur:
  - Sheets: SI, FI-subj, FI-obj, VI  (elk per jaar 2014/2016/2018/2020/2022/2024)
  - Rij 1  : categorie-codes  (Zs, Ss, Ps, etc.)
  - Rij 2  : kolomcodes        (variabelenamen)
  - Rij 3  : kolomlabels       (volledige omschrijving)
  - Rij 4+ : data              (naam gebied, wijknr, BUURT85, waarden...)
"""

import pandas as pd
import numpy as np

# ─────────────────────────────────────────────────────────
# Config
# ─────────────────────────────────────────────────────────
EXCEL_PATH = r"D:\Interdisciplinair_Team3\dataset\Datastructuur wijkprofiel_2024_totaal_Dataset voor derden_basis voor gebieden.xlsx"

SI_SHEETS      = ["SI 2014", "SI 2016", "SI 2018", "SI 2020", "SI 2022", "SI 2024"]
FI_SUBJ_SHEETS = ["FI-subj 2014", "FI-subj 2016", "FI-subj 2018",
                  "FI-subj 2020", "FI-subj 2022", "FI-subj 2024"]
FI_OBJ_SHEETS  = ["FI-obj 2014", "FI-obj 2016", "FI-obj 2018",
                  "FI-obj 2020", "FI-obj 2022", "FI-obj 2024"]
VI_SHEETS      = ["VI 2014", "VI 2016", "VI 2018", "VI 2020", "VI 2022", "VI 2024"]
ALL_DATA_SHEETS = SI_SHEETS + FI_SUBJ_SHEETS + FI_OBJ_SHEETS + VI_SHEETS

ID_COLS = ["naam_gebied", "wijknr", "buurt85"]

INDEX_COLS_PATTERN = ["si", "si_s", "si_o", "fi", "fis", "fio", "vi", "vis", "vio"]

PCT_SUFFIX = "_p"


# ─────────────────────────────────────────────────────────
# Helper: laad één sheet als pandas DataFrame
# ─────────────────────────────────────────────────────────
def load_sheet(path: str, sheet_name: str) -> pd.DataFrame:
    """
    Laad een wijkprofiel-sheet. De eerste 3 rijen zijn metadata;
    rij 2 (index 1) bevat de technische kolomnamen die we als header gebruiken.
    Rij 3 (index 2) bevat de labels — deze slaan we over.
    """
    df = pd.read_excel(
        path,
        sheet_name=sheet_name,
        header=1,       # rij 2 = variabelenamen
        skiprows=[2],   # sla de label-rij (rij 3) over na header
        engine="openpyxl"
    )
    # Verwijder volledig lege rijen
    df = df.dropna(how="all")
    # Kolommen schoon: verwijder spaties, lowercase
    df.columns = [str(c).strip().lower().replace(" ", "_") for c in df.columns]
    # Jaar toevoegen
    year = sheet_name.split(" ")[-1]
    df["jaar"] = int(year)
    return df


# ─────────────────────────────────────────────────────────
# 1. COMPLEETHEID
# ─────────────────────────────────────────────────────────
def check_compleetheid(df: pd.DataFrame, sheet_name: str) -> None:
    total = len(df)
    if total == 0:
        print(f"  [LEEG]  {sheet_name}")
        return

    print(f"\n  Sheet: {sheet_name}  ({total} rijen, {len(df.columns)} kolommen)")

    null_counts = df.isnull().sum()
    probleem_cols = null_counts[null_counts > 0].sort_values(ascending=False)

    if probleem_cols.empty:
        print("    [OK]  Geen missende waarden")
    else:
        for col_name, cnt in probleem_cols.items():
            pct = round(cnt / total * 100, 1)
            print(f"    [!]  {col_name:<45} {cnt:>4} nulls ({pct}%)")


# ─────────────────────────────────────────────────────────
# 2. VALIDITEIT
# ─────────────────────────────────────────────────────────
def check_validiteit(df: pd.DataFrame, sheet_name: str) -> None:
    total = len(df)
    print(f"\n  Sheet: {sheet_name}")

    cols = df.columns.tolist()

    # 2a. Percentage-kolommen (_p): verwacht [0, 1]
    pct_cols = [c for c in cols if c.endswith(PCT_SUFFIX) and c not in ID_COLS]
    for col_name in pct_cols:
        try:
            series = pd.to_numeric(df[col_name], errors="coerce")
            mask = series.notna() & ((series < 0) | (series > 1))
            out = mask.sum()
            if out > 0:
                sample_cols = ["naam_gebied", col_name] if "naam_gebied" in cols else [col_name]
                sample = df.loc[mask, sample_cols].head(3)
                sample_list = [(row["naam_gebied"], round(row[col_name], 3))
                               for _, row in sample.iterrows()]
                print(f"    [!]  {col_name:<45} {out} waarden buiten [0,1]  "
                      f"(bijv. {sample_list})")
        except Exception:
            pass

    # 2b. Index-scores: verwacht [0, 200]
    idx_cols = [c for c in cols if c.lower() in INDEX_COLS_PATTERN]
    for col_name in idx_cols:
        try:
            series = pd.to_numeric(df[col_name], errors="coerce")
            mask = series.notna() & ((series < 0) | (series > 200))
            out = mask.sum()
            if out > 0:
                print(f"    [!]  {col_name:<45} {out} waarden buiten [0,200]")
        except Exception:
            pass

    # 2c. Numerieke outliers via IQR
    num_cols = [
        c for c in cols
        if c not in ID_COLS + ["jaar"]
        and not c.endswith(PCT_SUFFIX)
        and pd.api.types.is_numeric_dtype(df[c])
    ]

    outlier_totaal = 0
    for col_name in num_cols:
        try:
            series = pd.to_numeric(df[col_name], errors="coerce").dropna()
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            out = ((series < (q1 - 3 * iqr)) | (series > (q3 + 3 * iqr))).sum()
            if out > 0:
                outlier_totaal += out
                print(f"    [!]  {col_name:<45} {out} extreme outliers (3xIQR)")
        except Exception:
            pass

    if outlier_totaal == 0 and not pct_cols and not idx_cols:
        print("    [OK]  Geen validiteitsproblemen gevonden")
    elif outlier_totaal == 0:
        print("    [OK]  Geen outliers (3xIQR) gevonden")


# ─────────────────────────────────────────────────────────
# 3. CONSISTENTIE
# ─────────────────────────────────────────────────────────
def check_consistentie_cross_sheets(dfs: dict) -> None:
    """
    Controleer of hetzelfde gebied (buurt85) in verschillende
    jaarssheets van hetzelfde type dezelfde naam_gebied heeft.
    """
    print("\n  Cross-sheet consistentie: naam_gebied vs buurt85")

    for label, sheets in [("SI", SI_SHEETS), ("FI-subj", FI_SUBJ_SHEETS),
                           ("FI-obj", FI_OBJ_SHEETS), ("VI", VI_SHEETS)]:
        available = [s for s in sheets if s in dfs]
        if len(available) < 2:
            continue

        # Check if required columns exist
        required_cols = ["buurt85", "naam_gebied", "jaar"]
        available = [s for s in available if all(c in dfs[s].columns for c in required_cols)]
        if len(available) < 2:
            continue

        frames = []
        for s in available:
            subset = dfs[s][["buurt85", "naam_gebied", "jaar"]].drop_duplicates(
                subset=["buurt85", "naam_gebied"]
            )
            frames.append(subset)
        combined = pd.concat(frames, ignore_index=True)

        inconsistent = (
            combined.groupby("buurt85")["naam_gebied"]
            .nunique()
            .reset_index(name="unieke_namen")
        )
        inconsistent = inconsistent[inconsistent["unieke_namen"] > 1]

        cnt = len(inconsistent)
        if cnt > 0:
            print(f"    [!]  [{label}]  {cnt} buurt85-codes met wisselende naam_gebied:")
            print(inconsistent.head(10).to_string(index=False))
        else:
            print(f"    [OK]  [{label}]  naam_gebied consistent over alle jaren")

    # Controleer of wijknr en buurt85 altijd dezelfde combinatie vormen
    print("\n  Consistentie wijknr ↔ buurt85 (per sheet-type)")
    for label, sheets in [("SI", SI_SHEETS), ("VI", VI_SHEETS)]:
        available = [s for s in sheets if s in dfs]
        if not available:
            continue

        # Check if required columns exist
        available = [s for s in available if all(c in dfs[s].columns for c in ["wijknr", "buurt85"])]
        if not available:
            continue

        frames = [dfs[s][["wijknr", "buurt85"]].drop_duplicates() for s in available]
        combined = pd.concat(frames, ignore_index=True)

        conflict = (
            combined.groupby("buurt85")["wijknr"]
            .nunique()
            .reset_index(name="unieke_wijknrs")
        )
        conflict = conflict[conflict["unieke_wijknrs"] > 1]

        cnt = len(conflict)
        if cnt > 0:
            print(f"    [!]  [{label}]  {cnt} buurt85-codes met meerdere wijknrs")
            print(conflict.head(5).to_string(index=False))
        else:
            print(f"    [OK]  [{label}]  wijknr <-> buurt85 consistent")


# ─────────────────────────────────────────────────────────
# 4. DUPLICATIE
# ─────────────────────────────────────────────────────────
def check_duplicatie(df: pd.DataFrame, sheet_name: str) -> None:
    total = len(df)
    print(f"\n  Sheet: {sheet_name}  ({total} rijen)")

    cols = df.columns.tolist()

    # Exacte duplicaten
    exact = df.duplicated().sum()
    if exact > 0:
        print(f"    [!]  Exacte duplicaten (alle kolommen): {exact}")
    else:
        print(f"    [OK]  Geen exacte duplicaten")

    # Duplicaten op business key: buurt85
    if "buurt85" in cols:
        key_dupes = df.duplicated(subset=["buurt85"]).sum()
        if key_dupes > 0:
            print(f"    [!]  Dubbele buurt85-codes: {key_dupes}")
            counts = (
                df.groupby("buurt85").size()
                .reset_index(name="count")
                .query("count > 1")
                .sort_values("count", ascending=False)
            )
            print(counts.head(10).to_string(index=False))
        else:
            print(f"    [OK]  Elke buurt85-code komt precies 1x voor")

    # Duplicaten op naam_gebied + jaar
    if "naam_gebied" in cols and "jaar" in cols:
        name_dupes = df.duplicated(subset=["naam_gebied", "jaar"]).sum()
        if name_dupes > 0:
            print(f"    [!]  Dubbele naam_gebied+jaar combinaties: {name_dupes}")
        else:
            print(f"    [OK]  Elke naam_gebied+jaar combinatie is uniek")


# ─────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("=" * 70)
    print("  WIJKPROFIEL ROTTERDAM  –  DATA QUALITY RAPPORT")
    print("=" * 70)

    # Laad alle sheets
    print("\nExcel inladen...")
    dfs = {}
    for sheet in ALL_DATA_SHEETS:
        try:
            dfs[sheet] = load_sheet(EXCEL_PATH, sheet)
            print(f"  [OK]  {sheet}")
        except Exception as e:
            print(f"  [FOUT]  {sheet}: {e}")

    # ── 1. COMPLEETHEID ──────────────────────────────────
    print("\n" + "=" * 70)
    print("1. COMPLEETHEID  –  Missende waarden per sheet")
    print("=" * 70)
    for sheet, df in dfs.items():
        check_compleetheid(df, sheet)

    # ── 2. VALIDITEIT ────────────────────────────────────
    print("\n" + "=" * 70)
    print("2. VALIDITEIT  –  Bereik- en outlier-controles")
    print("=" * 70)
    for sheet, df in dfs.items():
        check_validiteit(df, sheet)

    # ── 3. CONSISTENTIE ──────────────────────────────────
    print("\n" + "=" * 70)
    print("3. CONSISTENTIE  –  Cross-sheet controles")
    print("=" * 70)
    check_consistentie_cross_sheets(dfs)

    # ── 4. DUPLICATIE ────────────────────────────────────
    print("\n" + "=" * 70)
    print("4. DUPLICATIE  –  Dubbele rijen en sleutels")
    print("=" * 70)
    for sheet, df in dfs.items():
        check_duplicatie(df, sheet)

    print("\n" + "=" * 70)
    print("  Data quality check voltooid")
    print("=" * 70)